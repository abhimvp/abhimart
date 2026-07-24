# interview-pep notes

**Your goal:** Walk through your AbhiMart project (LangChain/LangGraph/vectorDB AI-agent portfolio app) so you can *confidently defend it in interviews* as senior-level work. Along the way: understand what it does, clean up/restructure where messy, add improvements, and produce crisp point-form notes you can revise from — all done **one step at a time** with a **tracker** so you never feel lost or overloaded, and with **approval before any code change**.

The user's current instruction, verbatim:

> "Hey , i just want to explore through this abhimart project i have built as a portfolio project to showcase my understanding of building ai agents using langchain, langgraph , vectordbs ..etc - so it's been a while i worked on this project as i was constantly hopping on to different learning stuff and interviews and never got to this project again and now it's looking new for me as it's been a real while and i am sort of having an interview deadline prep and want to be able to defend this project and be ready to answer in interviews about this project - and this project repo already has lot of files where i kind of tried to document things on how to say and all - but past is past right like it's all overwhelming at this point to go through everything one by one as there is lot of those docs -> so here is what i am thinking like understand the project and what it's doing and what all main components/things it have and how the flow is looking like and what all the different use-cases it's handling and at the same time thinking to refactor the repo like if it's not clean make it better and structured to be able to walkthrough and also document stuff in points to be able to re-call before interview and how to say things in technical way on each of the things present in here and end goal is to justify this is a senior engineer production app ( even if it's not let's improve it ) and add new things along the way - step by step everything - one thing at a time - so i don't get lost and overloaded - so let's track what we're doing now & what we want to do - like have a seperate thing tracking all what we're doing - so i can look back if i missed anything and resume from there as needed - let me know if you got the point and just give me guided instrcutions on whatever you want to do - so i will run them and i can see what;s happening and knows what my project as well - just take approvals alright for any code changes so i know what;s changing too at any point"

## Here's the honest state of AbhiMart

### What this project actually is

An **AI customer-support agent for a fictional e-commerce store**, built as a 7-stage full-stack GenAI system. This is *not* a toy — it's genuinely mid-to-senior-level in ambition. The architecture:

```
User → FastAPI (SSE stream) → LangGraph agent
        ├─ deterministic guardrails (PII / prompt-injection / bulk-data blocks)
        ├─ refund path → human-in-the-loop interrupt() → resume
        └─ LLM (Gemini) with 6 tools ⇄ ToolNode
              ├─ lookup_order / get_product_info (Postgres)
              ├─ search_faq / assess_return_eligibility (RAG: pgvector + Gemini embeddings)
              ├─ check_inventory_for_order / prepare_simulated_order (Stage 7)
        + Postgres checkpointer (durable memory) + OpenTelemetry/Jaeger/Prometheus + LangSmith evals
```

### The components you'll be defending

| Area | What's there | Senior-signal |
|---|---|---|
| **Agent orchestration** | LangGraph `StateGraph`, llm⇄tools loop, `tools_condition` | Solid |
| **Human-in-the-loop** | `interrupt()` + Postgres checkpoint + `/chat/resume`, idempotent re-entry | **Strong** — this is the standout |
| **RAG** | pgvector, chunking, spotlighting XML defense, source citations | Strong |
| **Guardrails** | Deterministic pre-LLM checks (injection, bulk-data, cross-customer) | Good, with known semantic-bypass gap |
| **Durable refunds** | SHA-256 idempotency keys, double-read race handling, `Numeric(10,2)` money | **Strong** |
| **Structured policy** | `with_structured_output` + Pydantic + temp=0 classifier | Strong |
| **Observability** | OTel traces/spans/metrics, Jaeger, Prometheus `/metrics` | Strong |
| **Evals** | Golden JSONL + rule-based scoring + LLM-as-judge + LangSmith | Strong |

**The good news:** your existing `docs/AbhiMart_Codebase_Walkthrough.md` is already excellent — line-by-line "why + how it fails" reasoning. You've done more real documentation than most portfolio projects ever get.

---

## AbhiMart Architecture & Flow Map

This is your **big-picture mental model**. Learn this one page and you can narrate the whole system in an interview before drilling into any component.

### 1. The one-sentence pitch

> "AbhiMart is a production-shaped AI customer-support agent for an e-commerce store: a FastAPI backend streams a LangGraph agent over SSE; the agent uses Gemini with six tools, does RAG over policy docs in pgvector, enforces deterministic safety guardrails, and pauses for human approval on money-moving actions using LangGraph's durable checkpointer — all instrumented with OpenTelemetry and covered by a LangSmith eval harness."

