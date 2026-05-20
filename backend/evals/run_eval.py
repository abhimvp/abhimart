"""Local Stage 4 eval runner.

First goal:
- Load golden examples from JSONL.
- Run the real LangGraph agent.
- Capture final answer text.
- Capture tool calls.
- Print raw-ish event shape so we understand what LangGraph emits.

This is intentionally not scoring yet.
We inspect first, then write evaluators.
"""

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any

# Allows this script to import app.* when run as:
#   uv run python evals/run_eval.py
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from langgraph.checkpoint.memory import InMemorySaver

from app.agents.customer_support.graph import build_graph

DATASET_PATH = Path(__file__).parent / "datasets" / "stage4_golden.jsonl"
RESULTS_DIR = Path(__file__).parent / "results"
DEFAULT_OUTPUT_PATH = RESULTS_DIR / "stage4_baseline.jsonl"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load one JSON object per line.

    Blank lines are ignored so the file is easier to edit manually.
    """
    examples = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                examples.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {path}"
                ) from exc

    return examples


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Append one eval result as JSONL.

    This preserves partial progress if a model call fails midway.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")


def extract_text_from_chunk(content: Any) -> str:
    """Normalize Gemini/LangChain streamed content into plain text.

    Sometimes content is a string.
    Sometimes it is a list of content parts.
    We keep this small and inspect-friendly for now.
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []

        for item in content:
            if isinstance(item, dict):
                parts.append(item.get("text", ""))
            else:
                parts.append(str(item))

        return "".join(parts)

    return ""


def is_top_level_agent_llm_event(event: dict[str, Any]) -> bool:
    """Return True for customer-facing LLM streams from the graph's llm node."""
    metadata = event.get("metadata") or {}
    return metadata.get("langgraph_node") == "llm"


def extract_direct_llm_text(event: dict[str, Any]) -> str:
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


async def run_one_example(graph: Any, example: dict[str, Any]) -> dict[str, Any]:
    """Run one dataset example through the real agent graph."""
    message = example["inputs"]["message"]

    # New thread per eval example keeps memory isolated.
    # Otherwise one eval case can pollute the next case.
    thread_id = f"eval-{example['id']}-{uuid.uuid4()}"

    config = {"configurable": {"thread_id": thread_id}}
    inputs = {"messages": [{"role": "user", "content": message}]}

    final_answer_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []
    event_samples: list[dict[str, Any]] = []

    async for event in graph.astream_events(inputs, config=config, version="v2"):
        event_name = event.get("event")
        event_data = event.get("data", {})

        # Keep a few lightweight samples so we can inspect event shape.
        # Do not store everything forever; real traces can get noisy.
        if len(event_samples) < 12:
            event_samples.append(
                {
                    "event": event_name,
                    "name": event.get("name"),
                    "data_keys": (
                        list(event_data.keys()) if isinstance(event_data, dict) else []
                    ),
                }
            )

        if event_name == "on_tool_start":
            tool_calls.append(
                {
                    "name": event.get("name"),
                    "input": event_data.get("input"),
                }
            )

        direct_text = extract_direct_llm_text(event)
        if direct_text and not final_answer_parts:
            final_answer_parts.append(direct_text)
            continue

        if event_name == "on_chat_model_stream":
            if not is_top_level_agent_llm_event(event):
                continue

            chunk = event_data.get("chunk")
            if chunk is None:
                continue

            text = extract_text_from_chunk(chunk.content)
            if text:
                final_answer_parts.append(text)

    return {
        "id": example["id"],
        "input": message,
        "expected": example["expected"],
        "actual": {
            "final_answer": "".join(final_answer_parts).strip(),
            "tool_calls": tool_calls,
        },
        "debug": {
            "event_samples": event_samples,
        },
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run AbhiMart Stage 4 evals.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only run the first N examples.",
    )
    parser.add_argument(
        "--start",
        type=int,
        default=0,
        help="Start from this zero-based example index.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Seconds to wait between examples to reduce rate-limit pressure.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=DATASET_PATH,
        help="JSONL dataset to run.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to append JSONL eval results.",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Delete the output file before running.",
    )

    args = parser.parse_args()

    if args.fresh and args.output.exists():
        args.output.unlink()

    examples = load_jsonl(args.dataset)

    if args.start:
        examples = examples[args.start :]

    if args.limit is not None:
        examples = examples[: args.limit]

    graph = build_graph(checkpointer=InMemorySaver())

    print(f"Loaded {len(examples)} eval examples from {args.dataset}")
    print()

    for index, example in enumerate(examples, start=1):
        try:
            result = await run_one_example(graph, example)
            append_jsonl(args.output, result)

        except Exception as exc:
            result = {
                "id": example["id"],
                "input": example["inputs"]["message"],
                "expected": example["expected"],
                "actual": None,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            }

            append_jsonl(args.output, result)

            print("=" * 100)
            print(f"ID: {example['id']}")
            print("ERROR:")
            print(f"{type(exc).__name__}: {exc}")
            print()
            continue

        print("=" * 100)
        print(f"ID: {result['id']}")
        print(f"INPUT: {result['input']}")
        print()
        print("EXPECTED:")
        print(json.dumps(result["expected"], indent=2))
        print()
        print("ACTUAL TOOL CALLS:")
        print(json.dumps(result["actual"]["tool_calls"], indent=2))
        print()
        print("ACTUAL FINAL ANSWER:")
        print(result["actual"]["final_answer"])
        print()
        print("EVENT SAMPLES:")
        print(json.dumps(result["debug"]["event_samples"], indent=2))
        print()

        if index < len(examples):
            await asyncio.sleep(args.delay)


if __name__ == "__main__":
    asyncio.run(main())
