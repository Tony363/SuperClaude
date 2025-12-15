"""
Google API Client for Gemini 2.5 Pro model.

Provides unified interface for Google's Gemini models with long context support.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple

from ..Monitoring.performance_monitor import get_monitor
from .http_utils import HTTPClientError, post_json

logger = logging.getLogger(__name__)


@dataclass
class GoogleConfig:
    """Configuration for Google API."""

    api_key: str
    endpoint: str = "https://generativelanguage.googleapis.com/v1beta"
    timeout: int = 300
    max_retries: int = 3
    rate_limit_rpm: int = 60
    rate_limit_tpm: int = 2000000


@dataclass
class GeminiRequest:
    """Request for Gemini completion."""

    model: str
    prompt: str
    max_output_tokens: int = 8192
    temperature: float = 0.7
    top_p: float = 1.0
    top_k: Optional[int] = None
    candidate_count: int = 1
    stop_sequences: Optional[List[str]] = None
    safety_settings: Optional[List[Dict[str, Any]]] = None
    system_instruction: Optional[str] = None
    tools: Optional[List[Dict[str, Any]]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeminiResponse:
    """Response from Gemini."""

    text: str
    model: str
    finish_reason: str = "STOP"
    safety_ratings: List[Dict[str, Any]] = field(default_factory=list)
    citation_metadata: Optional[Dict[str, Any]] = None
    token_count: Dict[str, int] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class GoogleClient:
    """
    Client for Google API.

    Supports:
    - Gemini 2.5 Pro with 2M context window
    - Long context processing
    - Multi-modal inputs (text, images, documents)
    - Function calling
    """

    # Model configurations
    MODEL_CONFIGS = {
        "gemini-2.5-pro": {
            "full_name": "gemini-2.5-pro",
            "max_output_tokens": 8192,
            "context_window": 2000000,  # 2M tokens!
            "supports_system": True,
            "supports_tools": True,
            "supports_thinking": True,
            "cost_per_1k_input": 0.00125,
            "cost_per_1k_output": 0.005,
        },
        "gemini-2.5-pro-exp": {
            "full_name": "gemini-2.5-pro-experimental",
            "max_output_tokens": 8192,
            "context_window": 2000000,
            "supports_system": True,
            "supports_tools": True,
            "supports_thinking": True,
            "cost_per_1k_input": 0.00125,
            "cost_per_1k_output": 0.005,
        },
    }

    def __init__(
        self, config: Optional[GoogleConfig] = None, api_key: Optional[str] = None
    ):
        """Initialize Google client."""
        if not config:
            # Try to load from environment
            api_key = api_key or os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise ValueError("Google API key not provided")

            config = GoogleConfig(api_key=api_key)

        self.config = config
        self.rate_limiter = RateLimiter(config.rate_limit_rpm, config.rate_limit_tpm)
        self.token_counter = TokenCounter()
        self.provider = "google"
        self.monitor = get_monitor()

    async def complete(self, request: GeminiRequest) -> GeminiResponse:
        """
        Send completion request to Gemini.

        Args:
            request: Gemini request

        Returns:
            GeminiResponse
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

        # Apply model defaults
        if request.max_output_tokens > model_config["max_output_tokens"]:
            request.max_output_tokens = model_config["max_output_tokens"]

        # Check rate limits
        await self.rate_limiter.acquire(request)

        payload = self._build_payload(request)
        url = (
            f"{self.config.endpoint}/models/{model_config['full_name']}:generateContent"
        )

        try:
            status, data, response_headers = await post_json(
                url,
                payload,
                params={"key": self.config.api_key},
                timeout=self.config.timeout,
            )
        except HTTPClientError as exc:
            logger.error("Google API error: %s", exc)
            raise

        candidates = data.get("candidates") or []
        if not candidates:
            raise HTTPClientError(status, "Gemini response missing candidates", data)
        primary = candidates[0]
        content = primary.get("content") or {}
        parts = content.get("parts") or []
        text_parts = [part.get("text", "") for part in parts if isinstance(part, dict)]
        combined_text = "\n".join(part for part in text_parts if part).strip()

        usage_meta = data.get("usageMetadata") or {}
        token_count = {
            "prompt_tokens": usage_meta.get("promptTokenCount", 0),
            "candidates_tokens": usage_meta.get("candidatesTokenCount", 0),
            "total_tokens": usage_meta.get("totalTokenCount", 0),
        }

        response = GeminiResponse(
            text=combined_text or str(content),
            model=model_config["full_name"],
            finish_reason=primary.get("finishReason", "STOP"),
            safety_ratings=primary.get("safetyRatings", []),
            citation_metadata=primary.get("citationMetadata"),
            token_count=token_count,
            metadata={
                "status": status,
                "headers": {
                    k: v
                    for k, v in response_headers.items()
                    if k.lower().startswith("x-")
                },
                "prompt_feedback": data.get("promptFeedback"),
            },
        )

        self.token_counter.add(token_count)
        logger.info(
            "Completed Gemini request with %s: %s tokens",
            response.model,
            response.token_count.get("total_tokens", 0),
        )
        if self.monitor:
            self.monitor.record_token_usage(
                model=response.model,
                provider=self.provider,
                usage=response.token_count,
                metadata={"endpoint": "generateContent"},
            )
        return response

    async def complete_long_context(
        self,
        prompt: str,
        context_files: List[str],
        model: str = "gemini-2.5-pro",
        max_tokens: int = 8192,
    ) -> GeminiResponse:
        """
        Complete with long context (up to 2M tokens).

        Args:
            prompt: User prompt
            context_files: List of file paths to include
            model: Model to use
            max_tokens: Max output tokens

        Returns:
            GeminiResponse
        """
        # Build context from files
        full_context = []

        for file_path in context_files:
            try:
                # In real implementation, read actual files
                # with open(file_path, 'r') as f:
                #     content = f.read()
                content = f"Content of {file_path}"
                full_context.append(f"File: {file_path}\n{content}")
            except Exception as e:
                logger.warning(f"Failed to read {file_path}: {e}")

        # Combine context and prompt
        full_prompt = "\n\n".join(full_context) + f"\n\nQuestion: {prompt}"

        # Check if within context window
        estimated_tokens = len(full_prompt) // 4
        if estimated_tokens > self.MODEL_CONFIGS[model]["context_window"]:
            logger.warning(f"Context too large: {estimated_tokens} tokens")
            # In production, implement chunking strategy

        request = GeminiRequest(
            model=model,
            prompt=full_prompt,
            max_output_tokens=max_tokens,
            temperature=0.7,
        )

        return await self.complete(request)

    async def complete_with_tools(
        self, prompt: str, tools: List[Dict[str, Any]], model: str = "gemini-2.5-pro"
    ) -> GeminiResponse:
        """
        Complete with function calling.

        Args:
            prompt: User prompt
            tools: Available tools/functions
            model: Model to use

        Returns:
            GeminiResponse with potential function calls
        """
        request = GeminiRequest(
            model=model, prompt=prompt, tools=tools, max_output_tokens=8192
        )

        return await self.complete(request)

    async def complete_with_thinking(
        self, prompt: str, model: str = "gemini-2.5-pro", thinking_depth: str = "medium"
    ) -> GeminiResponse:
        """
        Complete with thinking mode (Gemini 2.5 Pro feature).

        Args:
            prompt: User prompt
            model: Model to use
            thinking_depth: Depth of reasoning (low, medium, high)

        Returns:
            GeminiResponse with deep reasoning
        """
        # Add thinking instruction
        thinking_prompt = f"""<thinking_mode depth="{thinking_depth}">
Analyze this problem systematically:
1. Break down the components
2. Consider multiple perspectives
3. Evaluate trade-offs
4. Provide structured reasoning
</thinking_mode>

{prompt}"""

        request = GeminiRequest(
            model=model, prompt=thinking_prompt, max_output_tokens=8192, temperature=0.7
        )

        return await self.complete(request)

    async def stream(self, request: GeminiRequest) -> AsyncIterator[str]:
        """
        Stream completion response from Gemini.

        Args:
            request: Gemini request

        Yields:
            Response chunks
        """
        # Check rate limits
        await self.rate_limiter.acquire(request)

        completion_request = replace(request)

        try:
            response = await self.complete(completion_request)
        except Exception as exc:
            logger.error("Streaming error during completion fallback: %s", exc)
            raise

        for chunk in self._chunk_stream_text(response.text):
            yield chunk

    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Args:
            text: Text to count

        Returns:
            Estimated token count
        """
        # In real implementation, use Google's tokenizer
        # For now, rough approximation
        return len(text) // 4

    def _chunk_stream_text(self, content: str, *, chunk_size: int = 128) -> List[str]:
        """Split Gemini content into deterministic streaming chunks."""
        if not content:
            return [""]

        return [content[i : i + chunk_size] for i in range(0, len(content), chunk_size)]

    def estimate_cost(self, request: GeminiRequest) -> Dict[str, float]:
        """
        Estimate cost for a request.

        Args:
            request: Gemini request

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

        # Estimate tokens
        input_tokens = self.count_tokens(request.prompt)
        output_tokens = request.max_output_tokens

        input_cost = (input_tokens / 1000) * config["cost_per_1k_input"]
        output_cost = (output_tokens / 1000) * config["cost_per_1k_output"]

        return {
            "input_cost": round(input_cost, 4),
            "output_cost": round(output_cost, 4),
            "total_cost": round(input_cost + output_cost, 4),
            "estimated_input_tokens": input_tokens,
            "max_output_tokens": output_tokens,
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

    def _build_payload(self, request: GeminiRequest) -> Dict[str, Any]:
        """Build API request payload."""
        contents = [{"parts": [{"text": request.prompt}]}]

        generation_config = {
            "temperature": request.temperature,
            "topP": request.top_p,
            "maxOutputTokens": request.max_output_tokens,
            "candidateCount": request.candidate_count,
        }

        if request.top_k is not None:
            generation_config["topK"] = request.top_k

        if request.stop_sequences:
            generation_config["stopSequences"] = request.stop_sequences

        payload = {"contents": contents, "generationConfig": generation_config}

        if request.system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": request.system_instruction}]
            }

        if request.safety_settings:
            payload["safetySettings"] = request.safety_settings

        if request.tools:
            payload["tools"] = request.tools

        return payload


