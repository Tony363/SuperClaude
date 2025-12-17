"""
OpenAI API Client for GPT-5, GPT-4.1, GPT-4o, and GPT-4o-mini models.

Provides unified interface for all OpenAI models with streaming and function calling support.
"""

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any

from .http_utils import HTTPClientError, post_json

logger = logging.getLogger(__name__)


@dataclass
class OpenAIConfig:
    """Configuration for OpenAI API."""

    api_key: str
    endpoint: str = "https://api.openai.com/v1"
    organization: str | None = None
    timeout: int = 300
    max_retries: int = 3
    rate_limit_rpm: int = 100
    rate_limit_tpm: int = 1000000


@dataclass
class CompletionRequest:
    """Request for completion."""

    model: str
    messages: list[dict[str, str]]
    temperature: float = 0.7
    max_tokens: int | None = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stream: bool = False
    functions: list[dict[str, Any]] | None = None
    function_call: dict[str, str] | None = None
    user: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CompletionResponse:
    """Response from completion."""

    id: str
    model: str
    content: str
    role: str = "assistant"
    function_call: dict[str, Any] | None = None
    usage: dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"
    metadata: dict[str, Any] = field(default_factory=dict)


class OpenAIClient:
    """
    Client for OpenAI API.

    Supports:
    - GPT-5 with thinking mode
    - GPT-4.1 with extended context
    - GPT-4o for standard operations
    - GPT-4o-mini for quick tasks
    """

    # Model configurations
    MODEL_CONFIGS = {
        "gpt-5": {
            "max_tokens": 50000,
            "supports_thinking": True,
            "context_window": 400000,
            "cost_per_1k_input": 0.02,
            "cost_per_1k_output": 0.06,
        },
        "gpt-4.1": {
            "max_tokens": 50000,
            "supports_thinking": False,
            "context_window": 1000000,
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.045,
        },
        "gpt-4o": {
            "max_tokens": 4096,
            "supports_thinking": False,
            "context_window": 128000,
            "cost_per_1k_input": 0.01,
            "cost_per_1k_output": 0.03,
        },
        "gpt-4o-mini": {
            "max_tokens": 4096,
            "supports_thinking": False,
            "context_window": 128000,
            "cost_per_1k_input": 0.001,
            "cost_per_1k_output": 0.002,
        },
    }

    def __init__(self, config: OpenAIConfig | None = None, api_key: str | None = None):
        """Initialize OpenAI client."""
        if not config:
            # Try to load from environment
            api_key = api_key or os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not provided")

            config = OpenAIConfig(api_key=api_key)

        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit_rpm, config.rate_limit_tpm)
        self.token_counter = TokenCounter()
        self.provider = "openai"
        self.monitor = None  # Monitoring removed

    async def complete(self, request: CompletionRequest) -> CompletionResponse:
        """
        Send completion request.

        Args:
            request: Completion request

        Returns:
            CompletionResponse
        """
        # Validate model
        if request.model not in self.MODEL_CONFIGS:
            raise ValueError(f"Unsupported model: {request.model}")

        model_config = self.MODEL_CONFIGS[request.model]

        # Apply model defaults
        if not request.max_tokens:
            request.max_tokens = model_config["max_tokens"]

        # Check rate limits
        await self.rate_limiter.acquire(request)

        payload = self._build_payload(request)
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        if self.config.organization:
            headers["OpenAI-Organization"] = self.config.organization

        try:
            status, data, response_headers = await post_json(
                f"{self.config.endpoint}/chat/completions",
                payload,
                headers=headers,
                timeout=self.config.timeout,
            )
        except HTTPClientError as exc:
            logger.error("OpenAI API error: %s", exc)
            raise

        choices = data.get("choices") or []
        if not choices:
            raise HTTPClientError(status, "OpenAI response missing choices", data)

        choice = choices[0]
        message = choice.get("message") or {}
        role = message.get("role", "assistant")
        content = message.get("content") or ""
        function_call = message.get("function_call")
        usage = data.get("usage") or {}
        finish_reason = choice.get("finish_reason", data.get("finish_reason", "stop"))

        response = CompletionResponse(
            id=data.get("id", f"chatcmpl-{datetime.now().timestamp()}"),
            model=data.get("model", request.model),
            content=content,
            role=role,
            function_call=function_call,
            usage=usage,
            finish_reason=finish_reason or "stop",
            metadata={
                "created": data.get("created"),
                "system_fingerprint": data.get("system_fingerprint"),
                "status": status,
                "headers": {
                    k: v
                    for k, v in response_headers.items()
                    if k.lower().startswith("x-")
                },
            },
        )

        if "prompt_annotations" in data:
            response.metadata["prompt_annotations"] = data["prompt_annotations"]
        if "usage" not in data:
            # Populate total tokens when API response omits them
            response.usage.setdefault(
                "total_tokens",
                response.usage.get("prompt_tokens", 0)
                + response.usage.get("completion_tokens", 0),
            )

        self.token_counter.add(response.usage)
        logger.info(
            "Completed OpenAI request with %s: %s tokens",
            response.model,
            response.usage.get("total_tokens", 0),
        )
        if self.monitor:
            self.monitor.record_token_usage(
                model=response.model,
                provider=self.provider,
                usage=response.usage,
                metadata={"endpoint": "chat.completions"},
            )
        return response

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """
        Stream completion response.

        Args:
            request: Completion request with stream=True

        Yields:
            Response chunks
        """
        request.stream = True

        # Check rate limits ahead of the synthesized streaming fallback.
        await self.rate_limiter.acquire(request)

        # We currently rely on the non-streaming completion endpoint and
        # progressively yield the returned content so callers still receive
        # incremental output without fake placeholders.
        streamed_request = replace(request, stream=False)

        try:
            response = await self.complete(streamed_request)
        except Exception as exc:
            logger.error("Streaming error during completion fallback: %s", exc)
            raise

        for chunk in self._chunk_stream_text(response.content):
            yield chunk

    async def complete_with_thinking(
        self, prompt: str, model: str = "gpt-5", think_level: int = 3
    ) -> CompletionResponse:
        """
        Complete with thinking mode (GPT-5 only).

        Args:
            prompt: User prompt
            model: Model to use (must support thinking)
            think_level: Thinking depth (1-3)

        Returns:
            CompletionResponse with thinking
        """
        if model not in ["gpt-5", "grok-4"]:
            logger.warning(
                f"Model {model} doesn't support thinking mode, using standard completion"
            )
            return await self.complete(
                CompletionRequest(
                    model=model, messages=[{"role": "user", "content": prompt}]
                )
            )

        # Calculate token budget based on think level
        token_budgets = {1: 5000, 2: 15000, 3: 50000}
        max_tokens = token_budgets.get(think_level, 50000)

        # Add thinking instruction
        thinking_prompt = f"""<thinking_mode level="{think_level}">
Think deeply about this problem before responding.
Use structured reasoning and consider multiple angles.
</thinking_mode>

{prompt}"""

        request = CompletionRequest(
            model=model,
            messages=[{"role": "user", "content": thinking_prompt}],
            max_tokens=max_tokens,
            temperature=0.7,
        )

        return await self.complete(request)

    async def complete_with_functions(
        self, prompt: str, functions: list[dict[str, Any]], model: str = "gpt-4o"
    ) -> CompletionResponse:
        """
        Complete with function calling.

        Args:
            prompt: User prompt
            functions: Available functions
            model: Model to use

        Returns:
            CompletionResponse with potential function call
        """
        request = CompletionRequest(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            functions=functions,
            function_call="auto",
        )

        return await self.complete(request)

    def _chunk_stream_text(self, content: str, *, chunk_size: int = 128) -> list[str]:
        """Split completion content into chunks for streaming fallback."""
        if not content:
            return [""]

        return [content[i : i + chunk_size] for i in range(0, len(content), chunk_size)]

    def estimate_cost(self, request: CompletionRequest) -> dict[str, float]:
        """
        Estimate cost for a request.

        Args:
            request: Completion request

        Returns:
            Cost breakdown
        """
        if request.model not in self.MODEL_CONFIGS:
            return {"error": "Unknown model"}

        config = self.MODEL_CONFIGS[request.model]

        # Estimate tokens (rough approximation)
        prompt_tokens = sum(len(m["content"]) // 4 for m in request.messages)
        completion_tokens = request.max_tokens or config["max_tokens"]

        input_cost = (prompt_tokens / 1000) * config["cost_per_1k_input"]
        output_cost = (completion_tokens / 1000) * config["cost_per_1k_output"]

        return {
            "input_cost": round(input_cost, 4),
            "output_cost": round(output_cost, 4),
            "total_cost": round(input_cost + output_cost, 4),
            "estimated_tokens": prompt_tokens + completion_tokens,
        }

    def get_model_info(self, model: str) -> dict[str, Any] | None:
        """Get model configuration info."""
        return self.MODEL_CONFIGS.get(model)

    def _build_payload(self, request: CompletionRequest) -> dict[str, Any]:
        """Build API request payload."""
        payload = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": request.stream,
        }

        if request.functions:
            payload["functions"] = request.functions
            if request.function_call:
                payload["function_call"] = request.function_call

        if request.user:
            payload["user"] = request.user

        return payload


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, rpm_limit: int, tpm_limit: int):
        """Initialize rate limiter."""
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.request_times: list[datetime] = []
        self.token_counts: list[tuple[datetime, int]] = []

    async def acquire(self, request: CompletionRequest):
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
        estimated_tokens = len(str(request.messages)) // 4 + (
            request.max_tokens or 1000
        )
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
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.request_count = 0

    def add(self, usage: dict[str, int]):
        """Add usage from a response."""
        self.total_prompt_tokens += usage.get("prompt_tokens", 0)
        self.total_completion_tokens += usage.get("completion_tokens", 0)
        self.total_tokens += usage.get("total_tokens", 0)
        self.request_count += 1

    def get_summary(self) -> dict[str, Any]:
        """Get usage summary."""
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "request_count": self.request_count,
            "average_tokens_per_request": self.total_tokens // self.request_count
            if self.request_count > 0
            else 0,
        }


# Convenience functions
async def create_openai_client(api_key: str | None = None) -> OpenAIClient:
    """Create and initialize OpenAI client."""
    config = OpenAIConfig(api_key=api_key) if api_key else None
    return OpenAIClient(config)
