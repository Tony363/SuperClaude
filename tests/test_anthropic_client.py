import pytest

from SuperClaude.APIClients import anthropic_client
from SuperClaude.APIClients.anthropic_client import (
    AnthropicClient,
    AnthropicConfig,
    ClaudeRequest,
    HTTPClientError,
)


@pytest.fixture(autouse=True)
def disable_monitor(monkeypatch):
    """Stub out the performance monitor to avoid filesystem side effects."""

    monkeypatch.setattr(anthropic_client, "get_monitor", lambda: None)


def build_client(**overrides) -> AnthropicClient:
    """Utility to create an Anthropic client with deterministic config."""

    config = AnthropicConfig(api_key="test-key", **overrides)
    return AnthropicClient(config=config)


def test_build_payload_injects_thinking_when_enabled():
    client = build_client(enable_thinking=True, thinking_budget_tokens=1234, thinking_type="enabled")
    request = ClaudeRequest(
        model="claude-opus-4.1",
        messages=[{"role": "user", "content": "hello"}],
    )

    payload = client._build_payload(request)

    assert payload["thinking"] == {"type": "enabled", "budget_tokens": 1234}


@pytest.mark.asyncio
async def test_complete_retries_when_thinking_required(monkeypatch):
    client = build_client(enable_thinking=False)
    request = ClaudeRequest(
        model="claude-opus-4.1",
        messages=[{"role": "user", "content": "hi"}],
    )

    call_payloads = []

    async def fake_post_json(url, payload, **kwargs):
        call_payloads.append(payload)
        if len(call_payloads) == 1:
            raise HTTPClientError(
                status=400,
                message="Bad Request",
                payload={
                    "error": {
                        "type": "invalid_request_error",
                        "message": "`clear_thinking_20251015` strategy requires `thinking` to be enabled",
                    }
                },
            )
        return (
            200,
            {
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
            {},
        )

    monkeypatch.setattr(anthropic_client, "post_json", fake_post_json)

    response = await client.complete(request)

    assert response.content == "ok"
    assert len(call_payloads) == 2
    assert "thinking" not in call_payloads[0]
    assert call_payloads[1]["thinking"]["type"] == client.config.thinking_type