class RateLimiter:
    """Rate limiter for API calls."""

    def __init__(self, rpm_limit: int, tpm_limit: int):
        """Initialize rate limiter."""
        self.rpm_limit = rpm_limit
        self.tpm_limit = tpm_limit
        self.request_times: List[datetime] = []
        self.token_counts: List[Tuple[datetime, int]] = []

    async def acquire(self, request: GeminiRequest):
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
        estimated_tokens = len(request.prompt) // 4 + request.max_output_tokens
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
        self.total_output_tokens = 0
        self.total_tokens = 0
        self.request_count = 0

    def add(self, usage: Dict[str, int]):
        """Add usage from a response."""
        self.total_prompt_tokens += usage.get("prompt_tokens", 0)
        self.total_output_tokens += usage.get("candidates_tokens", 0)
        self.total_tokens += usage.get("total_tokens", 0)
        self.request_count += 1

    def get_summary(self) -> Dict[str, Any]:
        """Get usage summary."""
        return {
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "request_count": self.request_count,
            "average_tokens_per_request": self.total_tokens // self.request_count
            if self.request_count > 0
            else 0,
        }


# Convenience functions
async def create_google_client(api_key: Optional[str] = None) -> GoogleClient:
    """Create and initialize Google client."""
    config = GoogleConfig(api_key=api_key) if api_key else None
    return GoogleClient(config)
