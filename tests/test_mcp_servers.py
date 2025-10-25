"""
Smoke tests for MCP integrations.
"""

from pathlib import Path

import yaml

from SuperClaude.MCP import MCP_SERVERS, get_mcp_integration


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
