"""OpenTelemetry setup for AbhiMart.

The default exporter prints spans to the console. For visual local debugging,
set OTEL_EXPORTER=otlp and send traces to Jaeger on localhost:4317.
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


def _build_span_exporter(settings: Settings):
    """Build the configured span exporter."""
    exporter = settings.OTEL_EXPORTER.lower()

    if exporter == "console":
        return ConsoleSpanExporter()

    if exporter == "otlp":
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )

        return OTLPSpanExporter(
            endpoint=settings.OTEL_OTLP_ENDPOINT,
            insecure=settings.OTEL_OTLP_INSECURE,
        )

    raise ValueError(
        "Unsupported OTEL_EXPORTER. Expected 'console' or 'otlp', "
        f"got {settings.OTEL_EXPORTER!r}."
    )


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
    provider.add_span_processor(BatchSpanProcessor(_build_span_exporter(settings)))
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
        exporter=settings.OTEL_EXPORTER,
    )


def get_tracer(name: str):
    """Return a tracer with a stable project namespace."""
    return trace.get_tracer(name)
