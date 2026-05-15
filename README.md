# AbhiMart

AI customer support agent for a fictional e-commerce store.

Learning-focused project covering full-stack AI engineering: agent loop, RAG,
multi-agent orchestration, durable execution, evals, observability, guardrails,
and production deployment.

## Project docs

See [Evaluation](docs/evaluation.md) for the current agent eval harness, golden
dataset, LangSmith experiment workflow, and Stage 4 evaluation learning guide.

## Status

| Stage | Description | Status |
|-------|-------------|--------|
| Stage 0 | Scaffolding, infrastructure, DB, first migration | Complete |
| Stage 1 | LangGraph agent + streaming SSE chat API | Complete |
| Stage 2 | Tools (order lookup, product info) + Postgres-backed memory | Complete |
| Stage 3 | RAG pipeline - pgvector + Gemini embeddings + `search_faq` tool | Complete |
| Stage 4 | Local eval harness complete; LangSmith experiments + observability next | In progress |
| Stage 5 | Guardrails + multi-agent | Planned |
| Stage 6 | React frontend + production deployment | Planned |

## Stack

Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x async, asyncpg, Postgres 17
with pgvector, Alembic, structlog, Docker Compose, uv, LangGraph, LangChain,
Google Gemini, and LangSmith.

Coming later: Redis, React 19, TypeScript, OpenTelemetry, AWS.

## Project structure

```text
abhimart/
├── backend/
│   ├── app/
│   │   ├── config.py                   # Pydantic Settings
│   │   ├── database.py                 # Async SQLAlchemy engine/session
│   │   ├── main.py                     # FastAPI app and LangGraph wiring
│   │   ├── seed.py                     # Seed products, users, orders
│   │   ├── models/                     # SQLAlchemy ORM models
│   │   ├── api/v1/                     # Products and chat endpoints
│   │   ├── agents/customer_support/    # LangGraph graph and tools
│   │   ├── rag/                        # Knowledge base ingestion/docs
│   │   └── static/chat.html            # Simple chat UI for testing
│   ├── alembic/                        # Database migrations
│   ├── evals/
│   │   ├── datasets/stage4_golden.jsonl
│   │   ├── run_eval.py
│   │   ├── score_results.py
│   │   ├── langsmith_dataset.py
│   │   └── langsmith_run.py
│   ├── pyproject.toml
│   └── .env.example
├── docs/
│   └── evaluation.md
└── infra/
    └── docker-compose.yml
```

## Local development

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [uv](https://docs.astral.sh/uv/)
- Python 3.12+
- Google Gemini API key
- LangSmith API key

### Setup

```bash
# 1. Start Postgres (pgvector-enabled)
docker compose -f infra/docker-compose.yml up -d

# 2. Install Python dependencies
cd backend
uv sync

# 3. Create .env from template and fill required values
cp .env.example .env

# 4. Run database migrations
uv run alembic upgrade head

# 5. Seed the database
uv run python -m app.seed

# 6. Index knowledge base docs into pgvector
uv run python -m app.rag.ingest

# 7. Start the dev server
uv run uvicorn app.main:app --reload
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |
| GET | `/v1/products` | List all products |
| POST | `/v1/chat` | Streaming SSE chat |
| GET | `/v1/chat/history/{session_id}` | Conversation history |
| GET | `/static/chat.html` | Simple chat UI |
