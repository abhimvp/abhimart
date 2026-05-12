"""FastAPI application entry point.

This is the file Uvicorn loads:
    uvicorn app.main:app --reload

The lifespan context manager runs setup/teardown logic:
- On startup: verify database connectivity
- On shutdown: close the connection pool cleanly
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import get_settings
from app.database import engine
from app.api.v1.products import router as products_router


logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager.

    This is a context manager — the code before 'yield' runs at startup,
    the code after 'yield' runs at shutdown.

    Why check DB on startup?
    - If Postgres is down, we want to know immediately, not when the
      first user request fails 30 seconds later.
    """
    # --- Startup ---
    logger.info("Starting AbhiMart backend", version=settings.APP_VERSION)

    # Verify database is reachable
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connection verified")

    yield  # App is running and serving requests between here...

    # --- Shutdown ---
    logger.info("Shutting down AbhiMart backend")
    await engine.dispose()
    logger.info("Database connections closed")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI customer support agent for AbhiMart e-commerce",
    lifespan=lifespan,
)

# CORS — permissive for local dev. We'll lock this down for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products_router, prefix="/v1")


@app.get("/health")
async def health_check():
    """Health check endpoint.

    Used by Docker healthchecks, load balancers, and monitoring
    to verify the service is alive.
    """
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }
