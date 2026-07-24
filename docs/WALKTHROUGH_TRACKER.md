# AbhiMart Interview-Prep Walkthrough Tracker

> Living log of our review + refactor + interview-prep effort. Resume from here anytime.
> No code changes without your approval.

## Goal

Understand AbhiMart end-to-end, clean up structure, add improvements, and produce
crisp recall notes to defend it as senior-level production work in interviews.

## Legend

✅ Done · 🔄 In progress · ⬜ Not started · ⏸️ Parked

## Phases

| # | Phase | Status | Notes |
|---|-------|--------|-------|
| 0 | Reconnaissance — map repo, read orientation docs | ✅ | Backend, frontend, docs, agent graph reviewed |
| 1 | Repo hygiene — gitignore venv, remove stale worktrees, consolidate 14 docs | ⬜ | `backend/.venv` + `.claude/worktrees/` noise found |
| 2 | Component deep reads + recall notes (one at a time) | ⬜ | See component map |
| 3 | Architecture & flow map | ✅ | Delivered; captured below |
| 4 | Use-case catalogue | ⬜ | Every scenario + tool path + what to say |
| 5 | Gap analysis vs senior/production bar | ⬜ | |
| 6 | Implement improvements (approved incrementally) | ⬜ | |
| 7 | Interview recall pack (Q&A + talking points) | ⬜ | |

## Component map (Phase 2 deep reads)

Backend `backend/app/`:

- ⬜ main.py — app lifespan, checkpointer wiring
- ⬜ config.py — Pydantic settings
- ⬜ database.py — async SQLAlchemy engine/session
- ⬜ agents/customer_support/graph.py — LangGraph orchestration
- ⬜ agents/customer_support/tools.py — agent tools + RAG search
- ⬜ agents/customer_support/policy.py — structured policy classifier
- ⬜ agents/customer_support/refund.py — durable refund + idempotency
- ⬜ agents/customer_support/guardrails.py — deterministic safety checks
- ⬜ api/v1/chat.py — SSE streaming + HITL resume
- ⬜ rag/ingest.py — chunk/embed/index into pgvector
- ⬜ observability.py / observability_metrics.py — OTel traces + metrics
- ⬜ services/order_preparation.py — Stage 7 inventory handling
- ⬜ models/ — ORM models
- ⬜ evals/ — golden datasets, scoring, LLM-judge, LangSmith

Frontend `frontend/src/`: App.tsx, hooks/useChatStream.ts, types.ts

## Phase 3 — Architecture & flow map (summary)

Pitch: FastAPI streams a LangGraph Gemini agent over SSE; 6 tools; RAG over
pgvector; deterministic guardrails; human-in-the-loop refund approval via
interrupt() + Postgres checkpointer; OpenTelemetry + LangSmith evals.

Request flow:
POST /v1/chat → llm_node

  1. check_input_guardrails(text) — blocked? return canned AIMessage (skip LLM)
  2. prepare_refund_review(text) — early response, or should_interrupt →
     interrupt(payload) serializes state to Postgres, graph PAUSES, HTTP returns
     → client resumes via POST /v1/chat/resume with Command(resume={approved,note})
     → complete_refund_review() + process_approved_refund() (idempotent)
  3. llm_with_tools.ainvoke([system]+messages) — tool_calls? tools_condition →
     ToolNode (6 tools) → edge back to llm → SSE token stream (on_chat_model_stream)

Three control planes (escalating by risk):

- Deterministic (pre-LLM): guardrails.py substring/regex, sub-ms, no model call
- Structured (in-tool): policy.py with_structured_output + Pydantic, temp=0
- Human (write actions): interrupt() + Postgres checkpointer for refunds

Key "why" defenses:

- LangGraph over bare loop → durable pause/resume survives restarts
- SSE over WebSockets → one-way streaming, plain HTTP, proxy-friendly
- pgvector over dedicated vector DB → one datastore, transactional, simpler ops
- SHA-256 idempotency key + unique constraint → never double-refund
- Deterministic guardrails pre-LLM → block attacks without token cost/hijack

Known weak points (state before interviewer finds them):

- Substring guardrails → semantic obfuscation bypass
- Idempotency key includes reason but not order_item_id → same-order collisions
- Single-agent graph → no supervisor/multi-agent routing yet
- `.venv` committed; 14-doc sprawl

