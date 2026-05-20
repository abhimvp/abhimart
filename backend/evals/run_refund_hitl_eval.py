"""Focused evals for refund human-in-the-loop behavior.

These checks are separate from the normal answer scorer because the expected
first outcome is an interrupt, not a final LLM answer.
"""

import asyncio
import sys
import uuid
from pathlib import Path
from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from sqlalchemy import func, select

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.agents.customer_support.graph import build_graph
from app.database import async_session_factory
from app.models.refund_request import RefundRequest


class EvalFailure(Exception):
    """Raised when a refund HITL eval fails."""


def _interrupt_payload(result: dict[str, Any]) -> dict[str, Any] | None:
    interrupts = result.get("__interrupt__", ())
    if not interrupts:
        return None

    first = interrupts[0]
    value = getattr(first, "value", first)
    return value if isinstance(value, dict) else None


async def _run_until_interrupt(graph, *, message: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke(
        {"messages": [{"role": "user", "content": message}]},
        config=config,
    )
    return result, _interrupt_payload(result)


async def _resume(graph, *, thread_id: str, approved: bool, note: str):
    config = {"configurable": {"thread_id": thread_id}}
    result = await graph.ainvoke(
        Command(resume={"approved": approved, "reviewer_note": note}),
        config=config,
    )
    return result["messages"][-1].content


async def _refund_status(refund_request_id: str) -> str:
    async with async_session_factory() as session:
        result = await session.execute(
            select(RefundRequest.status).where(
                RefundRequest.id == uuid.UUID(refund_request_id)
            )
        )
        status = result.scalar_one_or_none()
        if status is None:
            raise EvalFailure(f"Refund request {refund_request_id} was not found")
        return status


async def _refund_count_by_key(idempotency_key: str) -> int:
    async with async_session_factory() as session:
        result = await session.execute(
            select(func.count()).select_from(RefundRequest).where(
                RefundRequest.idempotency_key == idempotency_key
            )
        )
        return int(result.scalar_one())


def _assert(condition: bool, message: str):
    if not condition:
        raise EvalFailure(message)


async def test_approval(graph, run_id: str):
    thread_id = f"refund-approval-{run_id}"
    message = (
        "My email is rohit@example.com. Please start a refund for my MacBook "
        f"order. Eval approval request id: {run_id}."
    )

    _, payload = await _run_until_interrupt(
        graph,
        message=message,
        thread_id=thread_id,
    )
    _assert(payload is not None, "approval case did not interrupt")
    _assert(
        payload["kind"] == "refund_approval_required",
        "approval interrupt kind was wrong",
    )

    final_answer = await _resume(
        graph,
        thread_id=thread_id,
        approved=True,
        note="Eval approval",
    )
    status = await _refund_status(payload["refund_request_id"])

    _assert(status == "approved", f"expected approved status, got {status}")
    _assert("approved" in final_answer.lower(), "final answer did not mention approval")


async def test_rejection(graph, run_id: str):
    thread_id = f"refund-rejection-{run_id}"
    message = (
        "My email is rohit@example.com. Please start a refund for my MacBook "
        f"order. Eval rejection request id: {run_id}."
    )

    _, payload = await _run_until_interrupt(
        graph,
        message=message,
        thread_id=thread_id,
    )
    _assert(payload is not None, "rejection case did not interrupt")

    final_answer = await _resume(
        graph,
        thread_id=thread_id,
        approved=False,
        note="Eval rejection",
    )
    status = await _refund_status(payload["refund_request_id"])

    _assert(status == "rejected", f"expected rejected status, got {status}")
    _assert(
        "not approved" in final_answer.lower(),
        "final answer did not mention rejection",
    )


async def test_duplicate_request_is_idempotent(graph, run_id: str):
    message = (
        "My email is rohit@example.com. Please start a refund for my MacBook "
        f"order. Eval duplicate request id: {run_id}."
    )

    _, first_payload = await _run_until_interrupt(
        graph,
        message=message,
        thread_id=f"refund-duplicate-first-{run_id}",
    )
    _assert(first_payload is not None, "duplicate first request did not interrupt")

    await _resume(
        graph,
        thread_id=f"refund-duplicate-first-{run_id}",
        approved=True,
        note="Eval duplicate first approval",
    )

    second_result, second_payload = await _run_until_interrupt(
        graph,
        message=message,
        thread_id=f"refund-duplicate-second-{run_id}",
    )
    final_answer = second_result["messages"][-1].content
    count = await _refund_count_by_key(first_payload["idempotency_key"])

    _assert(second_payload is None, "duplicate reviewed request interrupted again")
    _assert(count == 1, f"expected one refund row for key, got {count}")
    _assert(
        "already reviewed" in final_answer.lower()
        or "already been reviewed" in final_answer.lower(),
        "duplicate response did not mention prior review",
    )


async def test_missing_matching_order(graph, run_id: str):
    message = (
        "My email is rohit@example.com. Please start a refund for my Nintendo "
        f"Switch order. Eval missing order request id: {run_id}."
    )

    result, payload = await _run_until_interrupt(
        graph,
        message=message,
        thread_id=f"refund-missing-order-{run_id}",
    )
    final_answer = result["messages"][-1].content

    _assert(payload is None, "missing matching order should not interrupt")
    _assert(
        "which order or product" in final_answer.lower(),
        "missing order response did not ask for clearer order/product info",
    )


async def main():
    run_id = str(uuid.uuid4())[:8]
    graph = build_graph(InMemorySaver())
    tests = [
        ("approval", test_approval),
        ("rejection", test_rejection),
        ("duplicate_request_is_idempotent", test_duplicate_request_is_idempotent),
        ("missing_matching_order", test_missing_matching_order),
    ]

    passed = 0
    for name, test in tests:
        try:
            await test(graph, run_id)
            passed += 1
            print(f"PASS: {name}")
        except Exception as exc:
            print(f"FAIL: {name}")
            print(f"  {exc}")

    print(f"\nRefund HITL eval passed: {passed}/{len(tests)}")
    if passed != len(tests):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
