"""
Optional proxy integration for the Composio Rube MCP server.

The connector remains disabled until operators opt in via environment
variable or configuration. It performs light validation and surfaces
clear errors instead of attempting network calls in offline mode.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class RubeProxyIntegration:
    """Lightweight adapter that proxies requests to the hosted Rube MCP endpoint."""

    DEFAULT_ENDPOINT = "https://rube.app/mcp"
    DEFAULT_ENV_TOGGLE = "SC_MCP_RUBE_ENABLED"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.endpoint = self.config.get("endpoint", self.DEFAULT_ENDPOINT)
        self.env_toggle = self.config.get("env_toggle", self.DEFAULT_ENV_TOGGLE)
        self.requires_network = bool(self.config.get("requires_network", True))
        self.oauth_token = self.config.get("oauth_token")  # placeholder for future secure storage
        self._session_ready = False
        self._enabled = self._read_opt_in()

    @property
    def enabled(self) -> bool:
        """Return whether the connector is enabled."""
        return self._enabled

    def _read_opt_in(self) -> bool:
        """Determine whether the integration has been explicitly enabled."""
        env_value = os.getenv(self.env_toggle)
        if env_value is not None:
            return env_value.strip().lower() in {"1", "true", "yes", "on"}

        enabled_flag = self.config.get("enabled")
        if enabled_flag is None:
            return False

        if isinstance(enabled_flag, bool):
            return enabled_flag

        if isinstance(enabled_flag, str):
            return enabled_flag.strip().lower() in {"1", "true", "yes", "on"}

        return bool(enabled_flag)

    def initialize(self) -> bool:
        """
        Perform synchronous initialization.

        Raises:
            RuntimeError: if the integration is not enabled.
        """
        if not self._enabled:
            raise RuntimeError(
                "Rube MCP connector is disabled. Set "
                f"{self.env_toggle}=true to opt in."
            )

        logger.info("Initializing Rube MCP proxy (endpoint=%s)", self.endpoint)
        return True

    async def initialize_session(self) -> bool:
        """
        Perform asynchronous session setup.

        Returns:
            bool indicating whether the session is ready.

        Raises:
            RuntimeError: if the integration is not enabled.
        """
        if not self._enabled:
            raise RuntimeError(
                "Cannot start Rube MCP session while connector is disabled."
            )

        if self.requires_network and not self._can_attempt_network():
            raise RuntimeError(
                "Rube MCP requires network connectivity. Enable online mode "
                "and ensure outbound traffic to rube.app is permitted."
            )

        # For Option A we keep the session lightweight and defer actual network calls.
        await asyncio.sleep(0)
        self._session_ready = True
        return True

    async def invoke(self, tool: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Proxy a tool invocation.

        Raises:
            RuntimeError: for disabled integrations or missing network support.
        """
        if not self._enabled:
            raise RuntimeError("Rube MCP connector is disabled.")

        if not self._session_ready:
            raise RuntimeError("Rube MCP session not initialized. Call initialize_session first.")

        if self.requires_network and not self._can_attempt_network():
            raise RuntimeError(
                "Network access is required for Rube MCP operations. "
                "Ensure online mode is enabled and credentials are configured."
            )

        # Placeholder until the full MCP client handshake is implemented.
        raise RuntimeError(
            "Rube MCP proxy is configured but network forwarding is not yet implemented. "
            "Connect to the Composio SDK or CLI in a future phase."
        )

    def _can_attempt_network(self) -> bool:
        """Best-effort check for network opt-in flag."""
        network_flag = os.getenv("SC_NETWORK_MODE", "offline").lower()
        return network_flag in {"online", "rube", "mixed"}
