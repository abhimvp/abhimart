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
│   └── policy_decision_golden.jsonl
├── run_eval.py
├── score_results.py
├── run_policy_decision_eval.py
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
| LangSmith latest inspected experiment | 8/8 passing |
| Structured policy decision evals | 3/3 passing |

The previously flaky case was:

```text
policy_return_electronics_001
```

This case asks whether opened Sony headphones used for a week can be returned.
The agent retrieved and cited the correct return policy, but earlier versions
could answer too permissively by saying the item may be eligible despite the
policy requiring original/unused condition. This was a policy-reasoning/
synthesis issue, not a retrieval failure.

To reduce this variability, AbhiMart now has a structured policy eligibility
classifier in `app/agents/customer_support/policy.py` and a higher-level
`assess_return_eligibility` tool in `app/agents/customer_support/tools.py`.

It classifies return-policy situations as:

- `eligible`
- `likely_not_eligible`
- `need_more_info`

This creates an explicit intermediate business decision before generating a
customer-facing answer. The classifier is evaluated separately with
`policy_decision_golden.jsonl` and `run_policy_decision_eval.py`, and the full
agent eval now requires return-eligibility questions to use
`assess_return_eligibility`.

The streaming layer also filters nested model events so structured-output model
calls inside tools are not leaked to the customer-facing SSE response.

## Next Improvements

- Add structured policy eligibility decisions:
- Rerun LangSmith experiments after structured eligibility tool wiring.
- Compare prompt/model versions in LangSmith.
- Add LLM-as-judge only for semantic checks that deterministic rules cannot
  capture cleanly.
- Add OpenTelemetry-based system observability for traces, logs, and metrics.

## Learning Checklist

Evaluation is not just a library feature. It is an engineering habit: identify
what can go wrong, turn those risks into examples, run the real system, score
the behavior, and use failures to guide changes.

Before adding or changing agent behavior, ask:

1. What is the user trying to accomplish?
2. What tool or data source should the agent use?
3. What tool should the agent avoid?
4. What facts must be grounded in retrieved or database-backed data?
5. What should the agent ask for before acting?
6. What should the agent refuse?
7. What business decision must be correct?
8. Can this be checked with deterministic code?
9. Does this require human review or LLM-as-judge?
10. What failure would be dangerous in production?

For AbhiMart, those questions become eval categories:

- Policy/RAG: answers must use `search_faq`, cite source docs, and apply all
  policy conditions.
- Order lookup: the agent must ask for email before lookup and use
  `lookup_order` when the customer provides the email.
- Product lookup: the agent must use `get_product_info` and avoid inventing
  unavailable products.
- Security/privacy: the agent must not expose another customer's orders.

Useful vocabulary:

| Observation | Engineering phrase |
|---|---|
| Agent called the wrong tool | Tool-routing failure |
| Agent skipped a required tool | Missing tool invocation |
| RAG returned the wrong document | Retrieval failure |
| RAG returned the right document but answer was wrong | Synthesis/reasoning failure |
| Answer lacks source document | Citation/grounding failure |
| Answer invents unsupported facts | Hallucination |
| Answer allows something too easily | Overly permissive / policy-compliance failure |
| Answer refuses a valid request | Overly restrictive / false refusal |
| Eval fails on harmless wording differences | Evaluator brittleness |
| Same case passes and fails across runs | Model variability / flaky eval case |
| Agent exposes another user's data | Privacy/authorization failure |

Primary docs to read:

- [LangSmith evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts)
- [LangSmith evaluation types](https://docs.langchain.com/langsmith/evaluation-types)
- [LangSmith LLM-as-judge](https://docs.langchain.com/langsmith/llm-as-judge)
- [OpenAI graders](https://platform.openai.com/docs/guides/graders/)

Map those docs back to this project:

| Docs concept | AbhiMart implementation |
|---|---|
| Dataset | `abhimart-stage4-golden` / `stage4_golden.jsonl` |
| Example | One JSONL row |
| Target function | `run_agent` in `langsmith_run.py` |
| Evaluator | `deterministic_behavior_evaluator` / `score_results.py` |
| Experiment | `abhimart-stage4-local-agent-*` |
| Trace | One LangGraph agent run with model/tool calls |

If these concepts are skipped, agent work becomes guesswork: prompt changes may
feel better but regress hidden workflows, failures are hard to reproduce, and
there is no clear way to compare one version of the agent to another. Reading
the docs and mapping them to this project is what turns the eval harness from
"scripts that pass" into an engineering system you can explain and extend.
