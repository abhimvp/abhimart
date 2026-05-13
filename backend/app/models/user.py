"""User ORM model."""

import uuid

from sqlalchemy import Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    """A customer of AbhiMart."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    orders: Mapped[list["Order"]] = relationship(back_populates="user")

    __table_args__ = (Index("ix_users_email", "email"),)

    def __repr__(self) -> str:
        return f"<User {self.email}>"
