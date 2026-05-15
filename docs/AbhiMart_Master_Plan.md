# AbhiMart — Master Plan & Learning Journey

**Document version:** 1.0
**Last updated:** May 12, 2026
**Owner:** Abhi
**Purpose:** Complete portable context for the AbhiMart AI agent project. Any LLM or collaborator picking this up should be able to read this document and know exactly what's being built, why, where the learner is, and what comes next.

---

## Section 1 — Context for the next LLM/collaborator

### Who Abhi is

Full-stack developer transitioning to AI Engineering. Target roles: AI Engineer, Full Stack AI Developer, LLM Application Engineer. Currently between jobs, can dedicate **6-8 hours/day, sustainable pace**.

**Existing strengths:**

- Solid Python (functions, classes, async/await, type hints — comfortable)
- React fundamentals (components, props, state — comfortable)
- HTML/CSS comfortable
- Has written FastAPI before (basic level)
- HTTP fundamentals comfortable
- AWS basic familiarity (has account, used some services)
- **Strong AI/agent foundations** — already studied: LangGraph state, agent loops, Runnable protocol, RAG indexing/retrieval, tool decorators, structured output, RAG agent vs chain, Corrective/Self-RAG, indirect prompt injection. Has detailed self-maintained RAG_Reference_Notes.md.
- LangSmith — used it

**Gaps to fill (these are teaching priorities):**

- Decorators, context managers — heard of, needs hands-on
- Dependency injection — needs explanation + practice
- Database fundamentals, SQL, ORM concept — **no idea**, this is the biggest gap
- Message queues — **no idea**
- Caching — **no idea**
- Docker / Docker Compose — heard of, needs hands-on
- Pydantic models — heard of, needs the "why" + practice
- SQLAlchemy — heard of, needs the "why" + practice
- REST API design principles, JSON serialization — heard of
- Authentication (sessions, JWT, OAuth2) — heard of
- TypeScript — heard of, needs the "why"
- React hooks beyond basics — heard of (and React 19 has new ones to learn)
- Redux / state management — heard of
- React Router — heard of
- LangGraph checkpointing with Postgres — never used
- LangGraph middleware (new v1 concept) — never used
- `create_agent` API (LangChain v1) — never used
- Embeddings & vector stores hands-on — only conceptual
- Evaluation frameworks (LangSmith evals, ragas, DeepEval) — never used
- AWS deeper (IAM, VPC, security groups) — heard of
- Kubernetes — heard of
- GitHub Actions / CI/CD — heard of
- Observability three pillars (logs/metrics/traces) — needs examples
- OpenTelemetry — **no idea**

### How Abhi learns best

- Wants to understand the *why* before the *how*
- Prefers layered explanations: analogy first, then technical precision
- Likes Q&A-style reference notes he can save (RAG_Reference_Notes.md is his model — bold Q&A format, README-style)
- Builds mental models incrementally: end goal first, then component-by-component with comprehension checks
- Hates tutorial loops — wants to build one real thing and iterate
- Wants to know the latest stable versions, not outdated tutorials
- Wants production-grade patterns from day one, not "we'll add real stuff later"

### What we're building

**AbhiMart** — a fake e-commerce store selling:

1. Electronics (laptops, phones, accessories)
2. Home appliances (kitchen gear, vacuums, air purifiers)
3. Fitness equipment (treadmills, weights, wearables)
4. Books & stationery

We're building an **AI customer support agent** for this store. The agent:

- Answers product questions (RAG over product docs/FAQs)
- Looks up orders for the asking customer
- Processes refunds with human-in-the-loop approval
- Escalates to human agents when stuck
- Multi-tenant aware (each customer only sees their own orders)
- Streams responses in real time
- Survives crashes mid-conversation (durable execution)
- Has guardrails, observability, evals, the full production harness

Why customer support? Because **every concept Abhi needs to learn has a natural reason to appear in this domain.** No bolted-on features. RAG (product docs), tools (order lookup), write actions (refunds), HITL (refund approval), multi-tenancy (per-customer data), guardrails (PII, prompt injection), evals (correctness), observability (debugging) — all organic to the use case.

### Why this scope (the "don't get stuck in tutorial loops" rule)

This is **not a portfolio project optimized for resume bullets**. This is a learning journey where Abhi writes every line of code, understands why each piece exists, and ends knowing what a senior AI engineer knows because he built it.

The project will take **6-9 months at sustainable pace**. That's intentional. Faster = shallower understanding.

---

## Section 2 — The four-layer mental model

Every concept in this project sits in one of four layers. Keep this mental model when explaining anything:

```
┌─────────────────────────────────────────────────┐
│  Layer 1: AGENT (the loop)                      │
│  observe → plan → act → verify → repeat         │
│  This is what the LLM does.                     │
├─────────────────────────────────────────────────┤
│  Layer 2: HARNESS (engineering around model)    │
│  Prompts, tools, skills, memory, RAG,           │
│  guardrails, evals, observability               │
│  This is the AI-specific engineering.           │
├─────────────────────────────────────────────────┤
│  Layer 3: RUNTIME (production infrastructure)   │
│  Durable execution, multi-tenancy, HITL,        │
│  streaming, time travel, sandboxes, cron        │
│  This is what keeps agents running in prod.     │
├─────────────────────────────────────────────────┤
│  Layer 4: SYSTEM (still software)               │
│  Queues, rate limits, fallbacks, consistency,   │
│  load balancing, caching, observability,        │
│  microservices, databases, deployment           │
│  This is normal backend engineering.            │
└─────────────────────────────────────────────────┘
```

**The Razorpay engineer's insight:** Layer 4 is what most AI tutorials skip and where most AI products fail in production. We build all four layers.

---

## Section 3 — Tech stack (pinned versions, current as of May 2026)

### Backend

