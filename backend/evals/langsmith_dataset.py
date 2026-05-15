"""Sync AbhiMart golden eval examples to a LangSmith dataset.

This does not run the agent.
It only uploads local JSONL examples into LangSmith so future experiments
can run against a versioned dataset.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from langsmith import Client

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import get_settings

DATASET_PATH = Path(__file__).parent / "datasets" / "stage4_golden.jsonl"
DEFAULT_DATASET_NAME = "abhimart-stage4-golden"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
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


def get_or_create_dataset(client: Client, dataset_name: str):
    existing = list(client.list_datasets(dataset_name=dataset_name))

    if existing:
        dataset = existing[0]
        print(f"Using existing LangSmith dataset: {dataset.name}")
        return dataset

    dataset = client.create_dataset(
        dataset_name=dataset_name,
        description=(
            "AbhiMart Stage 4 golden eval dataset covering policy/RAG, "
            "order lookup, product lookup, and privacy/safety behaviors."
        ),
    )
    print(f"Created LangSmith dataset: {dataset.name}")
    return dataset


def sync_examples(
    client: Client,
    dataset_name: str,
    examples: list[dict[str, Any]],
    *,
    replace: bool,
) -> None:
    if replace:
        existing_examples = list(client.list_examples(dataset_name=dataset_name))

        for example in existing_examples:
            client.delete_example(example.id)

        print(f"Deleted {len(existing_examples)} existing example(s).")

    langsmith_examples = []

    for example in examples:
        expected = example["expected"]

        langsmith_examples.append(
            {
                "inputs": example["inputs"],
                "outputs": expected,
                "metadata": {
                    "id": example["id"],
                    "category": expected.get("category", "unknown"),
                },
            }
        )

    client.create_examples(
        dataset_name=dataset_name,
        examples=langsmith_examples,
    )

    print(f"Uploaded {len(langsmith_examples)} example(s).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync AbhiMart golden eval examples to LangSmith."
    )
    parser.add_argument(
        "--dataset-name",
        default=DEFAULT_DATASET_NAME,
        help="LangSmith dataset name.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Delete existing examples in the dataset before uploading.",
    )
    args = parser.parse_args()

    settings = get_settings()

    if not settings.LANGSMITH_API_KEY:
        raise RuntimeError("LANGSMITH_API_KEY is not set in .env")

    client = Client(
        api_key=settings.LANGSMITH_API_KEY,
        api_url=settings.LANGSMITH_ENDPOINT,
    )

    examples = load_jsonl(DATASET_PATH)

    get_or_create_dataset(client, args.dataset_name)
    sync_examples(
        client,
        args.dataset_name,
        examples,
        replace=args.replace,
    )


if __name__ == "__main__":
    main()
