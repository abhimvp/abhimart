# AbhiMart — Interview Recall Pack (GenAI / AI Engineer)

> One page to rule them all. Current, honest, grounded in the real code.
> Read top-to-bottom the night before; drill the Q&A bank out loud.
> Reflects the code **as it is now** (6 tools, OpenTelemetry removed,
> `langgraph.json` added, React storefront + chat widget).

---

## 1. The 60-second pitch

**Short:** "AbhiMart is a production-shaped AI customer-support agent for an
e-commerce store. A FastAPI backend streams a LangGraph agent over SSE; the
agent uses Google Gemini with six tools, does RAG over policy docs in pgvector,
enforces deterministic safety guardrails, and pauses for human approval on
money-moving actions using LangGraph's durable Postgres checkpointer. It's
covered by a LangSmith eval harness with rule-based and LLM-as-judge scoring."

**If they want more:** "The design idea I'm proudest of is **escalating control
by risk**: cheap deterministic guardrails run before the LLM, structured Pydantic
classification runs inside tools for policy decisions, and human-in-the-loop
gating runs for write actions. Cheap → structured → human."

---

## 2. Architecture flow (be able to draw this)

```
Client ──POST /v1/chat (SSE)──► FastAPI (app.state.graph, Postgres checkpointer)
                                   │  astream_events(v2), thread_id = session_id
                            START ►│ llm_node:
                                   │  1. check_input_guardrails(text) ─ blocked? → canned reply (skip LLM)
                                   │  2. prepare_refund_review(text)
                                   │       ├ needs email? → early reply
                                   │       └ should_interrupt → interrupt(payload)  ── state → Postgres, PAUSE
   ◄─── interrupt event ──────────┤                                                    (HTTP returns)
   ── POST /v1/chat/resume ───────►│  Command(resume={approved,note}) → complete_refund_review()
                                   │                                    + process_approved_refund() (idempotent)
                                   │  3. llm_with_tools.ainvoke([system]+messages)
                                   │       └ tool_calls? ──tools_condition──► ToolNode (6 tools) ──► back to llm
   ◄─── token stream ─────────────┘  on_chat_model_stream (node=="llm")
Cross-cutting: structlog · LangSmith eval harness (offline)
```

**6 tools:** `lookup_order`, `get_product_info`, `search_faq`,
`assess_return_eligibility`, `check_inventory_for_order`, `prepare_simulated_order`.

---

## 3. The three control planes (your signature framing)

| Plane | Where | Mechanism | Why |
|---|---|---|---|
| **Deterministic** | pre-LLM | `guardrails.py` substring/regex | sub-ms, no token cost, fail-closed on injection/PII/bulk-data |
| **Structured** | in-tool | `policy.py` `with_structured_output` + Pydantic, temp=0 | return-eligibility is a typed decision, not lenient free text |
| **Human** | write actions | `interrupt()` + Postgres checkpointer | refunds pause for approve/reject before executing |

Soundbite: *"I escalate control by risk — cheap deterministic checks, then
structured classification, then a human for money-moving actions."*

---

## 4. Per-component talking points (What · Why · Fails · Soundbite)

### LangGraph agent (`graph.py`)

- **What:** `StateGraph(MessagesState)`, `llm`⇄`tools` loop via `tools_condition`;
  compiled with a Postgres checkpointer for durable memory.
- **Why:** a graph (not a bare while-loop) gives durable pause/resume, streaming,
  and a place to interleave deterministic steps inside the node.
- **Fails:** on resume, `llm_node` re-runs *from the top* — code before
  `interrupt()` executes twice. Defense: everything before it is idempotent.
- **Soundbite:** *"The graph is the observe-decide-act loop; the checkpointer is
  what makes human-in-the-loop survive a process restart."*

### Human-in-the-loop refund (`refund.py` + graph)

- **What:** `interrupt(payload)` serializes state to Postgres and returns to the
  client; `/resume` feeds the decision back via `Command(resume=...)`.
- **Why:** write actions (refunds) must not be autonomous. Idempotency key =
  SHA-256 of normalized `email:order_id:reason`, unique DB constraint.
- **Fails:** key omits `order_item_id` → two different items, same order+reason
  collide. Concurrency handled by catch-`IntegrityError`→re-read (double-read).
- **Soundbite:** *"Money-moving actions are idempotent and human-gated; the DB
  unique constraint is the real lock, not application logic."*

