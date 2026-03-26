"""Tests for .github/scripts/bedrock_helper.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add .github/scripts to path for import
sys.path.insert(0, str(Path(__file__).parent.parent.parent / ".github" / "scripts"))

from bedrock_helper import (
    BEDROCK_MODEL_MAP,
    ContentBlock,
    MessageResponse,
    Usage,
    create_message,
)


class TestUsage:
    """Tests for Usage dataclass."""

    def test_creation(self):
        usage = Usage(input_tokens=100, output_tokens=50)
        assert usage.input_tokens == 100
        assert usage.output_tokens == 50


class TestContentBlock:
    """Tests for ContentBlock dataclass."""

    def test_default_text(self):
        block = ContentBlock(type="text")
        assert block.text == ""

    def test_with_text(self):
        block = ContentBlock(type="text", text="hello")
        assert block.text == "hello"


class TestMessageResponse:
    """Tests for MessageResponse dataclass."""

    def test_default_empty(self):
        resp = MessageResponse()
        assert resp.content == []
        assert resp.usage.input_tokens == 0
        assert resp.usage.output_tokens == 0

    def test_with_content(self):
        blocks = [ContentBlock(type="text", text="hi")]
        resp = MessageResponse(content=blocks, usage=Usage(10, 20))
        assert len(resp.content) == 1
        assert resp.content[0].text == "hi"
        assert resp.usage.input_tokens == 10


class TestBedrockModelMap:
    """Tests for model ID mapping."""

    def test_opus_mapping_exists(self):
        assert "claude-opus-4-20250514" in BEDROCK_MODEL_MAP

    def test_haiku_mapping_exists(self):
        assert "claude-haiku-4-5-20251001" in BEDROCK_MODEL_MAP

    def test_bedrock_format(self):
        for anthropic_id, bedrock_id in BEDROCK_MODEL_MAP.items():
            assert bedrock_id.startswith("us.anthropic.")
            assert bedrock_id.endswith(":0")


class TestCreateMessage:
    """Tests for create_message dispatch logic."""

    def test_no_credentials_exits(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("AWS_BEARER_TOKEN_BEDROCK", raising=False)

        import pytest

        with pytest.raises(SystemExit):
            create_message(
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
                temperature=0.5,
                messages=[{"role": "user", "content": "test"}],
            )

    @patch("bedrock_helper._create_via_anthropic")
    def test_prefers_anthropic_api_key(self, mock_anthropic, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "test-token")

        mock_anthropic.return_value = MessageResponse()

        create_message(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            temperature=0.5,
            messages=[{"role": "user", "content": "test"}],
        )

        mock_anthropic.assert_called_once()

    @patch("bedrock_helper._create_via_bedrock")
    def test_falls_back_to_bedrock(self, mock_bedrock, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "test-token")

        mock_bedrock.return_value = MessageResponse()

        create_message(
            model="claude-haiku-4-5-20251001",
            max_tokens=100,
            temperature=0.5,
            messages=[{"role": "user", "content": "test"}],
        )

        mock_bedrock.assert_called_once()

    @patch("bedrock_helper._create_via_anthropic")
    def test_passes_thinking_param(self, mock_anthropic, monkeypatch):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        mock_anthropic.return_value = MessageResponse()

        thinking = {"type": "enabled", "budget_tokens": 5000}
        create_message(
            model="claude-opus-4-20250514",
            max_tokens=8000,
            temperature=0,
            messages=[{"role": "user", "content": "test"}],
            thinking=thinking,
        )

        call_kwargs = mock_anthropic.call_args[1]
        assert call_kwargs["thinking"] == thinking


class TestCreateViaAnthropic:
    """Tests for _create_via_anthropic."""

    def _make_mock_anthropic(self, blocks, in_tok=10, out_tok=20):
        """Create a mock anthropic module."""
        mock_response = MagicMock()
        mock_response.content = blocks
        mock_response.usage.input_tokens = in_tok
        mock_response.usage.output_tokens = out_tok

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        mock_mod = MagicMock()
        mock_mod.Anthropic.return_value = mock_client
        return mock_mod, mock_client

    def test_basic_call(self, monkeypatch):
        from bedrock_helper import _create_via_anthropic

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "Hello"

        mock_mod, mock_client = self._make_mock_anthropic([mock_block])

        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            result = _create_via_anthropic(
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
                temperature=0.5,
                messages=[{"role": "user", "content": "hi"}],
                thinking=None,
            )

        assert len(result.content) == 1
        assert result.content[0].text == "Hello"
        assert result.usage.input_tokens == 10

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["temperature"] == 0.5

    def test_with_thinking_forces_temp_1(self, monkeypatch):
        from bedrock_helper import _create_via_anthropic

        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = "response"
        mock_thinking = MagicMock()
        mock_thinking.type = "thinking"

        mock_mod, mock_client = self._make_mock_anthropic([mock_thinking, mock_block], 100, 50)

        with patch.dict("sys.modules", {"anthropic": mock_mod}):
            result = _create_via_anthropic(
                model="claude-opus-4-20250514",
                max_tokens=8000,
                temperature=0,
                messages=[{"role": "user", "content": "test"}],
                thinking={"type": "enabled", "budget_tokens": 5000},
            )

        assert len(result.content) == 1
        assert result.content[0].text == "response"

        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["temperature"] == 1
        assert "thinking" in call_kwargs


class TestCreateViaBedrock:
    """Tests for _create_via_bedrock."""

    def _make_mock_httpx(self, json_data, status_code=200):
        """Create a mock httpx module with a Client context manager."""
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json.return_value = json_data
        mock_response.text = "error" if status_code >= 400 else "ok"

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_response

        mock_httpx = MagicMock()
        mock_httpx.Client.return_value = mock_client
        return mock_httpx, mock_client

    def test_basic_call(self, monkeypatch):
        from bedrock_helper import _create_via_bedrock

        monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "test-token")
        monkeypatch.setenv("AWS_REGION", "us-west-2")

        mock_httpx, mock_client = self._make_mock_httpx(
            {
                "content": [{"type": "text", "text": "Bedrock response"}],
                "usage": {"input_tokens": 50, "output_tokens": 30},
            }
        )

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            result = _create_via_bedrock(
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
                temperature=0.5,
                messages=[{"role": "user", "content": "test"}],
                thinking=None,
            )

        assert len(result.content) == 1
        assert result.content[0].text == "Bedrock response"
        assert result.usage.input_tokens == 50

        url = mock_client.post.call_args[0][0]
        assert "us-west-2" in url

    def test_with_thinking_forces_temp_1(self, monkeypatch):
        from bedrock_helper import _create_via_bedrock

        monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "test-token")
        monkeypatch.setenv("AWS_REGION", "us-east-1")

        mock_httpx, mock_client = self._make_mock_httpx(
            {
                "content": [{"type": "text", "text": "ok"}],
                "usage": {"input_tokens": 100, "output_tokens": 50},
            }
        )

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            _create_via_bedrock(
                model="claude-opus-4-20250514",
                max_tokens=8000,
                temperature=0,
                messages=[{"role": "user", "content": "test"}],
                thinking={"type": "enabled", "budget_tokens": 5000},
            )

        call_kwargs = mock_client.post.call_args[1]
        body = call_kwargs["json"]
        assert body["temperature"] == 1
        assert body["thinking"] == {"type": "enabled", "budget_tokens": 5000}

    def test_api_error_raises(self, monkeypatch):
        from bedrock_helper import _create_via_bedrock

        monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "test-token")
        monkeypatch.setenv("AWS_REGION", "us-east-1")

        mock_httpx, _ = self._make_mock_httpx({}, status_code=500)

        import pytest

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            with pytest.raises(RuntimeError, match="Bedrock API error"):
                _create_via_bedrock(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=100,
                    temperature=0.5,
                    messages=[{"role": "user", "content": "test"}],
                    thinking=None,
                )

    def test_model_mapping(self, monkeypatch):
        from bedrock_helper import _create_via_bedrock

        monkeypatch.setenv("AWS_BEARER_TOKEN_BEDROCK", "test-token")
        monkeypatch.setenv("AWS_REGION", "us-east-1")

        mock_httpx, mock_client = self._make_mock_httpx(
            {
                "content": [],
                "usage": {"input_tokens": 0, "output_tokens": 0},
            }
        )

        with patch.dict("sys.modules", {"httpx": mock_httpx}):
            _create_via_bedrock(
                model="claude-haiku-4-5-20251001",
                max_tokens=100,
                temperature=0.5,
                messages=[{"role": "user", "content": "test"}],
                thinking=None,
            )

        url = mock_client.post.call_args[0][0]
        assert "us.anthropic.claude-haiku" in url
