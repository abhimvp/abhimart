"""Tools available to the AbhiMart customer support agent."""

from langchain_core.tools import tool
from sqlalchemy import select

from app.database import async_session_factory
from app.models.order import Order
from app.models.product import Product
from app.models.user import User


@tool
async def lookup_order(email: str) -> str:
    """Look up all orders for a customer by their email address.

    Use this when the customer asks about their orders, order status,
    or order history. Always ask for the customer's email first.

    Args:
        email: The customer's email address
    """
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            return f"No customer found with email '{email}'."

        result = await session.execute(
            select(Order)
            .where(Order.user_id == user.id)
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()

        if not orders:
            return f"No orders found for {user.name} ({email})."

        lines = [f"Orders for {user.name} ({email}):"]
        for order in orders:
            items_str = ", ".join(
                f"{i['product_name']} x{i['qty']}" for i in order.items
            )
            lines.append(
                f"  - Order #{str(order.id)[:8]} | "
                f"Status: {order.status.upper()} | "
                f"Total: ${order.total_amount} | "
                f"Items: {items_str}"
            )
        return "\n".join(lines)


@tool
async def get_product_info(product_name: str) -> str:
    """Look up product details from the AbhiMart catalog by name.

    Use this when the customer asks about a product's price,
    availability, description, or stock quantity.

    Args:
        product_name: The product name or partial name to search for
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(Product)
            .where(
                Product.name.ilike(f"%{product_name}%"),
                Product.is_active == True,
            )
            .limit(3)
        )
        products = result.scalars().all()

        if not products:
            return f"No products found matching '{product_name}'."

        lines = []
        for p in products:
            stock = (
                f"In Stock ({p.stock_quantity} units)"
                if p.stock_quantity > 0
                else "Out of Stock"
            )
            lines.append(
                f"{p.name}\n"
                f"  Price: ${p.price}\n"
                f"  Category: {p.category}\n"
                f"  Availability: {stock}\n"
                f"  Description: {p.description[:150]}..."
            )
        return "\n\n".join(lines)
