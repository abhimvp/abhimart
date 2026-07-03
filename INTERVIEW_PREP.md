# AbhiMart — EPAM Senior GenAI/Agentic AI Interview Prep

**Date of interview:** 2026-07-04  
**Role:** Senior Software Engineer — GenAI / Agentic AI + Python  
**Ground rule:** Every technical claim below is traceable to actual code. Where I am not 100% certain, I say so. Accuracy > impressiveness.

---

## 1. PROJECT OVERVIEW

### 60-Second Spoken Pitch (say this out loud, practice it)

> "AbhiMart is a production-style AI customer support backend I built from scratch.
> The core is a LangGraph agent that handles customer queries for a simulated e-commerce store — answering policy questions, looking up orders and products, and routing refund requests through a human review workflow.
>
> On the infrastructure side: FastAPI handles the HTTP layer with SSE streaming so tokens appear in real time; Postgres stores both business data and durable conversation checkpoints; pgvector powers semantic search over policy documents using Gemini embeddings.
>
> On the AI side: I used LangGraph's StateGraph with a two-node loop — an LLM node that calls Gemini with bound tools, and a ToolNode that executes them. For refund requests the graph pauses at an `interrupt()` call, serialises the review payload to a durable Postgres checkpoint, and resumes only when a human reviewer sends approval back via a separate `/chat/resume` endpoint.
>
> I added a full evaluation layer: a local JSONL harness with deterministic scorers checking tool usage, source citations, and required facts — plus an LLM-as-judge pass that grades answer quality for cases a regex can't catch. Those evaluations also run as LangSmith experiments for experiment tracking.
>
> The safety layer is deterministic: regex-and-keyword guardrails that catch prompt injection, cross-customer data requests, bulk PII exfiltration, and refund bypasses before the LLM even sees the message. I also have pytest integration tests for the HTTP API layer using the rollback-savepoint pattern for test isolation.
>
> The honest status: production patterns are all there. What isn't there yet: real auth, a live payment provider, and a full React frontend — those are next stages."

---

### Resume Bullet Traceability Table

#### Bullet 1
>
> "Built AbhiMart AI Customer Support Agent, a production-style AI support backend with FastAPI, LangGraph, PostgreSQL/pgvector, Gemini, RAG over policy documents, tool-based order/product lookup, SSE streaming, and Postgres-backed conversation memory."

| Phrase | File | Exact location |
|--------|------|----------------|
| **FastAPI** | `backend/app/main.py` | `app = FastAPI(...)`, lifespan, routers |
| **LangGraph** | `backend/app/agents/customer_support/graph.py` | `StateGraph`, `build_graph()` |
| **PostgreSQL/pgvector** | `backend/app/rag/ingest.py` | `PGVector(...)`, `CHECKPOINT_DATABASE_URL` |
| **Gemini** | `backend/app/agents/customer_support/graph.py` | `ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite")` |
| **RAG over policy documents** | `backend/app/rag/ingest.py` + `tools.py` | `load_and_chunk_docs()`, `search_faq` tool, `PGVector` similarity search |
| **tool-based order lookup** | `backend/app/agents/customer_support/tools.py` | `lookup_order`, `get_product_info` decorated with `@tool` |
| **SSE streaming** | `backend/app/api/v1/chat.py` | `StreamingResponse(event_stream(...), media_type="text/event-stream")` |
| **Postgres-backed conversation memory** | `backend/app/main.py` | `AsyncPostgresSaver.from_conn_string(...)` + `checkpointer.setup()` |

#### Bullet 2
>
> "Added AI evaluation and safety workflows using local JSONL datasets, deterministic scorers, LangSmith experiments, LLM-as-judge checks, prompt-injection guardrails, PII protection, cross-customer access checks, and human-in-the-loop refund approval with durable state and idempotency."

| Phrase | File | Exact location |
|--------|------|----------------|
| **local JSONL datasets** | `backend/evals/datasets/` | `stage4_golden.jsonl`, `stage5_guardrails.jsonl`, `policy_decision_golden.jsonl`, `stage7_order_preparation.jsonl` |
| **deterministic scorers** | `backend/evals/score_results.py` | `check_required_tools()`, `check_answer_facts()`, `check_required_sources()` etc. |
| **LangSmith experiments** | `backend/evals/langsmith_run.py` | `aevaluate(run_agent, data=..., evaluators=[...])` |
| **LLM-as-judge checks** | `backend/evals/judge_results.py` | `QualityGrade` Pydantic model, `build_judge()`, structured output grading |
| **prompt-injection guardrails** | `backend/app/agents/customer_support/guardrails.py` | `injection_intent` keyword check in `check_input_guardrails()` |
| **PII protection** | `backend/app/agents/customer_support/tools.py` | `_email_domain()` — logs domain only, never full email; span attributes use domain |
| **cross-customer access checks** | `backend/app/agents/customer_support/guardrails.py` | `len(set(emails)) > 1` check + `asks_for_order_data` block |
| **HITL refund approval** | `backend/app/agents/customer_support/graph.py` | `interrupt(refund_review.payload)` + `/chat/resume` endpoint |
| **durable state** | `backend/app/main.py` | `AsyncPostgresSaver` checkpointer persists the paused graph state |
| **idempotency** | `backend/app/agents/customer_support/refund.py` | `_refund_idempotency_key()` → SHA-256 hash, `create_or_get_refund_request()` |

---

## 2. FULL ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          CLIENT (browser / eval script)                  │
│     POST /v1/chat          POST /v1/chat/resume       GET /v1/chat/     │
│     {message, session_id}  {session_id, approved}     history/{id}      │
└────────────────┬────────────────────────┬───────────────────────────────┘
                 │ SSE stream             │ SSE stream (resume)
┌────────────────▼────────────────────────▼───────────────────────────────┐
│                       FastAPI  (app/main.py)                              │
│  CORSMiddleware  |  OpenTelemetry FastAPIInstrumentor  |  /health  |     │
│  /metrics (Prometheus)  |  /static (chat.html)                           │
│                                                                           │
│  chat_router  (app/api/v1/chat.py)                                       │
│    event_stream() — async generator → StreamingResponse                  │
│    graph.astream_events(v2)  |  extract_interrupt_payload()              │
│    Command(resume=...) on /resume                                        │
└────────────────────────┬────────────────────────────────────────────────┘
                         │ graph.astream_events / graph.ainvoke
