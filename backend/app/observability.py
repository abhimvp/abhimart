"""OpenTelemetry setup for AbhiMart.

This first pass intentionally exports spans to the console. That lets us learn
the trace shape locally before adding Jaeger, Grafana Tempo, or a hosted vendor.
"""

import structlog
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from app.config import Settings

logger = structlog.get_logger()
_configured = False


def setup_observability(app: FastAPI, settings: Settings) -> None:
    """Configure OpenTelemetry instrumentation for the FastAPI app."""
    global _configured

    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry disabled")
        return

    if _configured:
        return

    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "service.version": settings.APP_VERSION,
            "deployment.environment": settings.OTEL_ENVIRONMENT,
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(
        app,
        tracer_provider=provider,
        # SSE streams produce many low-value ASGI send/receive spans. Keep the
        # main request span and AbhiMart business spans readable in local output.
        exclude_spans=["receive", "send"],
    )

    _configured = True
    logger.info(
        "OpenTelemetry enabled",
        service_name=settings.OTEL_SERVICE_NAME,
        environment=settings.OTEL_ENVIRONMENT,
    )


def get_tracer(name: str):
    """Return a tracer with a stable project namespace."""
    return trace.get_tracer(name)
