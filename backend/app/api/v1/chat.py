"""Chat API route — Stage 1.

POST /v1/chat
- Accepts a user message
- Runs it through the LangGraph agent
- Streams the response back token-by-token via SSE

SSE (Server-Sent Events) format — each chunk looks like:
    data: hello\n\n
    data:  world\n\n
    data: [DONE]\n\n

The browser reads these chunks as they arrive and appends
them to the UI — that's how streaming chat works.

Conversation memory: stored in-process as a dict keyed by session_id.
Not durable — server restart loses history. Stage 2 replaces this
with LangGraph's Postgres checkpointer.

Chat API route — Stage 2.

POST /v1/chat
- Accepts a user message + session_id
- Runs it through the LangGraph agent (Postgres-backed memory)
- Streams the response token-by-token via SSE
"""

import json
from time import perf_counter

import structlog
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.observability import get_tracer

router = APIRouter(prefix="/chat", tags=["Chat"])
tracer = get_tracer(__name__)
logger = structlog.get_logger()


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


async def event_stream(graph, message: str, session_id: str):
    config = {"configurable": {"thread_id": session_id}}
    inputs = {"messages": [{"role": "user", "content": message}]}
    start = perf_counter()
    chunk_count = 0

    with tracer.start_as_current_span("chat.agent_stream") as span:
        span.set_attribute("abhimart.session_id", session_id)
        span.set_attribute("abhimart.message_length", len(message))

        logger.info(
            "chat_stream_started",
            session_id=session_id,
            message_length=len(message),
        )

        try:
            async for event in graph.astream_events(inputs, config=config, version="v2"):
                if event["event"] == "on_chat_model_stream":
                    metadata = event.get("metadata") or {}
                    if metadata.get("langgraph_node") != "llm":
                        continue

                    chunk = event["data"]["chunk"]
                    content = chunk.content

                    if isinstance(content, list):
                        text = "".join(
                            part.get("text", "")
                            if isinstance(part, dict)
                            else str(part)
                            for part in content
                        )
                    else:
                        text = content

                    if text:
                        chunk_count += 1
                        yield f"data: {json.dumps({'text': text})}\n\n"
        except Exception:
            logger.exception(
                "chat_stream_failed",
                session_id=session_id,
                duration_ms=round((perf_counter() - start) * 1000, 2),
                chunk_count=chunk_count,
            )
            raise

        logger.info(
            "chat_stream_completed",
            session_id=session_id,
            duration_ms=round((perf_counter() - start) * 1000, 2),
            chunk_count=chunk_count,
        )

    yield "data: [DONE]\n\n"


@router.post("")
async def chat(request: ChatRequest, req: Request):
    graph = req.app.state.graph
    with tracer.start_as_current_span("chat.request") as span:
        span.set_attribute("abhimart.session_id", request.session_id)
        span.set_attribute("abhimart.message_length", len(request.message))
        logger.info(
            "chat_request_received",
            session_id=request.session_id,
            message_length=len(request.message),
        )
        return StreamingResponse(
            event_stream(graph, request.message, request.session_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    
@router.get("/history/{session_id}")
async def get_history(session_id: str, req: Request):
    graph = req.app.state.graph
    config = {"configurable": {"thread_id": session_id}}
    with tracer.start_as_current_span("chat.history") as span:
        span.set_attribute("abhimart.session_id", session_id)
        state = await graph.aget_state(config)
    return {
        "messages": [
            {"role": m.type, "content": m.content}
            for m in state.values["messages"]
        ]
    }