┌────────────────────────▼────────────────────────────────────────────────┐
│              LangGraph StateGraph  (graph.py)                             │
│                                                                           │
│   START ──► [llm node] ──► tools_condition ──► [tools node] ──┐         │
│                │                                               │         │
│                │ (no tool call)                    (loop back) │         │
│                ▼                                               │         │
│              END ◄─────────────────────────────────────────────┘         │
│                                                                           │
│  llm node logic:                                                         │
│    1. check_input_guardrails() — deterministic, blocks before LLM        │
│    2. prepare_refund_review() — detect refund intent, load order         │
│    3. interrupt(payload) — PAUSE graph, serialise to Postgres checkpoint │
│    4. llm_with_tools.ainvoke(messages) — Gemini + bound tools            │
│                                                                           │
│  Checkpointer: AsyncPostgresSaver (langgraph.checkpoint.postgres.aio)   │
│    — thread_id = session_id                                              │
│    — persists full MessagesState after every node                       │
└──────────┬─────────────────────────────────────┬───────────────────────┘
           │ tool calls                           │ RAG / policy
┌──────────▼──────────────┐          ┌───────────▼───────────────────────┐
│   LangChain ToolNode     │          │   pgvector  (PostgreSQL)           │
│   (langgraph.prebuilt)   │          │   collection: abhimart_knowledge_base│
│                          │          │   embeddings: gemini-embedding-001  │
│  lookup_order            │          │   dim: 768                         │
│  get_product_info        │          │   docs: return-policy.md,          │
│  search_faq ─────────────┼──────────►        shipping-policy.md,        │
│  assess_return_eligibility│          │        warranty-terms.md,          │
│  check_inventory_for_order│          │        product-faqs.md            │
│  prepare_simulated_order │          └───────────────────────────────────┘
└──────────┬───────────────┘
           │ async SQLAlchemy
┌──────────▼───────────────────────────────────────────────────────────────┐
│                     PostgreSQL  (app/database.py)                         │
│                                                                           │
│  Tables (via Alembic migrations):                                        │
│    users, products, orders        — business data                        │
│    refund_requests                — HITL durable state + idempotency     │
│    checkpoints (LangGraph)        — paused graph state per thread_id     │
│    langchain_pg_embedding         — pgvector document store              │
│                                                                           │
│  Engine: create_async_engine (asyncpg driver)                            │
│  Pool: pool_size=5, max_overflow=10                                      │
└──────────────────────────────────────────────────────────────────────────┘

Observability layer (horizontal — wraps everything):
  structlog  →  structured JSON logs
  OpenTelemetry TracerProvider  →  spans sent to Jaeger via OTLP
  Prometheus metrics  →  /metrics endpoint (abhimart_chat_requests_total,
                          abhimart_tool_calls_total, abhimart_rag_retrievals_total, …)

Evaluation layer (offline):
  evals/run_eval.py         →  runs agent against JSONL datasets
  evals/score_results.py    →  deterministic scorers (tools, facts, sources)
  evals/judge_results.py    →  LLM-as-judge (Gemini, structured output)
  evals/langsmith_run.py    →  LangSmith aevaluate() experiments
  evals/langsmith_dataset.py→  uploads JSONL → LangSmith dataset

LangSmith (remote):
  LANGSMITH_TRACING=true → every graph.astream_events call is auto-traced
  langsmith_run.py → experiment results stored in LangSmith project "abhimart"
