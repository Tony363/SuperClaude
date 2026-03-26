#!/usr/bin/env python3
"""
Shared helper for Anthropic API / AWS Bedrock authentication.

Provides a unified `create_message()` function that works with either:
- Direct Anthropic API (ANTHROPIC_API_KEY)
- AWS Bedrock bearer token (AWS_BEARER_TOKEN_BEDROCK + AWS_REGION)

Used by scanner scripts: security-consensus.py, generate-type-hints.py, generate-docstrings.py
"""

import os
import sys
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

# Anthropic model ID -> Bedrock model ID
BEDROCK_MODEL_MAP: dict[str, str] = {
    "claude-opus-4-20250514": "us.anthropic.claude-opus-4-20250514-v1:0",
    "claude-haiku-4-5-20251001": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
}


@dataclass
class Usage:
    input_tokens: int
    output_tokens: int


@dataclass
class ContentBlock:
    type: str
    text: str = ""


@dataclass
class MessageResponse:
    """Minimal response object matching anthropic.Message interface used by scanner scripts."""

    content: list[ContentBlock] = field(default_factory=list)
    usage: Usage = field(default_factory=lambda: Usage(0, 0))


def create_message(
    *,
    model: str,
    max_tokens: int,
    temperature: float,
    messages: list[dict[str, Any]],
    thinking: dict[str, Any] | None = None,
) -> MessageResponse:
    """Create a message using either Anthropic API or Bedrock bearer token.

    Checks ANTHROPIC_API_KEY first, then falls back to AWS_BEARER_TOKEN_BEDROCK.
    """
    if os.getenv("ANTHROPIC_API_KEY"):
        return _create_via_anthropic(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
            thinking=thinking,
        )

    if os.getenv("AWS_BEARER_TOKEN_BEDROCK"):
        return _create_via_bedrock(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
            thinking=thinking,
        )

    print(
        "::error::No API credentials. Set ANTHROPIC_API_KEY or AWS_BEARER_TOKEN_BEDROCK + AWS_REGION",
        file=sys.stderr,
    )
    sys.exit(1)


def _create_via_anthropic(*, model, max_tokens, temperature, messages, thinking) -> MessageResponse:
    """Call Anthropic Messages API directly."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    kwargs: dict[str, Any] = dict(model=model, max_tokens=max_tokens, messages=messages)
    if thinking:
        kwargs["thinking"] = thinking
        # Anthropic API requires temperature=1 when thinking is enabled
        kwargs["temperature"] = 1
    else:
        kwargs["temperature"] = temperature

    response = client.messages.create(**kwargs)

    content_blocks = [
        ContentBlock(type="text", text=block.text)
        for block in response.content
        if block.type == "text"
    ]

    return MessageResponse(
        content=content_blocks,
        usage=Usage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        ),
    )


def _create_via_bedrock(*, model, max_tokens, temperature, messages, thinking) -> MessageResponse:
    """Call Bedrock InvokeModel with bearer token auth (Anthropic Messages format)."""
    import httpx

    token = os.getenv("AWS_BEARER_TOKEN_BEDROCK")
    region = os.getenv("AWS_REGION", "us-east-1")

    bedrock_model = BEDROCK_MODEL_MAP.get(model, model)
    encoded_model = quote(bedrock_model, safe="")

    url = f"https://bedrock-runtime.{region}.amazonaws.com/model/{encoded_model}/invoke"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    body: dict[str, Any] = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": messages,
    }

    if thinking:
        body["thinking"] = thinking
        # Bedrock also requires temperature=1 when thinking is enabled
        body["temperature"] = 1
    else:
        body["temperature"] = temperature

    with httpx.Client(timeout=300) as http_client:
        response = http_client.post(url, headers=headers, json=body)
        if response.status_code >= 400:
            raise RuntimeError(f"Bedrock API error: {response.status_code} - {response.text}")
        data = response.json()

    content_blocks = [
        ContentBlock(type="text", text=block["text"])
        for block in data.get("content", [])
        if block.get("type") == "text"
    ]

    usage_data = data.get("usage", {})
    return MessageResponse(
        content=content_blocks,
        usage=Usage(
            input_tokens=usage_data.get("input_tokens", 0),
            output_tokens=usage_data.get("output_tokens", 0),
        ),
    )
