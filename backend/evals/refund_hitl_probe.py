"""Probe the refund human-in-the-loop pause/resume flow.

This is intentionally separate from the normal answer scorer because the first
run should pause instead of producing a final assistant answer.
"""

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.agents.customer_support.graph import build_graph


DEFAULT_MESSAGE = (
    "My email is rohit@example.com. Please start a refund for my MacBook order."
)


def _jsonable_interrupt(value):
    if hasattr(value, "value"):
        return _jsonable_interrupt(value.value)
    if isinstance(value, dict):
        return {key: _jsonable_interrupt(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable_interrupt(item) for item in value]
    return value


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--message", default=DEFAULT_MESSAGE)
    parser.add_argument("--session-id", default=f"refund-hitl-{uuid.uuid4()}")
    parser.add_argument("--approve", action="store_true")
    args = parser.parse_args()

    config = {"configurable": {"thread_id": args.session_id}}
    inputs = {"messages": [{"role": "user", "content": args.message}]}

    checkpointer = InMemorySaver()
    graph = build_graph(checkpointer)

    paused = await graph.ainvoke(inputs, config=config)
    interrupts = paused.get("__interrupt__", ())
    if not interrupts:
        print("No interrupt was raised.")
        print(paused)
        return

    print("INTERRUPT:")
    print(json.dumps(_jsonable_interrupt(interrupts), indent=2))

    resumed = await graph.ainvoke(
        Command(
            resume={
                "approved": args.approve,
                "reviewer_note": "Probe approval" if args.approve else "Probe rejection",
            }
        ),
        config=config,
    )
    print("\nRESUMED FINAL MESSAGE:")
    print(resumed["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(main())
