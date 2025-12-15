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
import time
from typing import Any, Awaitable, Callable, Dict

logger = logging.getLogger(__name__)

try:  # Optional dependency for real HTTP calls
    import httpx  # type: ignore
except ImportError:  # pragma: no cover - httpx may not be installed
    httpx = None  # type: ignore


AsyncSender = Callable[[str, Dict[str, Any]], Awaitable[Dict[str, Any]]]

# LinkUp defaults
DEFAULT_LINKUP_DEPTH = "deep"
DEFAULT_LINKUP_OUTPUT_TYPE = "sourcedAnswer"
DEFAULT_LINKUP_TOOL = "LINKUP_SEARCH"


class RubeInvocationError(RuntimeError):
    """Structured error raised when a live Rube MCP invocation fails."""

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        code: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.status = status
        self.code = code
        self.details = details or {}


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
        config: dict[str, Any] | None = None,
        http_sender: AsyncSender | None = None,
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
        self._client: httpx.AsyncClient | None = None  # type: ignore[name-defined]
        self.telemetry_enabled = bool(self.config.get("telemetry_enabled", True))
        self.telemetry_label = self.config.get("telemetry_label", "rube_mcp")
        # LinkUp config
        linkup_cfg = self.config.get("linkup", {})
        self._linkup_depth = linkup_cfg.get("default_depth", DEFAULT_LINKUP_DEPTH)
        self._linkup_output_type = linkup_cfg.get(
            "default_output_type", DEFAULT_LINKUP_OUTPUT_TYPE
        )
        self._linkup_max_concurrent = max(1, int(linkup_cfg.get("max_concurrent", 4)))

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

        if (
            not self._dry_run
            and self.requires_network
            and not self._http_sender
            and httpx is None
        ):
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
            headers = (
                {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
            )
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

    async def invoke(self, tool: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Invoke a tool via Rube MCP.

        Args:
            tool: The tool identifier to execute.
            payload: Parameters for the tool.
        """
        if not self._session_ready:
            raise RuntimeError(
                "Rube MCP session not initialized. Call initialize_session() first."
            )

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
        return await self._invoke_with_retries(sender, request_body, tool)

    # -------------------------------------------------------------------------
    # LinkUp convenience methods
    # -------------------------------------------------------------------------

    async def linkup_search(
        self,
        query: str,
        depth: str | None = None,
        output_type: str | None = None,
    ) -> dict[str, Any]:
        """Execute a single LinkUp web search.

        Args:
            query: The search query string.
            depth: Search depth ("deep" or "standard"). Defaults to config.
            output_type: Output format ("sourcedAnswer", "searchResults"). Defaults to config.

        Returns:
            Dict with search results including citations and sources.
        """
        if not query or not query.strip():
            raise ValueError("LinkUp query cannot be empty")

        payload = {
            "query": query.strip(),
            "depth": depth or self._linkup_depth,
            "output_type": output_type or self._linkup_output_type,
        }
        return await self.invoke(DEFAULT_LINKUP_TOOL, payload)

    async def linkup_batch_search(
        self,
        queries: list[str],
        max_concurrent: int | None = None,
    ) -> list[dict[str, Any]]:
        """Execute multiple LinkUp searches with concurrency control.

        Args:
            queries: List of search query strings.
            max_concurrent: Max parallel requests. Defaults to config (4).

        Returns:
            List of result dicts, one per query. Failed queries return
            {"status": "failed", "error": "..."}.
        """
        if not queries:
            return []

        concurrency = max_concurrent or self._linkup_max_concurrent
        semaphore = asyncio.Semaphore(concurrency)

        async def _run(q: str) -> dict[str, Any]:
            async with semaphore:
                try:
                    return await self.linkup_search(q)
                except RubeInvocationError as exc:
                    return {"status": "failed", "error": str(exc), "query": q}
                except ValueError as exc:
                    return {"status": "failed", "error": str(exc), "query": q}

        results = await asyncio.gather(
            *(_run(q) for q in queries), return_exceptions=False
        )
        return list(results)

    async def _send_via_httpx(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
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

    async def _invoke_with_retries(
        self,
        sender: AsyncSender,
        request_body: dict[str, Any],
        tool: str,
    ) -> dict[str, Any]:
        """Invoke sender with single retry on transient errors."""
        for attempt in (1, 2):  # Max 2 attempts (1 retry)
            start = time.perf_counter()
            try:
                response = await sender(self.endpoint, request_body)
                duration = time.perf_counter() - start
                if not isinstance(response, dict):
                    raise RuntimeError("Unexpected Rube MCP response format.")
                self._record_telemetry("success", tool, request_body, attempt, duration)
                return response
            except Exception as exc:
                duration = time.perf_counter() - start
                retryable = self._is_retryable(exc)

                if attempt == 2 or not retryable:
                    self._record_telemetry(
                        "failure", tool, request_body, attempt, duration, error=exc
                    )
                    error_details = self._format_error(exc)
                    error_details.update(
                        {"tool": tool, "attempts": attempt, "endpoint": self.endpoint}
                    )
                    raise RubeInvocationError(
                        f"Rube MCP request failed after {attempt} attempt(s)",
                        status=error_details.get("status"),
                        code=error_details.get("code"),
                        details=error_details,
                    ) from exc

                # Single retry with fixed 1s delay
                logger.debug("Rube MCP transient error, retrying in 1s: %s", exc)
                await asyncio.sleep(1.0)

        raise RubeInvocationError("Unexpected retry exhaustion")

    def _is_retryable(self, exc: Exception) -> bool:
        """Determine if an exception is retryable."""
        transient_types = (asyncio.TimeoutError,)
        if httpx is not None:
            transient_types = transient_types + (
                httpx.TransportError,  # type: ignore[attr-defined]
                httpx.TimeoutException,  # type: ignore[attr-defined]
            )

        if isinstance(exc, transient_types):
            return True

        message = str(exc).lower()
        transient_tokens = (
            "timeout",
            "temporarily",
            "again later",
            "rate limit",
            "429",
        )
        return any(token in message for token in transient_tokens)

    def _record_telemetry(
        self,
        outcome: str,
        tool: str,
        request_body: dict[str, Any],
        attempt: int,
        duration: float,
        *,
        error: Exception | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        """Emit structured telemetry for each invocation outcome."""
        if not self.telemetry_enabled:
            return

        payload_keys = sorted(request_body.get("payload", {}).keys())
        event = {
            "label": self.telemetry_label,
            "event": "rube_mcp.invoke",
            "tool": tool,
            "outcome": outcome,
            "attempt": attempt,
            "duration_ms": round(duration * 1000, 3),
            "endpoint": self.endpoint,
            "dry_run": self._dry_run,
            "payload_keys": payload_keys,
            "scopes": list(self.scopes),
        }

        if extra:
            event.update(extra)

        if error:
            event["error"] = self._summarize_error(error)

        log_line = "[RubeMCP] %s"
        log_payload = json.dumps(event, default=str)
        if outcome == "success":
            logger.info(log_line, log_payload)
        elif outcome == "retry":
            logger.warning(log_line, log_payload)
        else:
            logger.error(log_line, log_payload)

    def _summarize_error(self, exc: Exception) -> dict[str, Any]:
        """Provide a compact summary of an exception for telemetry."""
        summary: dict[str, Any] = {
            "type": exc.__class__.__name__,
            "message": str(exc),
        }
        response = getattr(exc, "response", None)
        if response is not None:
            summary["status"] = getattr(response, "status_code", None)
        return summary

    def _format_error(self, exc: Exception) -> dict[str, Any]:
        """Produce a detailed, structured error payload."""
        details = self._summarize_error(exc)
        response = getattr(exc, "response", None)
        if response is not None:
            details["status"] = getattr(response, "status_code", None)
            details["code"] = getattr(response, "reason_phrase", None)
            try:
                details["response_body"] = response.json()
            except Exception:  # pragma: no cover - defensive
                text = response.text
                details["response_body"] = self._truncate(text)
            headers = {
                k: v for k, v in response.headers.items() if k.lower().startswith("x-")
            }
            if headers:
                details["response_headers"] = headers
            request = getattr(response, "request", None)
            if request is not None:
                details["method"] = getattr(request, "method", None)
                details["url"] = str(getattr(request, "url", "")) or None
        return details

    @staticmethod
    def _truncate(value: str, limit: int = 512) -> str:
        """Truncate long strings for error reporting."""
        if len(value) <= limit:
            return value
        return value[:limit] + "...<truncated>"
