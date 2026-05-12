"""ORM models package.

Import all models here so that:
1. Alembic's autogenerate can see them (it imports this package)
2. Other code can do: from app.models import Product
"""

from app.models.base import Base
from app.models.product import Product

__all__ = ["Base", "Product"]
