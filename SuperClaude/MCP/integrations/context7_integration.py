"""
Context7 MCP Integration (offline stub).

Provides framework and library reference lookups sourced from a static,
lightweight catalog so commands can activate the integration without
network access.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Context7Reference:
    """Simple structure describing a documentation excerpt."""

    name: str
    summary: str
    snippet: str
    tags: List[str]


class Context7Integration:
    """
    Deterministic, catalog-backed Context7 implementation.

    The real Context7 MCP provides live framework documentation. This stub
    ships with curated highlights that cover common frameworks so that the
    command executor can reason about library-level guidance even while
    offline or in test environments.
    """

    def __init__(self, catalog_path: Optional[str] = None) -> None:
        self._catalog = self._load_catalog(catalog_path)

    def _load_catalog(self, catalog_path: Optional[str]) -> Dict[str, Context7Reference]:
        if catalog_path:
            path = Path(catalog_path)
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    return {
                        key: Context7Reference(**value)
                        for key, value in data.items()
                    }
                except Exception:
                    pass  # fall back to embedded catalog

        # Embedded seed catalog for popular frameworks.
        return {
            "react-component-patterns": Context7Reference(
                name="React Component Patterns",
                summary="Guidelines for functional components with hooks and accessibility.",
                snippet=(
                    "- Prefer function components with hooks.\n"
                    "- Keep state local; hoist when multiple consumers emerge.\n"
                    "- Expose props with explicit typing (`Props` interface).\n"
                    "- Provide aria attributes for interactive elements."
                ),
                tags=["react", "frontend", "accessibility"],
            ),
            "fastapi-routing": Context7Reference(
                name="FastAPI Routing Essentials",
                summary="Idiomatic FastAPI route declaration with dependency injection.",
                snippet=(
                    "@app.get('/items/{item_id}', response_model=Item)\n"
                    "async def read_item(item_id: int, repo: Repo = Depends(get_repo)):\n"
                    "    item = await repo.fetch(item_id)\n"
                    "    if not item:\n"
                    "        raise HTTPException(status_code=404, detail='Item not found')\n"
                    "    return item"
                ),
                tags=["python", "fastapi", "backend"],
            ),
            "terraform-best-practices": Context7Reference(
                name="Terraform Module Best Practices",
                summary="Structure your Terraform modules for reusability and safety.",
                snippet=(
                    "- Separate root modules per environment.\n"
                    "- Surface variables with descriptive types and defaults.\n"
                    "- Use `locals` to DRY repeated expressions.\n"
                    "- Enable backend state locking and version pinning."
                ),
                tags=["devops", "terraform", "infrastructure"],
            ),
        }

    def search(self, query: str, limit: int = 5) -> List[Context7Reference]:
        """Return catalog entries whose tags or names match the query."""
        if not query:
            return list(self._catalog.values())[:limit]

        query_lower = query.lower()
        matches: List[Context7Reference] = []
        for reference in self._catalog.values():
            haystack = [reference.name.lower()] + [tag.lower() for tag in reference.tags]
            if any(query_lower in value for value in haystack):
                matches.append(reference)
            elif query_lower in reference.summary.lower():
                matches.append(reference)

            if len(matches) >= limit:
                break

        return matches

    def get_reference(self, key: str) -> Optional[Context7Reference]:
        """Fetch a single reference by key."""
        return self._catalog.get(key)

    def list_topics(self) -> List[str]:
        """List all available catalog keys."""
        return sorted(self._catalog.keys())

    async def resolve_for_command(self, command_name: str) -> List[Context7Reference]:
        """
        Provide helpful references tailored to a command.

        Example: `/sc:implement` → include frontend/backend snippets.
        """
        command_lower = command_name.lower()
        if command_lower in {'implement', 'task', 'workflow'}:
            keys = [
                "react-component-patterns",
                "fastapi-routing",
                "terraform-best-practices",
            ]
        elif command_lower in {'analyze', 'troubleshoot'}:
            keys = ["fastapi-routing", "terraform-best-practices"]
        else:
            keys = list(self._catalog.keys())
        return [self._catalog[key] for key in keys if key in self._catalog]
