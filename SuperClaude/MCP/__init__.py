"""SuperClaude Framework MCP Server Integrations."""

from __future__ import annotations

from typing import Any, Dict, Mapping, Type

from .rube_integration import RubeIntegration, RubeInvocationError

__version__ = "6.0.0-alpha"

__all__ = [
    "RubeIntegration",
    "RubeInvocationError",
    "get_mcp_integration",
    "integration_import_errors",
]

_IMPORT_ERRORS: dict[str, ModuleNotFoundError] = {}

try:  # Optional dependency: PyYAML via ModelRouter
    from .zen_integration import (  # type: ignore[unused-import]
        ConsensusResult,
        ConsensusType,
        ModelConfig,
        ThinkingMode,
        ZenIntegration,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - depends on local extras
    if exc.name == "yaml":
        _IMPORT_ERRORS["zen"] = exc
    else:
        raise
else:
    __all__.extend(
        [
            "ConsensusResult",
            "ConsensusType",
            "ModelConfig",
            "ThinkingMode",
            "ZenIntegration",
        ]
    )

MCP_SERVERS: dict[str, type[Any]] = {
    "rube": RubeIntegration,
}

if "zen" not in _IMPORT_ERRORS:
    MCP_SERVERS["zen"] = ZenIntegration


def integration_import_errors() -> Mapping[str, ModuleNotFoundError]:
    """Return a mapping of server name → import error (if any)."""

    return dict(_IMPORT_ERRORS)


def get_mcp_integration(server_name: str, **kwargs):
    """Factory to create an MCP integration instance by server name."""
    cls = MCP_SERVERS.get(server_name)
    if not cls:
        available = ", ".join(sorted(MCP_SERVERS.keys()))
        raise ValueError(f"Unknown MCP server: {server_name}. Available: {available}")
    return cls(**kwargs)
