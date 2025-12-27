"""Tests for telemetry factory.

These tests require the archived SDK to be properly installed.
Mark all tests with @pytest.mark.archived_sdk to skip in CI.
"""

import os
from unittest.mock import patch

import pytest

from SuperClaude.Telemetry.factory import create_telemetry
from SuperClaude.Telemetry.jsonl import JsonlTelemetryClient
from SuperClaude.Telemetry.noop import NoopTelemetryClient

# Mark all tests in this module as requiring archived SDK
pytestmark = pytest.mark.archived_sdk


class TestCreateTelemetryDefault:
    """Default behavior tests."""

    def test_creates_jsonl_client_by_default(self, tmp_path):
        """Default creation returns JsonlTelemetryClient."""
        # Clear any existing env var
        with patch.dict(os.environ, {}, clear=True):
            client = create_telemetry(metrics_dir=tmp_path)
            assert isinstance(client, JsonlTelemetryClient)


class TestCreateTelemetryEnvironment:
    """Environment-based selection tests."""

    @pytest.mark.parametrize("value", ["0", "false", "no", "off", "FALSE", "NO", "OFF"])
    def test_disabled_values_recognized(self, value):
        """'false', 'no', 'off', '0' all disable telemetry."""
        with patch.dict(os.environ, {"SUPERCLAUDE_TELEMETRY_ENABLED": value}):
            client = create_telemetry()
            assert isinstance(client, NoopTelemetryClient)

    def test_enabled_by_default_when_env_unset(self, tmp_path):
        """Telemetry is enabled when env var not set."""
        with patch.dict(os.environ, {}, clear=True):
            client = create_telemetry(metrics_dir=tmp_path)
            assert isinstance(client, JsonlTelemetryClient)

    @pytest.mark.parametrize("value", ["1", "true", "yes", "on", "TRUE", "YES"])
    def test_enabled_values_recognized(self, value, tmp_path):
        """Various truthy values enable telemetry."""
        with patch.dict(os.environ, {"SUPERCLAUDE_TELEMETRY_ENABLED": value}):
            client = create_telemetry(metrics_dir=tmp_path)
            assert isinstance(client, JsonlTelemetryClient)

    def test_metrics_dir_from_env(self, tmp_path):
        """SUPERCLAUDE_METRICS_DIR env var sets directory."""
        custom_dir = tmp_path / "custom"
        with patch.dict(os.environ, {"SUPERCLAUDE_METRICS_DIR": str(custom_dir)}, clear=True):
            client = create_telemetry()
            assert isinstance(client, JsonlTelemetryClient)
            assert client.metrics_dir == custom_dir


class TestCreateTelemetryExplicitParams:
    """Explicit parameter tests."""

    def test_enabled_false_returns_noop(self):
        """enabled=False returns NoopTelemetryClient."""
        client = create_telemetry(enabled=False)
        assert isinstance(client, NoopTelemetryClient)

    def test_enabled_true_returns_jsonl(self, tmp_path):
        """enabled=True returns JsonlTelemetryClient."""
        client = create_telemetry(enabled=True, metrics_dir=tmp_path)
        assert isinstance(client, JsonlTelemetryClient)

    def test_custom_metrics_dir_passed_to_client(self, tmp_path):
        """metrics_dir parameter is forwarded to client."""
        custom_dir = tmp_path / "my_metrics"
        client = create_telemetry(metrics_dir=custom_dir)
        assert isinstance(client, JsonlTelemetryClient)
        assert client.metrics_dir == custom_dir

    def test_custom_session_id_passed_to_client(self, tmp_path):
        """session_id parameter is forwarded to client."""
        client = create_telemetry(metrics_dir=tmp_path, session_id="test-session")
        assert isinstance(client, JsonlTelemetryClient)
        assert client.session_id == "test-session"

    def test_custom_buffer_size_passed_to_client(self, tmp_path):
        """buffer_size parameter is forwarded to client."""
        client = create_telemetry(metrics_dir=tmp_path, buffer_size=42)
        assert isinstance(client, JsonlTelemetryClient)
        assert client.buffer_size == 42

    def test_explicit_enabled_overrides_env(self, tmp_path):
        """Explicit enabled parameter overrides environment variable."""
        # Env says disabled, but explicit param says enabled
        with patch.dict(os.environ, {"SUPERCLAUDE_TELEMETRY_ENABLED": "0"}):
            client = create_telemetry(enabled=True, metrics_dir=tmp_path)
            assert isinstance(client, JsonlTelemetryClient)

        # Env says enabled (default), but explicit param says disabled
        with patch.dict(os.environ, {}, clear=True):
            client = create_telemetry(enabled=False)
            assert isinstance(client, NoopTelemetryClient)


class TestCreateTelemetryErrorHandling:
    """Error handling tests."""

    def test_falls_back_to_noop_on_error(self):
        """Returns NoopTelemetryClient if JsonlTelemetryClient init raises."""
        # Mock JsonlTelemetryClient to raise an exception during init
        with (
            patch(
                "SuperClaude.Telemetry.factory.JsonlTelemetryClient",
                side_effect=Exception("Simulated init failure"),
            ),
            patch.dict(os.environ, {}, clear=True),
        ):
            client = create_telemetry()
            # Should fall back to NoopTelemetryClient
            assert isinstance(client, NoopTelemetryClient)


class TestTelemetryClientTypeAlias:
    """Type alias tests."""

    def test_type_alias_covers_both_clients(self):
        """TelemetryClientType includes both client types."""
        # This is more of a static type check, but we can verify runtime behavior
        jsonl_client = JsonlTelemetryClient()
        noop_client = NoopTelemetryClient()

        # Both should be valid TelemetryClientType instances
        assert isinstance(jsonl_client, (JsonlTelemetryClient, NoopTelemetryClient))
        assert isinstance(noop_client, (JsonlTelemetryClient, NoopTelemetryClient))

        jsonl_client.close()
