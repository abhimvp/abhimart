"""Tests for simulated order preparation business rules."""

from contextlib import asynccontextmanager
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.exceptions import (
    CustomerNotFoundError,
    InsufficientStockError,
    InvalidOrderQuantityError,
    ProductNotFoundError,
)
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.services.order_preparation import (
    SIMULATED_ORDER_STATUS,
    check_inventory_for_order,
    prepare_simulated_order,
)


@asynccontextmanager
async def _service_session_factory(db_session):
    """Expose the rollback-safe pytest session through the service interface."""

    yield db_session


async def add_product(db_session, *, name="Sony WH-1000XM5", stock=5):
    product = Product(
        name=name,
        description="Noise-cancelling wireless headphones",
        price=Decimal("349.99"),
        category="electronics",
        sku=f"TEST-{name[:8].upper().replace(' ', '-')}-{stock}",
        stock_quantity=stock,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    return product


async def add_user(db_session, *, email="rohit@example.com"):
    user = User(name="Rohit", email=email)
    db_session.add(user)
    await db_session.commit()
    return user


async def test_check_inventory_returns_current_stock(db_session):
    await add_product(db_session, stock=5)

    result = await check_inventory_for_order(
        product_name="Sony WH-1000XM5",
        quantity=3,
        session_factory=lambda: _service_session_factory(db_session),
    )

    assert result.product_name == "Sony WH-1000XM5"
    assert result.requested_quantity == 3
    assert result.available_quantity == 5


async def test_check_inventory_raises_for_invalid_quantity(db_session):
    with pytest.raises(InvalidOrderQuantityError) as exc_info:
        await check_inventory_for_order(
            product_name="Sony WH-1000XM5",
            quantity=0,
            session_factory=lambda: _service_session_factory(db_session),
        )

    assert exc_info.value.quantity == 0


async def test_check_inventory_raises_for_missing_product(db_session):
    with pytest.raises(ProductNotFoundError) as exc_info:
        await check_inventory_for_order(
            product_name="Missing Product",
            quantity=1,
            session_factory=lambda: _service_session_factory(db_session),
        )

    assert exc_info.value.product_name == "Missing Product"


async def test_check_inventory_raises_for_insufficient_stock(db_session):
    product = await add_product(db_session, stock=5)

    with pytest.raises(InsufficientStockError) as exc_info:
        await check_inventory_for_order(
            product_name="Sony WH-1000XM5",
            quantity=10,
            session_factory=lambda: _service_session_factory(db_session),
        )

    assert exc_info.value.product_id == product.id
    assert exc_info.value.requested_quantity == 10
    assert exc_info.value.available_quantity == 5


async def test_prepare_simulated_order_decrements_stock_and_creates_order(db_session):
    product = await add_product(db_session, stock=5)
    user = await add_user(db_session)

    result = await prepare_simulated_order(
        product_name="Sony WH-1000XM5",
        quantity=2,
        customer_email=user.email,
        session_factory=lambda: _service_session_factory(db_session),
    )

    assert result.status == SIMULATED_ORDER_STATUS
    assert result.quantity == 2
    assert result.remaining_stock == 3
    assert result.total_amount == Decimal("699.98")

    await db_session.refresh(product)
    assert product.stock_quantity == 3

    order_result = await db_session.execute(
        select(Order).where(Order.id == result.order_id)
    )
    order = order_result.scalar_one()
    assert order.status == SIMULATED_ORDER_STATUS
    assert order.user_id == user.id
    assert order.items[0]["product_name"] == "Sony WH-1000XM5"
    assert order.items[0]["qty"] == 2
    assert order.items[0]["simulated"] is True


async def test_prepare_simulated_order_raises_for_unknown_customer(db_session):
    await add_product(db_session, stock=5)

    with pytest.raises(CustomerNotFoundError) as exc_info:
        await prepare_simulated_order(
            product_name="Sony WH-1000XM5",
            quantity=1,
            customer_email="missing@example.com",
            session_factory=lambda: _service_session_factory(db_session),
        )

    assert exc_info.value.email == "missing@example.com"


async def test_prepare_simulated_order_does_not_create_order_when_stock_low(
    db_session,
):
    product = await add_product(db_session, stock=1)
    await add_user(db_session)

    with pytest.raises(InsufficientStockError) as exc_info:
        await prepare_simulated_order(
            product_name="Sony WH-1000XM5",
            quantity=2,
            customer_email="rohit@example.com",
            session_factory=lambda: _service_session_factory(db_session),
        )

    assert exc_info.value.available_quantity == 1
    await db_session.refresh(product)
    assert product.stock_quantity == 1

    order_count = await db_session.execute(select(Order))
    assert order_count.scalars().all() == []
