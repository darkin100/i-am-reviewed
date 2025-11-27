"""Tracing configuration for the PR Review Agent using OpenTelemetry and Cloud Trace."""

from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Optional

from opentelemetry import trace
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from agent.logging_config import get_logger

logger = get_logger(__name__)


def setup_tracing(
    project_id: str,
    service_name: str = "pr-review-agent",
    enable_cloud_trace: bool = True
) -> trace.Tracer:
    """Initialize OpenTelemetry tracing with Cloud Trace exporter.

    Args:
        project_id: Google Cloud project ID
        service_name: Service name for trace identification
        enable_cloud_trace: If False, uses console exporter (for local debugging)

    Returns:
        Configured tracer instance
    """
    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    if enable_cloud_trace:
        # Cloud Trace exporter for GCP
        cloud_exporter = CloudTraceSpanExporter(project_id=project_id)
        provider.add_span_processor(BatchSpanProcessor(cloud_exporter))
        logger.info(
            "Cloud Trace tracing enabled",
            extra={"context": {"project_id": project_id, "service_name": service_name}}
        )
    else:
        # Console exporter for local debugging
        provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
        logger.info(
            "Console tracing enabled (Cloud Trace disabled)",
            extra={"context": {"service_name": service_name}}
        )

    trace.set_tracer_provider(provider)
    return trace.get_tracer(__name__)


def get_tracer() -> trace.Tracer:
    """Get the global tracer instance.

    Returns:
        The current tracer instance
    """
    return trace.get_tracer(__name__)


def traced(span_name: Optional[str] = None) -> Callable:
    """Decorator to add tracing to methods.

    Args:
        span_name: Optional custom span name. If not provided, uses
                   '{ClassName}.{method_name}' format.

    Returns:
        Decorated function with tracing enabled
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(self, *args: Any, **kwargs: Any) -> Any:
            tracer = trace.get_tracer(__name__)
            name = span_name or f"{self.__class__.__name__}.{func.__name__}"

            with tracer.start_as_current_span(name) as span:
                # Add platform attribute if available
                if hasattr(self, 'get_platform_name'):
                    span.set_attribute("platform", self.get_platform_name())

                try:
                    result = func(self, *args, **kwargs)
                    span.set_status(trace.StatusCode.OK)
                    return result
                except Exception as e:
                    span.set_status(trace.StatusCode.ERROR, str(e))
                    span.record_exception(e)
                    raise
        return wrapper
    return decorator


@contextmanager
def custom_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Context manager for creating custom spans anywhere in the code.

    Usage:
        with custom_span("my_operation", {"key": "value"}):
            # do work

    Args:
        name: The span name
        attributes: Optional dictionary of span attributes

    Yields:
        The created span
    """
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(name) as span:
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, value)
        try:
            yield span
        except Exception as e:
            span.set_status(trace.StatusCode.ERROR, str(e))
            span.record_exception(e)
            raise
