from enum import Enum
from functools import wraps
from typing import Any, TypeAlias

from fastapi import FastAPI
from loguru import logger

from app.core.config import settings

SpanAttributeValue: TypeAlias = str | int | float | bool

_is_observability_initialized = False


class TelemetryAttributeKey(str, Enum):
    TENANT_ID = "tenant.id"
    USER_ID = "user.id"


def setup_observability(app: FastAPI) -> None:
    if not settings.OTEL_ENABLED:
        logger.info("OpenTelemetry is disabled for api_server.")
        return

    global _is_observability_initialized
    if _is_observability_initialized:
        return

    try:
        provider = _build_tracer_provider()
        _set_tracer_provider(provider)
        _instrument_libraries(app)
        _is_observability_initialized = True
        logger.info(
            "OpenTelemetry initialized: service_name={}, endpoint={}",
            settings.OTEL_SERVICE_NAME,
            settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        )
    except Exception:
        logger.exception(
            "Failed to initialize OpenTelemetry: service_name={}, endpoint={}",
            settings.OTEL_SERVICE_NAME,
            settings.OTEL_EXPORTER_OTLP_ENDPOINT,
        )


def set_span_attributes(
    attributes: dict[TelemetryAttributeKey, SpanAttributeValue | None],
) -> None:
    try:
        from opentelemetry import trace

        span = trace.get_current_span()
        for key, value in attributes.items():
            if value is not None:
                span.set_attribute(key.value, value)
    except Exception:
        logger.exception("Failed to set OpenTelemetry span attributes.")


def trace_async_span(span_name):
    # Build a decorator with the span name that should appear in Tempo/Grafana.
    def decorator(func):
        # Preserve the original function name and metadata for FastAPI and debugging.
        @wraps(func)
        async def wrapper(*args, **kwargs):
            from opentelemetry import trace

            # Use the decorated function's module as the tracer name.
            tracer = trace.get_tracer(func.__module__)

            # Measure everything that happens while the original async function runs.
            with tracer.start_as_current_span(str(span_name)):
                return await func(*args, **kwargs)

        # Replace the original function with the traced wrapper.
        return wrapper

    # Return the decorator so it can be used as @trace_async_span("span.name").
    return decorator


def _build_tracer_provider() -> Any:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create(
        {
            "service.name": settings.OTEL_SERVICE_NAME,
            "service.namespace": settings.OTEL_SERVICE_NAMESPACE,
            "deployment.environment": settings.APP_ENV,
        }
    )
    provider = TracerProvider(
        resource=resource,
        sampler=_build_sampler(),
    )
    provider.add_span_processor(
        BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                insecure=settings.OTEL_EXPORTER_OTLP_INSECURE,
            )
        )
    )
    return provider


def _build_sampler() -> Any:
    from opentelemetry.sdk.trace.sampling import (
        ALWAYS_OFF,
        ALWAYS_ON,
        ParentBased,
        TraceIdRatioBased,
    )

    sampler_name = settings.OTEL_TRACES_SAMPLER.lower()
    if sampler_name == "always_on":
        return ALWAYS_ON
    if sampler_name == "always_off":
        return ALWAYS_OFF
    if sampler_name == "parentbased_traceidratio":
        return ParentBased(TraceIdRatioBased(settings.OTEL_TRACES_SAMPLER_ARG))
    if sampler_name == "traceidratio":
        return TraceIdRatioBased(settings.OTEL_TRACES_SAMPLER_ARG)

    logger.error(
        "Unsupported OpenTelemetry sampler configured: sampler={}. Falling back to parentbased_traceidratio.",
        settings.OTEL_TRACES_SAMPLER,
    )
    return ParentBased(TraceIdRatioBased(settings.OTEL_TRACES_SAMPLER_ARG))


def _set_tracer_provider(provider: Any) -> None:
    from opentelemetry import trace

    trace.set_tracer_provider(provider)


def _instrument_libraries(app: FastAPI) -> None:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.instrumentation.requests import RequestsInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

    FastAPIInstrumentor.instrument_app(app)
    HTTPXClientInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    LoggingInstrumentor().instrument(set_logging_format=False)

    try:
        from app.models.engines import engine

        SQLAlchemyInstrumentor().instrument(engine=engine)
    except Exception:
        logger.exception("Failed to instrument SQLAlchemy engine.")
