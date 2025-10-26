"""
Rube MCP Integration

Provides an asynchronous client wrapper that can talk to the hosted Rube MCP
endpoint when network access is permitted, while supporting a dry-run mode for
offline execution.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any, Awaitable, Callable, Dict, Optional

logger = logging.getLogger(__name__)

try:  # Optional dependency for real HTTP calls
    import httpx  # type: ignore
except ImportError:  # pragma: no cover - httpx may not be installed
    httpx = None  # type: ignore


AsyncSender = Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]


class RubeIntegration:
    """
    Integration that talks to the Rube MCP server via HTTP.

    Behaviour:
        - Enabled by configuration (defaults to True).
        - Requires outbound network access unless running in dry-run mode.
        - Reads OAuth token from config or environment variable `SC_RUBE_API_KEY`.
        - Respects `SC_RUBE_MODE=dry-run` or offline network mode to avoid real calls.
    """

    DEFAULT_ENDPOINT = "https://rube.app/mcp"
    NETWORK_OK_VALUES = {"online", "mixed", "rube", "auto"}
    DRY_RUN_VALUES = {"dry-run", "dryrun", "1", "true", "yes", "enabled"}

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        http_sender: Optional[AsyncSender] = None,
    ):
        self.config = config or {}
        self.endpoint = self.config.get("endpoint", self.DEFAULT_ENDPOINT)
        self.requires_network = bool(self.config.get("requires_network", True))
        self.timeout_seconds = float(self.config.get("timeout_seconds", 60))
        self.api_key = self.config.get("api_key") or os.getenv("SC_RUBE_API_KEY")
        self.scopes = self.config.get("scopes", [])
        self._enabled = bool(self.config.get("enabled", True))
        self._initialized = False
        self._session_ready = False
        self._dry_run = False
        self._http_sender = http_sender
        self._client: Optional["httpx.AsyncClient"] = None  # type: ignore[name-defined]

    @property
    def enabled(self) -> bool:
        """Return whether the integration is enabled."""
        return self._enabled

    def initialize(self) -> bool:
        """Perform synchronous initialization."""
        if not self.enabled:
            raise RuntimeError("Rube MCP integration is disabled in configuration.")

        self._initialized = True
        logger.info("Initialized Rube MCP integration (endpoint=%s)", self.endpoint)
        return True

    async def initialize_session(self) -> bool:
        """Prepare asynchronous resources and determine dry-run mode."""
        if not self._initialized:
            raise RuntimeError("Call initialize() before initialize_session().")

        self._dry_run = self._should_dry_run()

        if not self._dry_run and self.requires_network and not self._http_sender and httpx is None:
            raise RuntimeError(
                "httpx is required for live Rube MCP requests. "
                "Install httpx or set SC_RUBE_MODE=dry-run."
            )

        if not self._dry_run and self.requires_network and not self.api_key:
            raise RuntimeError(
                "SC_RUBE_API_KEY must be set to use Rube MCP in live mode. "
                "Set SC_RUBE_MODE=dry-run to simulate responses."
            )

        if not self._dry_run and self._http_sender is None and httpx is not None:
            headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            self._client = httpx.AsyncClient(  # type: ignore[name-defined]
                base_url=self.endpoint,
                timeout=self.timeout_seconds,
                headers=headers or None,
            )

        self._session_ready = True
        logger.debug(
            "Rube MCP session ready (dry_run=%s, network_required=%s).",
            self._dry_run,
            self.requires_network,
        )
        return True

    async def close(self) -> None:
        """Close any underlying resources."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def invoke(self, tool: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Invoke a tool via Rube MCP.

        Args:
            tool: The tool identifier to execute.
            payload: Parameters for the tool.
        """
        if not self._session_ready:
            raise RuntimeError("Rube MCP session not initialized. Call initialize_session() first.")

        request_body = {
            "tool": tool,
            "payload": payload,
            "scopes": self.scopes,
        }

        if self._dry_run:
            logger.info("Rube MCP dry-run: %s", json.dumps(request_body, default=str))
            return {
                "status": "dry-run",
                "tool": tool,
                "payload": payload,
                "message": "Dry-run mode: no external request was sent.",
            }

        sender = self._http_sender or self._send_via_httpx

        try:
            response = await sender(self.endpoint, request_body)
        except Exception as exc:  # pragma: no cover - network errors depend on environment
            logger.error("Rube MCP request failed: %s", exc)
            raise RuntimeError(f"Rube MCP request failed: {exc}") from exc

        if not isinstance(response, dict):
            raise RuntimeError("Unexpected Rube MCP response format.")

        return response

    async def _send_via_httpx(self, url: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Send a request using httpx (live mode)."""
        if self._client is None:
            raise RuntimeError("HTTP client not initialized for Rube MCP.")

        response = await self._client.post("", json=body)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict):
            raise RuntimeError("Rube MCP returned non-object JSON.")
        return data

    def _should_dry_run(self) -> bool:
        """Determine if the integration should operate in dry-run mode."""
        explicit = os.getenv("SC_RUBE_MODE", "").strip().lower()
        if explicit in self.DRY_RUN_VALUES:
            return True

        network_mode = os.getenv("SC_NETWORK_MODE", "offline").strip().lower()
        if self.requires_network and network_mode not in self.NETWORK_OK_VALUES:
            return True

        # Fallback to dry-run when no HTTP transport is available
        if self.requires_network and self._http_sender is None and httpx is None:
            return True

        return False
