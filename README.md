# AbhiMart

AI customer support agent for a fictional e-commerce store.

Learning-focused project covering full-stack AI engineering: agent loop, RAG, multi-agent orchestration, durable execution, evals, observability, guardrails, and production deployment.

## Project plan

See [`docs/MASTER_PLAN.md`](docs/AbhiMart_Master_Plan.md) — the complete plan,
tech stack, stage-by-stage roadmap, and learning journey.

## Status

**Stage 0 — Part 1 complete** (scaffolding, infrastructure, first model + migration).

Working on Part 2 — CRUD API endpoints.

## Stack

Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2.x (async) · asyncpg · Postgres 17 · Alembic · structlog · Docker Compose · uv

_Coming later:_ pgvector · Redis · LangGraph 1.x · LangChain 1.x · React 19 · TypeScript · OpenTelemetry · AWS

## Project structure

```
abhimart/
├── backend/                  # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py         # Pydantic Settings (reads .env)
│   │   ├── database.py       # Async SQLAlchemy engine + session factory
│   │   ├── main.py           # FastAPI app, lifespan, health endpoint
│   │   └── models/
│   │       ├── __init__.py   # Model registry (imports all models)
│   │       ├── base.py       # DeclarativeBase + TimestampMixin
│   │       └── product.py    # Product ORM model
│   ├── alembic/              # Database migrations
│   │   ├── env.py            # Async-aware migration runner
│   │   └── versions/         # Migration files
│   ├── alembic.ini           # Alembic config
│   ├── pyproject.toml        # Dependencies + tool config
│   ├── uv.lock               # Pinned dependency lockfile
│   ├── .env                  # Local config (git-ignored)
│   └── .env.example          # Template for .env
├── infra/
│   └── docker-compose.yml    # Postgres 17 service
└── docs/
    └── AbhiMart_Master_Plan.md
```

## Local development

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for Postgres)
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.12+

### Setup

```bash
# 1. Start Postgres
docker compose -f infra/docker-compose.yml up -d

# 2. Install Python dependencies
cd backend
uv sync

# 3. Create .env from template
cp .env.example .env
# Edit .env with your local config

# 4. Run database migrations
uv run alembic upgrade head

# 5. Start the dev server
uv run uvicorn app.main:app --reload
```

### Endpoints

- `http://localhost:8000/health` — Health check
- `http://localhost:8000/docs` — Swagger UI
