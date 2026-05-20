"""Refund approval helpers for the customer support graph."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import async_session_factory
from app.models.order import Order
from app.models.refund_request import RefundRequest
from app.models.user import User


EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)


@dataclass(frozen=True)
class RefundReviewResult:
    """Result of checking whether a refund request needs approval."""

    should_interrupt: bool
    payload: dict[str, Any] | None = None
    response: str | None = None


def _email_domain(email: str) -> str:
    if "@" not in email:
        return "unknown"
    return email.rsplit("@", 1)[1].lower()


def _contains_refund_intent(message: str) -> bool:
    lowered = message.lower()
    return "refund" in lowered or "return my money" in lowered


def _item_matches_message(item_name: str, message: str) -> bool:
    message_words = set(re.findall(r"[a-z0-9]+", message.lower()))
    item_words = {
        word
        for word in re.findall(r"[a-z0-9]+", item_name.lower())
        if len(word) >= 4
    }
    return bool(item_words & message_words)


def _format_money(value: Decimal) -> str:
    return f"{float(value):.2f}"


def _refund_idempotency_key(email: str, order_id: Any, reason: str) -> str:
    normalized_reason = " ".join(reason.lower().split())
    raw = f"refund:{email.lower()}:{order_id}:{normalized_reason}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def _get_refund_request_by_key(idempotency_key: str) -> RefundRequest | None:
    async with async_session_factory() as session:
        result = await session.execute(
            select(RefundRequest).where(
                RefundRequest.idempotency_key == idempotency_key
            )
        )
        return result.scalar_one_or_none()


async def create_or_get_refund_request(
    *,
    email: str,
    user_id: Any,
    order_id: Any,
    requested_amount: Decimal,
    reason: str,
) -> RefundRequest:
    """Create a pending refund request once for a customer/order pair.

    This function is intentionally idempotent because LangGraph re-runs code
    before interrupt() when a paused graph resumes.
    """

    idempotency_key = _refund_idempotency_key(email, order_id, reason)
    existing = await _get_refund_request_by_key(idempotency_key)
    if existing:
        return existing

    async with async_session_factory() as session:
        refund_request = RefundRequest(
            order_id=order_id,
            user_id=user_id,
            idempotency_key=idempotency_key,
            status="pending_review",
            requested_amount=requested_amount,
            reason=reason,
        )
        session.add(refund_request)
        try:
            await session.commit()
            await session.refresh(refund_request)
            return refund_request
        except IntegrityError:
            await session.rollback()
            existing = await _get_refund_request_by_key(idempotency_key)
            if existing:
                return existing
            raise


async def complete_refund_review(
    *,
    refund_request_id: str,
    approved: bool,
    reviewer_note: str,
) -> dict[str, Any]:
    """Persist the human review decision for a pending refund request."""

    async with async_session_factory() as session:
        result = await session.execute(
            select(RefundRequest).where(RefundRequest.id == refund_request_id)
        )
        refund_request = result.scalar_one_or_none()

        if not refund_request:
            return {
                "found": False,
                "status": "missing",
                "changed": False,
            }

        if refund_request.status != "pending_review":
            return {
                "found": True,
                "status": refund_request.status,
                "changed": False,
            }

        refund_request.status = "approved" if approved else "rejected"
        refund_request.reviewer_note = reviewer_note or None
        await session.commit()

        return {
            "found": True,
            "status": refund_request.status,
            "changed": True,
        }


async def process_approved_refund(
    *,
    refund_request_id: str,
) -> dict[str, Any]:
    """Simulate processing an approved refund exactly once.

    This does not call a payment provider. It moves the local request state from
    approved to processed so the rest of the workflow can be tested safely.
    """

    async with async_session_factory() as session:
        result = await session.execute(
            select(RefundRequest).where(RefundRequest.id == refund_request_id)
        )
        refund_request = result.scalar_one_or_none()

        if not refund_request:
            return {
                "found": False,
                "status": "missing",
                "changed": False,
            }

        if refund_request.status == "processed":
            return {
                "found": True,
                "status": "processed",
                "changed": False,
            }

        if refund_request.status != "approved":
            return {
                "found": True,
                "status": refund_request.status,
                "changed": False,
            }

        refund_request.status = "processed"
        await session.commit()

        return {
            "found": True,
            "status": "processed",
            "changed": True,
        }


async def prepare_refund_review(message: str) -> RefundReviewResult:
    """Build a human-review payload for refund requests with customer identity.

    This helper is intentionally read-only. It may look up the customer's order
    so a human has useful context, but it does not create or process a refund.
    """

    if not _contains_refund_intent(message):
        return RefundReviewResult(should_interrupt=False)

    emails = EMAIL_RE.findall(message)
    if not emails:
        return RefundReviewResult(should_interrupt=False)

    email = emails[0].lower()

    async with async_session_factory() as session:
        user_result = await session.execute(select(User).where(User.email == email))
        user = user_result.scalar_one_or_none()

        if not user:
            return RefundReviewResult(
                should_interrupt=False,
                response=(
                    "I could not find an AbhiMart account for that email address. "
                    "Please check the email and try again."
                ),
            )

        order_result = await session.execute(
            select(Order)
            .where(Order.user_id == user.id)
            .order_by(Order.created_at.desc())
        )
        orders = order_result.scalars().all()

    matching_orders = []
    for order in orders:
        if any(
            _item_matches_message(item.get("product_name", ""), message)
            for item in order.items
        ):
            matching_orders.append(order)

    if not matching_orders:
        return RefundReviewResult(
            should_interrupt=False,
            response=(
                "I found your account, but I need to know which order or product "
                "you want a refund for before I can prepare it for human review."
            ),
        )

    if len(matching_orders) > 1:
        return RefundReviewResult(
            should_interrupt=False,
            response=(
                "I found multiple matching orders. Please include the order ID or "
                "a more specific product name so I can prepare the refund request "
                "for human review."
            ),
        )

    order = matching_orders[0]
    refund_request = await create_or_get_refund_request(
        email=email,
        user_id=user.id,
        order_id=order.id,
        requested_amount=order.total_amount,
        reason=message,
    )

    if refund_request.status != "pending_review":
        return RefundReviewResult(
            should_interrupt=False,
            response=(
                "A refund request for this order was already reviewed. "
                f"Current status: {refund_request.status}."
            ),
        )

    items = [
        {
            "product_name": item.get("product_name"),
            "qty": item.get("qty"),
            "price": item.get("price"),
        }
        for item in order.items
    ]

    return RefundReviewResult(
        should_interrupt=True,
        payload={
            "kind": "refund_approval_required",
            "action": "review_refund_request",
            "customer_email": email,
            "customer_email_domain": _email_domain(email),
            "customer_name": user.name,
            "refund_request_id": str(refund_request.id),
            "refund_status": refund_request.status,
            "idempotency_key": refund_request.idempotency_key,
            "order_id": str(order.id),
            "order_id_preview": str(order.id)[:8],
            "order_status": order.status,
            "total_amount": _format_money(order.total_amount),
            "items": items,
            "message": (
                "A customer requested a refund. Review the order context and "
                "resume with approved=true or approved=false."
            ),
        },
    )
