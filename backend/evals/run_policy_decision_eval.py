"""Evaluate structured return-policy eligibility decisions.

This evaluates the policy classifier as a subcomponent, separate from the full
customer-support agent. Subcomponent evals help isolate whether a failure came
from policy classification or final answer generation.

Run:
    uv run python evals/run_policy_decision_eval.py
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.agents.customer_support.policy import classify_return_eligibility

DATASET_PATH = Path(__file__).parent / "datasets" / "policy_decision_golden.jsonl"
POLICY_DOCS_DIR = BACKEND_DIR / "app" / "rag" / "docs"
RESULTS_DIR = Path(__file__).parent / "results"
DEFAULT_OUTPUT_PATH = RESULTS_DIR / "policy_decision_baseline.jsonl"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []

    with path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()

            if not line:
                continue

            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {path}"
                ) from exc

    return rows


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize(text: str) -> str:
    return text.lower().replace("–", "-").replace("—", "-").replace("’", "'")


def score_result(row: dict[str, Any]) -> dict[str, Any]:
    expected = row["expected"]
    actual = row.get("actual") or {}
    checks = []

    decision_passed = actual.get("decision") == expected.get("decision")
    checks.append(
        {
            "name": "decision",
            "passed": decision_passed,
            "comment": (
                f"Expected {expected.get('decision')}, " f"got {actual.get('decision')}"
            ),
        }
    )

    source_passed = actual.get("source") == row["inputs"].get("source")
    checks.append(
        {
            "name": "source",
            "passed": source_passed,
            "comment": (
                f"Expected {row['inputs'].get('source')}, "
                f"got {actual.get('source')}"
            ),
        }
    )

    reason = normalize(actual.get("reason", ""))
    missing_groups = []
    for group in expected.get("must_mention_any", []):
        if not any(normalize(phrase) in reason for phrase in group):
            missing_groups.append(group)

    checks.append(
        {
            "name": "reason_mentions",
            "passed": not missing_groups,
            "comment": (
                "Required reason phrase groups appeared."
                if not missing_groups
                else f"Missing one phrase from each group: {missing_groups}"
            ),
        }
    )

    return {
        "id": row["id"],
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }


async def run_one(example: dict[str, Any]) -> dict[str, Any]:
    source = example["inputs"]["source"]
    policy_text = (POLICY_DOCS_DIR / source).read_text(encoding="utf-8")

    decision = await classify_return_eligibility(
        customer_question=example["inputs"]["customer_question"],
        policy_text=policy_text,
        source=source,
    )

    return {
        "id": example["id"],
        "inputs": example["inputs"],
        "expected": example["expected"],
        "actual": decision.model_dump(),
    }


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run structured policy decision evals."
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Delete the output file before running.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write JSONL results.",
    )
    args = parser.parse_args()

    if args.fresh and args.output.exists():
        args.output.unlink()

    examples = load_jsonl(DATASET_PATH)
    scores = []

    for example in examples:
        result = await run_one(example)
        append_jsonl(args.output, result)
        score = score_result(result)
        scores.append(score)

        status = "PASS" if score["passed"] else "FAIL"
        print("=" * 100)
        print(f"{status}: {result['id']}")
        print(json.dumps(result["actual"], indent=2))
        for check in score["checks"]:
            check_status = "PASS" if check["passed"] else "FAIL"
            print(f"  [{check_status}] {check['name']}: {check['comment']}")
        print()

    passed_count = sum(1 for score in scores if score["passed"])
    print(f"Passed: {passed_count}/{len(scores)}")


if __name__ == "__main__":
    asyncio.run(main())
