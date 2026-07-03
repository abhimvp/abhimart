"""Order preparation service for simulated customer orders.

The LLM can ask for an order to be prepared, but this module owns the business
rules: product lookup, quantity validation, stock checks, and the transactional
stock decrement.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select, update

from app.database import async_session_factory
from app.exceptions import (
    CustomerNotFoundError,
    InsufficientStockError,
    InvalidOrderQuantityError,
    ProductNotFoundError,
)
from app.models.order import Order
from app.models.product import Product
from app.models.user import User


SIMULATED_ORDER_STATUS = "pending_simulated"


@dataclass(frozen=True, slots=True)
class InventoryCheckResult:
    """Current inventory snapshot for a product order request."""

    product_id: UUID
    product_name: str
    requested_quantity: int
    available_quantity: int
    unit_price: Decimal


@dataclass(frozen=True, slots=True)
class SimulatedOrderResult:
    """Created simulated order details."""

    order_id: UUID
    order_id_preview: str
    product_id: UUID
    product_name: str
    quantity: int
    unit_price: Decimal
    total_amount: Decimal
    remaining_stock: int
    status: str


def _validate_quantity(quantity: int) -> None:
    if quantity <= 0:
        raise InvalidOrderQuantityError(quantity=quantity)


async def _get_active_product(session, product_name: str) -> Product:
    result = await session.execute(
        select(Product)
        .where(
            Product.name.ilike(f"%{product_name}%"),
            Product.is_active == True,
        )
        .order_by(Product.name)
        .limit(1)
    )
    product = result.scalar_one_or_none()
    if not product:
        raise ProductNotFoundError(product_name=product_name)
    return product


async def _get_customer_by_email(session, customer_email: str) -> User:
    email = customer_email.strip().lower()
    result = await session.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        raise CustomerNotFoundError(email=email)
    return user


async def check_inventory_for_order(
    *,
    product_name: str,
    quantity: int,
    session_factory: Any = async_session_factory,
) -> InventoryCheckResult:
    """Check current stock for a requested product quantity.

    This is a read-only snapshot. It does not reserve or decrement stock.
    Confirmed order preparation must re-check stock inside a transaction.
    """

    _validate_quantity(quantity)

    async with session_factory() as session:
        product = await _get_active_product(session, product_name)
        result = InventoryCheckResult(
            product_id=product.id,
            product_name=product.name,
            requested_quantity=quantity,
            available_quantity=product.stock_quantity,
            unit_price=product.price,
        )

    if quantity > result.available_quantity:
        raise InsufficientStockError(
            product_id=result.product_id,
            product_name=result.product_name,
            requested_quantity=quantity,
            available_quantity=result.available_quantity,
        )

    return result


async def prepare_simulated_order(
    *,
    product_name: str,
    quantity: int,
    customer_email: str,
    session_factory: Any = async_session_factory,
) -> SimulatedOrderResult:
    """Create a simulated pending order and decrement stock atomically.

    No payment provider is called and no shipment is created. The stock decrement
    happens in the same database transaction as the pending order creation.
    """

    _validate_quantity(quantity)

    async with session_factory() as session:
        async with session.begin():
            user = await _get_customer_by_email(session, customer_email)
            product = await _get_active_product(session, product_name)

            decrement_result = await session.execute(
                update(Product)
                .where(
                    Product.id == product.id,
                    Product.stock_quantity >= quantity,
                )
                .values(stock_quantity=Product.stock_quantity - quantity)
                .returning(Product.stock_quantity)
            )
            remaining_stock = decrement_result.scalar_one_or_none()

            if remaining_stock is None:
                await session.refresh(product)
                raise InsufficientStockError(
                    product_id=product.id,
                    product_name=product.name,
                    requested_quantity=quantity,
                    available_quantity=product.stock_quantity,
                )

            total_amount = product.price * quantity
            order = Order(
                user_id=user.id,
                status=SIMULATED_ORDER_STATUS,
                total_amount=total_amount,
                items=[
                    {
                        "product_name": product.name,
                        "qty": quantity,
                        "price": str(product.price),
                        "simulated": True,
                    }
                ],
            )
            session.add(order)
            await session.flush()

            return SimulatedOrderResult(
                order_id=order.id,
                order_id_preview=str(order.id)[:8],
                product_id=product.id,
                product_name=product.name,
                quantity=quantity,
                unit_price=product.price,
                total_amount=total_amount,
                remaining_stock=remaining_stock,
                status=order.status,
            )
