"""Logging configuration for the PR Review Agent."""

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any

from opentelemetry import trace


class JsonFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging output."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON.

        Args:
            record: The log record to format

        Returns:
            JSON-formatted string
        """
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add trace context if available
        span = trace.get_current_span()
        if span and span.is_recording():
            ctx = span.get_span_context()
            log_entry["trace_id"] = format(ctx.trace_id, "032x")
            log_entry["span_id"] = format(ctx.span_id, "016x")

        # Add context if provided via extra parameter
        context = getattr(record, "context", None)
        if context:
            log_entry["context"] = context

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def setup_logging() -> None:
    """Configure logging for the application.

    Reads LOG_LEVEL from environment variable (default: DEBUG).
    Configures JSON structured output to stderr.

    This function should be called once at application startup,
    before any logging occurs.
    """
    log_level_str = os.getenv("LOG_LEVEL", "DEBUG").upper()
    log_level = getattr(logging, log_level_str, logging.DEBUG)

    # Create root logger for pr_agent package
    root_logger = logging.getLogger("pr_agent")
    root_logger.setLevel(log_level)

    # Remove any existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Create stderr handler with JSON formatter
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(log_level)
    handler.setFormatter(JsonFormatter())

    root_logger.addHandler(handler)
