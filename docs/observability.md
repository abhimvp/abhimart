# Observability Notes

This document captures the observability concepts used in AbhiMart and why we
are adding them. It is intentionally written as project knowledge, not just a
tool checklist.

## What Observability Means

Observability is the ability to understand what a running system is doing from
the outside.

For AbhiMart, a single chat request may involve:

1. FastAPI receiving `/v1/chat`
2. LangGraph running the customer-support agent
3. The LLM deciding whether to call tools
4. Tools querying Postgres or RAG documents
5. Gemini generating the final response
6. FastAPI streaming the answer back to the user

Without observability, a slow or incorrect answer becomes hard to debug. We may
know that something failed, but not where or why.

With observability, we can answer questions such as:

- Did the API receive the request?
- How long did the agent run take?
- Which tool was called?
- Did RAG retrieval happen?
- Was Postgres slow?
- Did the request fail before or after the LLM call?
- Did an internal structured-output call leak into the customer-facing stream?

## What OpenTelemetry Is

OpenTelemetry, often called OTel, is an open-source, vendor-neutral standard for
generating, collecting, and exporting telemetry data.

Telemetry data means structured information emitted by an application while it
runs. The main types are:

- **Traces**: the full path of one request through the system
- **Spans**: timed steps inside a trace
- **Logs**: event records explaining what happened
- **Metrics**: numeric measurements over time, such as request count or latency

In one sentence:

> OpenTelemetry lets our code emit standardized "what happened" data.

## Is OpenTelemetry Free?

OpenTelemetry itself is free and open source.

The part that may cost money is the backend where telemetry is stored and
visualized.

Free or local options include:

- console exporter
- Jaeger
- Prometheus
- Grafana
- OpenTelemetry Collector

Paid or hosted options include:

- Datadog
- New Relic
- Honeycomb
- Grafana Cloud
- AWS CloudWatch / X-Ray
- Google Cloud Trace
- Azure Monitor

The useful mental model:

> OpenTelemetry is the instrumentation standard. The backend or viewer can be
> free, self-hosted, or paid.

## Why We Use Both LangSmith And OpenTelemetry

LangSmith and OpenTelemetry solve related but different problems.

LangSmith is best for AI and agent debugging:

- What prompt was sent?
- What tool calls happened?
- What did the model return?
- Which eval cases passed or failed?
- Which prompt/model version performed better?

OpenTelemetry is best for application and system debugging:

- Is the API slow?
- Is Postgres slow?
- Are requests failing?
- Which part of the request path caused latency?
- How does one request move through the backend?

Interview-ready summary:

> LangSmith gives us AI/agent observability. OpenTelemetry gives us application
> and distributed-system observability. In production, we usually want both.

## Core Terms

### Trace

A trace is the full journey of one request.

Example:

```text
POST /v1/chat
  -> run customer_support_graph
    -> call assess_return_eligibility
      -> retrieve return-policy.md
      -> call Gemini classifier
    -> generate final response
```

### Span

A span is one timed operation inside a trace.

Example:

```text
span: chat.request              1200ms
span: langgraph.agent_run        980ms
span: tool.assess_return         420ms
span: db.product_lookup           35ms
```

### Attribute

An attribute is structured metadata attached to a span.

Example:

```text
session_id = "abc123"
agent_name = "customer_support"
tool_name = "lookup_order"
eval_case_id = "order_with_email_001"
```

Attributes are important because they let us filter and search telemetry later.

## How AbhiMart Will Use OpenTelemetry

The first implementation should stay small and useful.

The first implementation exports spans to the console. This keeps the learning
loop simple: no Jaeger, Grafana, or external vendor is required yet.

FastAPI's low-level ASGI `send` and `receive` spans are disabled because SSE
streaming emits many response-body events. We keep the main HTTP request span
and the AbhiMart business spans so local traces stay readable.

Current spans include:

- incoming chat requests
- LangGraph agent runs
- tool calls
- RAG retrieval
- Postgres lookups
- structured return-policy classification

Later, we can add metrics such as:

- request count
- request latency
- agent latency
- tool call count
- error count

We do not need a paid observability platform to learn this. Local console output
or a local tracing backend is enough for the first pass.

## Local Commands

After OpenTelemetry dependencies are added to `backend/pyproject.toml`, install
them from the backend directory:

```bash
cd backend
uv sync
```

Enable local console tracing in `.env`:

```env
OTEL_ENABLED=true
OTEL_SERVICE_NAME=abhimart-backend
OTEL_ENVIRONMENT=local
```

Start the API:

```bash
uv run uvicorn app.main:app --reload
```

Then send a chat request from the browser chat UI or with curl/Postman. The
terminal should print OpenTelemetry span JSON for the FastAPI request and
AbhiMart-specific spans such as:

```text
chat.request
chat.agent_stream
agent.llm_node
tool.lookup_order
tool.get_product_info
tool.assess_return_eligibility
rag.retrieve
policy.classify_return_eligibility
```

If the console output becomes noisy, set this back to false:

```env
OTEL_ENABLED=false
```

## Questions To Ask Before Adding Observability

When adding observability to any project, ask:

- What production failures would be painful to debug?
- What request path matters most?
- Which operations are slow, expensive, or risky?
- What metadata would help us filter the problem later?
- Are we collecting enough information to debug without exposing sensitive data?
- Which data belongs in LangSmith, and which belongs in OpenTelemetry?

For AbhiMart, sensitive values such as full customer emails, full chat content,
or private order details should be handled carefully. Observability should help
debug the system without becoming a privacy leak.

## Official Resources

- [OpenTelemetry: What is OpenTelemetry?](https://opentelemetry.io/docs/what-is-opentelemetry/)
- [OpenTelemetry observability primer](https://opentelemetry.io/docs/concepts/observability-primer/)
- [OpenTelemetry docs](https://opentelemetry.io/docs/)
