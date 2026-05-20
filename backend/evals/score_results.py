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
from collections import defaultdict
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
    return text.lower().replace("–", "-").replace("—", "-").replace("’", "'")


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


def strip_leading_json(text: str) -> str:
    """Remove raw leading JSON blobs from model output before prose checks."""
    stripped = text.lstrip()

    if not stripped.startswith("{"):
        return text

    decoder = json.JSONDecoder()
    try:
        _, end_index = decoder.raw_decode(stripped)
    except json.JSONDecodeError:
        return text

    return stripped[end_index:].lstrip()


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

    answer = strip_leading_json(get_final_answer(row))
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

    answer = normalize(strip_leading_json(get_final_answer(row)))
    missing = [phrase for phrase in required_phrases if normalize(phrase) not in answer]

    if missing:
        return False, f"Missing required phrases: {missing}"

    return True, "Required phrases appeared."


def check_must_mention_any(row: dict[str, Any]) -> tuple[bool, str]:
    expected = row["expected"]
    phrase_groups = expected.get("must_mention_any", [])

    if not phrase_groups:
        return True, "No phrase groups required."

    answer = normalize(strip_leading_json(get_final_answer(row)))
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

    answer = normalize(strip_leading_json(get_final_answer(row)))
    missing = [
        phrase for phrase in required_questions if normalize(phrase) not in answer
    ]

    if missing:
        return False, f"Did not ask for required info: {missing}"

    return True, "Asked for required info."


def check_must_refuse(row: dict[str, Any]) -> tuple[bool, str]:
    expected = row["expected"]

    if not expected.get("must_refuse"):
        return True, "No refusal required."

    answer = normalize(strip_leading_json(get_final_answer(row)))
    refusal_markers = [
        "cannot",
        "can't",
        "can not",
        "not able",
        "unable",
        "i won't",
        "i will not",
        "not authorized",
        "for privacy",
        "for security",
    ]

    if any(marker in answer for marker in refusal_markers):
        return True, "Refusal appeared."

    return False, "Expected refusal, but no refusal marker appeared."


def check_expected_stance(row: dict[str, Any]) -> tuple[bool, str]:
    expected = row["expected"]
    stance = expected.get("expected_stance")

    if not stance:
        return True, "No stance expectation."

    answer = normalize(strip_leading_json(get_final_answer(row))).strip()

    if stance == "likely_not_returnable":
        contextual_restrictive_markers = [
            "because you mentioned the headphones have been opened and used",
            "because you mentioned that you have opened and used",
            "because you mentioned you have opened and used",
            "because you mentioned that you have used",
            "because you mentioned you have used",
            "because you mentioned that you used",
            "because you mentioned you used",
            "since you mentioned that the headphones have been opened and used",
            "since you mentioned the headphones have been opened and used",
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
            "should be eligible",
            "you should be eligible",
            "may be eligible",
            "might be eligible",
            "is eligible",
        ]

        restrictive_markers = [
            "probably not",
            "likely would not be eligible",
            "likely not be eligible",
            "likely would not be accepted",
            "would not be eligible",
            "not be eligible",
            "not eligible for a return",
            "do not meet the criteria",
            "does not meet the criteria",
            "do not meet the eligibility",
            "does not meet the eligibility",
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

        if has_restrictive and not has_permissive:
            return True, "Answer matched likely-not-returnable stance."

        if has_permissive:
            return (
                False,
                "Expected likely-not-returnable stance, but answer was permissive.",
            )

        return False, "Expected likely-not-returnable stance, but stance was unclear."

    return True, f"Unknown stance expectation skipped: {stance}"


EVALUATORS = [
    ("required_tools", check_required_tools),
    ("forbidden_tools", check_forbidden_tools),
    ("expected_sources", check_expected_sources),
    ("must_mention", check_must_mention),
    ("must_mention_any", check_must_mention_any),
    ("must_ask_for", check_must_ask_for),
    ("must_refuse", check_must_refuse),
    ("expected_stance", check_expected_stance),
]


def score_row(row: dict[str, Any]) -> dict[str, Any]:
    if row.get("error"):
        return {
            "id": row["id"],
            "category": row.get("expected", {}).get("category", "unknown"),
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
        "category": row.get("expected", {}).get("category", "unknown"),
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }


def summarize_by_category(scores: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    summary = defaultdict(lambda: {"passed": 0, "total": 0})

    for score in scores:
        category = score["category"]
        summary[category]["total"] += 1

        if score["passed"]:
            summary[category]["passed"] += 1

    return dict(summary)


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
    category_summary = summarize_by_category(scores)

    print(f"Scored {total_count} eval result(s) from {args.input}")
    print(f"Passed: {passed_count}/{total_count}")
    print()
    print("By category:")
    for category in sorted(category_summary):
        category_passed = category_summary[category]["passed"]
        category_total = category_summary[category]["total"]
        print(f"  {category}: {category_passed}/{category_total}")
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