| Component | Choice | Version | Why |
|---|---|---|---|
| Language | Python | 3.12 | Modern syntax, mature ecosystem |
| Web framework | FastAPI | 0.136.1 | Auto OpenAPI docs, async-first, Pydantic v2 native, industry standard for Python APIs in 2026 |
| Server | Uvicorn | latest | ASGI server FastAPI runs on |
| Validation | Pydantic | 2.7+ | Rust-backed core, 5-50x faster than v1, type-safe schemas |
| ORM | SQLAlchemy | 2.x async | Industry standard, async-native in 2.x |
| DB driver | asyncpg | latest | Async Postgres driver |
| Migrations | Alembic | 1.13+ | Standard with SQLAlchemy |
| Database | PostgreSQL | 16 | OLTP store + vector store (via pgvector extension) |
| Vector extension | pgvector | latest | pgvector inside Postgres — one fewer service to run |
| Cache / broker | Redis | 7 | Caching, rate limiting, Celery broker |
| Task queue | Celery | 5.x | Industry standard; Redis as broker |
| Settings | pydantic-settings | 2.x | Typed config from env |
| HTTP client | httpx | latest | Async-native, modern alternative to requests |
| Retries | tenacity | latest | Decorator-based retry logic |
| Logging | structlog | latest | Structured JSON logging |
| Testing | pytest, pytest-asyncio, testcontainers | latest | Standard Python test stack |

### AI / Agents

| Component | Choice | Version | Why |
|---|---|---|---|
| Agent framework | LangGraph | 1.1.10+ | v1.0 launched Oct 2025, durable execution, checkpointing, middleware |
| Higher-level abstractions | LangChain | 1.x | New `create_agent` API + middleware system |
| Primary model | Claude (Anthropic) | claude-opus-4-7 / claude-sonnet-4-6 | Strong reasoning, tool use |
| Fallback model | OpenAI GPT-4 family | latest | Provider redundancy |
| Embeddings | OpenAI text-embedding-3-large (initial), Bedrock Titan later | — | Standard, cheap |
| Reranker | Cohere Rerank or cross-encoder | — | Added Stage 4+ |
| Observability | LangSmith | latest | Tracing, datasets, evals, time-travel debugging |
| Production inference (later) | AWS Bedrock | — | Same models, AWS-routed for prod |

### Frontend (intentionally scoped)

| Component | Choice | Version | Why |
|---|---|---|---|
| Framework | React | 19.2.6 | Latest. New hooks (`use`, `useActionState`, `useOptimistic`, `useFormStatus`), ref-as-prop |
| Build tool | Vite | 6.x | Fast dev server, modern bundler |
| Language | TypeScript | 5.x | Type safety mirrors Pydantic schemas |
| Styling | Tailwind CSS + shadcn/ui | latest | Quick to build, looks professional |
| Server state | TanStack Query (React Query) | v5 | Server state caching, modern default |
| Forms | react-hook-form + zod | latest | Validation that mirrors Pydantic |
| Routing | React Router | 7.x | Standard |
| Streaming | Native EventSource | — | SSE consumption |

**Explicitly NOT including in v1:** Redux, complex routing patterns, SSR, micro-frontends. Reason: those don't add to AI engineering profile.

### Infrastructure

| Component | Choice | Why |
|---|---|---|
| Local orchestration | Docker Compose | One `docker compose up` brings the whole stack up |
| Containerization | Docker | Multi-stage builds, non-root users |
| CI/CD | GitHub Actions | Lint → typecheck → test → build → deploy |
| Tracing | OpenTelemetry SDK + collector | Industry standard for traces/metrics/logs |
| Trace viewer | Jaeger or Tempo | Local trace UI |
| Metrics | Prometheus | Metrics scraping |
| Dashboards | Grafana | Visualization |
| Cloud (later, Stage 7+) | AWS — ECS Fargate, RDS Postgres, ElastiCache Redis, S3, Secrets Manager, CloudWatch, ALB, Bedrock | Industry standard |

### Reference architectures we're following

- **Anthropic's multi-agent research system** — orchestrator + parallel subagents pattern (Stage 6)
- **Exa's deep research agent** — LangGraph-based planner/tasks/observer pattern (Stage 6)
- **LangChain runtime post** — durable execution, time travel, multi-tenancy, HITL primitives
- **OpenTelemetry demo** — service interconnection patterns (NOT forked, used as reference)
- **FastAPI full-stack template** — project structure (NOT forked, used as reference)

---

## Section 4 — Final project folder structure (target state)

This is what the repo looks like at Stage 8 (end state). We build toward this, not start with it.

```
abhimart/
├── backend/
│   ├── pyproject.toml
│   ├── alembic/                      # DB migrations
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── main.py                   # FastAPI entry point
│   │   ├── config.py                 # Pydantic Settings
│   │   ├── api/                      # Route handlers (controllers)
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── orders.py
│   │   │   │   ├── products.py
│   │   │   │   ├── chat.py           # Agent conversation endpoints (SSE/WS)
│   │   │   │   └── webhooks.py
│   │   │   └── deps.py               # FastAPI dependencies
│   │   ├── core/                     # Cross-cutting concerns
│   │   │   ├── security.py           # JWT, password hashing
│   │   │   ├── logging.py            # Structured logging setup
│   │   │   ├── tracing.py            # OpenTelemetry setup
│   │   │   ├── errors.py             # Exception handlers
│   │   │   └── middleware.py         # CORS, request ID, etc.
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── order.py
│   │   │   ├── product.py
│   │   │   └── conversation.py
│   │   ├── schemas/                  # Pydantic request/response schemas
│   │   ├── repositories/             # Data access layer
│   │   ├── services/                 # Business logic layer
│   │   ├── agents/                   # AI agent code
│   │   │   ├── customer_support/
│   │   │   │   ├── graph.py          # LangGraph graph definition
│   │   │   │   ├── state.py          # Agent state schema
│   │   │   │   ├── nodes.py          # Graph nodes
│   │   │   │   ├── middleware.py     # LangChain middleware (guardrails)
│   │   │   │   └── prompts/          # Versioned prompt files
│   │   │   ├── tools/                # @tool-decorated functions
│   │   │   │   ├── read_tools.py     # lookup_order, search_faq, get_product
│   │   │   │   └── write_tools.py    # process_refund, create_ticket, escalate
│   │   │   ├── rag/                  # Retrieval pipeline
│   │   │   │   ├── ingest.py
│   │   │   │   ├── retrieve.py
│   │   │   │   └── chunking.py
│   │   │   └── memory/               # Long-term memory store
│   │   ├── tasks/                    # Celery tasks
│   │   │   ├── celery_app.py
│   │   │   ├── agent_tasks.py        # Long-running agent runs
│   │   │   └── scheduled.py          # Cron jobs
│   │   └── tests/
│   │       ├── unit/
│   │       ├── integration/
│   │       └── e2e/
│   ├── evals/                        # Eval suite (separate from tests)
│   │   ├── datasets/                 # Golden datasets
│   │   ├── judges/                   # LLM-as-judge prompts
│   │   └── runners/
│   └── Dockerfile
├── frontend/
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── routes/
│   │   ├── components/
│   │   │   ├── ui/                   # shadcn/ui primitives
│   │   │   ├── chat/                 # Chat UI components
│   │   │   ├── approval/             # HITL approval UI
│   │   │   └── orders/
│   │   ├── hooks/                    # Custom React hooks
│   │   ├── lib/
│   │   │   ├── api.ts                # Typed API client
│   │   │   ├── auth.ts
│   │   │   └── sse.ts                # SSE streaming logic
│   │   ├── types/                    # TypeScript types
│   │   └── styles/
│   └── Dockerfile
├── infra/
│   ├── docker-compose.yml            # All services for local dev
│   ├── docker-compose.observability.yml  # Otel collector, Jaeger, Prom, Grafana
│   ├── otel-collector-config.yaml
│   ├── prometheus.yml
│   └── grafana/
│       └── dashboards/
├── docs/
│   ├── architecture.md
│   ├── runbook.md
│   └── adr/                          # Architecture decision records
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── deploy.yml
│       └── evals.yml
└── README.md
```

