"""Run AbhiMart agent evals as a LangSmith experiment.

This runs the real LangGraph agent against the LangSmith dataset created by
langsmith_dataset.py and attaches deterministic evaluators.
"""

import asyncio
import argparse
import sys
import uuid
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langsmith import Client, aevaluate

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.agents.customer_support.graph import build_graph
from app.config import get_settings
from evals.score_results import score_row

DEFAULT_DATASET_NAME = "abhimart-stage4-golden"
DEFAULT_EXPERIMENT_PREFIX = "abhimart-stage4-local-agent"


def extract_text_from_chunk(content: Any) -> str:
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


async def run_agent(inputs: dict[str, Any]) -> dict[str, Any]:
    """LangSmith target function.

    LangSmith passes each dataset example's `inputs` here.
    We return outputs that match our local scorer shape.
    """
    graph = build_graph(checkpointer=InMemorySaver())

    message = inputs["message"]
    thread_id = f"langsmith-eval-{uuid.uuid4()}"

    config = {"configurable": {"thread_id": thread_id}}
    graph_inputs = {"messages": [{"role": "user", "content": message}]}

    final_answer_parts: list[str] = []
    tool_calls: list[dict[str, Any]] = []

    async for event in graph.astream_events(
        graph_inputs,
        config=config,
        version="v2",
    ):
        event_name = event.get("event")
        event_data = event.get("data", {})

        if event_name == "on_tool_start":
            tool_calls.append(
                {
                    "name": event.get("name"),
                    "input": event_data.get("input"),
                }
            )

        if event_name == "on_chat_model_stream":
            chunk = event_data.get("chunk")
            if chunk is None:
                continue

            text = extract_text_from_chunk(chunk.content)
            if text:
                final_answer_parts.append(text)

    return {
        "final_answer": "".join(final_answer_parts).strip(),
        "tool_calls": tool_calls,
    }


def deterministic_behavior_evaluator(run, example) -> dict[str, Any]:
    """Evaluate one LangSmith run using the same local scoring logic.

    LangSmith passes:
    - run.outputs: what run_agent returned
    - example.outputs: expected behavior from the dataset
    """
    run_outputs = run.outputs if hasattr(run, "outputs") else run.get("outputs", {})
    example_inputs = (
        example.inputs if hasattr(example, "inputs") else example.get("inputs", {})
    )
    example_outputs = (
        example.outputs if hasattr(example, "outputs") else example.get("outputs", {})
    )
    example_metadata = (
        example.metadata
        if hasattr(example, "metadata")
        else example.get("metadata", {})
    )

    row = {
        "id": example_metadata.get("id", "unknown"),
        "input": example_inputs.get("message", ""),
        "expected": example_outputs,
        "actual": run_outputs,
    }

    score = score_row(row)

    failed_checks = [check["name"] for check in score["checks"] if not check["passed"]]

    if failed_checks:
        comment = f"Failed checks: {failed_checks}"
    else:
        comment = "All deterministic behavior checks passed."

    return {
        "key": "deterministic_behavior",
        "score": 1 if score["passed"] else 0,
        "comment": comment,
    }


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run AbhiMart Stage 4 evals in LangSmith."
    )
    parser.add_argument(
        "--dataset-name",
        default=DEFAULT_DATASET_NAME,
        help="LangSmith dataset name.",
    )
    parser.add_argument(
        "--experiment-prefix",
        default=DEFAULT_EXPERIMENT_PREFIX,
        help="Experiment prefix shown in LangSmith.",
    )
    args = parser.parse_args()

    settings = get_settings()

    if not settings.LANGSMITH_API_KEY:
        raise RuntimeError("LANGSMITH_API_KEY is not set in .env")

    client = Client(
        api_key=settings.LANGSMITH_API_KEY,
        api_url=settings.LANGSMITH_ENDPOINT,
    )

    results = await aevaluate(
        run_agent,
        data=args.dataset_name,
        evaluators=[deterministic_behavior_evaluator],
        experiment_prefix=args.experiment_prefix,
        client=client,
        max_concurrency=1,
    )

    print(results)


if __name__ == "__main__":
    asyncio.run(main())
