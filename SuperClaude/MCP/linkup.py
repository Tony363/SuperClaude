"""LinkUp helper built on top of the Rube MCP integration."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Union

from .rube_integration import RubeIntegration, RubeInvocationError

logger = logging.getLogger(__name__)


DEFAULT_DEPTH = "deep"
DEFAULT_OUTPUT_TYPE = "sourcedAnswer"
DEFAULT_TOOL = "LINKUP_SEARCH"


class LinkUpError(RuntimeError):
    """Raised when LinkUp operations fail."""


@dataclass
class LinkUpQuery:
    """Typed payload for issuing a LinkUp search."""

    query: str
    depth: Optional[str] = None
    output_type: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def build_payload(
        self,
        defaults: Dict[str, Any],
        *,
        default_depth: str,
        default_output_type: str,
    ) -> Dict[str, Any]:
        """Merge defaults with user provided overrides."""

        merged: Dict[str, Any] = {}
        merged.update(defaults)
        merged.update(self.payload)
        merged["query"] = self.query
        merged.setdefault("depth", self.depth or default_depth)
        merged.setdefault("output_type", self.output_type or default_output_type)
        return merged


class LinkUpClient:
    """Convenience wrapper that invokes LinkUp via an active Rube MCP session."""

    def __init__(
        self,
        rube: RubeIntegration,
        *,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        if rube is None:
            raise ValueError("LinkUpClient requires an active RubeIntegration instance")

        self._rube = rube
        self._config = config or {}
        self._defaults: Dict[str, Any] = dict(self._config.get("payload_defaults", {}))
        self._tool = self._config.get("tool", DEFAULT_TOOL)
        self._default_depth = self._config.get("default_depth", DEFAULT_DEPTH)
        self._default_output_type = self._config.get("default_output_type", DEFAULT_OUTPUT_TYPE)
        self._throttle_seconds = max(0.0, float(self._config.get("throttle_seconds", 0.0)))
        self._max_concurrent = max(1, int(self._config.get("max_concurrent", 4)))
        self._throttle_lock = asyncio.Lock()
        self._last_invocation: float = 0.0

    @property
    def tool(self) -> str:
        return self._tool

    async def search(
        self,
        query: Union[str, LinkUpQuery],
        **overrides: Any,
    ) -> Dict[str, Any]:
        """Execute a single LinkUp search request."""

        request = self._normalize_query(query, overrides)
        payload = request.build_payload(
            self._defaults,
            default_depth=self._default_depth,
            default_output_type=self._default_output_type,
        )

        await self._maybe_throttle()

        try:
            response = await self._rube.invoke(self._tool, payload)
        except RubeInvocationError as exc:
            logger.warning("LinkUp invocation failed: status=%s code=%s", exc.status, exc.code)
            raise LinkUpError(str(exc)) from exc
        except Exception as exc:  # pragma: no cover - unexpected runtime issues
            logger.error("Unexpected LinkUp failure: %s", exc)
            raise LinkUpError("LinkUp request failed") from exc

        if not isinstance(response, dict):
            raise LinkUpError("LinkUp returned non-dict response")

        return response

    async def batch_search(
        self,
        queries: Sequence[Union[str, LinkUpQuery]],
    ) -> List[Dict[str, Any]]:
        """Execute multiple LinkUp searches with concurrency control."""

        if not queries:
            return []

        semaphore = asyncio.Semaphore(self._max_concurrent)

        async def _run(item: Union[str, LinkUpQuery]) -> Dict[str, Any]:
            async with semaphore:
                return await self.search(item)

        results: List[Dict[str, Any]] = []
        responses = await asyncio.gather(
            *(_run(query) for query in queries),
            return_exceptions=True,
        )

        for response in responses:
            if isinstance(response, Exception):
                message = str(response)
                if isinstance(response, LinkUpError):
                    message = str(response)
                elif isinstance(response, RubeInvocationError):
                    message = response.details.get("message") or str(response)
                results.append({
                    "status": "failed",
                    "error": message,
                })
            else:
                results.append(response)

        return results

    def _normalize_query(
        self,
        query: Union[str, LinkUpQuery],
        overrides: Dict[str, Any],
    ) -> LinkUpQuery:
        if isinstance(query, LinkUpQuery):
            if overrides:
                merged_payload = dict(query.payload)
                merged_payload.update(overrides)
                return LinkUpQuery(
                    query=query.query,
                    depth=overrides.get("depth", query.depth),
                    output_type=overrides.get("output_type", query.output_type),
                    payload=merged_payload,
                )
            return query

        text = (query or "").strip()
        if not text:
            raise ValueError("LinkUp query cannot be empty")

        payload_overrides = dict(overrides)
        depth = payload_overrides.pop("depth", None)
        output_type = payload_overrides.pop("output_type", None)

        return LinkUpQuery(
            query=text,
            depth=depth,
            output_type=output_type,
            payload=payload_overrides,
        )

    async def _maybe_throttle(self) -> None:
        if self._throttle_seconds <= 0:
            return

        async with self._throttle_lock:
            now = time.monotonic()
            elapsed = now - self._last_invocation
            wait_time = self._throttle_seconds - elapsed
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                now = time.monotonic()
            self._last_invocation = now


__all__ = [
    "LinkUpClient",
    "LinkUpError",
    "LinkUpQuery",
]
