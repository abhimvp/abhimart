# AbhiMart v2 — Build-From-Scratch Mastery Blueprint

> A staged plan to rebuild AbhiMart from the ground up, learning each concept
> deeply enough to defend it in a senior AI-engineering interview. Two-track:
> the **current** AbhiMart stays the working demo; **abhimart-v2** is the
> stage-gated learning build. Each stage is a **vertical slice** — it runs on
> its own and gives you something concrete to explain.

## How to use this

- Build **one stage at a time**. Don't start a stage until the previous one runs.
- Each stage has: **Goal · What you build · Concepts & soundbites · "Why not X"
  · A failure mode you can name · Reference reading (your PDFs).**
- Hand a stage to Claude/Codex with: "Implement Stage N from BLUEPRINT.md,
  explain each decision, stop for my review at each acceptance-criteria item."
- Track status in [PROGRESS_TRACKER.md](PROGRESS_TRACKER.md).

## Reference library (your PDFs → where they matter)

| Reference | Used in stages |
|---|---|
| FastAPI Cheatsheet | 0–5 (backend) |
| LangChain Cheatsheet, LangGraph Core Concepts | 6 (agent) |
| RAG Architecture (8 patterns), RAG_CheatSheet, VectorDbs | 7 (RAG) |
| RAG Evaluation & Testing, Hallucination in RAG & Agents | 8 (RAG in prod) |
| Guardrails, Prompt-Injection diagram | 9 (safety) |
| Model Fallback techniques, LLMOps Q&A | 10, 14 (reliability, LLMOps) |
| AI Engineer Scenario Walkthroughs | every stage (failure drills) |
| Prompt vs Context vs Harness diagram | 6+ (agent design philosophy) |

## The mental model that frames everything (from your diagram)

Three nested layers — memorize this, it structures every agent answer:

- **Prompt engineering** = one assembled input (role, context, instructions,
  examples, format) → LLM → response. Unit of work: *one input.*
- **Context engineering** = curate what stays in the finite context window
  (query, system prompt, retrieved docs, tool outputs, memory, prior turns)
  step by step. Unit of work: *what stays in the window.*
- **Harness engineering** = the machine: Gather (context) → Act (LLM + tools +
  sub-agents) → Verify (tests / LLM-as-judge) → retry. Prompt & context
  engineering live *inside* Gather. Unit of work: *the whole machine.*

AbhiMart v2 is a harness. We build it Gather → Act → Verify.

---

# EPIC 1 — Backend mastery (no AI yet)

The goal here is real backend depth: SQL, schema design, auth, and the
"advanced" concerns (idempotency, concurrency, transactions) that separate a
toy from production. Reference: FastAPI Cheatsheet.

## Stage 0 — Foundation

- **Goal:** A running, observable, well-structured FastAPI service.
- **Build:** repo scaffold (uv, ruff, pytest), Docker Postgres, `config.py`
  (pydantic-settings), structured logging (structlog), `/health`, project
  layout (api / models / schemas / repositories / services).
- **Concepts:** 12-factor config, fail-fast settings, dependency injection,
  layered architecture (thin controllers, logic in services).
- **Why not X:** why async SQLAlchemy over sync (event-loop blocking); why a
  service layer over fat route handlers.
- **Failure mode to name:** connection-pool starvation under load.
- **Acceptance:** `docker compose up` + `uvicorn` boots; `/health` green; tests run.

## Stage 1 — Data modeling

- **Goal:** A realistic e-commerce schema with migrations and seed data.
- **Build:** models for users, products, categories, orders, order_items,
  carts, inventory; Alembic migrations; a seed script.
- **Concepts:** ERD design, normalization, foreign keys / cascades,
  `Numeric(10,2)` for money (never float), indexes, timestamps mixin.
- **Why not X:** UUID vs auto-increment PKs; soft-delete vs hard-delete.
- **Failure mode:** floating-point money rounding; missing index → seq scan.
- **Acceptance:** migrations up/down cleanly; seed populates a browsable catalog.

## Stage 2 — Catalog API

- **Goal:** Production-shaped read APIs.
- **Build:** list/detail/search/filter/sort products with pagination; repository
  pattern; Pydantic request/response DTOs separate from ORM models.
