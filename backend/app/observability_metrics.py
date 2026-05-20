"""Privacy-safe OpenTelemetry metric helpers for AbhiMart."""

from functools import lru_cache

from app.observability import get_meter


@lru_cache
def _meter():
    return get_meter("abhimart.backend")


@lru_cache
def _chat_requests_total():
    return _meter().create_counter(
        "abhimart_chat_requests_total",
        description="Total number of chat requests accepted by the API.",
    )


@lru_cache
def _chat_stream_duration_ms():
    return _meter().create_histogram(
        "abhimart_chat_stream_duration_ms",
        unit="ms",
        description="Duration of the streamed chat agent response.",
    )


@lru_cache
def _errors_total():
    return _meter().create_counter(
        "abhimart_errors_total",
        description="Total number of observed application errors.",
    )


@lru_cache
def _tool_calls_total():
    return _meter().create_counter(
        "abhimart_tool_calls_total",
        description="Total number of customer-support tool calls.",
    )


@lru_cache
def _tool_duration_ms():
    return _meter().create_histogram(
        "abhimart_tool_duration_ms",
        unit="ms",
        description="Duration of customer-support tool calls.",
    )


@lru_cache
def _rag_retrievals_total():
    return _meter().create_counter(
        "abhimart_rag_retrievals_total",
        description="Total number of RAG retrieval operations.",
    )


@lru_cache
def _rag_retrieval_duration_ms():
    return _meter().create_histogram(
        "abhimart_rag_retrieval_duration_ms",
        unit="ms",
        description="Duration of RAG retrieval operations.",
    )


@lru_cache
def _policy_decisions_total():
    return _meter().create_counter(
        "abhimart_policy_decisions_total",
        description="Total number of structured policy decisions.",
    )


def record_chat_request() -> None:
    _chat_requests_total().add(1, {"route": "/v1/chat"})


def record_chat_stream(duration_ms: float, *, status: str) -> None:
    _chat_stream_duration_ms().record(
        duration_ms,
        {"route": "/v1/chat", "status": status},
    )


def record_error(*, area: str) -> None:
    _errors_total().add(1, {"area": area})


def record_tool_call(tool_name: str) -> None:
    _tool_calls_total().add(1, {"tool_name": tool_name})


def record_tool_duration(tool_name: str, duration_ms: float, *, status: str) -> None:
    _tool_duration_ms().record(
        duration_ms,
        {"tool_name": tool_name, "status": status},
    )


def record_rag_retrieval(duration_ms: float, *, status: str) -> None:
    _rag_retrievals_total().add(1, {"status": status})
    _rag_retrieval_duration_ms().record(duration_ms, {"status": status})


def record_policy_decision(decision: str) -> None:
    _policy_decisions_total().add(1, {"decision": decision})
