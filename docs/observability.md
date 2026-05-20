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

The second local implementation sends traces to Jaeger using OTLP. Jaeger gives
us a browser UI for viewing trace waterfalls instead of reading raw JSON.

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

## Console Exporter vs Jaeger

The console exporter is useful for proving that spans exist:

```text
AbhiMart -> OpenTelemetry SDK -> terminal JSON
```

Jaeger is useful for reading traces visually:

```text
AbhiMart -> OpenTelemetry SDK -> OTLP exporter -> Jaeger -> browser UI
```

In Jaeger, one chat request appears as a waterfall:

```text
POST /v1/chat
  chat.agent_stream
    agent.llm_node
    rag.retrieve
    agent.llm_node
```

This is how engineers usually inspect timing and nesting. The UI calculates
durations and shows parent/child relationships automatically.

## Structured Logs

Traces show the shape and timing of one request. Logs record important events
and outcomes.

For AbhiMart, structured logs are privacy-safe event records such as:

```text
chat_request_received
chat_stream_started
chat_stream_completed
chat_stream_failed
tool_lookup_order_started
tool_lookup_order_completed
tool_get_product_info_started
tool_get_product_info_completed
rag_retrieval_completed
policy_classification_started
policy_classification_completed
tool_assess_return_eligibility_started
tool_assess_return_eligibility_completed
```

These logs include operational metadata such as:

- `session_id`
- message/query length
- duration in milliseconds
- result counts
- retrieved source filenames
- policy decision/confidence
- email domain only, not full customer email

They intentionally avoid raw customer messages, full emails, private order
details, and full retrieved document text.

Interview-ready distinction:

> Traces help me understand where time went in a request. Structured logs help
> me understand what important events happened and what decisions/outcomes were
> produced.

## Metrics

Metrics are numeric measurements collected over time.

They answer different questions from logs and traces:

```text
Trace:   What happened inside this one request?
Log:     What event happened, and with what outcome?
Metric:  How often is this happening over time?
```

Examples:

- requests per minute
- error rate
- average / p95 / p99 latency
- number of RAG retrievals
- number of tool calls by tool name
- number of active requests
- LLM request duration distribution

Metrics are usually aggregated and visualized as graphs. They are also the main
signal used for alerting.

Example alert questions:

- Is the chat API error rate above 5%?
- Is p95 latency above 10 seconds?
- Did RAG retrieval failures spike?
- Did order lookup latency increase after a database change?

### Metrics vs Logs vs Traces

Use all three together:

```text
Metrics tell us something is wrong.
Traces show where time/errors happened in one request.
Logs explain important events and outcomes around that request.
```

Example incident:

```text
Metric:  p95 chat latency jumped from 4s to 15s.
Trace:   Most slow requests spend time in agent.llm_node.
Log:     Requests are still retrieving the right source documents.
Action:  Investigate model latency/quota/provider behavior, not RAG.
```

### Common Metric Types

OpenTelemetry exposes metric instruments. The most important ones for this
project are:

#### Counter

A value that only goes up.

Use for:

- total chat requests
- total tool calls
- total errors
- total RAG retrievals

Example mental model:

```text
chat_requests_total += 1
tool_calls_total{tool_name="search_faq"} += 1
```

#### Histogram

Records a distribution of values.

Use for:

- chat request duration
- agent run duration
- RAG retrieval duration
- tool execution duration
- LLM call duration

Histograms are how we later ask p95/p99 latency questions.

Example mental model:

```text
chat_request_duration_ms observe 3520
rag_retrieval_duration_ms observe 577
```

#### Gauge

A value that can go up or down.

Use for:

- active requests
- queue depth
- current worker count

We probably do not need many gauges yet.

### Prometheus

Prometheus is a common open-source metrics backend.

It stores metrics as time series:

```text
metric name + labels + timestamped values
```

Example:

```text
chat_requests_total{route="/v1/chat",status="200"} 1234
tool_calls_total{tool_name="search_faq"} 81
```

Prometheus commonly uses a pull model: it periodically scrapes an HTTP endpoint
from the app, such as:

```text
/metrics
```

For AbhiMart, a future Prometheus flow could be:

```text
AbhiMart /metrics endpoint -> Prometheus -> Grafana dashboard
```

### Grafana

Grafana is a visualization/dashboard tool.

It does not usually collect metrics itself. It reads from data sources such as:

- Prometheus for metrics
- Jaeger or Tempo for traces
- Loki or another log backend for logs

For AbhiMart, Grafana would be useful for dashboards like:

- chat request rate
- chat latency p50/p95/p99
- error rate
- tool call counts by tool
- RAG retrieval latency
- policy classifier decision counts

### What Metrics Should AbhiMart Add First?

Do not add every possible metric. Start with a small set that answers real
operational questions.

Recommended first metrics:

- request count
- request duration histogram
- chat stream duration histogram
- tool call counter by tool name
- tool duration histogram by tool name
- RAG retrieval counter
- RAG retrieval duration histogram
- error count
- policy decision counter by decision label

Implemented first metrics:

```text
abhimart_chat_requests_total
abhimart_chat_stream_duration_ms
abhimart_tool_calls_total
abhimart_tool_duration_ms
abhimart_rag_retrievals_total
abhimart_rag_retrieval_duration_ms
abhimart_errors_total
abhimart_policy_decisions_total
```

