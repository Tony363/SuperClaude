"""
MorphLLM MCP Integration (offline stub).

Provides a deterministic, config-driven interface so commands referencing the
`morphllm` MCP server can activate without network access. The stub reads a
static catalogue of transformation recipes and returns predictable responses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class MorphRecipe:
    """Describes a code transformation recipe."""

    name: str
    summary: str
    operations: List[str]
    confidence: float
    estimated_tokens: int


class MorphLLMIntegration:
    """
    Offline-compatible MorphLLM integration.

    The real MorphLLM server performs sophisticated bulk refactors. This stub
    provides curated recipes that mimic the interface so workflows and tests
    can rely on deterministic behaviour.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        config_path: Optional[str] = None,
    ) -> None:
        self._config = config or {}
        self._recipes = self._load_catalog(config_path or self._config.get("catalog_path"))

    def _load_catalog(self, override_path: Optional[str]) -> Dict[str, MorphRecipe]:
        """Load recipe definitions from disk or fall back to embedded defaults."""
        if override_path:
            path = Path(override_path)
            if path.exists():
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    return {
                        key: MorphRecipe(**value)
                        for key, value in data.items()
                    }
                except Exception:
                    pass  # fall back to defaults if parsing fails

        default_catalog = Path(__file__).resolve().parent.parent / "configs" / "morphllm.json"
        if default_catalog.exists():
            try:
                data = json.loads(default_catalog.read_text(encoding="utf-8"))
                return {
                    key: MorphRecipe(**value)
                    for key, value in data.items()
                }
            except Exception:
                pass

        # Embedded defaults as last resort.
        return {
            "safe-refactor": MorphRecipe(
                name="Safe Refactor Skeleton",
                summary="Outlines steps for refactoring without behavioural drift.",
                operations=[
                    "Snapshot existing behaviour with tests or recorded outputs.",
                    "Apply small, isolated transformations.",
                    "Run fast feedback checks after each change.",
                    "Summarise diffs and next actions.",
                ],
                confidence=0.82,
                estimated_tokens=900,
            )
        }

    def list_recipes(self) -> List[str]:
        """Return available recipe identifiers."""
        return sorted(self._recipes.keys())

    def get_recipe(self, recipe_id: str) -> Optional[MorphRecipe]:
        """Retrieve a single recipe by identifier."""
        return self._recipes.get(recipe_id)

    async def plan_transformation(
        self,
        scope: str,
        objectives: List[str],
        recipe: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Produce a deterministic transformation plan.

        Args:
            scope: Human-readable scope (e.g., file path or subsystem).
            objectives: Desired improvements.
            recipe: Optional recipe identifier.
        """
        selected = self._recipes.get(recipe or "safe-refactor")
        if not selected:
            # Select first available recipe to keep behaviour predictable.
            selected = next(iter(self._recipes.values()))

        return {
            "scope": scope,
            "objectives": objectives,
            "recipe": selected.name,
            "summary": selected.summary,
            "operations": selected.operations,
            "confidence": selected.confidence,
            "estimated_tokens": selected.estimated_tokens,
            "notes": [
                "Stub MorphLLM integration operating in offline mode.",
                "Upgrade to the full server to access automatic code application.",
            ],
        }

