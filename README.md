# AbhiMart

AI customer support agent for a fictional e-commerce store.

Learning-focused project covering full-stack AI engineering: agent loop, RAG, multi-agent orchestration, durable execution, evals, observability, guardrails, and production deployment.

## Project plan

See [`docs/MASTER_PLAN.md`](docs/AbhiMart_Master_Plan.md) — the complete plan,
tech stack, stage-by-stage roadmap, and learning journey.

## Status

| Stage | Description | Status |
|-------|-------------|--------|
| Stage 0 | Scaffolding, infrastructure, DB, first migration | ✅ Complete |
| Stage 1 | LangGraph agent + streaming SSE chat API | ✅ Complete |
| Stage 2 | Tools (order lookup, product info) + Postgres-backed memory | ✅ Complete |
| Stage 3 | RAG pipeline — pgvector + Gemini embeddings + `search_faq` tool | ✅ Complete |
| Stage 4 | Local eval harness complete; LangSmith experiments + observability next | 🚧 In Progress |
| Stage 5 | Guardrails + multi-agent | 🔜 Planned |
| Stage 6 | React frontend + production deployment | 🔜 Planned |

## Stack

Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2.x (async) · asyncpg · Postgres 17 + pgvector · Alembic · structlog · Docker Compose · uv · LangGraph · LangChain · Google Gemini (claude-sonnet-4-5 + gemini-embedding-001) · LangSmith

_Coming later:_ Redis · React 19 · TypeScript · OpenTelemetry · AWS

## Project structure

```md

abhimart/
├── backend/
│   ├── app/
│   │   ├── config.py                   # Pydantic Settings (reads .env)
│   │   ├── database.py                 # Async SQLAlchemy engine + session factory
│   │   ├── main.py                     # FastAPI app, lifespan, LangGraph wiring
│   │   ├── seed.py                     # Seed products, users, orders
│   │   ├── models/
│   │   │   ├── product.py              # Product ORM model
│   │   │   ├── user.py                 # User ORM model
│   │   │   └── order.py                # Order ORM model (JSONB items)
│   │   ├── api/v1/
│   │   │   ├── products.py             # GET /v1/products
│   │   │   └── chat.py                 # POST /v1/chat (SSE streaming) + GET /v1/chat/history/{session_id}
│   │   ├── agents/customer_support/
│   │   │   ├── graph.py                # LangGraph agent graph (Claude + ToolNode)
│   │   │   └── tools.py                # lookup_order, get_product_info, search_faq
│   │   ├── rag/
│   │   │   ├── ingest.py               # Chunk docs → Gemini embeddings → pgvector
│   │   │   └── docs/                   # Knowledge base markdown files
│   │   │       ├── return-policy.md
│   │   │       ├── shipping-policy.md
│   │   │       ├── warranty-terms.md
│   │   │       └── product-faqs.md
│   │   └── static/
│   │       └── chat.html               # Simple chat UI for testing
│   ├── alembic/                        # Database migrations
│   ├── pyproject.toml
│   ├── evals/
│   │   ├── datasets/
│   │   │   └── stage4_golden.jsonl   # Golden eval cases
│   │   ├── run_eval.py               # Runs real LangGraph agent on eval cases
│   │   └── score_results.py          # Deterministic scoring + category summary
│   └── .env.example
├── infra/
│   └── docker-compose.yml              # pgvector/pgvector:pg17
└── docs/
    └── AbhiMart_Master_Plan.md

```

## Local development

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- [uv](https://docs.astral.sh/uv/)
- Python 3.12+
- Google Gemini API key (for embeddings + LLM)
- LangSmith API key (for tracing)

### Setup

```bash
# 1. Start Postgres (pgvector-enabled)
docker compose -f infra/docker-compose.yml up -d

# 2. Install Python dependencies
cd backend
uv sync

# 3. Create .env from template
cp .env.example .env
# Fill in GEMINI_API_KEY, LANGSMITH_API_KEY, DATABASE_URL, etc.

# 4. Run database migrations
uv run alembic upgrade head

# 5. Seed the database
uv run python -m app.seed

# 6. Index knowledge base docs into pgvector
uv run python -m app.rag.ingest

# 7. Start the dev server
uv run uvicorn app.main:app --reload
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |
| GET | `/v1/products` | List all products |
| POST | `/v1/chat` | Streaming SSE chat (LangGraph agent) |
| GET | `/v1/chat/history/{session_id}` | Conversation history |
| GET | `/static/chat.html` | Simple chat UI |