### Local Docker Compose service map (end state)

```
┌────────────────┐     ┌─────────────────┐
│   Frontend     │     │   FastAPI       │
│   (Vite dev)   │────▶│   Backend       │
│   :5173        │     │   :8000         │
└────────────────┘     └─────────┬───────┘
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        ▼                        ▼                        ▼
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  Postgres    │         │   Redis      │         │  Celery      │
│  + pgvector  │         │  (cache,     │         │  Workers     │
│  :5432       │         │   broker)    │         │              │
└──────────────┘         └──────────────┘         └──────┬───────┘
                                                          │
                                                          ▼
                              ┌──────────────────────────────────┐
                              │   OpenTelemetry Collector        │
                              │   :4317 (gRPC) :4318 (HTTP)      │
                              └────┬─────────────┬───────────────┘
                                   │             │
                                   ▼             ▼
                              ┌─────────┐  ┌──────────┐
                              │ Jaeger  │  │Prometheus│
                              │ :16686  │  │  :9090   │
                              └─────────┘  └────┬─────┘
                                                │
                                                ▼
                                          ┌──────────┐
                                          │ Grafana  │
                                          │  :3000   │
                                          └──────────┘
```

---

## Section 5 — Stage 0: Foundations (Weeks 1-2)

**Goal:** Build a non-agent CRUD API for the AbhiMart product catalog. No LLM involvement yet. Purpose is to make the backend stop being mysterious — by the end of Stage 0, Abhi has written SQL, designed schemas, used migrations, built REST endpoints, run Docker Compose, and connected a Python service to Postgres.

### Concepts introduced

**Python depth refresher:**

- Decorators: how `@decorator` works, why FastAPI uses them, building one from scratch
- Context managers: `with` statement, why `async with` exists, building one
- Dependency injection: what it means, how FastAPI's `Depends()` works, why it's better than globals

**Database fundamentals:**

- What a table is, primary keys, foreign keys
- One-to-many, many-to-many relationships (User → Orders, Order ↔ Products)
- SQL: SELECT, INSERT, UPDATE, DELETE, JOIN, WHERE, GROUP BY
- Transactions: ACID, why they matter
- Indexes: when to add them, what they cost
- N+1 query problem and how ORMs cause it

**ORM concept (SQLAlchemy 2.x async):**

- Why ORMs exist (mapping Python objects to rows)
- Declarative models with `Mapped` type annotations
- Sessions, transactions, `commit()` and `rollback()`
- Eager vs lazy loading
- Why async ORMs need async drivers (asyncpg)

**Migrations (Alembic):**

- Why we don't `CREATE TABLE` in code
- Generating and applying migrations
- Reversibility

**Pydantic deep-dive:**

- Why it exists (runtime validation from type hints)
- BaseModel, Field, validators
- Separating ORM models from API schemas (DTO pattern)
- `from_attributes=True` for ORM serialization

**FastAPI patterns:**

- Project structure (controllers → services → repositories)
- Path/query/body params
- Response models
- Dependency injection patterns
- Exception handlers
- OpenAPI auto-docs

**REST API design:**

- Resource-oriented URLs (`/products/{id}`, not `/getProduct?id=`)
- HTTP method semantics (GET vs POST vs PUT vs PATCH vs DELETE)
- Status codes that matter (200, 201, 204, 400, 401, 403, 404, 409, 422, 500)
- Pagination patterns
- Versioning (`/v1/`)

**Docker basics:**

- Image vs container
- Dockerfile structure, multi-stage builds
- Volumes, networks, ports
- Docker Compose for multi-service local dev
- Why we run Postgres in a container locally

**Configuration management:**

- 12-factor app principles
- `.env` files for local
- Pydantic Settings for typed config

### Libraries introduced

- FastAPI, Uvicorn
- Pydantic v2, Pydantic Settings
- SQLAlchemy 2.x (async), asyncpg, Alembic
- pytest, pytest-asyncio
- Docker, Docker Compose

### What we build

A working AbhiMart product catalog API with:

- `POST /v1/products` — create product
- `GET /v1/products` — list with filtering, pagination
- `GET /v1/products/{id}` — get one
- `PATCH /v1/products/{id}` — update
- `DELETE /v1/products/{id}` — delete (soft delete)
- Postgres backing it
- Seed data for all 4 product categories (electronics, appliances, fitness, books)
- Alembic migrations
- Docker Compose running Postgres + FastAPI
- Basic pytest suite

### Stage 0 "done" criteria

