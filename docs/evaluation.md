# AbhiMart Evaluation

AbhiMart uses a small golden eval suite to measure whether the customer-support
agent behaves correctly across policy, order, product, and privacy workflows.

The goal is not exact text matching. The goal is to check business behavior:
which tools the agent uses, whether it cites the right sources, whether it asks
for missing information, and whether it makes safe policy decisions.

## Eval Components

The local eval harness lives in `backend/evals/`.

```text
backend/evals/
├── datasets/
│   └── stage4_golden.jsonl
├── run_eval.py
├── score_results.py
├── langsmith_dataset.py
└── langsmith_run.py
```

### Golden Dataset

`stage4_golden.jsonl` contains one JSON object per eval case.

Each row has:

- `inputs`: the user message sent to the agent
- `expected`: the behavior the agent should satisfy

The current dataset covers:

| Category | Cases |
|---|---:|
| Policy/RAG | 3 |
| Order lookup | 2 |
| Product lookup | 2 |
| Security/privacy | 1 |

Expected behavior can include:

- `must_use_tools`
- `must_not_use_tools`
- `must_cite_sources`
- `expected_sources`
- `must_mention`
- `must_mention_any`
- `must_ask_for`
- `expected_stance`

### Local Runner

`run_eval.py` runs the real LangGraph agent against the golden dataset.

It captures:

- final answer
- tool calls
- lightweight LangGraph event samples

Each eval case uses a fresh `InMemorySaver` thread id so one case does not
pollute another case's conversation memory.

Run all local evals:

```bash
cd backend
uv run python evals/run_eval.py --fresh --delay 5
```

Run a slice:

```bash
uv run python evals/run_eval.py --start 3 --limit 2 --fresh --delay 5
```

Results are saved to:

```text
backend/evals/results/stage4_baseline.jsonl
```

### Local Scorer

`score_results.py` reads saved results and applies deterministic checks.

Run:

```bash
uv run python evals/score_results.py
```

The scorer prints total pass rate, category pass rate, and per-case checks.

## LangSmith

The same golden dataset can be synced to LangSmith and run as a tracked
experiment.

Sync dataset:

```bash
cd backend
uv run python evals/langsmith_dataset.py --replace
```

Run LangSmith experiment:

```bash
uv run python evals/langsmith_run.py
```

LangSmith stores:

- dataset examples
- experiment outputs
- traces
- latency/tokens
- deterministic evaluator score

## Current Baseline

As of May 15, 2026:

| Eval mode | Result |
|---|---:|
| Local deterministic evals | 8/8 passing |
| LangSmith latest inspected experiment | 7/8 passing |

The known failing/flaky case is:

```text
policy_return_electronics_001
```

This case asks whether opened Sony headphones used for a week can be returned.
The agent usually retrieves and cites the correct return policy, but can still
occasionally answer too permissively by saying the item may be eligible despite
the policy requiring original/unused condition.

This is a policy-reasoning/synthesis issue, not a retrieval failure.

## Next Improvements

- Add structured policy eligibility decisions:
  `eligible`, `likely_not_eligible`, or `need_more_info`.
- Compare prompt/model versions in LangSmith.
- Add LLM-as-judge only for semantic checks that deterministic rules cannot
  capture cleanly.
- Add OpenTelemetry-based system observability for traces, logs, and metrics.