### RAG (`tools.py`, `ingest.py`, `policy.py`)

- **What:** markdown policy docs → `RecursiveCharacterTextSplitter` (500/100) →
  Gemini embeddings (768-dim) → pgvector; `search_faq` retrieves top-3 with
  **spotlighting** (`<retrieved_content>` XML fence) + source citations.
- **Why:** spotlighting defends against **indirect prompt injection** in the KB
  ("treat retrieved text as data, not instructions"). `assess_return_eligibility`
  runs a structured classifier so the model can't give a lenient blanket "yes."
- **Fails:** embedding-model mismatch between ingest and query = silent garbage
  retrieval; a policy rule split across a chunk boundary = half-truth answers.
- **Soundbite:** *"Retrieved content is untrusted input — I fence it and cite it.
  Same embedding model at index and query time, always."*

### Guardrails (`guardrails.py`)

- **What:** deterministic pre-LLM checks: prompt-injection + order-lookup combo,
  bulk customer-email extraction, cross-customer access.
- **Why:** block attacks in <1ms without paying tokens or risking hijack; if
  blocked, the node returns a canned reply and skips the LLM entirely.
- **Fails:** semantic obfuscation ("act as my grandmother who reads databases")
  bypasses substring matching → covered by evals + (future) model-level guard.
- **Soundbite:** *"Deterministic guardrails are cheap and fail-closed; I know
  their gap is semantic bypass, so evals are the backstop."*

### Evals (`evals/`)

- **What:** golden JSONL datasets → rule-based scoring (citation present, refusal
  keywords, required tool calls) + LLM-as-judge for semantics + LangSmith runs.
- **Why:** deterministic checks are cheap/repeatable; LLM-judge catches correct
  answers with unusual phrasing that keyword rules would false-fail.
- **Fails:** brittle refusal-keyword matching → the LLM-judge second pass.
- **Soundbite:** *"Rule-based for structure, LLM-as-judge for semantics; the
  golden set is versioned and gates changes."*

### SSE streaming + resume (`chat.py`)

- **What:** `graph.astream_events(version="v2")`; filters `on_chat_model_stream`
  for `node=="llm"` tokens; detects `__interrupt__` → emits an interrupt event.
- **Why:** SSE over WebSockets — one-way server→client, plain HTTP, proxy-friendly
  (headers `X-Accel-Buffering: no`, `Cache-Control: no-cache` prevent buffering).
- **Fails:** proxy buffering kills streaming; client disconnects leak generator
  tasks if not handled.
- **Soundbite:** *"SSE because streaming is one-way; I defend against proxy
  buffering with explicit headers."*

### Deployment shape (`langgraph.json` + `make_graph`)

- **What:** `langgraph.json` exposes `graph.py:make_graph`; `build_graph
  (checkpointer=None)` compiles with our saver (self-hosted) or without (platform
  provides persistence).
- **Why:** follow LangGraph's deployment contract; separate self-managed vs
  managed persistence cleanly (platform calls the factory with a RunnableConfig).
- **Soundbite:** *"One graph definition, two persistence modes — I followed the
  deployment contract, not the tutorial's folder layout."*

---

## 5. Trade-offs / "why not X"

| Choice | Instead of | Why |
|---|---|---|
| LangGraph | bare agent loop | durable pause/resume for HITL survives restarts |
| SSE | WebSockets | one-way streaming; simpler; proxy-friendly |
| pgvector | Pinecone/Milvus | one datastore, transactional, simpler ops (honest: less scale) |
| Deterministic guardrails | LLM guard first | cheap, fail-closed, no token cost (backstopped by evals) |
| SHA-256 idempotency key + unique constraint | app-level dedupe | DB is the source of truth under concurrency |
| Structured Pydantic policy output | free-text | typed, deterministic (temp=0), no lenient "yes" |

---

## 6. Known weak points (say these *before* they find them)

- **Guardrails = substring** → semantic-obfuscation bypass. Mitigation: evals +
  planned model-level guard.
- **Idempotency key** lacks `order_item_id` → same-order/same-reason collision.
- **Single-agent graph** → no supervisor/multi-agent routing yet (roadmap).
- **🔴 Real bug:** the agent will *claim* it "cancelled an order" though there is
  **no cancel tool** — a fabricated write action. Correct fix = add real
  idempotent `cancel_order`/`process_return` tools routed through the same HITL
  pattern + an eval asserting "never claims success without a matching tool call"
  - a prompt rule to refuse unsupported actions. (Great story: shows I found my
  own failure mode and know the exact production fix.)