- **Concepts:** REST design, query vs path vs body params, DTO/ORM separation,
  the N+1 problem, `EXPLAIN ANALYZE`, cursor vs offset pagination.
- **Why not X:** offset pagination pitfalls at scale → keyset pagination.
- **Failure mode:** N+1 queries on order→items; unbounded page size.
- **Acceptance:** `/products` filter+search+paginate; a documented Swagger.

## Stage 3 — Auth & authorization

- **Goal:** Real auth a store needs.
- **Build:** registration, login, JWT access + refresh tokens, password hashing
  (bcrypt/argon2), protected routes, role-based access (customer vs admin).
- **Concepts:** authn vs authz, OAuth2 password flow, token rotation/expiry,
  hashing vs encryption, RBAC, `Depends(get_current_user)`.
- **Why not X:** JWT vs server-side sessions; access+refresh vs single token.
- **Failure mode:** token replay; storing passwords reversibly; missing authz
  check on an admin route.
- **Acceptance:** a customer can only see their own orders; admin can manage catalog.

## Stage 4 — Advanced backend (the "senior" stage)

- **Goal:** The hard production concerns, done right.
- **Build:** idempotency keys on order creation/payment, optimistic locking on
  inventory decrement, DB transactions + rollback, rate limiting, background
  tasks, a structured error taxonomy (custom exceptions → HTTP codes).
- **Concepts:** idempotency (unique key + double-read pattern), race conditions,
  ACID, optimistic vs pessimistic locking, retries + backoff, 429 handling.
- **Why not X:** optimistic vs pessimistic locking trade-off for stock.
- **Failure mode:** double-charge on retry; oversell under concurrent buys
  (lost update); thundering-herd retries.
- **Acceptance:** concurrent buy test can't oversell; replaying a create is safe.

---

# EPIC 2 — Frontend

## Stage 5 — Storefront + checkout

- **Goal:** A real shopping UI on top of the API.
- **Build:** product grid + detail, cart, checkout, auth screens; typed API
  client; optimistic updates; loading/error states.
- **Concepts:** data fetching/caching, auth token handling on the client,
  optimistic UI, form validation, error boundaries.
- **Acceptance:** browse → add to cart → (simulated) checkout as a logged-in user.

---

# EPIC 3 — AI, from scratch → production

Now we add intelligence, deliberately, one layer at a time.

## Stage 6 — The agent, from first principles

- **Goal:** Understand *why* an agent framework exists by first not using one.
- **Build:** (a) a bare hand-written agent loop (LLM + tool schema + while loop,
  ReAct-style); then (b) rebuild it in LangGraph as a `StateGraph` with a
  tool node. Add the AbhiMart tools (order lookup, product info).
- **Concepts:** agent loop (observe→decide→act), tool/function calling, ReAct,
  state, why a graph gives durable pause/resume, checkpointer memory.
- **Why not X:** bare loop vs LangGraph (durability, HITL, streaming); single
  agent vs framework.
