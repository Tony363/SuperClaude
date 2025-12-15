"""
Anthropic API Client for Claude Opus 4.1 model.

Provides unified interface for Anthropic's Claude models with streaming support.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Mapping, Optional, Tuple

from ..Monitoring.performance_monitor import get_monitor
from .http_utils import HTTPClientError, post_json

logger = logging.getLogger(__name__)


def _default_enable_thinking() -> bool:
    """Resolve whether thinking should be enabled.

    Preference order:
    1) User-level ~/.claude/settings.json -> `alwaysThinkingEnabled`
    2) Environment variable ANTHROPIC_ENABLE_THINKING
    3) Default True
    """

    settings_path = Path.home() / ".claude" / "settings.json"
    try:
        if settings_path.exists():
            data = json.loads(settings_path.read_text())
            if "alwaysThinkingEnabled" in data:
                return bool(data.get("alwaysThinkingEnabled"))
    except Exception:
        # Fall back silently if the settings file is unreadable
        pass

    return str(os.getenv("ANTHROPIC_ENABLE_THINKING", "true")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@dataclass
class AnthropicConfig:
    """Configuration for Anthropic API."""

    api_key: str
    endpoint: str = "https://api.anthropic.com/v1"
    api_version: str = "2023-06-01"
    beta_headers: List[str] = field(
        default_factory=lambda: [
            h.strip()
            for h in os.getenv("ANTHROPIC_BETA", "clear_thinking_20251015").split(",")
            if h.strip()
        ]
    )
    timeout: int = 120
    max_retries: int = 3
    rate_limit_rpm: int = 100
    rate_limit_tpm: int = 400000
    # Thinking/Chain-of-thought support
    enable_thinking: bool = field(default_factory=_default_enable_thinking)
    thinking_budget_tokens: int = field(
        default_factory=lambda: int(os.getenv("ANTHROPIC_THINKING_BUDGET", "8000"))
    )
    thinking_type: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_THINKING_TYPE", "enabled")
    )


@dataclass
class ClaudeRequest:
    """Request for Claude completion."""

    model: str
    messages: List[Dict[str, str]]
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    top_k: Optional[int] = None
    stream: bool = False
    system: Optional[str] = None
    stop_sequences: Optional[List[str]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    thinking: Optional[Dict[str, Any]] = None


@dataclass
class ClaudeResponse:
    """Response from Claude."""

    id: str
    model: str
    content: str
    role: str = "assistant"
    stop_reason: str = "end_turn"
    usage: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AnthropicClient:
    """
    Client for Anthropic API.

    Supports:
    - Claude Opus 4.1 for validation and fallback
    - Streaming responses
    - System prompts
    """

    # Model configurations
    MODEL_CONFIGS = {
        "claude-opus-4.1": {
            "full_name": "claude-opus-4-1-20250805",
            "max_tokens": 4096,
            "context_window": 200000,
            "supports_system": True,
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075,
        },
        "claude-opus-4-1-20250805": {
            "full_name": "claude-opus-4-1-20250805",
            "max_tokens": 4096,
            "context_window": 200000,
            "supports_system": True,
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075,
        },
    }

    def __init__(
        self, config: Optional[AnthropicConfig] = None, api_key: Optional[str] = None
    ):
        """Initialize Anthropic client."""
        if not config:
            # Try to load from environment
            api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("Anthropic API key not provided")

            config = AnthropicConfig(api_key=api_key)

        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit_rpm, config.rate_limit_tpm)
        self.token_counter = TokenCounter()
        self.provider = "anthropic"
        self.monitor = get_monitor()

    async def complete(self, request: ClaudeRequest) -> ClaudeResponse:
        """
        Send completion request to Claude.

        Args:
            request: Claude request

        Returns:
            ClaudeResponse
        """
        # Validate model
        model_key = request.model
        if model_key not in self.MODEL_CONFIGS:
            # Try to find by full name
            for key, config in self.MODEL_CONFIGS.items():
                if config["full_name"] == request.model:
                    model_key = key
                    break
            else:
                raise ValueError(f"Unsupported model: {request.model}")

        model_config = self.MODEL_CONFIGS[model_key]

        # Use full model name
        request.model = model_config["full_name"]

        # Apply model defaults
        if request.max_tokens > model_config["max_tokens"]:
            request.max_tokens = model_config["max_tokens"]

        # Check rate limits
        await self.rate_limiter.acquire(request)

        payload = self._build_payload(request)
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": self.config.api_version,
            "content-type": "application/json",
        }
        if self.config.beta_headers:
            headers["anthropic-beta"] = ",".join(self.config.beta_headers)

        try:
            status, data, response_headers = await post_json(
                f"{self.config.endpoint}/messages",
                payload,
                headers=headers,
                timeout=self.config.timeout,
            )
        except HTTPClientError as exc:
            if self._should_retry_with_thinking(exc, payload):
                logger.warning(
                    "Anthropic API indicated thinking is required; retrying with default configuration."
                )
                request.thinking = self._default_thinking_payload()
                payload = self._build_payload(request)
                status, data, response_headers = await post_json(
                    f"{self.config.endpoint}/messages",
                    payload,
                    headers=headers,
                    timeout=self.config.timeout,
                )
            else:
                logger.error("Anthropic API error: %s", exc)
                raise

        content_blocks = data.get("content") or []
        text_parts: List[str] = []
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        content_text = "\n".join(part for part in text_parts if part) or str(
            content_blocks
        )

        usage = data.get("usage") or {}
        response = ClaudeResponse(
            id=data.get("id", f"msg_{datetime.now().timestamp()}"),
            model=data.get("model", request.model),
            content=content_text,
            stop_reason=data.get("stop_reason", "end_turn"),
            usage=usage,
            metadata={
                "type": data.get("type"),
                "role": data.get("role"),
                "status": status,
                "headers": {
                    k: v
                    for k, v in response_headers.items()
                    if k.lower().startswith("x-")
                },
            },
        )

        self.token_counter.add(response.usage)
        logger.info(
            "Completed Claude request with %s: %s tokens",
            response.model,
            response.usage.get("input_tokens", 0)
            + response.usage.get("output_tokens", 0),
        )
        if self.monitor:
            self.monitor.record_token_usage(
                model=response.model,
                provider=self.provider,
                usage=response.usage,
                metadata={"endpoint": "messages"},
            )
        return response

    async def stream(self, request: ClaudeRequest) -> AsyncIterator[str]:
        """
        Stream completion response from Claude.

        Args:
            request: Claude request with stream=True

        Yields:
            Response chunks
        """
        request.stream = True

        # Check rate limits
        await self.rate_limiter.acquire(request)

        completion_request = replace(request, stream=False)

        try:
            response = await self.complete(completion_request)
        except Exception as exc:
            logger.error("Streaming error during completion fallback: %s", exc)
            raise

        for chunk in self._chunk_stream_text(response.content):
            yield chunk

    async def complete_with_system(
        self,
        prompt: str,
        system_prompt: str,
        model: str = "claude-opus-4.1",
        max_tokens: int = 4096,
    ) -> ClaudeResponse:
        """
        Complete with system prompt.

        Args:
            prompt: User prompt
            system_prompt: System instructions
            model: Model to use
            max_tokens: Max response tokens

        Returns:
            ClaudeResponse
        """
        request = ClaudeRequest(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            system=system_prompt,
            max_tokens=max_tokens,
        )

        return await self.complete(request)

    def _chunk_stream_text(self, content: str, *, chunk_size: int = 128) -> List[str]:
        """Split Claude content into deterministic chunks for streaming."""
        if not content:
            return [""]

        return [content[i : i + chunk_size] for i in range(0, len(content), chunk_size)]

    async def validate_response(
        self, original_prompt: str, response: str, validation_criteria: str
    ) -> Dict[str, Any]:
        """
        Validate a response using Claude.

        Args:
            original_prompt: Original prompt
            response: Response to validate
            validation_criteria: What to validate for

        Returns:
            Validation results
        """
        validation_prompt = f"""Please validate this response against the criteria.