```

---

## 3. REQUEST FLOW WALKTHROUGHS

### (a) RAG / Policy Question End-to-End

> Customer: "Can I return an item I've already opened?"

1. **POST /v1/chat** received by `chat()` in `backend/app/api/v1/chat.py`.  
   Request body: `{"message": "Can I return an item I've already opened?", "session_id": "abc123"}`

2. FastAPI wraps response in `StreamingResponse(event_stream(...), media_type="text/event-stream")`.

3. `event_stream()` calls `graph.astream_events({"messages": [...]}, config={"configurable": {"thread_id": "abc123"}}, version="v2")`.

4. LangGraph loads checkpoint for `thread_id=abc123` from Postgres (empty for first turn). Enters `llm` node.

5. **Guardrail check** (`guardrails.py` `check_input_guardrails()`): message is clean, no block.

6. **Refund detection** (`refund.py` `prepare_refund_review()`): "return" is present but no email → `should_interrupt=False`, no payload.

7. **LLM call**: `llm_with_tools.ainvoke(messages)` sends to Gemini with the system prompt + all 6 tool schemas. Gemini decides to call `assess_return_eligibility`.

8. LangGraph routes to `tools` node via `tools_condition` (checks if last AI message has `tool_calls`).

9. **`assess_return_eligibility` tool** (`tools.py`):
   - Calls `search_faq` first (or is wired directly — verify against actual tool impl) to retrieve `return-policy.md` chunks from pgvector.
   - Calls `classify_return_eligibility()` in `policy.py`: sends a `SystemMessage` + `HumanMessage` to a *second* Gemini call configured with `llm.with_structured_output(PolicyEligibilityDecision)`.
   - Returns a `PolicyEligibilityDecision` dataclass: `decision`, `reason`, `source`, `confidence`.

10. Tool result returned as `ToolMessage` to LangGraph; state updated; loop back to `llm` node.

11. LLM node calls Gemini again with the tool result. System prompt says: "do not print raw JSON — use the decision to write a customer-facing answer."

12. Gemini streams tokens back. `event_stream()` detects `on_chat_model_stream` events where `metadata["langgraph_node"] == "llm"` and yields `data: {"text": "..."}\n\n` to the client.

13. Graph reaches `END` (no more tool calls). `event_stream()` yields `data: [DONE]\n\n`.

14. LangGraph saves updated `MessagesState` to Postgres checkpoint.

**What `search_faq` does internally** (from `tools.py`): creates a `PGVector` instance using `gemini-embedding-001` embeddings, calls `similarity_search_with_score(query, k=3)`, returns top-k chunks with their source filename prepended.

---

### (b) Tool Call — Order Lookup End-to-End

> Customer: "What's the status of my order?" → Agent asks for email → Customer provides it.

1. First turn: message "What's the status of my order?" → guardrails pass → LLM responds asking for email (no tool call, graph goes to END after single LLM turn).

2. Second turn: "my email is <alice@example.com>" → guardrails pass (single email, not a cross-customer request) → LLM calls `lookup_order(email="alice@example.com")`.

3. **`lookup_order` tool** (`tools.py`):

   ```python
   async with async_session_factory() as session:
       result = await session.execute(select(User).where(User.email == email))
       user = result.scalar_one_or_none()
       # ... then select Orders where Order.user_id == user.id
   ```

   - PII-safe: logs/spans only record `_email_domain(email)` = "example.com".
   - Records `record_tool_call("lookup_order")` and `record_tool_duration(...)` for Prometheus metrics.
   - Returns formatted string with truncated order IDs (`str(order.id)[:8]`).

4. ToolMessage with order list flows back to LLM node; Gemini writes customer-facing summary.

5. Tokens stream to client. Checkpoint updated.

---

### (c) Refund HITL Flow — interrupt() / resume Mechanics

> Customer: "I want a refund for my laptop order, my email is <alice@example.com>"

**Phase 1 — Detect and interrupt:**

1. Message enters `llm` node. Guardrails pass (no injection, single email).

2. `prepare_refund_review(latest_content)` in `refund.py`:
   - `_contains_refund_intent()` → True ("refund" in message).
   - Extracts email via `EMAIL_RE.findall(message)`.
   - Queries DB for user + orders → finds a matching order.
   - Calls `create_or_get_refund_request()`:
     - Computes `idempotency_key = SHA-256(f"refund:{email}:{order_id}:{reason}")`.
     - Checks if a row with that key already exists (idempotent re-run safety).
     - If not: inserts `RefundRequest(status="pending_review", ...)`.
   - Returns `RefundReviewResult(should_interrupt=True, payload={...})`.

3. `interrupt(refund_review.payload)` is called inside the `llm` node. **This is LangGraph's `interrupt()` from `langgraph.types`**.
   - Effect: LangGraph raises an internal `GraphInterrupt` exception.
   - The current graph state (including all messages + which node was running) is serialised to the Postgres checkpoint.
   - The graph is now "paused at" `thread_id=abc123`.

4. The paused `__interrupt__` value surfaces in `astream_events` as a special event. `extract_interrupt_payload()` in `chat.py` detects `"__interrupt__"` key and the SSE stream emits:

   ```
   data: {"type": "interrupt", "interrupt": {"order_id": "...", "amount": "...", ...}}
   ```

   Then `[DONE]`. Client (static `chat.html` or future React frontend) shows the approval UI.

**Phase 2 — Resume after human decision:**

1. Human reviewer clicks Approve/Reject in the UI. Client POSTs to `POST /v1/chat/resume`:

   ```json
   {"session_id": "abc123", "approved": true, "reviewer_note": "Verified"}
   ```

2. `resume_chat()` calls `event_stream(graph, Command(resume={"approved": true, "reviewer_note": "Verified"}), session_id="abc123", ...)`.

3. LangGraph loads the checkpoint for `thread_id=abc123`, sees the graph is interrupted, and resumes. The `interrupt()` call returns the resume value as `human_decision`.

4. **Important re-run behaviour**: LangGraph re-runs the `llm` node from the top before the `interrupt()`. That's why `create_or_get_refund_request()` is idempotent — the DB write is skipped on the second pass because the idempotency key already exists.

5. Code after `interrupt()` in `graph.py` runs: `approved = human_decision.get("approved")`. If True:
   - `complete_refund_review(approved=True, reviewer_note=...)` → updates `refund_requests.status = "approved"`.
   - `process_approved_refund(...)` → marks status `"processed"`.
   - Returns a plain-text response to the customer.

6. Tokens stream, graph reaches END, checkpoint updated.

---

## 4. COMPONENT DEEP DIVE

### FastAPI

**What problem it solves here:**  
Async HTTP layer for SSE streaming. The `event_stream` generator is an `async generator` — FastAPI wraps it in `StreamingResponse`. Every `yield` sends a chunk to the client without blocking the event loop. Also provides dependency injection via `Depends(get_db)` for database sessions.

**Why this choice over alternatives:**

- **vs Flask/Django**: Both are WSGI, which means blocking I/O. Streaming from a blocking framework requires threading or hacks. FastAPI is ASGI-native — `async def` route handlers and `async for` generator streams are first-class citizens.
- **vs Starlette directly**: FastAPI is Starlette + Pydantic validation + OpenAPI docs. We get request validation (the `ChatRequest` Pydantic model) for free.

**When NOT to use FastAPI:**

- If the team is primarily WSGI and has no async DB drivers. Async SQLAlchemy + asyncpg require discipline — any sync DB call blocks the event loop.
- CPU-bound workloads: async doesn't help there. Use workers/multiprocessing instead.

**Interview phrasing:**  
> "FastAPI lets me stream tokens to the client as an async generator wrapped in StreamingResponse. The alternative was Flask with `stream_with_context`, but Flask is WSGI — every request ties up a thread. With FastAPI's ASGI model, I can handle many concurrent SSE connections on a small number of threads."

---

### LangGraph (vs plain LangChain agents vs hand-rolled state machine)

**What problem it solves here:**  
Durable, pauseable agentic loops. The core need: pause execution mid-graph (for human approval), persist the exact state, and resume from that exact point later — across HTTP requests.

**Why LangGraph:**

- **vs plain LangChain `AgentExecutor`**: AgentExecutor is a while-loop in memory. It can't pause and resume across requests. Conversation history isn't automatically persisted. No built-in checkpointing.
- **vs hand-rolled state machine**: A custom state machine needs: state serialisation, Postgres persistence, resume logic, streaming integration, LangSmith tracing hooks. LangGraph provides all of that. The `interrupt()` + `Command(resume=...)` pattern would be 200+ lines of custom code to replicate.
- **vs LangGraph itself**: The honest cost is complexity. `astream_events(version="v2")` emits many event types; I needed custom `extract_interrupt_payload()` and `extract_direct_llm_text()` functions because guardrail responses (direct `AIMessage` return without hitting the chat model) take a different event path than normal LLM streaming.

**When NOT to use LangGraph:**

- Simple single-turn question-answering with no tools and no memory. Plain `llm.ainvoke()` is sufficient.
- When your team doesn't need durability or HITL — LangGraph's checkpointer adds a Postgres dependency and operational overhead.

**Interview phrasing:**  
> "LangGraph gave me the interrupt/resume primitive for free. When a customer asks for a refund, the graph pauses at `interrupt()`, the full state is serialised to Postgres, and a completely different HTTP request — the human reviewer's POST to `/chat/resume` — restores it and continues exactly where it left off. That would have been significant custom engineering without LangGraph."

---

### pgvector (vs Pinecone / Chroma / Weaviate)

**What problem it solves here:**  
Semantic search over 4 policy documents (return-policy.md, shipping-policy.md, warranty-terms.md, product-faqs.md). At query time, the `search_faq` tool embeds the question with `gemini-embedding-001` (768 dimensions) and does a nearest-neighbour search against stored document chunks.

**Why pgvector:**

- **vs Chroma**: Chroma is in-memory by default, with optional disk persistence. For a project that already has Postgres for business data AND LangGraph checkpointing, adding a separate vector DB means running a third service. pgvector puts vectors in the same Postgres instance.
- **vs Pinecone**: Managed cloud service — great for production at scale, but requires a paid account and a network call. pgvector is free and local.
- **vs Weaviate**: Same argument — separate service, separate operational concern.
- **Real trade-off**: pgvector's ANN (approximate nearest-neighbour) index (HNSW or IVFFlat) is less optimised than dedicated vector databases at large scale. For AbhiMart's 4-document knowledge base, performance is not a concern.

**When NOT to use pgvector:**

- Millions of documents, high query throughput. A dedicated ANN engine (Pinecone, Weaviate, Qdrant) will outperform pgvector at that scale.

**Interview phrasing:**  
> "pgvector let me keep the entire stack — business data, checkpoints, and vector embeddings — in one Postgres instance. At AbhiMart's scale, that simplicity outweighs the performance ceiling. If I were scaling to millions of documents or needed sub-10ms retrieval, I'd move the vector index to a dedicated engine like Weaviate or Qdrant."

---

### Gemini (vs OpenAI GPT models)

**What problem it solves here:**  
Two uses: (1) `gemini-3.1-flash-lite` with `bind_tools()` as the main agent LLM; (2) `gemini-embedding-001` for generating 768-dimensional embeddings at ingest and retrieval time.

**Why Gemini:**  
Honest answer: Gemini was a deliberate choice to demonstrate I can work beyond the OpenAI ecosystem. `gemini-3.1-flash-lite` has a large context window and competitive function-calling support. `gemini-embedding-001` supports task-type hints (`RETRIEVAL_DOCUMENT` vs `RETRIEVAL_QUERY`) which improve RAG quality.

**Why NOT use OpenAI here:**  
No architectural reason — OpenAI's `gpt-4o-mini` with `bind_tools()` and `text-embedding-3-small` would work identically at the LangChain abstraction layer. The LangChain abstraction means swapping the model is a 2-line change.

**When Gemini is NOT the right choice:**  

- If the team standardises on Azure OpenAI for enterprise compliance.
- If the system prompt relies on GPT-specific instruction-following quirks.

**Interview phrasing:**  
> "I used Gemini specifically to demonstrate multi-provider literacy. The LangChain `ChatGoogleGenerativeAI` interface is API-compatible with `ChatOpenAI` at the `bind_tools` and `with_structured_output` level — swapping providers is a two-line change. The meaningful technical choice was the embedding task-type hint: I use `RETRIEVAL_DOCUMENT` when indexing and `RETRIEVAL_QUERY` at retrieval time, which aligns with how the Gemini embedding model was trained."

---

### SSE Streaming (vs WebSockets)

**What problem it solves here:**  
Push tokens to the browser as they arrive from the LLM, without the client polling.

**Why SSE over WebSockets:**

- **Simplicity**: SSE is unidirectional server-push over plain HTTP. No handshake, no frame protocol. `StreamingResponse` with `media_type="text/event-stream"` is all it takes in FastAPI.
- **Use case fit**: Chat is mostly one-request → streaming-response. Bidirectional full-duplex (WebSocket) would be overengineering.
- **HTTP/2**: SSE works over HTTP/2 multiplexing. WebSockets require an upgrade handshake.

**When WebSockets ARE the right choice:**  

- True bidirectional communication (e.g., collaborative editing, multiplayer, real-time presence).
- If the client needs to stream audio/video back to the server simultaneously.

**Interview phrasing:**  
> "SSE is the right tool for unidirectional server-to-client streaming. The protocol is `data: <json>\n\n` — that's it. The interrupt payload for the HITL flow is also sent over the same SSE stream as a JSON object with `type: interrupt`, so the client can distinguish token chunks from human-approval prompts."

---

### Postgres Checkpointer (durable conversation memory)

**What problem it solves here:**  
`MessagesState` (the full message history for a `thread_id`) persists across requests, server restarts, and paused graphs. Without it, conversation history lives in Python memory — lost on restart.

**Implementation** (`main.py`):

```python
async with AsyncPostgresSaver.from_conn_string(_settings.CHECKPOINT_DATABASE_URL) as checkpointer:
    await checkpointer.setup()   # creates LangGraph tables (idempotent)
    app.state.graph = build_graph(checkpointer)
