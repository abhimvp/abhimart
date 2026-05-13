"""Score Stage 4 eval results with deterministic evaluators.

This script reads JSONL output from run_eval.py and checks objective behavior:
- required tools were called
- forbidden tools were not called
- required source docs appeared
- required facts/phrases appeared
- missing-info questions were asked
- simple stance expectations were met

Run:
    uv run python evals/score_results.py

Or:
    uv run python evals/score_results.py --input evals/results/stage4_baseline.jsonl
"""

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_INPUT_PATH = Path(__file__).parent / "results" / "stage4_baseline.jsonl"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []

    if not path.exists():
        raise FileNotFoundError(
            f"No results file found at {path}. Run evals/run_eval.py first."
        )

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


def normalize(text: str) -> str:
    return text.lower()


def get_tool_names(row: dict[str, Any]) -> list[str]:
    actual = row.get("actual") or {}
    tool_calls = actual.get("tool_calls") or []

    return [
        call.get("name", "")
        for call in tool_calls
        if isinstance(call, dict) and call.get("name")
    ]


def get_final_answer(row: dict[str, Any]) -> str:
    actual = row.get("actual") or {}
    return actual.get("final_answer") or ""


def check_required_tools(row: dict[str, Any]) -> tuple[bool, str]:
    expected = row["expected"]
    required = expected.get("must_use_tools", [])
    actual_tools = get_tool_names(row)

    missing = [tool for tool in required if tool not in actual_tools]

    if missing:
        return False, f"Missing required tools: {missing}. Actual tools: {actual_tools}"

    return True, "Required tools were used."


def check_forbidden_tools(row: dict[str, Any]) -> tuple[bool, str]:
    expected = row["expected"]
    forbidden = expected.get("must_not_use_tools", [])
    actual_tools = get_tool_names(row)

    used_forbidden = [tool for tool in forbidden if tool in actual_tools]

    if used_forbidden:
        return (
            False,
            f"Forbidden tools were used: {used_forbidden}. Actual tools: {actual_tools}",
        )

    return True, "Forbidden tools were not used."


def check_expected_sources(row: dict[str, Any]) -> tuple[bool, str]:
    expected = row["expected"]

    if not expected.get("must_cite_sources"):
        return True, "No source citation required."

    answer = get_final_answer(row)
    answer_normalized = normalize(answer)
    expected_sources = expected.get("expected_sources", [])

    missing = [
        source
        for source in expected_sources
        if normalize(source) not in answer_normalized
    ]

    if missing:
        return False, f"Missing expected source citations: {missing}"

    return True, "Expected source citations appeared."


def check_must_mention(row: dict[str, Any]) -> tuple[bool, str]:
    expected = row["expected"]
    required_phrases = expected.get("must_mention", [])

    if not required_phrases:
        return True, "No required phrases."

    answer = normalize(get_final_answer(row))
    missing = [phrase for phrase in required_phrases if normalize(phrase) not in answer]

    if missing:
        return False, f"Missing required phrases: {missing}"

    return True, "Required phrases appeared."


def check_must_mention_any(row: dict[str, Any]) -> tuple[bool, str]:
    expected = row["expected"]
    phrase_groups = expected.get("must_mention_any", [])

    if not phrase_groups:
        return True, "No phrase groups required."

    answer = normalize(get_final_answer(row))
    missing_groups = []

    for group in phrase_groups:
        if not any(normalize(phrase) in answer for phrase in group):
            missing_groups.append(group)

    if missing_groups:
        return False, f"Missing one phrase from each group: {missing_groups}"

    return True, "Required phrase groups appeared."


def check_must_ask_for(row: dict[str, Any]) -> tuple[bool, str]:
    expected = row["expected"]
    required_questions = expected.get("must_ask_for", [])

    if not required_questions:
        return True, "No required clarification."

    answer = normalize(get_final_answer(row))
    missing = [
        phrase for phrase in required_questions if normalize(phrase) not in answer
    ]

    if missing:
        return False, f"Did not ask for required info: {missing}"

    return True, "Asked for required info."


def check_expected_stance(row: dict[str, Any]) -> tuple[bool, str]:
    expected = row["expected"]
    stance = expected.get("expected_stance")

    if not stance:
        return True, "No stance expectation."

    answer = normalize(get_final_answer(row)).strip()

    if stance == "likely_not_returnable":
        contextual_restrictive_markers = [
            "because you mentioned the headphones have been opened and used",
            "because you mentioned that you have opened and used",
            "because you mentioned you have opened and used",
            "because you mentioned that you used",
            "because you mentioned you used",
            "since you mentioned that you have already used",
            "since you mentioned that you have used",
            "since you mentioned you have already used",
            "since you mentioned you have used",
            "since you mentioned that you used",
            "since you mentioned you used",
            "since you have used",
        ]

        permissive_markers = [
            "may be able to return",
            "yes, according",
            "yes, you can return",
            "yes you can return",
            "you can return",
            "eligible for return",
            "eligible for a return",
            "should be eligible",
            "you should be eligible",
        ]

        restrictive_markers = [
            "probably not",
            "may not be eligible",
            "not eligible",
            "cannot return",
            "can't return",
            "unlikely to be accepted",
            "may be rejected",
        ]

        has_permissive = any(marker in answer for marker in permissive_markers)
        has_restrictive = any(marker in answer for marker in restrictive_markers)
        has_contextual_restriction = (
            any(marker in answer for marker in contextual_restrictive_markers)
            and has_restrictive
        )

        if has_contextual_restriction:
            return True, "Answer tied the used-item condition to return risk."

        if has_permissive:
            return (
                False,
                "Expected likely-not-returnable stance, but answer was permissive.",
            )

        if has_restrictive:
            return True, "Answer matched likely-not-returnable stance."

        return False, "Expected likely-not-returnable stance, but stance was unclear."

    return True, f"Unknown stance expectation skipped: {stance}"


EVALUATORS = [
    ("required_tools", check_required_tools),
    ("forbidden_tools", check_forbidden_tools),
    ("expected_sources", check_expected_sources),
    ("must_mention", check_must_mention),
    ("must_mention_any", check_must_mention_any),
    ("must_ask_for", check_must_ask_for),
    ("expected_stance", check_expected_stance),
]


def score_row(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("error"):
        return {
            "id": row["id"],
            "passed": False,
            "checks": [
                {
                    "name": "run_error",
                    "passed": False,
                    "comment": row["error"]["message"],
                }
            ],
        }

    checks = []

    for name, evaluator in EVALUATORS:
        passed, comment = evaluator(row)
        checks.append(
            {
                "name": name,
                "passed": passed,
                "comment": comment,
            }
        )

    return {
        "id": row["id"],
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Score AbhiMart eval results.")
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_PATH,
        help="JSONL results file produced by evals/run_eval.py",
    )
    args = parser.parse_args()

    rows = load_jsonl(args.input)
    scores = [score_row(row) for row in rows]

    passed_count = sum(1 for score in scores if score["passed"])
    total_count = len(scores)

    print(f"Scored {total_count} eval result(s) from {args.input}")
    print(f"Passed: {passed_count}/{total_count}")
    print()

    for score in scores:
        status = "PASS" if score["passed"] else "FAIL"
        print("=" * 100)
        print(f"{status}: {score['id']}")

        for check in score["checks"]:
            check_status = "PASS" if check["passed"] else "FAIL"
            print(f"  [{check_status}] {check['name']}: {check['comment']}")

        print()


if __name__ == "__main__":
    main()
