# Interview - prep

AbhiMart's differentiators — HITL approval flows, guardrails, prompt-injection defenses, evals with deterministic scorers, tracing — are exactly the concerns of a regulated financial services firm. Most candidates walking in will demo a chatbot. You can talk about why a refund needs human approval and how you enforced it. Lead with that framing, not with "I built a RAG agent."

## Question areas to expect

- Agent architecture: why LangGraph over a plain chain or ReAct loop; how you modeled state; what happens on a node failure mid-run; how durable state and idempotency work; when you'd choose a deterministic workflow over an agent.
- Evals: what your JSONL dataset actually contains; deterministic scorers vs LLM-as-judge and when each lies to you; what you changed as a result of an eval.
- HITL: where the interrupt happens, how state survives the wait, what the approver sees, what happens on timeout or rejection.
- Retrieval: chunking strategy, why pgvector over Pinecone, how you measured retrieval quality separately from answer quality.
- Security: prompt injection through retrieved documents, tool-call authorization, PII handling.
- LLMOps: cost and latency tracking, model version pinning, what "regression" means for a non-deterministic system.
- SQL: joins, aggregation with GROUP BY/HAVING, window functions, indexing basics, and EXPLAIN. Practice ten on paper.
- Python: async/await and what actually blocks the event loop, Pydantic validation, generators, dict/list manipulation.

- **build the paper fallback**. One printed page: the AbhiMart architecture — request path, LangGraph node graph, pgvector retrieval, tool-calling boundary, the HITL interrupt point, and where tracing hooks in. Put it on the table when the architecture question comes.