```

`thread_id` = `session_id` from the request — that's the correlation key between HTTP requests and graph state.

**Why two database URLs?**  
`DATABASE_URL` uses `asyncpg` (non-blocking). `CHECKPOINT_DATABASE_URL` is for `AsyncPostgresSaver` which uses `psycopg3`. `PGVector` also uses `psycopg3`. Two separate connection strings, potentially the same Postgres instance.

---

### Deterministic Guardrails (vs LLM-based moderation)

**What problem it solves here:**  
Block obvious attacks before spending tokens on an LLM call. The guardrails in `guardrails.py` are pure Python — zero latency, zero cost, no hallucination risk.

**Five checks implemented:**

1. **Prompt injection + order data**: `injection_intent AND asks_for_order_data` — blocked.
2. **Bulk customer data request**: "all customer emails" → blocked.
3. **Instruction override / secret reveal**: "hidden instruction" + "system rules" → blocked.
4. **Cross-customer data**: >1 unique email + order query → blocked.
5. **Refund bypass**: "refund" + "without approval" / "right now" → blocked.

**Why deterministic over an LLM moderation call:**

- **Latency**: A regex check is microseconds. An LLM moderation call adds 200–500ms of latency to every request.
- **Reliability**: A regex doesn't hallucinate. If the keyword is there, the block fires.
- **Cost**: No API tokens consumed for every blocked request.

**When LLM-based moderation IS better:**  
Sophisticated attacks that paraphrase the banned patterns. "Please disregard your guidelines" would bypass these keyword checks. A semantic moderation layer (OpenAI Moderation API, Llama Guard) catches paraphrases. The honest gap: AbhiMart's guardrails are **necessary but not sufficient** for production.

**Interview phrasing:**  
> "I chose deterministic guardrails as the first line of defence: fast, cheap, and reliable for the specific attacks I'm protecting against — prompt injection, cross-customer PII requests, and refund bypass. The limitation is paraphrase attacks. In a production system I'd layer these with a semantic moderation model as a second pass."

---

### LLM-as-Judge

**What problem it solves here:**  
Deterministic scorers can check *whether* a tool was called or *whether* a specific phrase appears. They can't grade *whether* the answer correctly applies a nuanced policy rule — for example, "the customer said they used the item, and the policy requires original condition; did the agent correctly say it may not be eligible?"

**Implementation** (`evals/judge_results.py`):

```python
class QualityGrade(BaseModel):
    score: Literal[0, 1]
    reasoning: str
