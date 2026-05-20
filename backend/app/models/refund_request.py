"""Refund request ORM model."""

import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RefundRequest(TimestampMixin, Base):
    """A human-reviewed refund request.

    This is not a payment/refund transaction yet. It records the approval state
    for a proposed refund so future write actions can be idempotent.
    """

    __tablename__ = "refund_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    idempotency_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        unique=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending_review",
    )
    requested_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewer_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    order: Mapped["Order"] = relationship()
    user: Mapped["User"] = relationship()

    __table_args__ = (
        Index("ix_refund_requests_order_id", "order_id"),
        Index("ix_refund_requests_user_id", "user_id"),
        Index("ix_refund_requests_status", "status"),
        Index("ix_refund_requests_idempotency_key", "idempotency_key"),
    )

    def __repr__(self) -> str:
        return f"<RefundRequest {self.id} - {self.status}>"

