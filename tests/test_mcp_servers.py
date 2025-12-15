"""
Smoke tests and behaviour checks for MCP integrations.
"""

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict

import pytest

try:
    import yaml
except ModuleNotFoundError:  # pragma: no cover - optional dev dependency
    yaml = None  # type: ignore

import SuperClaude.MCP as mcp_module
from SuperClaude.Commands.executor import CommandContext, CommandExecutor
from SuperClaude.Commands.parser import CommandParser, ParsedCommand
from SuperClaude.Commands.registry import CommandMetadata, CommandRegistry
from SuperClaude.MCP import MCP_SERVERS, get_mcp_integration
from SuperClaude.MCP.rube_integration import RubeIntegration
from SuperClaude.Quality.quality_scorer import QualityDimension


def _project_root() -> Path:
    return Path(__file__).parent.parent


def test_all_mcp_servers_can_be_instantiated():
    """Ensure every server listed in the public configuration activates."""
    if yaml is None:
        pytest.skip("PyYAML not installed")
    config_path = _project_root() / "SuperClaude" / "Config" / "mcp.yaml"
    config_data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    servers = config_data.get("servers", {})

    assert servers, "Expected MCP configuration to list servers"

    for name, cfg in servers.items():
        if not cfg.get("enabled", True):
            continue

        assert name in MCP_SERVERS, f"{name} missing from MCP registry"

        server_config = cfg.get("config")
        try:
            instance = get_mcp_integration(name, config=server_config)
        except TypeError:
            instance = get_mcp_integration(name)

        assert instance is not None, f"Failed to instantiate MCP server '{name}'"


def test_rube_disabled_via_config():
    """Rube integration refuses to initialize when disabled in config."""
    integration = RubeIntegration(config={"enabled": False})
    assert integration.enabled is False

    with pytest.raises(RuntimeError):
        integration.initialize()


@pytest.mark.asyncio
async def test_executor_skips_disabled_rube(monkeypatch, caplog):
    """Executor logs and skips activation when network mode blocks Rube."""
    monkeypatch.setenv("SC_NETWORK_MODE", "offline")
    monkeypatch.delenv("SC_RUBE_MODE", raising=False)

    registry = CommandRegistry()
    parser = CommandParser(registry=registry)
    executor = CommandExecutor(registry, parser)

    metadata = CommandMetadata(
        name="test",
        description="",
        category="test",
        complexity="standard",
        mcp_servers=["rube"],
    )
    context = CommandContext(
        command=ParsedCommand(name="test", raw_string="/sc:test"),
        metadata=metadata,
    )

    caplog.set_level(logging.INFO)
    await executor._activate_mcp_servers(context)

    assert "Skipping MCP server 'rube'" in caplog.text
    assert "rube" not in executor.active_mcp_servers
    assert "rube" not in context.mcp_servers


@pytest.mark.asyncio
async def test_executor_activates_rube_when_enabled(monkeypatch):
    """Executor activates Rube when network is allowed."""
    monkeypatch.setenv("SC_NETWORK_MODE", "online")
    monkeypatch.setenv("SC_RUBE_MODE", "dry-run")

    registry = CommandRegistry()
    parser = CommandParser(registry=registry)
    executor = CommandExecutor(registry, parser)

    metadata = CommandMetadata(
        name="test",
        description="",
        category="test",
        complexity="standard",
        mcp_servers=["rube"],
    )
    context = CommandContext(
        command=ParsedCommand(name="test", raw_string="/sc:test"),
        metadata=metadata,
    )

    await executor._activate_mcp_servers(context)

    assert "rube" in executor.active_mcp_servers
    assert "rube" in context.mcp_servers


def test_loop_flag_enables_zen_review(monkeypatch):
    """Explicit --loop requests should automatically enable zen-review."""
    registry = CommandRegistry()
    parser = CommandParser(registry=registry)
    executor = CommandExecutor(registry, parser)

    metadata = CommandMetadata(
        name="implement",
        description="",
        category="dev",
        complexity="standard",
        mcp_servers=[],
    )
    parsed = ParsedCommand(
        name="implement", raw_string="/sc:implement --loop", flags={"loop": True}
    )
    context = CommandContext(command=parsed, metadata=metadata)

    executor._apply_execution_flags(context)

    assert context.zen_review_enabled is True
    assert "zen" in context.metadata.mcp_servers
    assert context.results.get("zen_review_enabled") is True


@pytest.mark.asyncio
async def test_rube_dry_run_without_network(monkeypatch):
    """Rube integration falls back to dry-run when network is unavailable."""
    monkeypatch.setenv("SC_NETWORK_MODE", "offline")
    monkeypatch.delenv("SC_RUBE_MODE", raising=False)

    integration = RubeIntegration()
    integration.initialize()
    await integration.initialize_session()

    response = await integration.invoke("tool", {"foo": "bar"})
    assert response["status"] == "dry-run"


