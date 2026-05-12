"""Product ORM model.

This maps to the 'products' table in Postgres. Each instance of this
class represents one row in that table.

AbhiMart product categories:
  - electronics (laptops, phones, accessories)
  - appliances  (kitchen gear, vacuums, air purifiers)
  - fitness     (treadmills, weights, wearables)
  - books       (books & stationery)
"""

import uuid
from decimal import Decimal

from sqlalchemy import Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Product(TimestampMixin, Base):
    """A product in the AbhiMart catalog."""

    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    sku: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    stock_quantity: Mapped[int] = mapped_column(default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    __table_args__ = (
        Index("ix_products_category", "category"),
        Index("ix_products_sku", "sku"),
        Index("ix_products_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Product {self.sku}: {self.name}>"