### 2. Request lifecycle (the flow you must be able to draw)

```
                        ┌─────────────────────── FastAPI (app.state.graph, Postgres checkpointer) ──────────────────────┐
 Client                 │                                                                                                │
   │  POST /v1/chat     │   astream_events(v2), thread_id = session_id                                                   │
   │───────────────────▶│                                                                                                │
   │  (SSE stream)      │        ┌──────────────┐                                                                        │
   │                    │  START→│   llm_node   │                                                                        │
   │                    │        └──────┬───────┘                                                                        │
   │                    │   1. check_input_guardrails(text)  ── blocked? ─▶ return canned AIMessage (skip LLM entirely)  │
   │                    │   2. prepare_refund_review(text)                                                               │
   │                    │        ├─ .response set?      ─▶ return early (e.g. "need your email")                         │
   │                    │        └─ should_interrupt?   ─▶ interrupt(payload) ──┐  (state serialized to Postgres)        │
   │◀───interrupt event─┼────────────────────────────────────────────────────  │  graph PAUSES, HTTP returns           │
   │                    │                                                        │                                       │
   │  POST /v1/chat/    │   Command(resume={approved, note})  ───────────────────┘  re-enters llm_node from top,         │
   │  resume            │        complete_refund_review() + process_approved_refund()  (idempotent)                      │
   │                    │   3. llm_with_tools.ainvoke([system]+messages)                                                 │
   │                    │        └─ tool_calls? ──tools_condition──▶ ┌───────────┐                                       │
   │                    │                                            │ ToolNode  │── lookup_order / get_product_info     │
   │                    │        ◀────── edge tools→llm ─────────────│  (6 tools)│── search_faq / assess_return_elig     │
   │◀────token stream───┼─── on_chat_model_stream (node==llm) ───    └───────────┘── check_inventory / prepare_order     │
   │                    │                                                  │                                             │
   │                    │                          search_faq/assess ──▶ pgvector similarity_search (Gemini embeddings)  │
   └────────────────────┴────────────────────────────────────────────────────────────────────────────────────────────┘
        Cross-cutting: OpenTelemetry spans → Jaeger · Prometheus /metrics · structlog · LangSmith eval harness (offline)
```

### 3. The three "control planes" (a senior framing that impresses)

AbhiMart layers **three different kinds of control** around the LLM — name them explicitly:

1. **Deterministic control (pre-LLM):** `guardrails.py` — sub-millisecond substring/regex blocks for prompt-injection, bulk-data, cross-customer. *No model call.* Fail-closed and cheap.
2. **Structured control (in-tool):** `policy.py` — forces the LLM into a Pydantic schema (`with_structured_output`, temp=0) so return-eligibility is a typed decision, not free text prone to lenient "yes".
3. **Human control (write actions):** `interrupt()` + checkpointer — money-moving refunds pause the graph, persist to Postgres, and wait for an out-of-band human approve/reject before executing.

That "cheap→structured→human, escalating by risk" story is exactly the kind of design reasoning senior interviewers probe for.

### 4. Why each big technology choice (your "why not X" defenses)

- **LangGraph over a plain agent loop** → because you need *durable* pause/resume for human-in-the-loop; `interrupt()` + Postgres checkpointer gives you that for free. A bare while-loop can't survive a process restart mid-approval.
- **SSE over WebSockets** → streaming is one-way server→client; SSE is plain HTTP, simpler, proxy-friendly (you even set `X-Accel-Buffering: no`).
- **pgvector over a dedicated vector DB** → you already run Postgres; one datastore = simpler ops, transactional consistency, no extra infra. Honest trade-off: less scale than Pinecone/Milvus.
- **Idempotency via SHA-256 key + unique constraint** → refunds must never double-fire; the DB constraint is the source of truth, and re-entry after resume is safe because reads happen before writes.
- **Deterministic guardrails before the LLM** → block attacks without paying token cost or risking hijack; you *know* the semantic-bypass gap exists and cover it with evals + LLM-judge.

### 5. Known weak points (say these *before* the interviewer finds them — it reads as senior)

- Guardrails are substring-based → **semantic obfuscation bypass** ("act as my grandmother who reads databases…"). Mitigation: evals + planned model-level guardrail.
- Idempotency key includes `reason` but not `order_item_id` → two different items, same order+reason collide.
