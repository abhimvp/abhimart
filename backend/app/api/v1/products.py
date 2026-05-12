"""Product API routes.

This is the controller layer — it handles HTTP concerns:
- Parse and validate request data (Pydantic does this automatically)
- Call the repository for database operations
- Return the right status code and response shape
- Handle errors (not found, duplicates)

The route handler should be THIN. If you find yourself writing
business logic here, it belongs in a service layer.
"""

import math
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.repositories.product import product_repo
from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.post(
    "",
    response_model=ProductResponse,
    status_code=201,
    summary="Create a new product",
    responses={409: {"description": "Product with this SKU already exists"}},
)
async def create_product(
    data: ProductCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a product in the catalog.

    - **201**: Product created successfully
    - **409**: Duplicate SKU (unique constraint violation)
    - **422**: Validation error (automatic from Pydantic)

    How does the data parameter get populated?
    FastAPI sees the type hint `data: ProductCreate` and knows:
    1. This is a Pydantic model → it must come from the request body (JSON)
    2. Parse the JSON body → validate against ProductCreate
    3. If valid, pass the validated object to the function
    4. If invalid, return 422 with detailed error messages

    You never write json.loads() or validation if-statements. Pydantic
    and FastAPI do it for you.
    """
    try:
        product = await product_repo.create(db, data)
        await db.commit()
        return product
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Product with SKU '{data.sku}' already exists.",
        )


@router.get(
    "",
    response_model=ProductListResponse,
    summary="List products with filtering and pagination",
)
async def list_products(
    db: AsyncSession = Depends(get_db),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    category: str | None = Query(default=None, description="Filter by category"),
    search: str | None = Query(default=None, description="Search in name/description"),
):
    """List products with optional category filter and text search.

    Query parameters vs path parameters vs body:
    - Path params (/products/{id}) → identifies a SPECIFIC resource
    - Query params (?page=2&category=electronics) → filters/options on a collection
    - Body → used for CREATE/UPDATE data (POST/PATCH)

    Query() is like Field() but for query string parameters. It adds
    validation (ge=1, le=100) and shows up in the Swagger docs with
    descriptions.
    """
    products, total = await product_repo.get_many(
        db, page=page, size=size, category=category, search=search
    )
    return ProductListResponse(
        items=products,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 0,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get a product by ID",
    responses={404: {"description": "Product not found"}},
)
async def get_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single product by its UUID.

    How does product_id get parsed?
    FastAPI sees `product_id: uuid.UUID` in the function signature and
    matches it to {product_id} in the path. It automatically:
    1. Extracts the string from the URL
    2. Tries to parse it as a UUID
    3. If it's not a valid UUID → 422 error (free validation!)
    """
    product = await product_repo.get_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    return product


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update a product",
    responses={
        404: {"description": "Product not found"},
        409: {"description": "SKU conflict"},
    },
)
async def update_product(
    product_id: uuid.UUID,
    data: ProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update specific fields of a product.

    PATCH vs PUT:
    - PATCH = partial update (send only what changed)
    - PUT = full replacement (send the entire object)
    We use PATCH because it's more practical — you rarely want to
    resend every field just to change the price.

    Note the pattern: fetch first, then update.
    We need the existing product to verify it exists (404 if not)
    and to apply partial updates to.
    """
    product = await product_repo.get_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    try:
        updated = await product_repo.update(db, product, data)
        await db.commit()
        return updated
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"Product with SKU '{data.sku}' already exists.",
        )


@router.delete(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Soft-delete a product",
    responses={404: {"description": "Product not found"}},
)
async def delete_product(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a product (sets is_active=False).

    Why return the product after deletion?
    - The client gets confirmation of WHAT was deleted
    - Useful for undo functionality
    - Alternative: return 204 No Content (no body). We chose
      200 with body for better developer experience.
    """
    product = await product_repo.get_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    deleted = await product_repo.soft_delete(db, product)
    await db.commit()
    return deleted
