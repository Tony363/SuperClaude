"""
Anthropic API Client for Claude Opus 4.1 model.

Provides unified interface for Anthropic's Claude models with streaming support.
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class AnthropicConfig:
    """Configuration for Anthropic API."""

    api_key: str
    endpoint: str = "https://api.anthropic.com/v1"
    api_version: str = "2023-06-01"
    timeout: int = 120
    max_retries: int = 3
    rate_limit_rpm: int = 100
    rate_limit_tpm: int = 400000


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
            "cost_per_1k_output": 0.075
        },
        "claude-opus-4-1-20250805": {
            "full_name": "claude-opus-4-1-20250805",
            "max_tokens": 4096,
            "context_window": 200000,
            "supports_system": True,
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075
        }
    }

    def __init__(self, config: Optional[AnthropicConfig] = None):
        """Initialize Anthropic client."""
        if not config:
            # Try to load from environment
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("Anthropic API key not provided")

            config = AnthropicConfig(api_key=api_key)

        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit_rpm, config.rate_limit_tpm)
        self.token_counter = TokenCounter()

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

        try:
            # In real implementation, make actual API call
            # async with aiohttp.ClientSession() as session:
            #     headers = {
            #         "x-api-key": self.config.api_key,
            #         "anthropic-version": self.config.api_version,
            #         "content-type": "application/json"
            #     }
            #
            #     payload = self._build_payload(request)
            #
            #     async with session.post(
            #         f"{self.config.endpoint}/messages",
            #         headers=headers,
            #         json=payload,
            #         timeout=self.config.timeout
            #     ) as response:
            #         data = await response.json()

            # Mock response
            response = ClaudeResponse(
                id=f"msg_{datetime.now().timestamp()}",
                model=request.model,
                content=f"Claude Opus response to: {request.messages[-1]['content'][:50]}...",
                usage={
                    "input_tokens": 100,
                    "output_tokens": 50
                }
            )

            # Track usage
            self.token_counter.add(response.usage)

            logger.info(f"Completed Claude request: {response.usage.get('input_tokens', 0)} + {response.usage.get('output_tokens', 0)} tokens")
            return response

        except Exception as e:
            logger.error(f"Anthropic API error: {e}")
            raise

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

        try:
            # In real implementation, stream from API
            # async with aiohttp.ClientSession() as session:
            #     headers = {
            #         "x-api-key": self.config.api_key,
            #         "anthropic-version": self.config.api_version,
            #         "content-type": "application/json"
            #     }
            #
            #     payload = self._build_payload(request)
            #
            #     async with session.post(
            #         f"{self.config.endpoint}/messages",
            #         headers=headers,
            #         json=payload,
            #         timeout=self.config.timeout
            #     ) as response:
            #         async for line in response.content:
            #             # Parse SSE and yield content
            #             yield content

            # Mock streaming
            response = f"Streaming response from Claude Opus 4.1"
            for word in response.split():
                yield word + " "
                await asyncio.sleep(0.1)

        except Exception as e:
            logger.error(f"Streaming error: {e}")
            raise

    async def complete_with_system(
        self,
        prompt: str,
        system_prompt: str,
        model: str = "claude-opus-4.1",
        max_tokens: int = 4096
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
            max_tokens=max_tokens
        )

        return await self.complete(request)

    async def validate_response(
        self,
        original_prompt: str,
        response: str,
        validation_criteria: str
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
            temperature=0.3  # Lower temperature for validation
        )

        result = await self.complete(validation_request)

        # Parse validation response (in real implementation)
        return {
            "valid": True,  # Mock result
            "confidence": 0.9,
            "issues": [],
            "suggestions": [],
            "raw_response": result.content
        }

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
            "estimated_tokens": input_tokens + output_tokens
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

    def _build_payload(self, request: ClaudeRequest) -> Dict[str, Any]:
        """Build API request payload."""
        payload = {
            "model": request.model,
            "messages": request.messages,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": request.stream
        }

        if request.system:
            payload["system"] = request.system

        if request.top_k is not None:
            payload["top_k"] = request.top_k

        if request.stop_sequences:
            payload["stop_sequences"] = request.stop_sequences

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
            wait_time = (self.request_times[0] + timedelta(minutes=1) - now).total_seconds()
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
            "average_tokens_per_request": total // self.request_count if self.request_count > 0 else 0
        }


# Convenience functions
async def create_anthropic_client(api_key: Optional[str] = None) -> AnthropicClient:
    """Create and initialize Anthropic client."""
    config = AnthropicConfig(api_key=api_key) if api_key else None
    return AnthropicClient(config)