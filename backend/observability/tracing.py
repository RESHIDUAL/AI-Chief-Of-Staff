"""OpenTelemetry LLM observability for agent calls and pipeline graph nodes."""

import time
import logging
import os
from contextlib import contextmanager
from functools import wraps

logger = logging.getLogger(__name__)

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter, BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from backend.config.settings import settings

    provider = TracerProvider(resource=Resource.create({"service.name": settings.OTEL_SERVICE_NAME}))
    exporter = (
        OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
        if settings.OTEL_EXPORTER_OTLP_ENDPOINT
        else ConsoleSpanExporter()
    )
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("ai-chief-of-staff")
    OTEL_AVAILABLE = True
    logger.info("OpenTelemetry tracing initialized.")
except ImportError:
    OTEL_AVAILABLE = False
    tracer = None
    logger.info("OpenTelemetry not installed. Tracing disabled (metrics logged to console).")


@contextmanager
def agent_span(agent_name: str, operation: str, attributes: dict | None = None):
    """Context manager for tracing agent calls with OpenTelemetry or console fallback."""
    start = time.perf_counter()
    attrs = attributes or {}
    
    if OTEL_AVAILABLE and tracer:
        with tracer.start_as_current_span(f"{agent_name}.{operation}") as span:
            for k, v in attrs.items():
                span.set_attribute(k, str(v))
            try:
                yield span
            finally:
                latency = time.perf_counter() - start
                span.set_attribute("latency_seconds", round(latency, 3))
    else:
        try:
            yield None
        finally:
            latency = time.perf_counter() - start
            logger.info(
                f"[TRACE] {agent_name}.{operation} | latency={latency:.3f}s | {attrs}"
            )


def traced_node(node_name: str):
    """Decorator to wrap LangGraph nodes with OTel spans."""
    def decorator(func):
        @wraps(func)
        def wrapper(state, *args, **kwargs):
            attrs = {"meeting_id": state.get("meeting_id", "unknown"), "node": node_name}
            with agent_span("pipeline_graph", node_name, attrs):
                return func(state, *args, **kwargs)
        return wrapper
    return decorator
