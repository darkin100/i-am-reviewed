"""Shared configuration for PR Review Agent.

This module provides configuration utilities shared between CLI and ADK web modes.
"""

import os
import tempfile
from typing import Optional

from dotenv import load_dotenv

from pr_agent.logging_config import get_logger

logger = get_logger(__name__)


def setup_environment(load_env_file: bool = True) -> None:
    """Set up environment for the agent.

    Configures ADK telemetry and Vertex AI settings.

    Args:
        load_env_file: Whether to load .env file (True for local, False for CI)
    """
    if load_env_file:
        load_dotenv()

    # Set ADK telemetry defaults
    os.environ.setdefault("GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY", "true")
    os.environ.setdefault("OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT", "true")
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")


def setup_google_cloud_auth() -> None:
    """Set up Google Cloud authentication from environment.

    Handles GOOGLE_CLOUD_CREDENTIALS for CI/CD environments by writing
    the JSON credentials to a temporary file and setting
    GOOGLE_APPLICATION_CREDENTIALS.

    For local development, this function does nothing and relies on
    default application credentials (gcloud auth application-default login).
    """
    credentials_json = os.getenv("GOOGLE_CLOUD_CREDENTIALS")
    if not credentials_json:
        logger.warning("No GOOGLE_CLOUD_CREDENTIALS found, using default credentials")
        return

    try:
        fd, credentials_path = tempfile.mkstemp(suffix=".json", text=True)
        with os.fdopen(fd, "w") as f:
            f.write(credentials_json)
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        logger.info(
            "Google Cloud credentials configured",
            extra={"context": {"credentials_path": credentials_path}},
        )
    except Exception:
        logger.error("Error setting up credentials", exc_info=True)
        raise


def get_required_env(name: str, default: Optional[str] = None) -> str:
    """Get required environment variable or raise error.

    Args:
        name: Environment variable name
        default: Default value if not set

    Returns:
        The environment variable value

    Raises:
        ValueError: If variable is not set and no default provided
    """
    value = os.getenv(name, default)
    if value is None:
        raise ValueError(f"Required environment variable {name} is not set")
    return value
