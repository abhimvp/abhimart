"""FastAPI dependencies — shared across all route handlers.

What is a dependency in FastAPI?
It's a function that runs BEFORE your route handler, and its return
value gets injected as a parameter. Think of it as middleware that's
scoped to specific routes.

    @router.get("/products")
    async def list_products(db: AsyncSession = Depends(get_db)):
        ...

When FastAPI sees Depends(get_db), it:
1. Calls get_db() — which opens a database session
2. Passes the session to your route as the `db` parameter
3. After the route finishes (or errors), runs the cleanup (session.close())

This is dependency injection — your route doesn't create or manage the
session. It just receives one. This makes routes easy to test (swap in
a fake session) and impossible to forget cleanup.
"""

from app.database import get_db

# Re-export so routes import from one place:
#   from app.api.deps import get_db
# Later we'll add: get_current_user, get_settings, etc.

__all__ = ["get_db"]