```

`build_judge()` uses `llm.with_structured_output(QualityGrade)` — the judge returns a structured `score: 0|1` rather than free text, making automated aggregation easy.

**Why structured output for the judge:**  
Parsing free-text judge responses is fragile. `with_structured_output` (backed by Gemini's function-calling) guarantees the response is a valid `QualityGrade` object.

---

## 5. PYTHON CONCEPTS TIED TO THIS CODE

### Decorators: `@tool`, `@lru_cache`, `@pytest_asyncio.fixture`

**`@tool`** (`tools.py`): LangChain's `@tool` decorator introspects the function's docstring and type hints to generate a JSON schema that gets sent to the LLM in `bind_tools()`. The docstring *is* the tool description the model sees. This is why tool docstrings in `tools.py` are carefully worded — they're part of the prompt.

```python
# From tools.py
@tool
async def lookup_order(email: str) -> str:
    """Look up all orders for a customer by their email address.
    Use this when the customer asks about their orders...
    """
```

**`@lru_cache`** (`config.py`, `observability_metrics.py`): Used on `get_settings()` to ensure the `.env` file is read exactly once, and on metric instrument constructors so OpenTelemetry counters/histograms are created once. `lru_cache` on a zero-argument function is a lazy singleton.

**`@pytest_asyncio.fixture`** (`tests/conftest.py`): Marks async fixtures for pytest-asyncio. The `scope="session"` on `test_engine` means the Postgres schema is created once per test run.

---

### Async / Await and the Event Loop

All database access in `tools.py` uses:

```python
async with async_session_factory() as session:
    result = await session.execute(select(User).where(...))
```

`asyncpg` is the underlying driver — it uses PostgreSQL's wire protocol asynchronously so the event loop can serve other requests while waiting for the DB.

**Why `expire_on_commit=False`** (`database.py`):  
> "In async SQLAlchemy, lazy loading is forbidden — you can't do an awaited DB call by just accessing an attribute. `expire_on_commit=False` keeps loaded data alive after a commit so attribute access doesn't trigger an implicit query."

---

### Generators / Context Managers — `event_stream` as async generator

`event_stream()` in `chat.py` is an `async def` function containing `yield` — making it an *async generator*. FastAPI's `StreamingResponse` consumes it:

```python
async def event_stream(graph, graph_input, session_id, message_for_metrics):
    async for event in graph.astream_events(...):
        ...
        yield f"data: {json.dumps({'text': text})}\n\n"
    yield "data: [DONE]\n\n"
```

The generator doesn't produce the whole response in memory first — it yields chunks as the LLM produces tokens.

**`interrupt()` as a pause-resume mechanism:**  
`interrupt()` from `langgraph.types` is not a Python generator `yield`. Internally, LangGraph raises a `GraphInterrupt` exception, catches it, serialises the state to Postgres, and returns from `astream_events`. The next call to `graph.ainvoke(Command(resume=...))` re-enters the graph, re-runs the node up to the `interrupt()` call, and then the `interrupt()` returns the resume value instead of raising — this is the *checkpoint-and-replay* pattern.

---

### Custom Exceptions (`exceptions.py`)

```python
@dataclass(slots=True)
class InsufficientStockError(AbhiMartError):
    product_id: UUID
    product_name: str
    requested_quantity: int
    available_quantity: int
```

Using `@dataclass(slots=True)` means:

- `__slots__` is generated — no `__dict__`, lower memory overhead.
- Fields are typed and accessible by attribute (not by indexing into `args`).
- Catching `InsufficientStockError` in `tools.py` gives structured access to `exc.available_quantity` to build the JSON error payload.

**Interview phrasing:**  
> "I used typed dataclass exceptions rather than generic `ValueError` so tool-layer catch blocks can build structured JSON responses — the tool returns `{"ok": false, "code": "INSUFFICIENT_STOCK", "available_quantity": N}` and the LLM uses that to tell the customer exactly how many units are available."

---

### Closures / `get_settings()` singleton

```python
@lru_cache
def get_settings() -> Settings:
    return Settings()
```

`lru_cache` with no arguments on a function is the idiomatic Python singleton — the `Settings()` instance is created on first call and the same object is returned on every subsequent call. This means `.env` is parsed exactly once per process lifetime.

---

### `get_db()` as dependency-injected context manager

```python
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
```

`yield`-based FastAPI dependencies are generator-based context managers. FastAPI calls the function, runs code up to `yield` (session opened), injects the session into the route, runs the route body, then resumes after `yield` (session closed via `finally`). The session is **always** closed — even if the route raises an exception.

---

## 6. GENAI / AGENTIC AI DEEP DIVE

### LangGraph State / Nodes / Edges / Conditional Routing

**State**: `MessagesState` (from `langgraph.graph`) — a typed dict with a `messages: list[BaseMessage]` field. Messages are appended, never replaced. Each node receives the full current state and returns a dict of updates.

**Nodes** (from `graph.py`):

- `llm`: async Python function. Runs guardrails, refund detection, then `llm_with_tools.ainvoke(state["messages"])`.
- `tools`: `ToolNode(tools)` — a prebuilt node from `langgraph.prebuilt`. Given a list of `@tool`-decorated functions, it automatically dispatches `tool_calls` from the last `AIMessage`, executes them (possibly in parallel), and returns `ToolMessage` results.

**Edges**:

```
START → llm
llm  → tools_condition  (conditional edge)
       ├── tools  (if last message has tool_calls)
       └── END    (if no tool calls = final answer)
