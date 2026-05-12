"""SQLAlchemy model base and common mixins.

Why a separate base module?
- Every ORM model (Product, User, Order, etc.) needs to inherit from
  the same DeclarativeBase. If we define it here, all models share one
  metadata registry — which is what Alembic needs to autogenerate migrations.
"""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models.

    Every model in app/models/ inherits from this. SQLAlchemy uses
    this to build a registry of all tables, which Alembic reads
    to know what migrations to generate.
    """

    pass


class TimestampMixin:
    """Adds created_at and updated_at columns to any model.

    Usage:
        class Product(TimestampMixin, Base):
            __tablename__ = "products"
            ...

    server_default=func.now() means Postgres sets the timestamp,
    not Python. This is important because:
    1. The database clock is the single source of truth
    2. It works even for raw SQL inserts outside the ORM
    """

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