- [ ] `docker compose up` spins up Postgres + FastAPI
- [ ] Can hit `http://localhost:8000/docs` and see Swagger UI
- [ ] Can create/list/update/delete products via Swagger
- [ ] Can run `alembic upgrade head` to create schema
- [ ] Can run `pytest` and all tests pass
- [ ] Can explain: why Pydantic, why SQLAlchemy, why migrations, what dependency injection means in FastAPI, what happens when you hit `GET /v1/products/{id}` (full request flow through controller → service → repository → DB)

### Reading list (priority order)

**Read these BEFORE coding:**

1. [FastAPI Tutorial - First Steps through Bigger Applications](https://fastapi.tiangolo.com/tutorial/) — sections 1-15
2. [SQLAlchemy 2.0 ORM Quickstart](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)
3. [Pydantic v2 Models](https://docs.pydantic.dev/latest/concepts/models/)

**Reference during coding:**

- [SQLAlchemy async ORM](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
- [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Docker Compose docs](https://docs.docker.com/compose/)

**Conceptual understanding:**

- [The Twelve-Factor App](https://12factor.net/)
- [REST API tutorial](https://restfulapi.net/)

---

## Section 6 — Stage 1: First agent that chats (Week 3)

**Goal:** A LangGraph agent that holds a conversation. No tools, no RAG yet. Just chat. Wired into FastAPI with SSE streaming.

### Concepts introduced

- LangGraph 1.x basics: `StateGraph`, nodes, edges, State schema with `Annotated[list, add_messages]`
- `create_agent` API (LangChain v1)
- The agent loop (observe → plan → act → verify)
- Why messages auto-append vs state fields overwrite
- ChatModel abstractions (provider-agnostic)
- Streaming: token-by-token output via async generators
- Server-Sent Events (SSE) in FastAPI
- LangSmith setup: API key, project, traces appearing
- Async patterns in agent context: `astream()`, `ainvoke()`

### Libraries introduced

- LangGraph, LangChain, langchain-anthropic
- LangSmith SDK

### What we build

- A LangGraph agent with one node (the LLM call)
- A FastAPI endpoint `POST /v1/chat` that accepts a message and streams a response via SSE
- A simple HTML test page (no React yet) that consumes the SSE stream
- LangSmith tracing wired up — every agent run shows up in the dashboard
- Conversations stored in Postgres (we'll switch to LangGraph checkpointer in Stage 2)

### Stage 1 "done" criteria

- [ ] Can chat with the agent via the test page
- [ ] Response streams token-by-token
- [ ] Trace appears in LangSmith showing the full run
- [ ] Conversation history persists in Postgres across page reloads
- [ ] Can explain: what a LangGraph graph is, what state means, why we use SSE vs WebSocket here, how streaming actually works under the hood

### Reading list

**Before coding:**

1. [LangGraph quickstart](https://langchain-ai.github.io/langgraph/tutorials/introduction/)
2. [LangChain `create_agent`](https://docs.langchain.com/oss/python/langchain/agents) — the new v1 API
3. [LangSmith setup](https://docs.smith.langchain.com/)

**Reference:**

- [FastAPI SSE patterns](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)
- [LangGraph State](https://langchain-ai.github.io/langgraph/concepts/low_level/#state)

---

## Section 7 — Stage 2: Tools + memory + durable execution (Weeks 4-5)

**Goal:** The agent can look up orders and products. Conversations are durable (survive server restarts). Memory persists across sessions.

### Concepts introduced

- LangChain `@tool` decorator
- Pydantic schemas as tool argument validation
- Why structured output matters
- LangGraph Postgres checkpointer — durable execution
- Thread IDs as persistent cursors
- Short-term memory (in-thread) vs long-term memory (cross-thread)
- The LangGraph `store` for long-term memory
- Multi-tenancy basics: user_id in state, row-level filtering in tool implementations
- `interrupt()` and `Command(resume=...)` primitives (we'll use HITL properly in Stage 5)

### Libraries introduced

- `langgraph-checkpoint-postgres`
- Tool decorator from LangChain

### What we build

- Two read tools: `lookup_order(order_id)`, `get_product_info(product_name)` — both backed by the Stage 0 database
- Tools have Pydantic input schemas
- LangGraph Postgres checkpointer wired up — kill the server mid-conversation, restart, conversation continues
- A `users` table; conversations are tied to user_id
- The agent only sees orders belonging to the asking user (multi-tenancy)
- Seed data: 5 fake users, each with 3-10 orders

### Stage 2 "done" criteria

- [ ] "Where's my order #123?" works
- [ ] "Tell me about the laptop in the electronics section" works
- [ ] Conversation survives server restart
- [ ] User A can't see User B's orders even when asking for them
- [ ] Can explain: what checkpointing solves, how tool calls flow through the loop, why Pydantic schemas on tools matter, how the agent decides to call a tool vs respond directly

### Reading list

- [LangGraph persistence](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [LangGraph Postgres checkpointer](https://langchain-ai.github.io/langgraph/reference/checkpoints/#langgraph.checkpoint.postgres)
- [LangChain tools](https://docs.langchain.com/oss/python/langchain/tools)

---

## Section 8 — Stage 3: RAG (Weeks 6-7)

**Goal:** Agent answers product/policy questions by retrieving from a knowledge base.

### Concepts introduced

- Document loaders, splitters (`RecursiveCharacterTextSplitter`)
- Embeddings: what they are, dimensions, similarity
- pgvector: vector storage inside Postgres
- Hybrid retrieval: BM25 (Postgres full-text) + dense vector
- Reranking
- Citations and provenance
- Spotlighting (treating retrieved content as untrusted)
- RAG agent vs RAG chain (Abhi's notes cover this — we implement the agent version)
- Indexing pipeline as a separate concern from runtime retrieval

### Libraries introduced

- `langchain-postgres` (PGVector)
- `langchain-openai` (embeddings)
- `langchain-cohere` (rerank) — optional

### What we build

- Knowledge base: return policy docs, shipping FAQs, warranty terms, product manuals (we'll write fake content for all 4 categories)
- Indexing script: chunks docs, embeds them, stores in pgvector
- `search_faq(query)` tool that does hybrid retrieval + rerank
- Citations: every retrieved chunk carries metadata (source doc, section, last_updated)
- Spotlighting: retrieved content wrapped in `<retrieved_content>` tags in the prompt
- The agent now answers "what's your return policy for electronics?" with citations

### Stage 3 "done" criteria

- [ ] Indexing script runs and populates pgvector
- [ ] Agent answers policy questions with correct citations
- [ ] Hybrid search retrieves both semantic matches AND exact-keyword matches (product codes)
- [ ] Rerank improves relevance over raw similarity
- [ ] Can explain: chunking tradeoffs, why we need hybrid not just dense, what reranking adds, how spotlighting defends against prompt injection

### Reading list

- Abhi's own RAG_Reference_Notes.md (refresher)
- [pgvector docs](https://github.com/pgvector/pgvector)
- [LangChain RAG tutorial](https://docs.langchain.com/oss/python/langchain/rag) — current version

---

## Section 9 — Stage 4: Evaluation + observability (Weeks 8-9)

**Goal:** We can measure whether the agent is good. Every code change runs through an eval suite. Production traces feed back into improvement.

### Concepts introduced

- Active vs passive evals (the Razorpay framing — CI golden set vs online LLM-as-judge on prod traces)
- Golden datasets: how to build one, how to maintain it
- LLM-as-judge: the pattern, its risks, how to validate the judge
- Metrics: retrieval (recall@k, MRR), generation (faithfulness, citation correctness), end-to-end (task success)
- Trajectory evaluation: did the agent take the right steps, not just produce the right answer?
- LangSmith datasets and evaluators
- OpenTelemetry: traces, metrics, logs (the three pillars)
- Wiring OTel into FastAPI and LangGraph
- Reading traces: what to look for when things break

### Libraries introduced

- LangSmith eval SDK
- OpenTelemetry SDK + auto-instrumentation
- Jaeger, Prometheus, Grafana (via Docker Compose)

### What we build

- Golden dataset of 25-30 customer queries with expected behaviors
- Eval runner: runs the agent against the dataset, scores each run
- LLM-as-judge prompts for fuzzy correctness, validated against 10 human-labeled examples
- LangSmith dataset wired up
- OpenTelemetry instrumentation: traces flow from frontend → FastAPI → LangGraph → tools → DB
- Jaeger UI showing distributed traces
- Grafana dashboard: requests/sec, p50/p95 latency, error rate, tokens/conversation, cost/conversation

### Stage 4 "done" criteria

- [ ] Eval suite runs in <2 minutes locally
- [ ] Can answer "is the agent better or worse than last week?" with numbers
- [ ] Can pull up a Jaeger trace showing the full path of a single request
- [ ] Grafana dashboard live showing key metrics
- [ ] Can explain: why evals are different from tests, why LLM-as-judge needs validation, what the three pillars of observability are, why agent debugging needs both LangSmith and OTel

### Reading list

- [LangSmith evaluators](https://docs.smith.langchain.com/evaluation)
- [OpenTelemetry Python](https://opentelemetry.io/docs/languages/python/)
- [OpenTelemetry demo repo](https://github.com/open-telemetry/opentelemetry-demo) (reference, don't fork)

---

## Section 10 — Stage 5: Write actions + HITL + guardrails (Weeks 10-11)

**Goal:** The agent can process refunds, but a human approves first. Guardrails block PII leaks and prompt injection.

### Concepts introduced

- Read vs write tool separation
- Dry-run defaults
- Idempotency keys
- Approval gates (`interrupt()` + `Command(resume=...)`)
- LangChain middleware (v1 concept): `before_model`, `wrap_model_call`, `wrap_tool_call`, `after_model`
- Built-in middleware: `PIIRedactionMiddleware`, `ToolCallLimitMiddleware`, `SummarizationMiddleware`
- Custom middleware: cost ceilings, step budgets, rate limits
- Prompt injection defense: spotlighting (done in Stage 3), structural delimiters, output validation
- Audit logs

### Libraries introduced

- LangChain middleware
- presidio or custom Pydantic-based PII detection

### What we build

- `process_refund(order_id, amount, reason)` write tool
- The tool *proposes* the refund; the agent calls `interrupt()` to wait for human approval
- Frontend (still basic HTML for now) shows "Approve / Edit amount / Reject with reason" UI
- Idempotency: calling the refund tool twice with the same key = single refund
- Audit log: every write tool call recorded to a `audit_log` table
- PII redaction middleware: emails, card numbers, names redacted from logs/traces
- Step budget middleware: max 20 tool calls per conversation
- Cost ceiling: max $1.50 of token spend per conversation
- Structured output for refund decisions (Pydantic schemas, validation, fallback chain for invalid output)

### Stage 5 "done" criteria

- [ ] Customer can request a refund; agent proposes; you approve; refund completes
- [ ] Calling the tool with same idempotency key twice doesn't double-refund
- [ ] Trying to inject "ignore previous instructions" into a customer message doesn't work
- [ ] PII never appears in logs
- [ ] Agent stops after 20 tool calls even if it's confused
- [ ] Can explain: when middleware runs in the agent loop, why HITL is its own primitive (not just another tool), what structured output fallback chains do

### Reading list

- [LangChain middleware](https://docs.langchain.com/oss/python/langchain/middleware)
- [LangGraph interrupts](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/)

---

## Section 11 — Stage 6: Multi-agent + frontend (Weeks 12-14)

**Goal:** Refactor to multi-agent orchestrator pattern (Anthropic/Exa style). Build a real React frontend.

### Concepts introduced

- Multi-agent orchestrator-worker pattern (planner → parallel workers → observer)
- LangGraph subgraph composition (each worker is a compiled subgraph used as a node)
- When to use single-agent vs multi-agent (mostly: don't, until you have to)
- Subagent budgeting (don't spawn 50 for simple queries)
- The Anthropic pattern: 15x more tokens, 90% better on complex tasks
- Frontend depth: TypeScript, React 19 hooks (`use`, `useActionState`, `useOptimistic`), TanStack Query, SSE consumption from React, HITL approval UI

### Libraries introduced

- React 19, TypeScript, Vite, Tailwind, shadcn/ui, TanStack Query, react-hook-form, zod

### What we build

- Refactor agent: complex queries route through Planner → 2-4 parallel Workers (FAQ searcher, order looker-upper, policy checker) → Observer combines results
- Simple queries skip the multi-agent path (cheap fast path)
- Subagent budget: max 4 workers, dynamic per query complexity
- Real React frontend:
  - Login / register flow with JWT
  - Chat UI with streaming tokens
  - Tool calls rendered as expandable cards
  - HITL approval card with Approve/Edit/Reject buttons
  - Order history page
  - Product browse page
- TypeScript types generated from FastAPI's OpenAPI schema (`openapi-typescript`)
- Optimistic UI for sending messages

### Stage 6 "done" criteria

- [ ] Complex query like "compare laptops under $1000 with my warranty options" triggers multi-agent path with parallel workers
- [ ] Simple query like "what's your phone number" stays single-agent
- [ ] Frontend is usable end to end — login, chat, see tool calls, approve refunds
- [ ] Frontend feels real (streaming, optimistic updates, loading states)
- [ ] Can explain: when multi-agent earns its cost, what subgraph composition gives you, how TypeScript types stay in sync with backend, what TanStack Query does that fetch doesn't

### Reading list

- Re-read the [Anthropic multi-agent post summary](https://blog.langchain.com/exa/) (Exa case study)
- [LangGraph multi-agent tutorials](https://github.com/langchain-ai/langgraph/blob/main/docs/docs/tutorials/multi_agent/agent_supervisor.ipynb)
- [React 19 release notes](https://react.dev/blog/2024/12/05/react-19)
- [TanStack Query docs](https://tanstack.com/query/latest)
- [shadcn/ui](https://ui.shadcn.com/)

---

## Section 12 — Stage 7: Queues + scheduled jobs + cost engineering (Weeks 15-16)

**Goal:** Long-running tasks go to Celery. Cron jobs do proactive work. We track cost per feature, not per model. Model routing and fallbacks.

### Concepts introduced

- Message queues: what they are, why they exist, broker vs worker
- Celery + Redis as broker
- Sync vs async work: when to push to a queue
- Idempotent task design
- Sleep-time compute / proactive agents (nightly summaries, prep work)
- Cron jobs as first-class
- Cost attribution per feature (tag every LLM call)
- Model routing: cheap model for classification, expensive for reasoning
- Graceful fallback chains: primary model → fallback model → degraded mode → fail
- Prompt caching (Anthropic's prompt cache for system prompts and tool schemas)
- Semantic caching (have we seen this query recently?)

### Libraries introduced

- Celery, Celery Beat
- redis-py
- (Anthropic prompt cache is just an API parameter)

### What we build

- Long agent runs (>30s) get dispatched to Celery workers; the API returns immediately with a run_id; SSE streams progress
- Nightly cron: "summarize the day's tickets, surface trends"
- Every LLM call tagged with `feature_id` ("chat", "rerank", "judge", "summary")
- Per-feature cost dashboard in Grafana
- Model router: classifies query, routes simple ones to Haiku, complex to Opus
- Fallback: if Anthropic times out, fall back to OpenAI
- Anthropic prompt caching enabled on system prompts (long, static) → big cost win
- Semantic cache: Redis-backed; for "what's your return policy" type queries, serve cached answer if confidence high

### Stage 7 "done" criteria

- [ ] Long-running queries don't block the API thread
- [ ] Nightly cron runs and produces a summary
- [ ] Grafana dashboard shows cost per feature broken down
- [ ] When Claude is down (simulate by setting bad API key), agent falls back to OpenAI gracefully
- [ ] Prompt caching reduces system-prompt token costs by 80%+
- [ ] Semantic cache hits on repeated questions, saving full LLM call
- [ ] Can explain: when to use a queue vs async-in-process, why idempotency matters for tasks, the difference between prompt caching and semantic caching, how to design fallback chains that degrade gracefully

### Reading list

- [Celery docs](https://docs.celeryq.dev/)
- [Anthropic prompt caching](https://docs.claude.com/en/docs/build-with-claude/prompt-caching)

---

## Section 13 — Stage 8: Production deployment + CI/CD (Weeks 17-20)

**Goal:** Deploy to AWS. CI/CD pipeline. Production-grade configuration. Real users could use this.

### Concepts introduced

- AWS IAM, VPC, security groups
- ECS Fargate vs EKS vs Lambda — when to use what
- RDS Postgres with pgvector
- ElastiCache Redis
- ALB and HTTPS via ACM
- Secrets Manager for credentials
- CloudWatch for logs
- AWS Bedrock for hosted models
- GitHub Actions CI/CD: lint → typecheck → test → eval → build → deploy
- Eval suite blocking deploys
- Blue/green or canary deploys
- Health checks and rollback

### Libraries introduced

- boto3, aws-cdk (Python) for infra-as-code
- GitHub Actions workflows
- AWS Bedrock SDK

### What we build

- Production infrastructure on AWS (managed via CDK):
  - ECS Fargate service for FastAPI
  - ECS Fargate service for Celery workers
  - RDS Postgres (with pgvector extension)
  - ElastiCache Redis
  - ALB with HTTPS
  - S3 for documents
  - Secrets Manager for API keys
- GitHub Actions:
  - On PR: lint, typecheck, unit tests, integration tests, eval suite
  - On merge to main: build images, deploy to staging
  - Manual approval: deploy to production
  - Evals must pass for deploy to proceed
- Frontend deployed to CloudFront + S3
- Health checks, CloudWatch alarms, basic SRE setup

### Stage 8 "done" criteria

- [ ] Public URL where anyone can use the agent
- [ ] CI runs on every PR and catches regressions
- [ ] Eval failures block deploys
- [ ] Can roll back a bad deploy in <5 minutes
- [ ] Can explain: why we chose Fargate over Lambda for this workload, what RDS gives us over self-managed Postgres, how the deploy pipeline enforces quality gates

### Reading list

- [AWS CDK Python](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html)
- [GitHub Actions docs](https://docs.github.com/en/actions)
- [Bedrock developer guide](https://docs.aws.amazon.com/bedrock/)

---

## Section 14 — Concept coverage matrix (the "did we cover everything" check)

Cross-reference of every concept from the four source PDFs + Razorpay X insights vs which stage it appears in:

| Concept | Stage |
|---|---|
| **Python depth** (decorators, context managers, DI, async patterns) | 0 |
| **HTTP, REST, JSON, status codes** | 0 |
| **Pydantic** (why, BaseModel, validation, DTOs) | 0 |
| **SQLAlchemy 2.x async** (ORM, sessions, queries) | 0 |
| **Database fundamentals** (tables, joins, transactions, indexes, N+1) | 0 |
| **Alembic migrations** | 0 |
| **Docker, Docker Compose** | 0 |
| **12-factor config** | 0 |
| **FastAPI patterns** (controllers/services/repositories, DI) | 0 |
| **OpenAPI docs** | 0 |
| **pytest, async testing** | 0 |
| **LangGraph basics** (State, nodes, edges) | 1 |
| **`create_agent` API** (v1) | 1 |
| **LangChain ChatModel abstractions** | 1 |
| **Streaming** (SSE, async generators) | 1 |
| **LangSmith tracing** | 1 |
| **`@tool` decorator** | 2 |
| **Tool schemas (Pydantic on tools)** | 2 |
| **LangGraph Postgres checkpointer** | 2 |
| **Durable execution** | 2 |
| **Short-term vs long-term memory** | 2 |
| **Multi-tenancy basics** | 2 |
| **RAG**: chunking, embeddings, pgvector, hybrid retrieval, reranking, citations | 3 |
| **Spotlighting** (prompt injection defense) | 3 |
| **Indexing pipeline** | 3 |
| **Evals**: golden datasets, LLM-as-judge, judge validation | 4 |
| **Active vs passive evals** | 4 |
| **OpenTelemetry**: traces, metrics, logs | 4 |
| **Three pillars of observability** | 4 |
| **Jaeger, Prometheus, Grafana** | 4 |
| **Read vs write tools** | 5 |
| **Dry-run, idempotency keys** | 5 |
| **Human-in-the-loop** (`interrupt()`, `Command(resume=...)`) | 5 |
| **LangChain middleware** (v1) | 5 |
| **Guardrails** (input, inline, output) | 5 |
| **PII redaction** | 5 |
| **Structured output fallback chains** | 5 |
| **Step budgets, cost ceilings** | 5 |
| **Audit logs** | 5 |
| **Multi-agent orchestrator pattern** (Anthropic/Exa) | 6 |
| **Subagent budgeting** | 6 |
| **LangGraph subgraph composition** | 6 |
| **React 19 + TypeScript** | 6 |
| **TanStack Query, react-hook-form, zod** | 6 |
| **Message queues** (Celery + Redis) | 7 |
| **Scheduled jobs** (cron, sleep-time compute) | 7 |
| **Cost attribution per feature** | 7 |
| **Model routing** | 7 |
| **Graceful fallback chains** | 7 |
| **Prompt caching** (Anthropic) | 7 |
| **Semantic caching** (Redis-backed) | 7 |
| **AWS deployment** (ECS, RDS, ElastiCache, ALB) | 8 |
| **IAM, VPC, security groups** | 8 |
| **Bedrock** | 8 |
| **CI/CD with eval gates** | 8 |
| **Infrastructure-as-code** (CDK) | 8 |

### Concepts deliberately NOT in this project (out of scope)

These appear in the source materials but won't be built. Abhi should know they exist, but they're irrelevant for an AI engineer at the application layer:

- KV cache management at scale (model-serving concern)
- Speculative decoding (model-serving concern)
- Quantization (model training/serving concern)
- Fine-tuning (we'll write a one-page README explaining why ICL+RAG beats it for our use case)
- Redux, complex SSR, micro-frontends (frontend depth beyond what AI eng roles need)
- Kubernetes (Fargate is easier, and the differences are not load-bearing for AI eng)
- A2A protocol (MCP covers the interop story for now)
- Custom sandbox infrastructure beyond Docker network egress controls

---

## Section 15 — How to use this document

### For Abhi

- This is your north star. Refer back to it whenever you're lost.
- At the end of each stage, update the "Current state" section below with what you completed, what surprised you, what failed, what you learned. This becomes your story for interviews.
- Don't read ahead. Each stage's reading list is what you need for that stage. Reading Stage 7 material during Stage 2 wastes time.
- When you find yourself in a tutorial loop or rabbit hole, close the tab and come back to the stage's "done criteria." If you can hit those, move on.

### For a future LLM picking this up

- Read all 15 sections before responding to Abhi.
- Abhi's existing RAG_Reference_Notes.md is in his project files — that's his learning style and depth model. Match that style.
- Don't restart the planning. The plan is done. Code, teach, debug, but don't re-plan unless Abhi explicitly asks.
- Match Abhi's tone: direct, no fluff, why-before-how, real-code-not-toy-code.
- When Abhi gets stuck, default to teaching the concept properly, not just fixing the code.
- The four source PDFs in chat history (Siagian Agentic AI roadmap, AI Harness Engineering handbook, Anthropic multi-agent research system, LangChain runtime post) are the conceptual ground truth.
- Current stage and progress: see Section 16.

### Pace expectations

- 6-8 hours/day, sustainable
- 20 weeks (5 months) total at this pace
- Stage 0: 2 weeks
- Stages 1-3: 5 weeks
- Stages 4-5: 4 weeks
- Stages 6-7: 5 weeks
- Stage 8: 4 weeks
- This will slip. Plan for 6-9 months total. That's fine.

---

## Section 16 — Current state (update as we go)

**Current stage:** Stage 4 — Evaluation + observability, local eval harness complete; LangSmith experiments next

**Stage 0 status:** Complete

**Stage 1 status:** Complete

**Stage 2 status:** Complete

**Stage 3 status:** Complete

**Stage 4 status:** In progress

**Latest progress update — May 15, 2026:**

- Built the first local Stage 4 eval harness under `backend/evals/`.
- Added `datasets/stage4_golden.jsonl` with 8 golden customer-support examples covering:
  - policy/RAG behavior
  - order lookup behavior
  - product lookup behavior
  - cross-customer privacy/safety behavior
- Added `run_eval.py` to run the real LangGraph agent against the golden dataset, isolate memory per example with `InMemorySaver`, capture tool calls/final answers from LangGraph event streams, and save JSONL results.
- Added `score_results.py` with deterministic evaluators for:
  - required tool usage
  - forbidden tool usage
  - source citation checks
  - required phrase checks
  - flexible phrase-group checks via `must_mention_any`
  - required clarification checks
  - policy stance checks
  - category-level pass-rate reporting
- Current local baseline: all 8 golden cases pass behaviorally after evaluator calibration.
- Synced the golden dataset to LangSmith as `abhimart-stage4-golden`.
- Added `langsmith_run.py` to run the real LangGraph agent as a LangSmith experiment with deterministic evaluator scoring.
- Latest inspected LangSmith experiments ran all 8 examples successfully; deterministic scores exposed expected model variability in the return-policy used-item case.
- Added public-facing `docs/evaluation.md` documenting the eval harness, local commands, LangSmith workflow, current baseline, and known flaky policy-reasoning case.
- Added structured policy eligibility classifier in `app/agents/customer_support/policy.py`.
- Added subcomponent evals for the policy classifier:
  - `datasets/policy_decision_golden.jsonl`
  - `run_policy_decision_eval.py`
  - current result: 3/3 passing
- Added `assess_return_eligibility` as a higher-level agent tool that retrieves the full return policy, calls the structured classifier, and returns a decision for final response generation.
- Updated `chat.py` and `run_eval.py` to filter nested model stream events so structured-output JSON from internal tool calls is not sent as customer-facing text.
- Latest full local eval suite after wiring structured eligibility: 8/8 passing.
- Latest inspected LangSmith experiment after syncing the updated dataset and filtering nested model streams: 8/8 passing.
- Improved the customer-support system prompt in `app/agents/customer_support/graph.py` so policy answers:
  - use `search_faq`
  - treat retrieved policy text as source of truth
  - apply all eligibility conditions
  - explicitly handle opened/used/installed/assembled/damaged/missing-packaging conditions
  - cite exact source filenames such as `[Source: return-policy.md]`
- Important learning: the first return-policy failure was not retrieval. The agent retrieved/cited the right policy but synthesized it too permissively. This was diagnosed as a policy-reasoning/synthesis failure and fixed through targeted prompt changes plus better evaluator checks.
- Next Stage 4 work:
  - compare prompt/model versions over time in LangSmith
  - add LLM-as-judge only for semantic checks that deterministic evaluators cannot cover cleanly
  - use LangSmith experiment comparisons to track future prompt/model/tool changes
  - begin observability work beyond LangSmith, especially OpenTelemetry/logs/metrics/traces

**Decisions locked:**

- Store name and categories chosen (AbhiMart: electronics, home appliances, fitness equipment, books & stationery)
- Stack: Python 3.12, FastAPI 0.136+, Pydantic v2, SQLAlchemy 2.x async, Postgres + pgvector, Redis, LangGraph 1.x, LangChain 1.x, React 19, TypeScript, Vite, Tailwind, shadcn/ui
- Local dev via Docker Compose from day 1
- Frontend deliberately scoped (no Redux, no SSR complexity)
- Build everything ourselves; FastAPI full-stack template and OpenTelemetry demo are *reference only*, not forked
- Stage 0 is non-agent prep (2 weeks) before any AI code
- Pace: 6-8 hours/day sustainable, 5-9 month total timeline

**What Abhi already knows (don't re-teach):**

- Python fundamentals, basic async/await, type hints, React components, HTTP, FastAPI basics
- All the AI/agent concepts in his RAG_Reference_Notes.md
- LangSmith conceptually

**What to teach in upcoming stages (priority order):**

1. Stage 0: decorators, context managers, DI, DB fundamentals, SQL, SQLAlchemy, Alembic, Docker, REST design, Pydantic depth
2. Stage 1: LangGraph 1.x, `create_agent`, SSE streaming, async streaming patterns
3. Stage 2: tool schemas hands-on, Postgres checkpointer, multi-tenancy basics
4. Stage 3: RAG hands-on (Abhi has theory, needs implementation), pgvector, hybrid search
5. Stage 4: LangSmith evals and OpenTelemetry from scratch
6. Stage 5: middleware (new v1 concept), HITL primitives
7. Stage 6: multi-agent patterns hands-on, full React 19 + TypeScript
8. Stage 7: Celery, cost engineering, model routing
9. Stage 8: AWS deeper (IAM, VPC), CI/CD with GitHub Actions

**Stage completion log:**

- [x] Stage 0 — Foundations
- [x] Stage 1 — First chatting agent
- [x] Stage 2 — Tools + memory + durable execution
- [x] Stage 3 — RAG
- [ ] Stage 4 — Evaluation + observability (in progress: local deterministic eval harness complete; LangSmith experiments next)
- [ ] Stage 5 — Write actions + HITL + guardrails
- [ ] Stage 6 — Multi-agent + frontend
- [ ] Stage 7 — Queues + scheduled jobs + cost engineering
- [ ] Stage 8 — Production deployment + CI/CD

---

## Section 17 — Glossary (so new LLMs/collaborators are calibrated)

- **AbhiMart** — the fake e-commerce store we're building the agent for
- **Agent** — a loop where an LLM decides what tool/action to take next
- **Harness** — engineering around the model: prompts, tools, memory, RAG, guardrails, evals, observability
- **Runtime** — production infrastructure under the harness: durable execution, multi-tenancy, HITL, etc.
- **Stage** — one of the 9 phases (0-8) of this learning journey
- **HITL** — Human-In-The-Loop
- **MCP** — Model Context Protocol (Anthropic's open standard for tool integration)
- **RAG** — Retrieval-Augmented Generation
- **SSE** — Server-Sent Events (HTTP streaming, one-way server→client)
- **LangGraph checkpointer** — durable state persistence for agent runs
- **Middleware (LangChain v1)** — code that runs at hooks in the agent loop (`before_model`, `wrap_tool_call`, etc.)
- **Golden dataset** — curated test cases for evaluating the agent
- **LLM-as-judge** — using an LLM to score another LLM's output
- **Active eval** — running eval suite in CI before merging
- **Passive eval** — running eval on production traces after the fact
- **Three pillars of observability** — logs, metrics, traces
- **OTel** — OpenTelemetry

---

*End of master plan. This document should be the single source of truth for the project. Update Section 16 as we progress.*
