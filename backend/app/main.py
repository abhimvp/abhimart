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
from fastapi.staticfiles import StaticFiles
from app.config import get_settings
from app.database import engine
from app.api.v1.products import router as products_router
from app.api.v1.chat import router as chat_router
import os

# Must be set in os.environ — LangSmith SDK reads these directly,
# not from our settings object.
from app.config import get_settings

logger = structlog.get_logger()

_settings = get_settings()
os.environ["LANGSMITH_TRACING"] = str(_settings.LANGSMITH_TRACING).lower()
os.environ["LANGSMITH_API_KEY"] = _settings.LANGSMITH_API_KEY
os.environ["LANGSMITH_PROJECT"] = _settings.LANGSMITH_PROJECT
os.environ["LANGSMITH_ENDPOINT"] = _settings.LANGSMITH_ENDPOINT


@asynccontextmanager
async def lifespan(app: FastAPI):
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    from app.agents.customer_support.graph import build_graph

    logger.info("Starting AbhiMart backend", version=_settings.APP_VERSION)

    # Verify app database is reachable
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
    logger.info("Database connection verified")

    # Wire up Postgres checkpointer for durable conversation memory
    async with AsyncPostgresSaver.from_conn_string(
        _settings.CHECKPOINT_DATABASE_URL
    ) as checkpointer:
        await checkpointer.setup()  # creates LangGraph checkpoint tables (idempotent)
        app.state.graph = build_graph(checkpointer)
        logger.info("LangGraph checkpointer ready")

        yield  # app serves requests here

    # --- Shutdown ---
    logger.info("Shutting down AbhiMart backend")
    await engine.dispose()
    logger.info("Database connections closed")


app = FastAPI(
    title=_settings.APP_NAME,
    version=_settings.APP_VERSION,
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
app.include_router(chat_router, prefix="/v1")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/health")
async def health_check():
    """Health check endpoint.

    Used by Docker healthchecks, load balancers, and monitoring
    to verify the service is alive.
    """
    return {
        "status": "ok",
        "app": _settings.APP_NAME,
        "version": _settings.APP_VERSION,
    }
