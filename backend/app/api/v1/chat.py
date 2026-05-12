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
"""

"""Chat API route — Stage 1."""

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.customer_support.graph import graph

router = APIRouter(prefix="/chat", tags=["Chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


async def event_stream(message: str, session_id: str):
    # thread_id tells LangGraph which conversation to resume
    config = {"configurable": {"thread_id": session_id}}

    # Only pass the NEW message — LangGraph loads prior history automatically
    inputs = {"messages": [{"role": "user", "content": message}]}

    async for event in graph.astream_events(inputs, config=config, version="v2"):
        if event["event"] == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            content = chunk.content

            if isinstance(content, list):
                text = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
            else:
                text = content

            if text:
                yield f"data: {json.dumps({'text': text})}\n\n"

    yield "data: [DONE]\n\n"


@router.post("")
async def chat(request: ChatRequest):
    return StreamingResponse(
        event_stream(request.message, request.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
