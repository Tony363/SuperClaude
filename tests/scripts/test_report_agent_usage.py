"""Tests for scripts/report_agent_usage.py.

Note: report_agent_usage.py imports SuperClaude.Agents.usage_tracker which
may not exist. We test _build_registry_summary by importing it indirectly.
"""

import importlib
import sys
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def mock_usage_tracker():
    """Mock the usage_tracker module that may not exist."""
    mock_mod = MagicMock()
    sys.modules.setdefault("SuperClaude.Agents.usage_tracker", mock_mod)
    yield mock_mod


def _get_build_registry_summary():
    """Import _build_registry_summary with mocked dependencies."""
    if "scripts.report_agent_usage" in sys.modules:
        mod = sys.modules["scripts.report_agent_usage"]
    else:
        mod = importlib.import_module("scripts.report_agent_usage")
    return mod._build_registry_summary


class TestBuildRegistrySummary:
    """Tests for _build_registry_summary."""

    def test_core_agent(self):
        fn = _get_build_registry_summary()
        registry = MagicMock()
        registry.get_all_agents.return_value = ["architect"]
        registry.get_agent_config.return_value = {"is_core": True}

        result = fn(registry)
        assert "architect" in result
        assert result["architect"]["source"] == "core"

    def test_extended_agent(self):
        fn = _get_build_registry_summary()
        registry = MagicMock()
        registry.get_all_agents.return_value = ["custom"]
        registry.get_agent_config.return_value = {"is_core": False}

        result = fn(registry)
        assert result["custom"]["source"] == "extended"

    def test_missing_config(self):
        fn = _get_build_registry_summary()
        registry = MagicMock()
        registry.get_all_agents.return_value = ["unknown"]
        registry.get_agent_config.return_value = None

        result = fn(registry)
        assert result["unknown"]["source"] == "extended"

    def test_multiple_agents(self):
        fn = _get_build_registry_summary()
        registry = MagicMock()
        registry.get_all_agents.return_value = ["a", "b", "c"]
        registry.get_agent_config.side_effect = [
            {"is_core": True},
            {"is_core": False},
            None,
        ]

        result = fn(registry)
        assert len(result) == 3


class TestReportAgentUsageMain:
    """Tests for main()."""

    def test_main_writes_report(self, monkeypatch, tmp_path):
        # Get the module
        if "scripts.report_agent_usage" in sys.modules:
            mod = sys.modules["scripts.report_agent_usage"]
        else:
            mod = importlib.import_module("scripts.report_agent_usage")

        output_path = tmp_path / "report.md"
        monkeypatch.setattr("sys.argv", ["prog", "--output", str(output_path)])

        # Mock AgentRegistry
        mock_registry_cls = MagicMock()
        mock_registry = MagicMock()
        mock_registry.get_all_agents.return_value = ["architect"]
        mock_registry.get_agent_config.return_value = {"is_core": True}
        mock_registry_cls.return_value = mock_registry

        monkeypatch.setattr(mod, "AgentRegistry", mock_registry_cls)

        # Mock usage_tracker.write_markdown_report
        mock_tracker = sys.modules["SuperClaude.Agents.usage_tracker"]
        mock_tracker.write_markdown_report.return_value = output_path

        mod.main()

        mock_registry.discover_agents.assert_called_once_with(force=True)
        mock_tracker.write_markdown_report.assert_called_once()
