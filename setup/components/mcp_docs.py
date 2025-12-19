"""
MCP Documentation component for SuperClaude.

Installs documentation files that describe how to use native MCP tools
(mcp__rube__*, mcp__pal__*) with SuperClaude.
"""

from pathlib import Path
from typing import Any

from setup import __version__

from ..core.base import Component
from ..services.claude_md import CLAUDEMdService


class MCPDocsComponent(Component):
    """MCP documentation component - installs docs for native MCP tools."""

    def __init__(self, install_dir: Path | None = None):
        """Initialize MCP docs component."""
        self.selected_servers: list[str] = []

        # Map documentation categories to files
        self.server_docs_map = {
            "pal": "MCP_Pal.md",
            "rube": "MCP_Rube.md",
            "linkup": "MCP_LinkUp.md",
        }
        self.default_doc_servers = ["pal", "rube", "linkup"]

        super().__init__(install_dir, Path(""))

    def get_metadata(self) -> dict[str, str]:
        """Get component metadata."""
        return {
            "name": "mcp_docs",
            "version": __version__,
            "description": "Native MCP tools documentation and usage guides",
            "category": "documentation",
        }

    def set_selected_servers(self, selected_servers: list[str]) -> None:
        """Set which documentation files to install."""
        seen = set()
        filtered: list[str] = []
        for server in selected_servers:
            server_key = server.lower()
            if server_key in self.server_docs_map and server_key not in seen:
                filtered.append(server_key)
                seen.add(server_key)
        self.selected_servers = filtered

    def get_files_to_install(self) -> list[tuple[Path, Path]]:
        """Return list of documentation files to install."""
        source_dir = self._get_source_dir()
        files = []

        if source_dir and self.selected_servers:
            for server_name in self.selected_servers:
                if server_name in self.server_docs_map:
                    doc_file = self.server_docs_map[server_name]
                    source = source_dir / doc_file
                    target = self.install_dir / doc_file
                    if source.exists():
                        files.append((source, target))

        return files

    def _discover_component_files(self) -> list[str]:
        """Discover documentation files."""
        files = []
        if self.selected_servers:
            for server_name in self.selected_servers:
                if server_name in self.server_docs_map:
                    files.append(self.server_docs_map[server_name])
        return files

    def _get_source_dir(self) -> Path | None:
        """Get source directory for documentation files."""
        possible_paths = [
            Path(__file__).parent.parent.parent / "SuperClaude" / "MCP",
            Path.cwd() / "SuperClaude" / "MCP",
        ]
        for path in possible_paths:
            if path.exists():
                return path
        return None

    def validate_prerequisites(
        self, installSubPath: Path | None = None
    ) -> tuple[bool, list[str]]:
        """No prerequisites for documentation."""
        return True, []

    def get_metadata_modifications(self) -> dict[str, Any]:
        """Get metadata modifications."""
        return {
            "components": {
                "mcp_docs": {
                    "version": __version__,
                    "installed": True,
                    "docs_installed": self.selected_servers or self.default_doc_servers,
                }
            }
        }

    def install(self, config: dict = None, **kwargs) -> bool:
        """Install documentation files."""
        if not self.selected_servers:
            self.selected_servers = self.default_doc_servers

        files = self.get_files_to_install()
        if not files:
            self.logger.info("No documentation files to install")
            return True

        for source, target in files:
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
                self.logger.info(f"Installed: {target.name}")
            except Exception as e:
                self.logger.error(f"Failed to install {source.name}: {e}")
                return False

        # Update CLAUDE.md imports if service available
        try:
            service = CLAUDEMdService(self.install_dir)
            for _, target in files:
                service.add_import(f"@{target.name}")
        except Exception:
            # CLAUDEMdService may not be available; imports are optional
            pass

        return True

    def uninstall(self) -> bool:
        """Remove documentation files."""
        for doc_file in self.server_docs_map.values():
            target = self.install_dir / doc_file
            if target.exists():
                target.unlink()
        return True

    def validate_installation(self, installSubPath: Path | None = None) -> bool:
        """Verify documentation files exist."""
        if not self.selected_servers:
            return True
        for server_name in self.selected_servers:
            doc_file = self.server_docs_map.get(server_name)
            if doc_file:
                target = self.install_dir / doc_file
                if not target.exists():
                    return False
        return True
