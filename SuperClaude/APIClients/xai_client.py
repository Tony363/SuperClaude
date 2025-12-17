"""
X.AI API Client for Grok-4 and Grok-Code-Fast-1 models.

Provides unified interface for X.AI's Grok models with code analysis capabilities.
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
class XAIConfig:
    """Configuration for X.AI API."""

    api_key: str
    endpoint: str = "https://api.x.ai/v1"
    timeout: int = 120
    max_retries: int = 3
    rate_limit_rpm: int = 100
    rate_limit_tpm: int = 500000


@dataclass
class GrokRequest:
    """Request for Grok completion."""

    model: str
    messages: list[dict[str, str]]
    max_tokens: int = 8192
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stream: bool = False
    stop: list[str] | None = None
    system: str | None = None
    tools: list[dict[str, Any]] | None = None
    tool_choice: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GrokResponse:
    """Response from Grok."""

    id: str
    model: str
    content: str
    role: str = "assistant"
    tool_calls: list[dict[str, Any]] | None = None
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class XAIClient:
    """
    Client for X.AI API.

    Supports:
    - Grok-4 for deep code analysis and thinking
    - Grok-Code-Fast-1 for quick code iterations
    - Function calling
    - Code-specific optimizations
    """

    # Model configurations
    MODEL_CONFIGS = {
        "grok-4": {
            "full_name": "grok-4",
            "max_tokens": 8192,
            "context_window": 256000,
            "supports_thinking": True,
            "supports_tools": True,
            "optimized_for": "code_analysis",
            "cost_per_1k_input": 0.01,
            "cost_per_1k_output": 0.03,
        },
        "grok-code-fast-1": {
            "full_name": "grok-code-fast-1",
            "max_tokens": 4096,
            "context_window": 128000,
            "supports_thinking": False,
            "supports_tools": True,
            "optimized_for": "quick_iteration",
            "cost_per_1k_input": 0.005,
            "cost_per_1k_output": 0.015,
        },
    }

    def __init__(self, config: XAIConfig | None = None, api_key: str | None = None):
        """Initialize X.AI client."""
        if not config:
            # Try to load from environment
            api_key = api_key or os.getenv("XAI_API_KEY")
            if not api_key:
                raise ValueError("X.AI API key not provided")

            config = XAIConfig(api_key=api_key)

        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit_rpm, config.rate_limit_tpm)
        self.token_counter = TokenCounter()
        self.provider = "xai"
        self.monitor = None  # Monitoring removed

    async def complete(self, request: GrokRequest) -> GrokResponse:
        """
        Send completion request to Grok.

        Args:
            request: Grok request

        Returns:
            GrokResponse
        """
        # Validate model
        if request.model not in self.MODEL_CONFIGS:
            raise ValueError(f"Unsupported model: {request.model}")

        model_config = self.MODEL_CONFIGS[request.model]

        # Apply model defaults
        if request.max_tokens > model_config["max_tokens"]:
            request.max_tokens = model_config["max_tokens"]

        # Check rate limits
        await self.rate_limiter.acquire(request)

        payload = self._build_payload(request)
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            status, data, response_headers = await post_json(
                f"{self.config.endpoint}/chat/completions",
                payload,
                headers=headers,
                timeout=self.config.timeout,
            )
        except HTTPClientError as exc:
            logger.error("X.AI API error: %s", exc)
            raise

        choices = data.get("choices") or []
        if not choices:
            raise HTTPClientError(status, "Grok response missing choices", data)
        choice = choices[0]
        message = choice.get("message") or {}
        role = message.get("role", "assistant")
        content = message.get("content") or ""

        response = GrokResponse(
            id=data.get("id", f"grok-{datetime.now().timestamp()}"),
            model=data.get("model", request.model),
            content=content,
            role=role,
            tool_calls=message.get("tool_calls") or message.get("toolCalls"),
            finish_reason=choice.get("finish_reason", "stop"),
            usage=data.get("usage", {}),
            metadata={
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
            "Completed Grok request with %s: %s tokens",
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

    async def analyze_code(
        self,
        code: str,
        language: str,
        analysis_type: str = "full",
        model: str = "grok-4",
    ) -> dict[str, Any]:
        """
        Analyze code with Grok.

        Args:
            code: Code to analyze
            language: Programming language
            analysis_type: Type of analysis (full, security, performance, quality)
            model: Model to use

        Returns:
            Analysis results
        """
        analysis_prompts = {
            "full": f"""Analyze this {language} code comprehensively:
1. Code quality and structure
2. Performance characteristics
3. Security vulnerabilities
4. Best practices compliance
5. Potential improvements

Code:
```{language}
{code}
```""",
            "security": f"""Perform security analysis on this {language} code:
1. Identify vulnerabilities
2. Check for injection risks
3. Review authentication/authorization
4. Assess data validation
5. Suggest security improvements

Code:
```{language}
{code}
```""",
            "performance": f"""Analyze performance of this {language} code:
1. Time complexity
2. Space complexity
3. Bottlenecks
4. Optimization opportunities
5. Scalability concerns

Code:
```{language}
{code}
```""",
            "quality": f"""Review code quality for this {language} code:
1. Readability and maintainability
2. Design patterns usage
3. SOLID principles compliance
4. Error handling
5. Documentation quality