- **Failure mode (AI Eng scenario #4):** two-agent infinite loop → fix with
  handoff logging, hard iteration cap, supervisor, fallback response.
- **Reference:** LangGraph Core Concepts, LangChain Cheatsheet, Prompt/Context/
  Harness diagram.
- **Acceptance:** agent answers order/product questions via tools; you can
  explain the loop line-by-line without the framework.

## Stage 7 — RAG done right (the 8-pattern ladder)

- **Goal:** Build RAG from Naive up, understanding each upgrade's *why*.
- **Build (incrementally):**
  1. **Naive RAG** — ingest, chunk, embed, pgvector, top-k, grounded prompt +
     citations + abstain path.
  2. **Hybrid RAG** — add BM25 + dense, fuse with **RRF**, dedupe, rerank
     (cross-encoder). For IDs/SKUs/error codes.
  3. **HyDE** — hypothetical-document embeddings for short/vague queries.
  4. **Corrective RAG** — validate retrieved evidence (freshness/conflict),
     augment from trusted source, reconcile or abstain.
  5. (Optional) **Adaptive RAG** — a router: one-shot vs hybrid vs decompose.
  6. (Optional) **Graph / Multimodal** — only if a use-case needs it.
- **Concepts & soundbites (from RAG book):**
  - "Naive RAG = top-k dense retrieval + grounded prompt + generation;
    correctness depends on retrieval quality and grounding."
  - "I tune chunking, embeddings, and k *before* I tune prompts."
  - recall@k, MRR, MMR, reranker, RRF (k0≈60), abstention, provenance.
- **Why not X:** dense vs BM25 (dense misses exact IDs; BM25 misses paraphrase)
  → hybrid; when NOT to add graph/multimodal (cost without benefit).
- **Failure modes (AI Eng scenarios #1, #7):** retrieves right docs but still
  hallucinates → grounding instruction, trim noise, low temp, faithfulness
  check, inline citations. Irrelevant chunks → chunk size, embedding-model
  consistency (same model index+query!), metadata filters, add reranker.
- **Reference:** RAG Architecture (8 patterns), RAG_CheatSheet, VectorDbs.
- **Acceptance:** Naive RAG runs with citations; hybrid+rerank measurably beats
  it on a labeled set (you can show recall@k lift).

## Stage 8 — RAG in production (evals + anti-hallucination)

- **Goal:** Prove quality, not just demo it.
- **Build:** golden dataset (JSONL), RAGAS-style metrics (faithfulness, context
  precision/recall, answer relevancy), LLM-as-judge, a CI eval gate, scheduled
  re-scoring, retrieval-confidence drift alert.
- **Concepts & soundbites:**
  - "Is it faithfulness (LLM problem) or context precision (retrieval problem)?
    Different root causes, different fixes." (weekly measure→analyze→fix loop)
  - eval-set drift (scores good, prod bad) → expand eval with real/adversarial
    queries; re-validate before every redeploy.
  - document drift, embedding-model version drift (silent!), query-pattern shift.
- **Failure modes (AI Eng scenarios #3, #11):** fine-tune/model good on eval,
  bad in prod; RAG quality decays 6 months post-launch with no code change.
- **Reference:** RAG Evaluation & Testing, Hallucination in RAG & Agents.
- **Acceptance:** an eval run prints metrics; a regression fails CI; you can name
  the 3 causes of silent RAG decay.

## Stage 9 — Guardrails & safety (defense in depth)

- **Goal:** Make the agent safe against misuse and injection.
- **Build (layered, per your diagram):**
  - Input validation (content filter, sanitization, pattern detection, PII).
  - Structured prompts (role separation, template isolation, function calling).
  - LLM processing (prompt boundaries, context isolation, spotlighting).
  - Output validation (response filter, anomaly detection, canary tokens).
  - Human-in-the-loop for write actions (refunds/cancellations) via `interrupt()`.
- **Concepts & soundbites:**
  - Direct vs indirect injection; "treat retrieved content as data, not
    instructions" (spotlighting / delimiter isolation).
  - Risk tiers: Low = automated, Medium = AI+human, High = human first.
  - "Safety tests are the only non-negotiable — 100% pass rate required."
- **Failure modes (AI Eng scenarios #6):** user extracts system prompt → refusal
  instructions, system/user separation, output filter, red-team the fix.
- **Reference:** Guardrails, Prompt-Injection Prevention diagram.
- **Acceptance:** a red-team suite of injection attempts all blocked; write
  actions pause for approval; agent never claims an action it has no tool for
  (the exact bug we found in current AbhiMart).

## Stage 10 — Reliability & cost (the LLM gateway)

- **Goal:** Production resilience and economics.
- **Build:** a small LLM gateway — model routing (cheap/med/expensive by
  complexity), semantic cache, prompt caching, fallback provider + circuit
  breaker, per-stage timeouts, token/cost logging, max_tokens caps.
- **Concepts & soundbites (from LLMOps + scenarios):**
  - "Model routing is the highest-ROI optimization after semantic caching."
    (route 70% cheap → ~69% cost cut). "38% cache hit = 38% cost saved."
  - Circuit breaker + fallback (OpenAI down → Claude), graceful degradation.
  - Cost spike debug: tokens/request, prompt bloat, silent retries, cache, caps.
  - Latency: separate provider vs pipeline time; stream; monitor p95/p99 not avg.
- **Failure modes (AI Eng scenarios #5, #8):** bill 3x on 20% traffic growth;
  random peak-hour latency spikes.
- **Reference:** Model Fallback techniques, LLMOps Q&A.
- **Acceptance:** a forced provider failure falls back cleanly; a repeated query
  hits cache; cost is logged per request.

## Stage 11 — OCR / unstructured ingestion

- **Goal:** Handle real-world messy documents (invoices, receipts, PDFs).
- **Build:** an ingestion pipeline: OCR/layout parse → structured extraction →
  validation → feed into the catalog/RAG store, with provenance (page/box).
- **Concepts:** "treat OCR/ASR as ingestion, not generation"; provenance +
  location-aware citations; extraction eval (OCR error rate).
- **Why not X:** when multimodal RAG is worth it (only when users need
  figures/screenshots/scans) vs added cost.
- **Failure mode:** OCR errors create wrong evidence retrieval can't fix; lost
  provenance when converting to text surrogates.
- **Reference:** RAG Architecture ch.2 (Multimodal), Hallucination doc.
- **Acceptance:** upload a sample invoice → extracted fields with source spans.

## Stage 12 — MCP (Model Context Protocol)

- **Goal:** Understand tool interop and expose AbhiMart via MCP.
- **Build:** an MCP server exposing AbhiMart tools/data; consume an external MCP
  server from the agent.
- **Concepts:** what MCP is and *why it exists* (standard client/server tool
  interface vs bespoke integrations), typed tool schemas, least-privilege tools.
- **Why not X:** MCP vs hand-wired tools (portability, governance).
- **Acceptance:** the agent calls an AbhiMart MCP tool; you can explain MCP's
  value proposition in two sentences.

## Stage 13 — Multi-agent

- **Goal:** Orchestrate specialists safely.
- **Build:** a supervisor/router agent + specialists (support, orders, catalog,
  returns); explicit handoffs; shared state; iteration cap + fallback.
- **Concepts & soundbites:** supervisor pattern, handoff logging, "cap the
  back-and-forth so it can never spin indefinitely," Agentic RAG (plan→act→
  observe→iterate→answer with budgets + traces).
- **Failure mode (AI Eng scenario #4):** agents loop forever → the fix stack.
- **Reference:** AI Agent Architecture, AI Engineer scenario walkthrough,
  RAG Architecture ch.8 (Agentic).
- **Acceptance:** a query routes to the right specialist; a stall hits the cap
  and returns a safe fallback, not an infinite loop.

## Stage 14 — LLMOps & deploy

- **Goal:** Ship it like a team would, with the full operational layer.
- **Build:** deploy (LangGraph Platform or container), re-add observability with
  intent (traces: prompt/response/tokens/cost/latency per step), prompt registry
  - versioning, dashboards + alerts, the "readiness" package (golden-eval scores,
  red-team results, load benchmarks, rollback plan).
- **Concepts & soundbites (from LLMOps + scenario #10):**
  - "LLMOps is NOT about retraining — it's managing prompts, RAG, guardrails,
    and cost, the operational layer above the model."
  - The 8-layer platform: Prompt → Gateway → Serving → RAG → Cache →
    Observability → Evaluation → Safety.
  - "Beyond a demo, I show: golden-eval scores, red-team results, load
    benchmarks, and a rollback plan."
- **Reference:** LLMOps Q&A, AI Engineer scenario walkthrough.
- **Acceptance:** deployed URL; a trace you can replay; a one-page "prod
  readiness" writeup.

---

## Cross-cutting: the "decide before you build" framework

From the LLMOps doc — rehearse this, it's a top interview question:
> **Prompt engineering first (hours) → RAG (days) → fine-tune (weeks).**
> Each step is ~10x more expensive than the last. Add RAG when the model needs
> knowledge it lacks or that changes often. Fine-tune only for consistent
> format/style/tone at high volume, and never with <500 examples or fast-
> changing knowledge.

## Interview drill (from the RAG book, adapted)

Per stage, do a 20-min drill: (1) recite 2–3 soundbites, (2) whiteboard the
framework in 3–5 steps, (3) 3 rapid-fire Qs under 20s each, (4) map a STAR story
to what you actually built in that stage.
