"""Pydantic schemas for Product API.

These are DTOs (Data Transfer Objects) — they define the shape of
data flowing IN to and OUT of the API, separately from the database model.

Why separate from SQLAlchemy models?
1. Validation: Pydantic enforces rules (price > 0, category in allowed list)
2. Security: Don't expose internal fields (is_active, soft-delete markers)
3. Decoupling: API contract stays stable even if DB schema changes
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ProductCategory(str, Enum):
    """Allowed product categories.

    Using an Enum instead of a raw string means:
    - Typos are caught at validation time ("electonics" → 422 error)
    - Auto-generated API docs show a dropdown, not a free-text field
    - You can iterate over categories in seed scripts
    """

    ELECTRONICS = "electronics"
    APPLIANCES = "appliances"
    FITNESS = "fitness"
    BOOKS = "books"


# --- Request Schemas (what clients SEND) ---


class ProductCreate(BaseModel):
    """Schema for creating a new product (POST /v1/products).

    Notice what's NOT here: id, created_at, updated_at, is_active.
    Those are server-managed. The client shouldn't set them.
    """

    name: str = Field(..., min_length=1, max_length=255, examples=["MacBook Pro 16"])
    description: str = Field(
        ..., min_length=1, examples=["Apple M3 Max chip, 36GB RAM"]
    )
    price: Decimal = Field(..., gt=0, decimal_places=2, examples=[2499.99])
    category: ProductCategory
    sku: str = Field(..., min_length=1, max_length=50, examples=["ELEC-MBP16-001"])
    stock_quantity: int = Field(default=0, ge=0)


class ProductUpdate(BaseModel):
    """Schema for updating a product (PATCH /v1/products/{id}).

    Every field is Optional — PATCH means "update only what you send."
    This is different from PUT which replaces the entire resource.

    Why not inherit from ProductCreate and make fields optional?
    Because that's fragile — if ProductCreate adds a required field,
    ProductUpdate would silently get it as optional. Explicit > implicit.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, min_length=1)
    price: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    category: ProductCategory | None = None
    sku: str | None = Field(default=None, min_length=1, max_length=50)
    stock_quantity: int | None = Field(default=None, ge=0)


# --- Response Schemas (what clients RECEIVE) ---


class ProductResponse(BaseModel):
    """Schema for a single product in API responses.

    model_config with from_attributes=True tells Pydantic:
    "You'll receive a SQLAlchemy model object, not a dict.
     Read its attributes (product.name) instead of keys (product['name'])."
    This is the bridge between ORM land and API land.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str
    price: Decimal
    category: ProductCategory
    sku: str
    stock_quantity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    """Paginated list of products.

    Why wrap in an object instead of returning a bare list?
    - You need pagination metadata (total count, page info)
    - Bare JSON arrays are a security risk (JSON hijacking, though
      modern browsers mitigate this)
    - Easier to add fields later (filters applied, sort order)
    """

    items: list[ProductResponse]
    total: int
    page: int
    size: int
    pages: int