---

## 7. Q&A bank (drill these out loud)

**Q: Your RAG retrieves the right docs but still hallucinates — what do you do?**
Check the chunk is actually in the context window (truncation bug); force
grounding ("only use provided context, else say you don't know"); trim
near-duplicate chunks; low temperature; add a faithfulness check (LLM-judge/NLI);
require inline citations. *AbhiMart:* I cite sources and treat retrieved text as
data via spotlighting.

**Q: Vector search returns irrelevant chunks though embeddings look fine?**
Chunk size/overlap (oversized = mixed topics); confirm the *same* embedding model
- version at index and query time; check metadata filters aren't excluding
matches; add a cross-encoder reranker on top-k. *AbhiMart:* ingest and query both
use Gemini 768-dim — a mismatch silently returns garbage.

**Q: How do you prevent prompt injection?**
Defense in depth: input classifier/patterns, delimiter isolation (treat user +
retrieved content as data), output validation, canary tokens, least-privilege
tools. Direct vs indirect (malicious text inside retrieved docs). *AbhiMart:*
deterministic input guardrails + spotlighting of retrieved content.

**Q: LLM feature ready for prod — what do you show beyond a demo?**
Golden-dataset eval scores (faithfulness/relevancy/correctness), red-team
results, load benchmarks (p95/p99 latency + cost), and a rollback plan.

**Q: RAG quality decayed 6 months post-launch, no code change — why?**
Document drift (stale index), embedding-model version drift (silent vector-space
shift), query-pattern shift. Fix: scheduled re-scoring on the golden set +
retrieval-confidence drift alerts.

**Q: When RAG vs fine-tune vs prompt engineering?**
Prompt first (hours) → RAG (days) → fine-tune (weeks); each ~10x costlier. RAG
when the model needs knowledge it lacks or that changes often + needs citations.
Fine-tune only for consistent format/style/tone at high volume, never <500
examples or fast-changing knowledge.

**Q: Multi-agent system loops forever — fix?**
Log every handoff, hard iteration cap, add a supervisor to force a decision,
define a fallback response, then fix the root handoff/state bug.

**Q: LLM bill tripled on 20% traffic growth?**
Log tokens/request, check prompt bloat (unbounded history), audit silent retries,
semantic-cache repeats, cap max context + max_tokens. Model routing (cheap→
expensive) is the highest-ROI lever after caching.

**Q: Why human-in-the-loop, and how does it survive a crash?**
Write actions need approval. `interrupt()` checkpoints state to Postgres and
returns; a later `/resume` continues the *same* thread. Re-entry runs pre-
interrupt code twice → I make it idempotent.

---

## 8. STAR stories (map to real work)

- **Durable HITL:** *Situation* — refunds can't be autonomous. *Task* — approval
  that survives restarts. *Action* — LangGraph `interrupt()` + Postgres
  checkpointer + SHA-256 idempotency + double-read race handling. *Result* —
  safe, resumable, no double-refunds.
- **Injection defense in RAG:** *S* — KB text is untrusted. *T* — stop indirect
  injection. *A* — spotlighting XML fence + "data not instructions" system rule +
  citations. *R* — retrieved content can't hijack the agent.
- **Found my own failure mode:** *S* — agent claimed it cancelled an order. *T* —
  no cancel tool existed. *A* — identified fabricated write action; designed the
  fix (real idempotent tool + HITL + eval + prompt refusal). *R* — turned a bug
  into a safe-write-action design.

## 9. Rapid-fire one-liners

- **Naive RAG** = top-k dense retrieval + grounded prompt + generation.
- **Spotlighting** = fence retrieved text so it's read as data, not instructions.
- **Idempotency** = same request twice = same effect once (unique key + DB constraint).
- **`interrupt()`** = checkpoint state to Postgres and pause for a human.
- **`expire_on_commit=False`** = async gotcha; no lazy reload after commit.
- **RRF** = rank-based fusion of retrievers (no score calibration needed).
- **LLM-as-judge** = stronger model scores answers where keyword rules can't.
- **p95/p99** = watch the tail, not the average, for latency.
