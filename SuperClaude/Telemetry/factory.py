"""
Telemetry factory for SuperClaude Framework.

Creates telemetry clients based on configuration and environment.
"""

import logging
import os
from pathlib import Path

from .jsonl import JsonlTelemetryClient
from .noop import NoopTelemetryClient

logger = logging.getLogger(__name__)

# Type alias for telemetry clients
TelemetryClientType = JsonlTelemetryClient | NoopTelemetryClient


def create_telemetry(
    metrics_dir: str | Path | None = None,
    enabled: bool | None = None,
    session_id: str | None = None,
    buffer_size: int = 10,
) -> TelemetryClientType:
    """
    Create a telemetry client based on configuration.

    Args:
        metrics_dir: Directory for metrics files (default from env or .superclaude_metrics/)
        enabled: Whether telemetry is enabled (default from env SUPERCLAUDE_TELEMETRY_ENABLED)
        session_id: Unique session identifier
        buffer_size: Number of entries to buffer before flush

    Returns:
        TelemetryClient implementation (JsonlTelemetryClient or NoopTelemetryClient)

    Environment Variables:
        SUPERCLAUDE_METRICS_DIR: Default metrics directory
        SUPERCLAUDE_TELEMETRY_ENABLED: '0' or 'false' to disable telemetry
    """
    # Check if telemetry is disabled
    if enabled is None:
        env_enabled = os.environ.get("SUPERCLAUDE_TELEMETRY_ENABLED", "1").lower()
        enabled = env_enabled not in ("0", "false", "no", "off")

    if not enabled:
        logger.debug("Telemetry disabled, using NoopTelemetryClient")
        return NoopTelemetryClient()

    # Resolve metrics directory
    if metrics_dir is None:
        metrics_dir = os.environ.get("SUPERCLAUDE_METRICS_DIR")

    try:
        client = JsonlTelemetryClient(
            metrics_dir=metrics_dir,
            session_id=session_id,
            buffer_size=buffer_size,
        )
        logger.debug(f"Created JsonlTelemetryClient at {client.metrics_dir}")
        return client
    except Exception as e:
        logger.warning(f"Failed to create JsonlTelemetryClient: {e}, using NoopTelemetryClient")
        return NoopTelemetryClient()
