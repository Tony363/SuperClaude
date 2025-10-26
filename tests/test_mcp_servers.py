"""
Smoke tests and behaviour checks for MCP integrations.
"""

import logging
from pathlib import Path

import pytest
import yaml

from SuperClaude.Commands.executor import CommandContext, CommandExecutor
from SuperClaude.Commands.parser import CommandParser, ParsedCommand
from SuperClaude.Commands.registry import CommandMetadata, CommandRegistry
from SuperClaude.MCP import MCP_SERVERS, get_mcp_integration
from SuperClaude.MCP.rube_integration import RubeIntegration


def _project_root() -> Path:
    return Path(__file__).parent.parent


def test_all_mcp_servers_can_be_instantiated():
    """Ensure every server listed in the public configuration activates."""
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
    monkeypatch.delenv("SC_RUBE_MODE", raising=False)
    monkeypatch.delenv("SC_RUBE_API_KEY", raising=False)

    integration = RubeIntegration()
    integration.initialize()

    with pytest.raises(RuntimeError):
        await integration.initialize_session()
