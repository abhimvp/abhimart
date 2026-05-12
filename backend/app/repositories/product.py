"""Product repository — all database operations for products.

Why a repository?
- Routes shouldn't contain SQL. They handle HTTP concerns (status codes,
  request parsing, response formatting).
- The repository handles data concerns (queries, filters, pagination).
- One place to optimize queries, add caching, or switch databases.

Pattern: Every method takes a `session` as the first argument.
The session is created by FastAPI's dependency injection (Depends(get_db))
and passed down. The repository never creates its own session.
"""

import math
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate


class ProductRepository:
    """Data access layer for Product model.

    Why a class and not just functions?
    Either works. A class groups related operations and makes it easy
    to swap implementations (e.g., a FakeProductRepository for tests).
    This is the foundation for dependency injection at the repo level later.
    """

    async def create(self, session: AsyncSession, data: ProductCreate) -> Product:
        """Insert a new product into the database.

        data.model_dump() converts the Pydantic schema to a plain dict:
            {"name": "MacBook Pro", "price": 2499.99, ...}
        We then unpack it into the ORM model constructor with **.

        session.flush() sends the INSERT to Postgres but doesn't commit.
        Why flush instead of commit?
        - The caller (route handler) controls when to commit.
        - If something fails after the insert, we can roll back.
        - flush() also populates server-generated fields (id, created_at).

        session.refresh() reloads the object from the DB to get
        those server-generated values (Postgres set the UUID and timestamps).
        """
        product = Product(**data.model_dump())
        session.add(product)
        await session.flush()
        await session.refresh(product)
        return product

    async def get_by_id(
        self, session: AsyncSession, product_id: uuid.UUID
    ) -> Product | None:
        """Fetch a single product by its UUID.

        scalar_one_or_none() returns:
        - The Product object if found
        - None if not found
        It would raise an error if multiple rows matched (impossible
        with a primary key, but good defensive practice).

        We filter is_active=True so soft-deleted products don't show up
        in normal lookups. This is the "soft delete" pattern — the row
        still exists in the DB, but we pretend it doesn't.
        """
        stmt = select(Product).where(
            Product.id == product_id,
            Product.is_active == True,  # noqa: E712 — SQLAlchemy needs == not 'is'
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_many(
        self,
        session: AsyncSession,
        *,
        page: int = 1,
        size: int = 20,
        category: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Product], int]:
        """Fetch a paginated, filterable list of products.

        Returns a tuple of (products, total_count).

        Why return total_count separately?
        - The client needs it to render "Page 1 of 5" or "47 results found"
        - We run TWO queries: one for the page of results, one for the count
        - This is the standard pattern. Some databases support window functions
          to do it in one query, but two queries is simpler and clearer.

        The * in the parameter list means everything after it is keyword-only.
        You must write get_many(session, page=2), not get_many(session, 2).
        This prevents bugs from accidentally swapping page and size.
        """
        # --- Base query (shared between count and results) ---
        base_query = select(Product).where(Product.is_active == True)  # noqa: E712

        # Optional filters
        if category:
            base_query = base_query.where(Product.category == category)
        if search:
            # ilike = case-insensitive LIKE. The % wildcards mean "contains".
            # This hits the name and description columns.
            base_query = base_query.where(
                Product.name.ilike(f"%{search}%")
                | Product.description.ilike(f"%{search}%")
            )

        # --- Count query ---
        count_stmt = select(func.count()).select_from(base_query.subquery())
        total_result = await session.execute(count_stmt)
        total = total_result.scalar_one()

        # --- Results query with pagination ---
        offset = (page - 1) * size
        results_stmt = (
            base_query.order_by(Product.created_at.desc()).offset(offset).limit(size)
        )
        results = await session.execute(results_stmt)
        products = list(results.scalars().all())

        return products, total

    async def update(
        self, session: AsyncSession, product: Product, data: ProductUpdate
    ) -> Product:
        """Update a product with only the fields that were provided.

        data.model_dump(exclude_unset=True) is the key trick here:
        - If the client sent {"price": 1999.99}, this returns {"price": 1999.99}
        - Fields the client DIDN'T send are excluded (not set to None)
        - This is how PATCH semantics work: only update what was sent

        setattr(product, key, value) is Python's way of doing:
            product.price = 1999.99
        when you have the field name as a string variable.
        """
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(product, key, value)
        await session.flush()
        await session.refresh(product)
        return product

    async def soft_delete(self, session: AsyncSession, product: Product) -> Product:
        """Soft-delete a product by setting is_active=False.

        Why soft delete instead of actual DELETE?
        - Orders reference products. If we delete a product, those
          orders have a broken foreign key (or we cascade-delete the
          orders, which is worse — "sorry, your order history is gone").
        - Soft delete lets us "undo" mistakes.
        - Analytics still works on historical product data.
        - The trade-off: every query needs WHERE is_active = true.
          We handle that in this repository so callers don't forget.
        """
        product.is_active = False
        await session.flush()
        await session.refresh(product)
        return product


# Module-level instance — importable from anywhere.
# This is a simple form of the Singleton pattern.
product_repo = ProductRepository()