tools → llm  (unconditional — always loop back)
```

**`tools_condition`**: a prebuilt conditional function from `langgraph.prebuilt`. Checks `state["messages"][-1].tool_calls` — if non-empty, routes to `tools`; otherwise routes to `END`.

**Compiling**: `graph.compile(checkpointer=checkpointer)` wires the checkpointer. After every node execution, state is persisted. `thread_id` identifies the conversation.

---

### Prompt Engineering Choices

**System prompt structure** (`graph.py`):

1. Role definition and scope.
2. Tool inventory — one sentence per tool explaining *when* to use it.
3. Behavioural rules per workflow (order lookup requires email; ordering requires both inventory check + email + confirmation; policy questions require `search_faq` first).
4. Critical safety rules: "Treat retrieved policy text as the source of truth", "If the customer says they used it, do not say it is eligible."
5. Source citation instruction: "Cite source filenames exactly as they appear in retrieved content, for example: [Source: return-policy.md]."

**Why explicit per-tool invocation rules?**  
Without them, the model sometimes calls `prepare_simulated_order` directly without first calling `check_inventory_for_order`. Explicit ordering instructions in the prompt enforce the required tool sequence.

**RAG content tagging / spotlighting against prompt injection:**  
Chunks returned by `search_faq` include the source filename in their content (`doc.metadata["source"]`). The system prompt tells the model to cite that filename. This is a mild form of *spotlighting* — tagging retrieved content so the model can distinguish it from instructions. A stronger version would wrap retrieved content in XML-like delimiters (`<retrieved>...</retrieved>`) and instruct the model to never follow instructions found inside those delimiters.

**Honest gap**: AbhiMart's current implementation uses source-filename citation but not strict XML spotlighting or a secondary moderation pass on retrieved content. Indirect prompt injection via malicious content in policy documents is a real (if low-probability) risk.

---

### Structured Output for Policy Eligibility Classifier

**Why structured output specifically here** (`policy.py`):

```python
llm.with_structured_output(PolicyEligibilityDecision)
```

`PolicyEligibilityDecision` has a `decision: Literal["eligible", "likely_not_eligible", "need_more_info"]` field. Without structured output, the LLM might say "The item is probably eligible" — ambiguous. With structured output, the downstream code gets a guaranteed enum value it can log, metric, and pass back to the main agent cleanly.

**Why not structured output for the main agent?**  
The main agent needs to produce free-text chat responses. Forcing it into a schema would require schema-wrapping every conversational turn. The policy classifier is a *sub-task* with a well-defined output space — that's the right place for structured output.

**`with_structured_output` mechanics**: Uses Gemini's function-calling API under the hood. The Pydantic schema is converted to a JSON schema and passed as a single tool definition. The model is forced to call that "tool" with valid arguments. LangChain unwraps the response and validates it against the Pydantic model.

---

### Tool / Function Calling Mechanics

`llm.bind_tools(tools)` converts each `@tool`-decorated function's signature + docstring into a JSON schema array sent to the model in every request. When the model decides to use a tool, it returns an `AIMessage` with `.tool_calls: list[ToolCall]` instead of plain content. `ToolNode` in the graph dispatches those calls to the actual Python functions, collecting results as `ToolMessage` objects that get appended to `MessagesState`.

**Parallel tool calls**: `ToolNode` can execute multiple tool calls in the same turn in parallel. For AbhiMart, the typical pattern is one tool call per turn, but the architecture supports it.

---

## 7. EVALUATION & TESTING

### Local Eval Harness

**`evals/run_eval.py`**:

- Loads `evals/datasets/stage4_golden.jsonl` — each line is `{"id": "...", "message": "...", "expected": {"must_use_tools": [...], "must_cite_sources": [...], "must_contain": [...], ...}}`.
- Builds the LangGraph graph with `InMemorySaver` (no Postgres needed for evals — each run is independent).
- Calls `graph.astream_events(...)` per example.
- Captures `on_tool_start` events → tool call list; `on_chat_model_stream` events → final answer text.
- Appends each result to `evals/results/stage4_baseline.jsonl`.

**`evals/score_results.py`** — deterministic checks:

- `check_required_tools()` — were all `must_use_tools` called?
- `check_required_sources()` — did the answer cite expected source docs?
- `check_answer_facts()` — do required phrases appear in the answer?
- `check_forbidden_tools()` — were any forbidden tools called?
- Aggregates per-check pass rates, prints a summary table.

**`evals/judge_results.py`** — LLM-as-judge:

- Reads the same JSONL results file.
- For each row, sends `(customer question, expected behavior notes, actual answer)` to Gemini with `with_structured_output(QualityGrade)`.
- Records `score: 0|1` + `reasoning` per example to a separate JSONL.

**`evals/langsmith_run.py`**:

- Uses LangSmith `aevaluate(run_agent, data="abhimart-stage4-golden", evaluators=[...])`.
- `run_agent()` calls the graph identically to `run_eval.py` but returns the output dict in the shape LangSmith expects.
- Deterministic scorer functions from `score_results.py` are reused as LangSmith evaluators — same logic, same signal, different reporting surface.

**Multiple eval datasets**:

- `stage4_golden.jsonl` — general agent behaviour
- `policy_decision_golden.jsonl` — policy classifier specifically
- `stage5_guardrails.jsonl` — guardrail blocking behaviour
- `stage7_order_preparation.jsonl` — inventory check / order preparation flow

---

### Pytest Tests

**Yes, pytest IS used.** (`backend/app/tests/`)

`test_products.py` and `test_order_preparation.py` are **HTTP integration tests** using `httpx.AsyncClient` + `ASGITransport`.

**Test isolation pattern** (`conftest.py`): The "rollback savepoint" pattern:

1. Session-scoped `test_engine` creates/drops tables once.
2. Per-test `db_session` fixture: opens a real connection, begins a transaction, creates a `Session` with `join_transaction_mode="create_savepoint"`.
3. Routes that call `db.commit()` release a savepoint (not a real commit).
4. After the test: `conn.rollback()` undoes everything — no truncation needed between tests.
5. `NullPool` prevents connection reuse — each test gets a fresh connection for the savepoint to work correctly.

**Honest gap on testing**: There are no pytest tests for the LangGraph agent itself (the `graph.py` logic, tools, guardrails). Those are covered by the eval harness (`run_eval.py`) and the HITL probe (`run_refund_hitl_eval.py`). The practical reason: agent tests are slow (LLM calls) and non-deterministic. The eval harness is better suited for that layer. What I'd add next: unit tests for `guardrails.py` (pure functions, no LLM) and `refund.py` (idempotency logic) using `pytest-asyncio` and a test database — those are deterministic and fast.

**How to describe the gap in an interview:**  
> "I have integration tests for the HTTP API layer using pytest and the rollback-savepoint pattern. The agent logic is covered by a separate eval harness with JSONL golden datasets and deterministic scorers — that's more appropriate for LLM behaviour than unit tests. The honest gap is: no pytest unit tests for the guardrail functions or the refund idempotency logic. Those would be the next tests I'd write because they're deterministic, fast, and currently only covered by the eval scripts."

---

## 8. FAILURE MODES

### FastAPI / SSE Layer

- **Client disconnects mid-stream**: The `async for event in graph.astream_events(...)` will eventually raise or stall. The `except Exception` in `event_stream` catches it, records the error metric, and re-raises. The LangGraph graph continues running server-side until the next node completes (there's no explicit cancellation propagation to the graph).
- **`[DONE]` never sent**: If an exception is raised, the `yield "data: [DONE]\n\n"` at the bottom of `event_stream` is never reached. The client's SSE connection closes without a clean termination signal. The client needs a timeout or reconnect logic.
- **Checkpoint write failure during interrupt**: If `AsyncPostgresSaver` fails to write the checkpoint when `interrupt()` is called, the graph state is lost. The customer sees an error but the `refund_requests` row was already inserted (that's a separate Postgres write). The system is in an inconsistent state: refund row exists but no checkpoint to resume from.

### LangGraph / Agent

- **LLM returns malformed tool call**: If Gemini returns a tool call with wrong argument types, `ToolNode` will fail. The error surfaces as an exception in `astream_events`. Current code has a broad `except Exception` that records the error metric but doesn't return a user-friendly degraded response.
- **Infinite tool loop**: If the LLM keeps calling tools without reaching a `tool_calls=[]` final message, the graph loops forever. LangGraph doesn't have a built-in loop limit. A production implementation should add a max-iterations check (e.g., count messages, stop if > N).
- **Re-run before interrupt**: LangGraph re-runs the `llm` node from the top when resuming. Any non-idempotent code before `interrupt()` would execute twice. `create_or_get_refund_request()` is idempotent by design, but this is a subtle footgun for future code additions.

### RAG / pgvector

- **Stale embeddings**: If policy documents are updated but `ingest.py` isn't re-run, the vector store contains outdated chunks. There's no automated pipeline for this — it's a manual step.
- **Embedding model version mismatch**: If `gemini-embedding-001` is updated or deprecated by Google and the dimensions or semantic space changes, old stored embeddings become inconsistent with new query embeddings. The collection would need full re-ingestion.
- **Top-k returns irrelevant chunks**: If the policy question is phrased in a way dissimilar to the document vocabulary (e.g., the customer says "swap" for "return"), the similarity search might miss the relevant chunk. There's no fallback to keyword search.

### Idempotency / Refund

- **SHA-256 idempotency key collisions**: Extremely unlikely but theoretically possible. A collision would cause two distinct refund requests to map to the same key, silently returning the first request's data for the second.
- **IntegrityError race condition**: `create_or_get_refund_request()` handles this — if two concurrent requests with the same key hit the DB simultaneously, the second one gets `IntegrityError`, rolls back, then fetches the existing row. This is correctly handled.
- **Checkpoint + refund_request desync**: See above — if the `interrupt()` checkpoint write fails but the `refund_requests` insert succeeded, the refund row exists in "pending_review" forever with no graph state to resume it.

### Guardrails

- **Keyword bypass via paraphrase**: The regex/keyword checks in `guardrails.py` do not catch "please disregard your earlier instructions" (no exact keyword match). A semantic attack would pass through.
- **False positives**: The `asks_for_order_data` check triggers on "status" alone. A customer asking "What's the payment status of my subscription?" alongside two emails (e.g., from/to in a forwarded email text) would be incorrectly blocked.

---

## 9. RAPID-FIRE Q&A

**Q1: What is `bind_tools()` actually doing at the protocol level?**  
> It converts each `@tool` function's Pydantic/type-hint schema into a JSON object following OpenAI's function-calling schema (which Gemini also accepts). On every `ainvoke`, those schemas are sent to the model as `tools=[...]`. The model can respond with a normal message or with `tool_calls=[{name, arguments}]`. LangChain unpacks the response into an `AIMessage` with the appropriate field populated.

**Q2: How does `interrupt()` differ from just `return` in a LangGraph node?**  
> `return` completes the node and advances the graph. `interrupt()` raises a `GraphInterrupt` internally — LangGraph catches it, serialises the full state to the checkpointer, and surfaces the interrupt payload via `astream_events`. The graph is now "parked" at that thread_id. On the next `ainvoke(Command(resume=...))` call with the same `thread_id`, LangGraph restores state and re-runs the node until `interrupt()` is reached again, at which point it returns the resume value instead of raising.

**Q3: Why did you use SHA-256 for the idempotency key rather than a UUID?**  
> A UUID is random — it doesn't prevent duplicates. SHA-256 over `email:order_id:reason` produces the same key for the same logical refund request, whether the code runs once or fifty times. That's idempotency: the second call to `create_or_get_refund_request()` with the same inputs returns the existing row without creating a new one.

**Q4: What is `tools_condition` and where does it come from?**  
> `tools_condition` is a prebuilt conditional edge function from `langgraph.prebuilt`. It checks whether `state["messages"][-1].tool_calls` is non-empty. If yes, it routes to the `tools` node; if no, it routes to `END`. It's the standard two-node agent loop pattern.

**Q5: What's the difference between the deterministic scorer and the LLM-as-judge?**  
> The deterministic scorer checks objective facts: was `lookup_order` called? Does the answer contain the string "30 days"? Does it cite "return-policy.md"? The LLM judge checks subjective quality: given the expected behaviour description, is the answer faithful, appropriately cautious, and free of hallucination? You need both — the deterministic scorer doesn't hallucinate but can't assess nuance; the judge can assess nuance but might occasionally misevaluate.

**Q6: Why `with_structured_output` for `PolicyEligibilityDecision`?**  
> The policy classifier has a fixed output space: `eligible | likely_not_eligible | need_more_info`. Without structured output, you'd get free text and need brittle string parsing. `with_structured_output(PolicyEligibilityDecision)` uses Gemini's function-calling to guarantee a valid Pydantic object — the `decision` field is always one of the three enum values.

**Q7: How do you handle PII in logs and traces?**  
> All tools use `_email_domain(email)` before logging — only "example.com" is recorded, never "<alice@example.com>". Span attributes in OpenTelemetry also use the domain. Order IDs in log lines are truncated to 8 characters. This is lightweight PII reduction, not full anonymisation — the full email is still in DB queries and in-memory tool arguments.

**Q8: What happens if the Postgres checkpoint database is unavailable at startup?**  
> `AsyncPostgresSaver.from_conn_string(...)` is an `async with` context manager in the `lifespan` function. If the connection fails, the exception propagates out of `lifespan`, which prevents the FastAPI app from starting. The app fails fast at startup rather than failing at request time — which is the intended behaviour.

**Q9: Why use `NullPool` in the test fixtures?**  
> SQLAlchemy's normal pool reuses connections across calls. In the rollback-savepoint test pattern, each test needs to get the *same* connection it started its transaction on (so the rollback undoes the test's writes). `NullPool` disables connection reuse, so every `engine.connect()` gets a fresh connection — the savepoint-based isolation works correctly.

**Q10: Could the main agent be swapped from Gemini to GPT-4o with no code changes beyond the import?**  
> Almost. `ChatGoogleGenerativeAI` → `ChatOpenAI`, update the API key settings field. The `bind_tools` and `with_structured_output` calls are LangChain-layer abstractions that work identically. The system prompt would likely need minor tuning since instruction-following characteristics differ between models. The RAG embeddings are model-specific — you'd also need to re-ingest with OpenAI's embedding model.

**Q11: What is the `langgraph_node` metadata check in the event stream for?**  
> `graph.astream_events(version="v2")` emits events from every node in the graph — including the ToolNode. If the tool calls Gemini (which they don't in this codebase — tools only call the DB), its tokens would also appear as `on_chat_model_stream`. The check `if metadata.get("langgraph_node") != "llm": continue` ensures only tokens from the main `llm` node are streamed to the client — preventing tool-internal LLM calls from leaking into the chat stream.

**Q12: What is `RecursiveCharacterTextSplitter` doing, and why those parameters?**  
> It splits documents into chunks ≤500 characters with 100-character overlap. It tries to split on paragraph breaks first (`\n\n`), then newlines, then spaces, then characters — preserving semantic units as long as possible. The 100-character overlap means the end of one chunk and the start of the next share context, so a policy rule that spans a paragraph break isn't split across two incomplete chunks.

**Q13: How does the HITL approval UI work?**  
> `backend/app/static/chat.html` is a static HTML+JS page mounted at `/static/chat.html`. When the SSE stream sends `{"type": "interrupt", "interrupt": {...}}`, the JavaScript shows an approval form. On submit, it POSTs to `POST /v1/chat/resume` with `{session_id, approved, reviewer_note}`. The FastAPI route passes `Command(resume=...)` to the graph.

**Q14: Is there auth protecting the `/chat/resume` endpoint?**  
> No. This is a known honest gap. The `session_id` is the only correlation, and it's not cryptographically signed. In production, this endpoint must be protected — either by a JWT that proves the caller is an authorised reviewer, or by a separate internal-only network path. I'd add a reviewer auth token check as the next stage.

**Q15: How would you scale this if AbhiMart's chat volume grew 100x?**  
> Three bottlenecks: (1) **Gemini API rate limits** — add a retry layer with exponential backoff and circuit breaker; consider batching or caching responses for identical questions. (2) **Postgres connection pool** — increase `pool_size`/`max_overflow`, or move to PgBouncer for connection pooling. (3) **pgvector query latency at scale** — switch from exact nearest-neighbour to an HNSW index (`CREATE INDEX USING hnsw`) which trades some recall for sub-linear query time. The SSE streaming architecture itself scales well because each connection is handled by a coroutine, not a thread.

---

## APPENDIX: Key File Reference

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app, lifespan, AsyncPostgresSaver setup |
| `backend/app/config.py` | pydantic-settings Settings class, `get_settings()` singleton |
| `backend/app/database.py` | `create_async_engine`, `async_session_factory`, `get_db()` |
| `backend/app/api/v1/chat.py` | `/v1/chat`, `/v1/chat/resume`, `event_stream()`, SSE |
| `backend/app/agents/customer_support/graph.py` | StateGraph, `llm` node, `build_graph()` |
| `backend/app/agents/customer_support/tools.py` | All 6 `@tool` functions, PII-safe logging |
| `backend/app/agents/customer_support/guardrails.py` | `check_input_guardrails()`, 5 deterministic checks |
| `backend/app/agents/customer_support/refund.py` | `prepare_refund_review()`, idempotency key, `create_or_get_refund_request()` |
| `backend/app/agents/customer_support/policy.py` | `classify_return_eligibility()`, `PolicyEligibilityDecision`, `with_structured_output` |
| `backend/app/rag/ingest.py` | Document chunking, pgvector ingestion, `gemini-embedding-001` |
| `backend/app/exceptions.py` | Typed domain exceptions (`InsufficientStockError` etc.) |
| `backend/app/models/refund_request.py` | `RefundRequest` ORM model, idempotency_key unique constraint |
| `backend/app/observability.py` | OTEL `TracerProvider`, Jaeger/console exporter, FastAPIInstrumentor |
| `backend/app/observability_metrics.py` | Prometheus counters/histograms for chat, tools, RAG, policy |
| `backend/app/tests/conftest.py` | `NullPool`, `create_savepoint`, rollback isolation |
| `backend/app/tests/test_products.py` | HTTP integration tests via `httpx.AsyncClient` |
| `backend/evals/run_eval.py` | Local JSONL eval runner |
| `backend/evals/score_results.py` | Deterministic scorers (tools, facts, sources) |
| `backend/evals/judge_results.py` | LLM-as-judge with `QualityGrade` structured output |
| `backend/evals/langsmith_run.py` | LangSmith `aevaluate()` experiment runner |
| `backend/evals/run_refund_hitl_eval.py` | HITL-specific eval: interrupt → approve → verify DB state |
| `backend/evals/datasets/` | 4 JSONL datasets for different eval scenarios |