Code:
```{language}
{code}
```""",
        }

        prompt = analysis_prompts.get(analysis_type, analysis_prompts["full"])

        request = GrokRequest(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=4096,
            temperature=0.3,  # Lower temperature for analysis
        )

        response = await self.complete(request)

        # Parse analysis (in real implementation)
        return {
            "analysis_type": analysis_type,
            "model": model,
            "language": language,
            "findings": response.content,
            "timestamp": datetime.now().isoformat(),
        }

    async def quick_fix(
        self, code: str, error: str, language: str, model: str = "grok-code-fast-1"
    ) -> dict[str, Any]:
        """
        Quick fix for code errors using fast model.

        Args:
            code: Code with error
            error: Error message
            language: Programming language
            model: Model to use (default: fast model)

        Returns:
            Fix suggestion
        """
        prompt = f"""Fix this {language} code error quickly:

Error: {error}

Code:
```{language}
{code}
```

Provide:
1. The fixed code
2. Brief explanation of the fix"""

        request = GrokRequest(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
            temperature=0.5,
        )

        response = await self.complete(request)

        # Parse fix (in real implementation)
        return {
            "fixed_code": response.content,
            "model": model,
            "error": error,
            "timestamp": datetime.now().isoformat(),
        }

    async def refactor_code(
        self, code: str, language: str, refactor_goals: list[str], model: str = "grok-4"
    ) -> dict[str, Any]:
        """
        Refactor code with specific goals.

        Args:
            code: Code to refactor
            language: Programming language
            refactor_goals: Goals for refactoring
            model: Model to use

        Returns:
            Refactored code and explanation
        """
        goals_text = "\n".join(f"- {goal}" for goal in refactor_goals)

        prompt = f"""Refactor this {language} code with these goals:
{goals_text}

Original Code:
```{language}
{code}
```

Provide:
1. Refactored code
2. Summary of changes
3. Benefits achieved"""

        request = GrokRequest(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=8192,
            temperature=0.5,
        )

        response = await self.complete(request)

        return {
            "refactored_code": response.content,
            "goals": refactor_goals,
            "model": model,
            "timestamp": datetime.now().isoformat(),
        }

    async def complete_with_thinking(
        self, prompt: str, model: str = "grok-4"
    ) -> GrokResponse:
        """
        Complete with thinking mode (Grok-4 only).

        Args:
            prompt: User prompt
            model: Model to use (must support thinking)

        Returns:
            GrokResponse with deep reasoning
        """
        if model not in ["grok-4"]:
            logger.warning(f"Model {model} doesn't support thinking mode")
            return await self.complete(
                GrokRequest(model=model, messages=[{"role": "user", "content": prompt}])
            )

        # Add thinking instruction
        thinking_prompt = f"""<thinking_mode>
Analyze this problem systematically using your deep reasoning capabilities.
Consider edge cases, performance implications, and best practices.
</thinking_mode>

{prompt}"""

        request = GrokRequest(
            model=model,
            messages=[{"role": "user", "content": thinking_prompt}],
            max_tokens=8192,
            temperature=0.7,
        )

        return await self.complete(request)

    async def stream(self, request: GrokRequest) -> AsyncIterator[str]:
        """
        Stream completion response from Grok.

        Args:
            request: Grok request with stream=True

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

    def estimate_cost(self, request: GrokRequest) -> dict[str, float]:
        """
        Estimate cost for a request.

        Args:
            request: Grok request

        Returns:
            Cost breakdown
        """
        if request.model not in self.MODEL_CONFIGS:
            return {"error": "Unknown model"}

        config = self.MODEL_CONFIGS[request.model]

        # Estimate tokens
        prompt_tokens = sum(len(m["content"]) // 4 for m in request.messages)
        if request.system:
            prompt_tokens += len(request.system) // 4

        completion_tokens = request.max_tokens

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

    def _chunk_stream_text(self, content: str, *, chunk_size: int = 128) -> list[str]:
        """Split Grok content into deterministic streaming chunks."""
        if not content:
            return [""]

        return [content[i : i + chunk_size] for i in range(0, len(content), chunk_size)]

    def _build_payload(self, request: GrokRequest) -> dict[str, Any]:
        """Build API request payload."""
        payload = {
            "model": request.model,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": request.stream,
        }

        if request.system:
            payload["messages"].insert(0, {"role": "system", "content": request.system})

        if request.stop:
            payload["stop"] = request.stop

        if request.tools:
            payload["tools"] = request.tools
            if request.tool_choice:
                payload["tool_choice"] = request.tool_choice

        return payload


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, rpm_limit: int, tpm_limit: int):
        """Initialize rate limiter."""
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.request_times: list[datetime] = []
        self.token_counts: list[tuple[datetime, int]] = []

    async def acquire(self, request: GrokRequest):
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

        # Estimate tokens
        estimated_tokens = len(str(request.messages)) // 4 + request.max_tokens
        current_tpm = sum(c for _, c in self.token_counts)

        # Check TPM
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
async def create_xai_client(api_key: str | None = None) -> XAIClient:
    """Create and initialize X.AI client."""
    config = XAIConfig(api_key=api_key) if api_key else None
    return XAIClient(config)
