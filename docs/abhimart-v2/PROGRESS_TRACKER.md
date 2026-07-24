# AbhiMart v2 — Progress Tracker

> Living status for the from-scratch mastery build. See
> [BLUEPRINT.md](BLUEPRINT.md) for the full stage definitions.
> Resume from here anytime. No code changes without approval.

**Approach:** Two-track. Current AbhiMart = working demo (untouched by v2 work).
abhimart-v2 = new repo, built stage by stage. Blueprint drafted here in the
current repo first; the v2 repo gets created when we start Stage 0.

## Legend
✅ Done · 🔄 In progress · ⬜ Not started · ⏸️ Parked

## Status
| Stage | Name | Status | Notes |
|---|---|---|---|
| — | Blueprint + reference mapping | ✅ | PDFs skimmed; BLUEPRINT.md written |
| — | Create abhimart-v2 repo | ⬜ | Do at Stage 0 start |
| 0 | Foundation (scaffold, Docker PG, config, health) | ⬜ | |
| 1 | Data modeling (schema, migrations, seed) | ⬜ | |
| 2 | Catalog API (pagination, search, repo pattern) | ⬜ | |
| 3 | Auth & authorization (JWT, RBAC) | ⬜ | |
| 4 | Advanced backend (idempotency, locking, tx) | ⬜ | the "senior" stage |
| 5 | Frontend storefront + checkout | ⬜ | |
| 6 | Agent from first principles (bare loop → LangGraph) | ⬜ | |
| 7 | RAG ladder (Naive → Hybrid → HyDE → Corrective) | ⬜ | |
| 8 | RAG in production (evals, anti-hallucination) | ⬜ | |
| 9 | Guardrails & safety (defense in depth) | ⬜ | |
| 10 | Reliability & cost (LLM gateway, fallback, cache) | ⬜ | |
| 11 | OCR / unstructured ingestion | ⬜ | |
| 12 | MCP (server + client) | ⬜ | |
| 13 | Multi-agent (supervisor + specialists) | ⬜ | |
| 14 | LLMOps & deploy | ⬜ | |

## Reference PDFs read so far
- ✅ AI Engineer Scenario Walkthroughs (10 prod scenarios)
- ✅ LLMOps Interview Q&A (21 Q, 8-layer platform)
- ✅ RAG Architecture (8 patterns + drill plan)
- ⬜ FastAPI Cheatsheet, LangChain, LangGraph Core, Guardrails,
  Hallucination, Model Fallback, RAG Evaluation, RAG_CheatSheet, VectorDbs
  (skim per-stage as we reach them)

## Decisions
- 2026-07-24: Two-track chosen (keep current app as demo). Blueprint in current
  repo docs/ first; v2 repo later.

## Change log
- 2026-07-24: Blueprint + tracker created; 3 core PDFs read and mapped.
