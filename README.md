# AbhiMart

AI customer support agent for a fictional e-commerce store.

Learning-focused project covering full-stack AI engineering: agent loop, RAG,
multi-agent orchestration, durable execution, evals, observability, guardrails,
and production deployment.

## Project docs

See [Evaluation](docs/evaluation.md) for the current agent eval harness, golden
dataset, LangSmith experiment workflow, and Stage 4 evaluation learning guide.

See [Observability Notes](docs/observability.md) for the project explanation of
OpenTelemetry, traces/spans/metrics/logs, and how observability fits alongside
LangSmith.

See [Guardrails Notes](docs/guardrails.md) for Stage 5 safety concepts such as
PII, prompt injection, tool misuse, write actions, and human-in-the-loop
approval.

See [RAG And Enterprise Document Intelligence Notes](docs/rag_document_intelligence.md)
for deeper RAG concepts such as rerankers, question parsing, expert
dictionaries, deterministic dispatch, corpus indexes, and auditability.

See [Interview Prep Guide](docs/AbhiMart_Interview_Prep_Guide.md) for the
end-to-end explanation of what has been built so far, why each concept exists,
how AbhiMart uses it, and how to discuss the project honestly in interviews.

See [EPAM Python GenAI Interview Playbook](docs/AbhiMart_EPAM_Python_GenAI_Interview_Playbook.md)
for a focused recruiter/interviewer storytelling guide, practice scripts,
trade-offs, failure modes, and honest project positioning.

See [Order Preparation And Inventory Conflict Plan](docs/order_preparation_inventory_plan.md)
for the proposed Stage 7 design covering custom exceptions, insufficient-stock
handling, race conditions, and simulated order preparation.

## Status

| Stage | Description | Status |
|-------|-------------|--------|
| Stage 0 | Scaffolding, infrastructure, DB, first migration | Complete |
| Stage 1 | LangGraph agent + streaming SSE chat API | Complete |
| Stage 2 | Tools (order lookup, product info) + Postgres-backed memory | Complete |
| Stage 3 | RAG pipeline - pgvector + Gemini embeddings + `search_faq` tool | Complete |
| Stage 4 | Eval harness, LangSmith experiments, LLM-as-judge checks, OpenTelemetry, Jaeger, logs, and metrics | Complete |
| Stage 5 | Guardrails, refund approval gate, and human-in-the-loop write-action safety | Complete |
| Stage 6 | React frontend foundation + production deployment | Frontend foundation in progress; deployment planned |
| Stage 7 | Simulated order preparation with inventory conflict handling | Proposed |

## Stack

Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x async, asyncpg, Postgres 17
with pgvector, Alembic, structlog, Docker Compose, uv, LangGraph, LangChain,
Google Gemini, LangSmith, OpenTelemetry, Jaeger, Prometheus-compatible metrics,
React, TypeScript, and Vite.

Coming later: Redis and AWS deployment.

## Project structure

```text
abhimart/
|-- backend/
|   |-- app/
|   |   |-- config.py                   # Pydantic Settings
|   |   |-- database.py                 # Async SQLAlchemy engine/session
|   |   |-- main.py                     # FastAPI app and LangGraph wiring
|   |   |-- seed.py                     # Seed products, users, orders
|   |   |-- models/                     # SQLAlchemy ORM models
|   |   |-- api/v1/                     # Products and chat endpoints
|   |   |-- agents/customer_support/    # LangGraph graph and tools
|   |   |-- rag/                        # Knowledge base ingestion/docs
|   |   `-- static/chat.html            # Simple chat UI for testing
|   |-- alembic/                        # Database migrations
|   |-- evals/
|   |   |-- datasets/stage4_golden.jsonl
|   |   |-- datasets/policy_decision_golden.jsonl
|   |   |-- run_eval.py
|   |   |-- score_results.py
|   |   |-- judge_results.py
|   |   |-- run_policy_decision_eval.py
|   |   |-- langsmith_dataset.py
|   |   `-- langsmith_run.py
|   |-- pyproject.toml
|   `-- .env.example
|-- docs/
|   |-- evaluation.md
|   |-- guardrails.md
|   `-- observability.md
`-- infra/
    `-- docker-compose.yml
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
| POST | `/v1/chat/resume` | Resume a paused human-in-the-loop chat run |
| GET | `/v1/chat/history/{session_id}` | Conversation history |
| GET | `/static/chat.html` | Simple chat UI |

## Refund Approval Demo

Start the backend:

```bash
cd backend
uv run uvicorn app.main:app --reload
```

In another terminal, run the HTTP probe:

```bash
cd backend
uv run python evals/chat_api_hitl_probe.py
```

The probe sends a refund request to `/v1/chat`, verifies the SSE interrupt event,
then resumes the same session through `/v1/chat/resume`.

You can also try the browser demo at:

```text
http://127.0.0.1:8000/static/chat.html
```

Ask:

```text
My email is rohit@example.com. Please start a refund for my MacBook order.
```

The page should show a refund approval card. Approve or reject it to resume the
paused graph run.
