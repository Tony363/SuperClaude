"""Codex-style completion client backed by OpenAI chat completions.

The fast Codex persona uses this helper to request structured change
suggestions when a real OpenAI key is available. When the environment is
offline or credentials are missing the helper raises ``CodexUnavailable`` so
callers can fall back to heuristic behaviour.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from .openai_client import OpenAIClient, CompletionRequest, CompletionResponse


class CodexUnavailable(RuntimeError):
    """Raised when no Codex backend is reachable."""


@dataclass
class CodexConfig:
    """Simple configuration container for Codex requests."""

    model: str = os.getenv("SUPERCLAUDE_CODEX_MODEL", "gpt-4o-mini")
    temperature: float = float(os.getenv("SUPERCLAUDE_CODEX_TEMPERATURE", "0.15"))
    max_tokens: int = int(os.getenv("SUPERCLAUDE_CODEX_MAX_TOKENS", "1024"))
    user: Optional[str] = os.getenv("SUPERCLAUDE_CODEX_USER")


class CodexClient:
    """Thin synchronous wrapper around :class:`OpenAIClient`."""

    def __init__(self, config: Optional[CodexConfig] = None) -> None:
        self.config = config or CodexConfig()
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("CODEX_API_KEY")
        if not api_key:
            raise CodexUnavailable("OPENAI_API_KEY or CODEX_API_KEY not configured")

        try:
            self._client = OpenAIClient(api_key=api_key)
        except ValueError as exc:  # OpenAIClient re-raises when key missing
            raise CodexUnavailable(str(exc)) from exc

    def complete_structured(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        """Execute a Codex request and parse JSON output.

        Parameters
        ----------
        system_prompt:
            Instructional system message.
        user_prompt:
            Task-specific message delivered as the user role.

        Returns
        -------
        dict
            Parsed JSON payload. Raises ``CodexUnavailable`` when the response
            cannot be decoded or when the call fails.
        """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        request = CompletionRequest(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            user=self.config.user,
        )

        try:
            response = _run_async(self._client.complete(request))
        except Exception as exc:  # pragma: no cover - network failure path
            raise CodexUnavailable(str(exc)) from exc

        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: CompletionResponse) -> Dict[str, Any]:
        """Parse the textual response into JSON."""

        content = response.content.strip()
        # Try raw JSON first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Frequently the model wraps JSON in code fences. Strip them.
        if content.startswith("```") and content.endswith("```"):
            fence_body = "\n".join(content.splitlines()[1:-1]).strip()
            try:
                return json.loads(fence_body)
            except json.JSONDecodeError:
                content = fence_body

        # Fall back to an empty payload so the caller can degrade gracefully.
        raise CodexUnavailable("Codex response was not valid JSON")


def _run_async(coro: asyncio.Future) -> CompletionResponse:
    """Run an async coroutine from synchronous code."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()

    return asyncio.run(coro)