Original Prompt: {original_prompt}

Response: {response}

Validation Criteria: {validation_criteria}

Provide:
1. Is the response valid? (yes/no)
2. Confidence score (0-1)
3. Issues found (if any)
4. Suggestions for improvement"""

        validation_request = ClaudeRequest(
            model="claude-opus-4.1",
            messages=[{"role": "user", "content": validation_prompt}],
            max_tokens=1000,
            temperature=0.3,  # Lower temperature for validation
        )

        result = await self.complete(validation_request)

        parsed = self._parse_validation_response(result.content)
        parsed["raw_response"] = result.content
        return parsed

    def estimate_cost(self, request: ClaudeRequest) -> Dict[str, float]:
        """
        Estimate cost for a request.

        Args:
            request: Claude request

        Returns:
            Cost breakdown
        """
        model_key = request.model
        if model_key not in self.MODEL_CONFIGS:
            for key, config in self.MODEL_CONFIGS.items():
                if config["full_name"] == request.model:
                    model_key = key
                    break
            else:
                return {"error": "Unknown model"}

        config = self.MODEL_CONFIGS[model_key]

        # Estimate tokens (rough approximation)
        input_tokens = sum(len(m["content"]) // 4 for m in request.messages)
        if request.system:
            input_tokens += len(request.system) // 4

        output_tokens = request.max_tokens

        input_cost = (input_tokens / 1000) * config["cost_per_1k_input"]
        output_cost = (output_tokens / 1000) * config["cost_per_1k_output"]

        return {
            "input_cost": round(input_cost, 4),
            "output_cost": round(output_cost, 4),
            "total_cost": round(input_cost + output_cost, 4),
            "estimated_tokens": input_tokens + output_tokens,
        }

    def get_model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """Get model configuration info."""
        # Check both short and full names
        if model in self.MODEL_CONFIGS:
            return self.MODEL_CONFIGS[model]

        for config in self.MODEL_CONFIGS.values():
            if config["full_name"] == model:
                return config

        return None

    def _parse_validation_response(self, text: str) -> Dict[str, Any]:
        """Parse validation output from Claude into structured data."""
        import re

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        verdict: Optional[bool] = None
        confidence: Optional[float] = None
        issues: List[str] = []
        suggestions: List[str] = []
        collector: Optional[List[str]] = None

        for line in lines:
            normalized = line.lower()

            if verdict is None:
                if normalized in {"yes", "valid: yes", "valid - yes"} or (
                    "yes" in normalized and "no" not in normalized
                ):
                    verdict = True
                elif normalized in {"no", "valid: no", "valid - no"} or (
                    "no" in normalized and "yes" not in normalized
                ):
                    verdict = False

            if confidence is None and "confidence" in normalized:
                match = re.search(r"([01](?:\.\d+)?)", normalized)
                if match:
                    try:
                        confidence = float(match.group(1))
                    except ValueError:
                        confidence = None

            if normalized.startswith("issues"):
                collector = issues
                continue
            if normalized.startswith("suggest"):
                collector = suggestions
                continue

            if collector is not None and (line.startswith("-") or line.startswith("*")):
                collector.append(line.lstrip("-* "))
                continue

            collector = None

        return {
            "valid": verdict if verdict is not None else False,
            "confidence": confidence if confidence is not None else 0.0,
            "issues": issues,
            "suggestions": suggestions,
        }

    def _default_thinking_payload(self) -> Dict[str, Any]:
        """Create the default thinking configuration."""

        return {
            "type": self.config.thinking_type or "enabled",
            "budget_tokens": self.config.thinking_budget_tokens,
        }

    def _error_requires_thinking(self, error: HTTPClientError) -> bool:
        """Check whether an Anthropic error demands thinking to be enabled."""

        fragments: List[str] = []
        if error.payload:
            detail = error.payload.get("error")
            if isinstance(detail, Mapping):
                fragments.append(str(detail.get("message", "")))
                fragments.append(str(detail.get("detail", "")))
            elif detail:
                fragments.append(str(detail))
        if error.message:
            fragments.append(error.message)

        normalized = (
            " ".join(part for part in fragments if part).lower().replace("`", "")
        )
        return (
            "requires thinking" in normalized or "thinking to be enabled" in normalized
        )

    def _should_retry_with_thinking(
        self, error: HTTPClientError, payload: Dict[str, Any]
    ) -> bool:
        """Determine if we should retry a request after enabling thinking."""

        if payload.get("thinking"):
            return False
        return self._error_requires_thinking(error)

    def _build_payload(self, request: ClaudeRequest) -> Dict[str, Any]:
        """Build API request payload."""
        payload = {
            "model": request.model,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": request.stream,
        }

        if request.system:
            payload["system"] = request.system

        if request.top_k is not None:
            payload["top_k"] = request.top_k

        if request.stop_sequences:
            payload["stop_sequences"] = request.stop_sequences

        # Enable Anthropic extended thinking by default to satisfy strategies like clear_thinking_20251015.
        thinking_cfg = request.thinking
        if (thinking_cfg is None or thinking_cfg == {}) and self.config.enable_thinking:
            thinking_cfg = self._default_thinking_payload()

        if thinking_cfg:
            payload["thinking"] = thinking_cfg

        return payload


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, rpm_limit: int, tpm_limit: int):
        """Initialize rate limiter."""
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.request_times: List[datetime] = []
        self.token_counts: List[Tuple[datetime, int]] = []

    async def acquire(self, request: ClaudeRequest):
        """Wait if necessary to respect rate limits."""
        now = datetime.now()

        # Clean old entries
        minute_ago = now - timedelta(minutes=1)
        self.request_times = [t for t in self.request_times if t > minute_ago]
        self.token_counts = [(t, c) for t, c in self.token_counts if t > minute_ago]

        # Check RPM
        if len(self.request_times) >= self.rpm_limit:
            wait_time = (
                self.request_times[0] + timedelta(minutes=1) - now
            ).total_seconds()
            if wait_time > 0:
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s for RPM")
                await asyncio.sleep(wait_time)

        # Check TPM (estimate)
        estimated_tokens = len(str(request.messages)) // 4 + request.max_tokens
        current_tpm = sum(c for _, c in self.token_counts)

        if current_tpm + estimated_tokens > self.tpm_limit:
            logger.debug("Rate limit: waiting for TPM window")
            await asyncio.sleep(1)

        # Record request
        self.request_times.append(now)
        self.token_counts.append((now, estimated_tokens))


class TokenCounter:
    """Track token usage."""

    def __init__(self):
        """Initialize counter."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.request_count = 0

    def add(self, usage: Dict[str, int]):
        """Add usage from a response."""
        self.total_input_tokens += usage.get("input_tokens", 0)
        self.total_output_tokens += usage.get("output_tokens", 0)
        self.request_count += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get usage summary."""
        total = self.total_input_tokens + self.total_output_tokens
        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": total,
            "request_count": self.request_count,
            "average_tokens_per_request": total // self.request_count
            if self.request_count > 0
            else 0,
        }


# Convenience functions
async def create_anthropic_client(api_key: Optional[str] = None) -> AnthropicClient:
    """Create and initialize Anthropic client."""
    config = AnthropicConfig(api_key=api_key) if api_key else None
    return AnthropicClient(config)
