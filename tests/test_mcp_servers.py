"""
Smoke tests and opt-in behaviour tests for MCP integrations.
"""

import logging
from pathlib import Path

import pytest
import yaml

from SuperClaude.Commands.executor import CommandContext, CommandExecutor
from SuperClaude.Commands.parser import CommandParser, ParsedCommand
from SuperClaude.Commands.registry import CommandMetadata, CommandRegistry
from SuperClaude.MCP import MCP_SERVERS, get_mcp_integration
from SuperClaude.MCP.rube_proxy import RubeProxyIntegration


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


def test_rube_disabled_without_opt_in(monkeypatch):
    """Rube connector refuses to initialize when opt-in flag is absent."""
    monkeypatch.delenv("SC_MCP_RUBE_ENABLED", raising=False)
    integration = RubeProxyIntegration(config={"enabled": False})
    assert integration.enabled is False

    with pytest.raises(RuntimeError):
        integration.initialize()


@pytest.mark.asyncio
async def test_rube_enabled_with_env(monkeypatch):
    """Rube connector initializes when the opt-in environment flag is set."""
    monkeypatch.setenv("SC_MCP_RUBE_ENABLED", "true")
    monkeypatch.setenv("SC_NETWORK_MODE", "online")

    integration = RubeProxyIntegration(config={"enabled": False})
    assert integration.enabled is True
    assert integration.initialize() is True
    assert await integration.initialize_session() is True

    with pytest.raises(RuntimeError):
        await integration.invoke("tool", {})


@pytest.mark.asyncio
async def test_executor_skips_disabled_rube(monkeypatch, caplog):
    """Executor logs and skips activation when Rube remains disabled."""
    monkeypatch.delenv("SC_MCP_RUBE_ENABLED", raising=False)
    monkeypatch.setenv("SC_NETWORK_MODE", "offline")

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
    """Executor activates Rube when opt-in flag is set and network allowed."""
    monkeypatch.setenv("SC_MCP_RUBE_ENABLED", "true")
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

    await executor._activate_mcp_servers(context)

    assert "rube" in executor.active_mcp_servers
    assert "rube" in context.mcp_servers
