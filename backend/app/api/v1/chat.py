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
from langgraph.types import Command
from pydantic import BaseModel

from app.observability import get_tracer
from app.observability_metrics import (
    record_chat_request,
    record_chat_stream,
    record_error,
)

router = APIRouter(prefix="/chat", tags=["Chat"])
tracer = get_tracer(__name__)
logger = structlog.get_logger()


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResumeRequest(BaseModel):
    session_id: str
    approved: bool
    reviewer_note: str | None = None


def extract_direct_llm_text(event: dict) -> str:
    """Extract text returned directly by the llm graph node.

    Guardrails can return an AIMessage without invoking the chat model. In that
    path LangGraph emits an on_chain_stream event, not token stream events.
    """
    if event.get("event") != "on_chain_stream" or event.get("name") != "llm":
        return ""

    chunk = (event.get("data") or {}).get("chunk")
    if not isinstance(chunk, dict):
        return ""

    messages = chunk.get("messages") or []
    if not messages:
        return ""

    content = getattr(messages[-1], "content", "")
    return content if isinstance(content, str) else ""


def _serialize_interrupt(value):
    if hasattr(value, "value"):
        return _serialize_interrupt(value.value)
    if isinstance(value, dict):
        return {key: _serialize_interrupt(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize_interrupt(item) for item in value]
    return value


def extract_interrupt_payload(event: dict):
    data = event.get("data") or {}
    candidates = []
    if isinstance(data, dict):
        candidates.extend([data.get("chunk"), data.get("output")])

    for candidate in candidates:
        if isinstance(candidate, dict) and "__interrupt__" in candidate:
            return _serialize_interrupt(candidate["__interrupt__"])
    return None


async def event_stream(graph, graph_input, session_id: str, message_for_metrics: str):
    config = {"configurable": {"thread_id": session_id}}
    start = perf_counter()
    chunk_count = 0
    interrupt_sent = False

    with tracer.start_as_current_span("chat.agent_stream") as span:
        span.set_attribute("abhimart.session_id", session_id)
        span.set_attribute("abhimart.message_length", len(message_for_metrics))

        logger.info(
            "chat_stream_started",
            session_id=session_id,
            message_length=len(message_for_metrics),
        )

        try:
            async for event in graph.astream_events(
                graph_input,
                config=config,
                version="v2",
            ):
                interrupt_payload = extract_interrupt_payload(event)
                if interrupt_payload and not interrupt_sent:
                    interrupt_sent = True
                    chunk_count += 1
                    yield (
                        "data: "
                        f"{json.dumps({'type': 'interrupt', 'interrupt': interrupt_payload})}"
                        "\n\n"
                    )
                    continue

                direct_text = extract_direct_llm_text(event)
                if direct_text and chunk_count == 0:
                    chunk_count += 1
                    yield f"data: {json.dumps({'text': direct_text})}\n\n"
                    continue

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
            duration_ms = round((perf_counter() - start) * 1000, 2)
            record_chat_stream(duration_ms, status="error")
            record_error(area="chat_stream")
            logger.exception(
                "chat_stream_failed",
                session_id=session_id,
                duration_ms=duration_ms,
                chunk_count=chunk_count,
            )
            raise

        duration_ms = round((perf_counter() - start) * 1000, 2)
        record_chat_stream(duration_ms, status="success")
        logger.info(
            "chat_stream_completed",
            session_id=session_id,
            duration_ms=duration_ms,
            chunk_count=chunk_count,
        )

    yield "data: [DONE]\n\n"


@router.post("")
async def chat(request: ChatRequest, req: Request):
    graph = req.app.state.graph
    inputs = {"messages": [{"role": "user", "content": request.message}]}
    with tracer.start_as_current_span("chat.request") as span:
        span.set_attribute("abhimart.session_id", request.session_id)
        span.set_attribute("abhimart.message_length", len(request.message))
        logger.info(
            "chat_request_received",
            session_id=request.session_id,
            message_length=len(request.message),
        )
        record_chat_request()
        return StreamingResponse(
            event_stream(graph, inputs, request.session_id, request.message),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )


@router.post("/resume")
async def resume_chat(request: ChatResumeRequest, req: Request):
    graph = req.app.state.graph
    resume_value = {
        "approved": request.approved,
        "reviewer_note": request.reviewer_note or "",
    }
    with tracer.start_as_current_span("chat.resume") as span:
        span.set_attribute("abhimart.session_id", request.session_id)
        span.set_attribute("abhimart.approved", request.approved)
        logger.info(
            "chat_resume_received",
            session_id=request.session_id,
            approved=request.approved,
        )
        return StreamingResponse(
            event_stream(
                graph,
                Command(resume=resume_value),
                request.session_id,
                "resume",
            ),
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
