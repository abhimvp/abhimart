"""Probe refund HITL through the real chat HTTP API.

Run the FastAPI server first:
    uv run uvicorn app.main:app --reload

Then run:
    uv run python evals/chat_api_hitl_probe.py
"""

import argparse
import asyncio
import json
import uuid
from typing import Any

import httpx


DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def _parse_sse_payloads(text: str) -> list[dict[str, Any] | str]:
    payloads: list[dict[str, Any] | str] = []
    for line in text.splitlines():
        if not line.startswith("data: "):
            continue

        raw = line.removeprefix("data: ").strip()
        if raw == "[DONE]":
            payloads.append(raw)
            continue

        payloads.append(json.loads(raw))
    return payloads


async def _post_sse(client: httpx.AsyncClient, path: str, body: dict[str, Any]):
    response = await client.post(path, json=body)
    response.raise_for_status()
    return _parse_sse_payloads(response.text)


def _find_interrupt(payloads: list[dict[str, Any] | str]) -> dict[str, Any] | None:
    for payload in payloads:
        if isinstance(payload, dict) and payload.get("type") == "interrupt":
            return payload.get("interrupt")
    return None


def _joined_text(payloads: list[dict[str, Any] | str]) -> str:
    chunks = [
        payload.get("text", "")
        for payload in payloads
        if isinstance(payload, dict) and "text" in payload
    ]
    return "".join(chunks)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--session-id", default=f"api-refund-hitl-{uuid.uuid4()}")
    parser.add_argument("--reject", action="store_true")
    args = parser.parse_args()

    message = (
        "My email is rohit@example.com. Please start a refund for my MacBook "
        f"order. API HITL probe request id: {args.session_id}."
    )

    async with httpx.AsyncClient(base_url=args.base_url, timeout=60.0) as client:
        first_payloads = await _post_sse(
            client,
            "/v1/chat",
            {"message": message, "session_id": args.session_id},
        )
        interrupt = _find_interrupt(first_payloads)
        if not interrupt:
            raise SystemExit(
                "FAIL: expected interrupt SSE event from /v1/chat, got:\n"
                f"{first_payloads}"
            )

        print("PASS: /v1/chat returned interrupt")
        print(json.dumps(interrupt, indent=2))

        approved = not args.reject
        resume_payloads = await _post_sse(
            client,
            "/v1/chat/resume",
            {
                "session_id": args.session_id,
                "approved": approved,
                "reviewer_note": "API probe approval"
                if approved
                else "API probe rejection",
            },
        )
        final_text = _joined_text(resume_payloads)

        expected = "processed" if approved else "not approved"
        if expected not in final_text.lower():
            raise SystemExit(
                f"FAIL: expected final response to mention {expected!r}, got:\n"
                f"{final_text}"
            )

        print("PASS: /v1/chat/resume returned final HITL response")
        print(final_text)


if __name__ == "__main__":
    asyncio.run(main())