## Environment notes

- `everything-claude-code` plugin's gateguard hook was blocking all Write/Edit/Bash
  on Windows (state file never persisted → denied forever). Disabled via env var
  ECC_DISABLED_HOOKS=pre:edit-write:gateguard-fact-force,pre:bash:gateguard-fact-force.

## Decisions / open questions

- (none yet)

## Findings / bugs
- 🔴 Agent hallucinated a write action: claimed "successfully canceled order
  #459c7cfd" but there is NO cancel tool (6 tools only). Same for "return
  process" — only assess_return_eligibility exists, no execution tool.
  Fabricated side-effects. Fix (Phase 6): add real idempotent
  cancel_order/process_return tools via the refund HITL pattern + an eval that
  catches "claims success without a tool call" + tighten prompt to refuse
  unsupported actions.

## Frontend storefront + chat widget (built 2026-07-24)
- Layout: full storefront (product grid, category filters, debounced search)
  + floating AI support chat widget (bottom-right bubble). Reuses existing
  useChatStream + refund-approval card unchanged.
- New: api/products.ts, hooks/useProducts.ts,
  components/{ProductCard,Storefront,ChatWidget}.tsx. Rewrote App.tsx (compose
  + "Ask AI about this" opens widget with a prefilled message). types.ts gained
  Product types. styles.css gained storefront/widget styles.
- Backend GET /v1/products already existed (pagination/category/search); CORS
  open for dev. Frontend typechecks clean (tsc -b).

## Observability removal (2026-07-24)
- Removed all OpenTelemetry / Jaeger / Prometheus code so the codebase reads
  clean. structlog structured logging + perf timing KEPT (not part of that
  stack). To re-add later, this is the revert point.
- Deleted: app/observability.py, app/observability_metrics.py.
- Edited: config.py (dropped OTEL_* settings), main.py (dropped setup call +
  duplicate import), graph.py/tools.py/policy.py/chat.py (dropped tracer spans
  + record_* metrics, de-indented bodies), pyproject.toml (dropped 6 otel +
  prometheus deps), infra/docker-compose.yml (dropped jaeger service),
  backend/.env.example (dropped OTEL_* vars), README (stack/status/notes).
- Verified: py_compile passes on all 6 edited modules; no lingering references.
- TODO: run `uv sync` (or `uv lock`) to prune removed deps from uv.lock/.venv.
- Left as conceptual notes (not deleted): docs/observability.md and section 9
  of docs/AbhiMart_Codebase_Walkthrough.md still describe OTel — revisit if we
  want docs fully consistent.

## LangGraph deployment alignment (from official application-structure docs)
- Added `backend/langgraph.json` (python_version 3.12, dependencies ["."],
  graph `customer_support` → `graph.py:make_graph`, env `.env`).
- `graph.py`: `build_graph(checkpointer=None)` now compiles with OR without a
  checkpointer; added `make_graph(config=None)` platform entrypoint that builds
  without one (LangGraph Platform provides its own persistence). Self-hosted
  `main.py` path unchanged.
- Verified against live docs: factory is called with a RunnableConfig; platform
  supplies persistence — hence the separate `make_graph` to avoid a positional
  checkpointer/config collision.
- Deliberately did NOT reshuffle files to match the tutorial's
  nodes.py/state.py/tools.py layout — existing structure is equivalent/cleaner.

## AbhiMart v2 (from-scratch mastery build)
- Decided to rebuild AbhiMart from scratch as a stage-gated learning project,
  two-track (this app stays the working demo). Full plan +
  reference-PDF mapping in [abhimart-v2/BLUEPRINT.md](abhimart-v2/BLUEPRINT.md);
  status in [abhimart-v2/PROGRESS_TRACKER.md](abhimart-v2/PROGRESS_TRACKER.md).

## Change log

- 2026-07-24: Tracker created. Phase 0 + Phase 3 complete.
- 2026-07-24: Drafted AbhiMart v2 blueprint (14 stages) + tracker from 3 core
  reference PDFs.
- 2026-07-24: LangGraph Platform deploy alignment — added langgraph.json,
  made checkpointer optional, added make_graph factory.
