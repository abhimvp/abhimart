"""AbhiMart domain exceptions.

These exceptions represent expected business failures, not programming bugs.
API routes and agent tools can catch them and turn them into clear user-facing
responses without hiding unexpected server errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


class AbhiMartError(Exception):
    """Base class for expected AbhiMart business errors."""


@dataclass(slots=True)
class ProductNotFoundError(AbhiMartError):
    """Raised when a requested product cannot be found in the catalog."""

    product_name: str

    def __post_init__(self) -> None:
        AbhiMartError.__init__(self, f"Product not found: {self.product_name}")


@dataclass(slots=True)
class CustomerNotFoundError(AbhiMartError):
    """Raised when an order operation references an unknown customer email."""

    email: str

    def __post_init__(self) -> None:
        AbhiMartError.__init__(self, f"Customer not found: {self.email}")


@dataclass(slots=True)
class InvalidOrderQuantityError(AbhiMartError):
    """Raised when an order quantity is zero, negative, or otherwise invalid."""

    quantity: int

    def __post_init__(self) -> None:
        AbhiMartError.__init__(
            self,
            f"Order quantity must be positive, got {self.quantity}",
        )


@dataclass(slots=True)
class InsufficientStockError(AbhiMartError):
    """Raised when requested quantity exceeds currently available stock."""

    product_id: UUID
    product_name: str
    requested_quantity: int
    available_quantity: int

    def __post_init__(self) -> None:
        AbhiMartError.__init__(
            self,
            f"{self.product_name}: requested {self.requested_quantity}, "
            f"only {self.available_quantity} available",
        )