@pytest.mark.asyncio
async def test_rube_live_requires_api_key(monkeypatch):
    """Live mode should fail fast if API key is missing."""
    monkeypatch.setenv("SC_NETWORK_MODE", "online")
    monkeypatch.setenv("SC_RUBE_MODE", "live")
    monkeypatch.delenv("SC_RUBE_API_KEY", raising=False)

    monkeypatch.setattr(RubeIntegration, "_should_dry_run", lambda self: False)
    integration = RubeIntegration()
    integration.initialize()

    with pytest.raises(RuntimeError):
        await integration.initialize_session()


@pytest.mark.asyncio
async def test_activate_mcp_records_warning_on_failure(monkeypatch, caplog):
    monkeypatch.setenv("SC_NETWORK_MODE", "online")

    registry = CommandRegistry()
    parser = CommandParser(registry=registry)
    executor = CommandExecutor(registry, parser)

    metadata = CommandMetadata(
        name="test",
        description="",
        category="test",
        complexity="standard",
        mcp_servers=["rube"],
    )
    context = CommandContext(
        command=ParsedCommand(name="test", raw_string="/sc:test"),
        metadata=metadata,
    )

    caplog.set_level(logging.WARNING, logger="SuperClaude.Commands.executor")

    def _failing_get(name, config=None):
        raise RuntimeError("boom")

    monkeypatch.setattr(mcp_module, "get_mcp_integration", _failing_get)
    from SuperClaude.Commands import executor as executor_module

    monkeypatch.setattr(executor_module, "get_mcp_integration", _failing_get)
    monkeypatch.setattr(executor_module.os.path, "exists", lambda path: False)

    await executor._activate_mcp_servers(context)

    assert "rube" not in executor.active_mcp_servers
    assert any(
        "Skipping MCP server 'rube'" in record.message for record in caplog.records
    )


@pytest.mark.asyncio
async def test_run_zen_reviews_attaches_results(monkeypatch):
    """Deferred zen-review targets should populate executor results."""
    registry = CommandRegistry()
    parser = CommandParser(registry=registry)
    executor = CommandExecutor(registry, parser)

    metadata = CommandMetadata(
        name="implement",
        description="",
        category="dev",
        complexity="standard",
        mcp_servers=["zen"],
    )
    parsed = ParsedCommand(
        name="implement", raw_string="/sc:implement --loop", flags={"loop": True}
    )
    context = CommandContext(command=parsed, metadata=metadata)
    context.zen_review_enabled = True
    context.results["zen_review_targets"] = [
        {"iteration": 1, "files": ["foo.py"], "diff": "diff data"}
    ]

    class _FakeZen:
        async def review_code(self, diff, *, files, model, metadata):
            assert diff == "diff data"
            return {"score": 95, "summary": "looks good", "issues": []}

    executor.active_mcp_servers["zen"] = {"instance": _FakeZen()}

    output: Dict[str, Any] = {}
    await executor._run_zen_reviews(context, output)

    assert context.results.get("zen_reviews")
    assert output.get("zen_reviews") == context.results.get("zen_reviews")


def test_zen_primary_evaluator_overrides_metrics(tmp_path, monkeypatch):
    registry = CommandRegistry()
    parser = CommandParser(registry=registry)
    executor = CommandExecutor(registry, parser)
    executor.repo_root = tmp_path

    (tmp_path / ".git").mkdir()
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE)
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.PIPE,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.PIPE,
    )
    tracked = tmp_path / "sample.txt"
    tracked.write_text("initial", encoding="utf-8")
    subprocess.run(
        ["git", "add", "sample.txt"], cwd=tmp_path, check=True, stdout=subprocess.PIPE
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=tmp_path,
        check=True,
        stdout=subprocess.PIPE,
    )
    tracked.write_text("changed", encoding="utf-8")

    context = CommandContext(
        command=ParsedCommand(
            name="implement", raw_string="/sc:implement --loop", flags={"loop": True}
        ),
        metadata=CommandMetadata(
            name="implement", description="", category="dev", complexity="standard"
        ),
    )
    context.zen_review_enabled = True

    class _FakeZen:
        async def review_code(self, diff, *, files, model, metadata):
            assert "sample.txt" in diff
            return {
                "overall_score": 92,
                "summary": "Looks solid",
                "dimensions": {
                    "correctness": {
                        "score": 94,
                        "issues": ["Nit"],
                        "suggestions": ["Add test"],
                    },
                    "testability": {"score": 88, "issues": [], "suggestions": []},
                },
                "improvements": ["Add regression tests"],
            }

    executor.active_mcp_servers["zen"] = {"instance": _FakeZen()}

    monkeypatch.setattr(
        executor,
        "_collect_full_repo_diff",
        lambda: "diff --git a/sample.txt b/sample.txt",
    )
    monkeypatch.setattr(executor, "_list_changed_files", lambda: ["sample.txt"])

    cleanup = executor._enable_primary_zen_quality(context)
    assert cleanup is not None

    assessment = executor.quality_scorer.evaluate({}, {}, iteration=0)
    dimensions = {metric.dimension for metric in assessment.metrics}
    assert QualityDimension.CORRECTNESS in dimensions
    assert assessment.improvements_needed == ["Add regression tests"]

    cleanup()
    assert executor.quality_scorer.primary_evaluator is None
