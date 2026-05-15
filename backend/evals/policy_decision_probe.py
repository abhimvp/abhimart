"""Probe structured return-policy decisions.

This is a small development script, not part of the API. It lets us test the
structured eligibility classifier before wiring it into the main LangGraph flow.

Run:
    uv run python evals/policy_decision_probe.py
"""

import asyncio
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.agents.customer_support.policy import classify_return_eligibility

POLICY_PATH = BACKEND_DIR / "app" / "rag" / "docs" / "return-policy.md"


async def main() -> None:
    policy_text = POLICY_PATH.read_text(encoding="utf-8")

    decision = await classify_return_eligibility(
        customer_question=(
            "Can I return opened Sony headphones if I used them for a week?"
        ),
        policy_text=policy_text,
        source="return-policy.md",
    )

    print(json.dumps(decision.model_dump(), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