They are exposed through a Prometheus-compatible `/metrics` endpoint when:

```env
OTEL_METRICS_ENABLED=true
OTEL_METRICS_EXPORTER=prometheus
```

Possible names:

```text
abhimart_chat_requests_total
abhimart_chat_request_duration_ms
abhimart_chat_stream_duration_ms
abhimart_tool_calls_total
abhimart_tool_duration_ms
abhimart_rag_retrievals_total
abhimart_rag_retrieval_duration_ms
abhimart_errors_total
abhimart_policy_decisions_total
```

### Metric Cardinality

Cardinality means how many unique label combinations a metric can produce.

This matters a lot in production. High-cardinality metrics can become expensive
and slow.

Good labels:

```text
route="/v1/chat"
status_code="200"
tool_name="search_faq"
policy_decision="likely_not_eligible"
environment="local"
```

Bad labels:

```text
session_id="abc123"
email="rohit@example.com"
message="Where is my order?"
order_id="..."
```

Why bad? They create too many unique time series and may expose private data.

Rule for AbhiMart:

> Never put raw user input, full emails, session IDs, order IDs, or retrieved
> text into metric labels.

### Do We Need Metrics Now?

Not urgently.

We already have:

- deterministic evals for behavior quality
- LangSmith for agent/LLM debugging
- Jaeger traces for request flow
- structured logs for important events and outcomes

Metrics are the next observability layer, but the first implementation should be
small. For a portfolio project, it is enough to show that we understand what
metrics we would add and why. If we implement them, we should add only a few
high-value counters/histograms first.

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
OTEL_EXPORTER=console
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

## Local Jaeger UI

Install the OTLP exporter dependency from the backend directory:

```bash
cd backend
uv add opentelemetry-exporter-otlp-proto-grpc
```

Start Jaeger from the repo root:

```bash
docker compose -f infra/docker-compose.yml up -d jaeger
```

Configure `.env` for Jaeger:

```env
OTEL_ENABLED=true
OTEL_EXPORTER=otlp
OTEL_OTLP_ENDPOINT=http://localhost:4317
OTEL_OTLP_INSECURE=true
OTEL_SERVICE_NAME=abhimart-backend
OTEL_ENVIRONMENT=local
```

Start the backend:

```bash
cd backend
uv run uvicorn app.main:app --reload
```

Send a chat request:

```bash
curl -N -X POST http://127.0.0.1:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What warranty do laptops come with?","session_id":"jaeger-test-1"}'
```

Open Jaeger:

```text
http://localhost:16686
```

Search for service:

```text
abhimart-backend
```

Expected trace shape:

```text
POST /v1/chat
  chat.agent_stream
    agent.llm_node
    rag.retrieve
    agent.llm_node
```

Jaeger is local and uses transient in-memory storage here. If the container is
restarted, old traces disappear. That is fine for local development.

## Local Metrics Endpoint

Install the Prometheus exporter dependency from the backend directory:

```bash
cd backend
uv add opentelemetry-exporter-prometheus prometheus-client
```

Enable metrics in `.env`:

```env
OTEL_METRICS_ENABLED=true
OTEL_METRICS_EXPORTER=prometheus
```

Start the backend:

```bash
uv run uvicorn app.main:app --reload
```

Send a chat request:

```bash
curl -N -X POST http://127.0.0.1:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What warranty do laptops come with?","session_id":"metrics-test-1"}'
```

Open metrics:

```text
http://127.0.0.1:8000/metrics
```

Search for:

```text
abhimart_
```

Expected examples:

```text
abhimart_chat_requests_total
abhimart_tool_calls_total
abhimart_rag_retrievals_total
abhimart_chat_stream_duration_ms
```

This is not a full Prometheus/Grafana setup yet. It proves the app emits
Prometheus-compatible metrics. A future step can add Prometheus and Grafana
containers to scrape and visualize this endpoint over time.

## Questions To Ask Before Adding Observability

When adding observability to any project, ask:

- What production failures would be painful to debug?
- What request path matters most?
- Which operations are slow, expensive, or risky?
- What metadata would help us filter the problem later?
- Are we collecting enough information to debug without exposing sensitive data?
- Which data belongs in LangSmith, and which belongs in OpenTelemetry?
- Which questions need traces, which need logs, and which need metrics?
- Which metric labels could accidentally create high cardinality?
- Which fields might expose customer data if logged or used as labels?

For AbhiMart, sensitive values such as full customer emails, full chat content,
or private order details should be handled carefully. Observability should help
debug the system without becoming a privacy leak.

## Official Resources

- [OpenTelemetry: What is OpenTelemetry?](https://opentelemetry.io/docs/what-is-opentelemetry/)
- [OpenTelemetry observability primer](https://opentelemetry.io/docs/concepts/observability-primer/)
- [OpenTelemetry docs](https://opentelemetry.io/docs/)
- [OpenTelemetry Python exporters](https://opentelemetry.io/docs/languages/python/exporters/)
- [Jaeger getting started](https://www.jaegertracing.io/docs/latest/getting-started/)
- [OpenTelemetry metrics API](https://opentelemetry.io/docs/specs/otel/metrics/api/)
- [Prometheus overview](https://prometheus.io/docs/introduction/overview/)
- [Grafana visualizations](https://grafana.com/docs/grafana/latest/visualizations/)
