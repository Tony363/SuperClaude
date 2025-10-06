"""
OpenAI API Client for GPT-5, GPT-4.1, GPT-4o, and GPT-4o-mini models.

Provides unified interface for all OpenAI models with streaming and function calling support.
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


@dataclass
class OpenAIConfig:
    """Configuration for OpenAI API."""

    api_key: str
    endpoint: str = "https://api.openai.com/v1"
    organization: Optional[str] = None
    timeout: int = 300
    max_retries: int = 3
    rate_limit_rpm: int = 100
    rate_limit_tpm: int = 1000000


@dataclass
class CompletionRequest:
    """Request for completion."""

    model: str
    messages: List[Dict[str, str]]
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stream: bool = False
    functions: Optional[List[Dict[str, Any]]] = None
    function_call: Optional[Dict[str, str]] = None
    user: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompletionResponse:
    """Response from completion."""

    id: str
    model: str
    content: str
    role: str = "assistant"
    function_call: Optional[Dict[str, Any]] = None
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"
    metadata: Dict[str, Any] = field(default_factory=dict)


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
            "cost_per_1k_output": 0.06
        },
        "gpt-4.1": {
            "max_tokens": 50000,
            "supports_thinking": False,
            "context_window": 1000000,
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.045
        },
        "gpt-4o": {
            "max_tokens": 4096,
            "supports_thinking": False,
            "context_window": 128000,
            "cost_per_1k_input": 0.01,
            "cost_per_1k_output": 0.03
        },
        "gpt-4o-mini": {
            "max_tokens": 4096,
            "supports_thinking": False,
            "context_window": 128000,
            "cost_per_1k_input": 0.001,
            "cost_per_1k_output": 0.002
        }
    }

    def __init__(self, config: Optional[OpenAIConfig] = None):
        """Initialize OpenAI client."""
        if not config:
            # Try to load from environment
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("OpenAI API key not provided")

            config = OpenAIConfig(api_key=api_key)

        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit_rpm, config.rate_limit_tpm)
        self.token_counter = TokenCounter()

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

        try:
            # In real implementation, make actual API call
            # async with aiohttp.ClientSession() as session:
            #     headers = {
            #         "Authorization": f"Bearer {self.config.api_key}",
            #         "Content-Type": "application/json"
            #     }
            #     if self.config.organization:
            #         headers["OpenAI-Organization"] = self.config.organization
            #
            #     payload = self._build_payload(request)
            #
            #     async with session.post(
            #         f"{self.config.endpoint}/chat/completions",
            #         headers=headers,
            #         json=payload,
            #         timeout=self.config.timeout
            #     ) as response:
            #         data = await response.json()

            # Mock response
            response = CompletionResponse(
                id=f"chatcmpl-{datetime.now().timestamp()}",
                model=request.model,
                content=f"Response from {request.model} to: {request.messages[-1]['content'][:50]}...",
                usage={
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "total_tokens": 150
                }
            )

            # Track usage
            self.token_counter.add(response.usage)

            logger.info(f"Completed request with {request.model}: {response.usage['total_tokens']} tokens")
            return response

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def stream(self, request: CompletionRequest) -> AsyncIterator[str]:
        """
        Stream completion response.

        Args:
            request: Completion request with stream=True

        Yields:
            Response chunks
        """
        request.stream = True

        # Check rate limits
        await self.rate_limiter.acquire(request)

        try:
            # In real implementation, stream from API
            # async with aiohttp.ClientSession() as session:
            #     ... make streaming request ...
            #     async for chunk in response.content:
            #         yield chunk

            # Mock streaming
            response = f"Streaming response from {request.model}"
            for word in response.split():
                yield word + " "
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise

    async def complete_with_thinking(
        self,
        prompt: str,
        model: str = "gpt-5",
        think_level: int = 3
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
            logger.warning(f"Model {model} doesn't support thinking mode, using standard completion")
            return await self.complete(CompletionRequest(
                model=model,
                messages=[{"role": "user", "content": prompt}]
            ))

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
            temperature=0.7
        )

        return await self.complete(request)

    async def complete_with_functions(
        self,
        prompt: str,
        functions: List[Dict[str, Any]],
        model: str = "gpt-4o"
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
            function_call="auto"
        )

        return await self.complete(request)

    def estimate_cost(self, request: CompletionRequest) -> Dict[str, float]:
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
            "estimated_tokens": prompt_tokens + completion_tokens
        }

    def get_model_info(self, model: str) -> Optional[Dict[str, Any]]:
        """Get model configuration info."""
        return self.MODEL_CONFIGS.get(model)

    def _build_payload(self, request: CompletionRequest) -> Dict[str, Any]:
        """Build API request payload."""
        payload = {
            "model": request.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "top_p": request.top_p,
            "frequency_penalty": request.frequency_penalty,
            "presence_penalty": request.presence_penalty,
            "stream": request.stream
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
        self.request_times: List[datetime] = []
        self.token_counts: List[Tuple[datetime, int]] = []

    async def acquire(self, request: CompletionRequest):
        """Wait if necessary to respect rate limits."""
        now = datetime.now()

        # Clean old entries
        minute_ago = now - timedelta(minutes=1)
        self.request_times = [t for t in self.request_times if t > minute_ago]
        self.token_counts = [(t, c) for t, c in self.token_counts if t > minute_ago]

        # Check RPM
        if len(self.request_times) >= self.rpm_limit:
            wait_time = (self.request_times[0] + timedelta(minutes=1) - now).total_seconds()
            if wait_time > 0:
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s for RPM")
                await asyncio.sleep(wait_time)

        # Check TPM (estimate)
        estimated_tokens = len(str(request.messages)) // 4 + (request.max_tokens or 1000)
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

    def add(self, usage: Dict[str, int]):
        """Add usage from a response."""
        self.total_prompt_tokens += usage.get("prompt_tokens", 0)
        self.total_completion_tokens += usage.get("completion_tokens", 0)
        self.total_tokens += usage.get("total_tokens", 0)
        self.request_count += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get usage summary."""
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_tokens,
            "request_count": self.request_count,
            "average_tokens_per_request": self.total_tokens // self.request_count if self.request_count > 0 else 0
        }


# Convenience functions
async def create_openai_client(api_key: Optional[str] = None) -> OpenAIClient:
    """Create and initialize OpenAI client."""
    config = OpenAIConfig(api_key=api_key) if api_key else None
    return OpenAIClient(config)