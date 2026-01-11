"""
Agent Registry for SuperClaude Framework.

Updated to work with the v7 tiered architecture:
- agents/core/     - 16 primary agents
- agents/traits/   - 8 composable modifiers
- agents/extensions/ - 7 domain specialists

This is a standalone implementation that doesn't depend on the archived SDK.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Optional

import yaml


# Find the SuperClaude root (contains CLAUDE.md)
def _find_superclaude_root() -> Path:
    """Find SuperClaude root by searching upward for CLAUDE.md."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists():
            return parent
    # Fallback
    return Path(__file__).parent.parent.parent


SUPERCLAUDE_ROOT = _find_superclaude_root()
AGENTS_DIR = SUPERCLAUDE_ROOT / "agents"


class AgentMarkdownParser:
    """Parser for agent markdown files with YAML frontmatter."""

    def parse_file(self, filepath: Path) -> Optional[dict[str, Any]]:
        """
        Parse a markdown file and extract frontmatter.

        Args:
            filepath: Path to the markdown file

        Returns:
            Dictionary of frontmatter data or None if parsing fails
        """
        try:
            content = filepath.read_text(encoding="utf-8")
            return self._extract_frontmatter(content)
        except Exception:
            return None

    def _extract_frontmatter(self, content: str) -> Optional[dict[str, Any]]:
        """Extract YAML frontmatter from markdown content."""
        if not content.startswith("---"):
            return None

        end_match = re.search(r"\n---\s*\n", content[3:])
        if not end_match:
            return None

        yaml_content = content[3:end_match.start() + 3]

        try:
            frontmatter = yaml.safe_load(yaml_content)
            if isinstance(frontmatter, dict):
                return frontmatter
            return None
        except yaml.YAMLError:
            return None


class AgentRegistry:
    """
    Agent registry for v7 tiered architecture.

    Scans the new directory structure:
    - agents/core/      - Core agents (priority 1)
    - agents/traits/    - Composable traits (not directly selectable)
    - agents/extensions/ - Domain extensions (priority 2)
    """

    def __init__(self, agents_dir: Path | None = None):
        """
        Initialize the agent registry with tiered agent paths.

        Args:
            agents_dir: Base agents directory. Defaults to SuperClaude/agents/.
        """
        if agents_dir is None:
            agents_dir = AGENTS_DIR

        self.agents_dir = agents_dir
        self.logger = logging.getLogger("agent.registry.v7")

        # Agent storage
        self._agents: dict[str, dict[str, Any]] = {}  # name -> config
        self._traits: dict[str, dict[str, Any]] = {}  # trait_name -> config
        self._categories: dict[str, list[str]] = {}  # category -> [agent_names]
        self._tier_agents: dict[str, list[str]] = {  # tier -> [agent_names]
            "core": [],
            "trait": [],
            "extension": [],
        }

        # Parser for markdown files
        self.parser = AgentMarkdownParser()

        # Discovery flag
        self._discovered = False

    def discover_agents(self, force: bool = False) -> int:
        """
        Discover all agents from the tiered directory structure.

        Args:
            force: Force re-discovery even if already discovered

        Returns:
            Number of agents discovered
        """
        if self._discovered and not force:
            return len(self._agents)

        self._agents.clear()
        self._categories.clear()
        self._traits.clear()
        self._tier_agents = {"core": [], "trait": [], "extension": []}

        total = 0

        # Discover core agents
        core_dir = self.agents_dir / "core"
        if core_dir.exists():
            count = self._discover_tiered_agents(core_dir, tier="core", is_core=True)
            total += count
            self.logger.debug(f"Discovered {count} core agents")

        # Discover traits (stored separately, not directly selectable)
        traits_dir = self.agents_dir / "traits"
        if traits_dir.exists():
            count = self._discover_tiered_agents(traits_dir, tier="trait", is_core=False)
            total += count
            self.logger.debug(f"Discovered {count} traits")

        # Discover extensions
        extensions_dir = self.agents_dir / "extensions"
        if extensions_dir.exists():
            count = self._discover_tiered_agents(extensions_dir, tier="extension", is_core=False)
            total += count
            self.logger.debug(f"Discovered {count} extension agents")

        self._discovered = True

        self.logger.info(
            f"Discovered {total} agents: "
            f"{len(self._tier_agents['core'])} core, "
            f"{len(self._tier_agents['trait'])} traits, "
            f"{len(self._tier_agents['extension'])} extensions"
        )

        return total

    def _discover_tiered_agents(
        self, directory: Path, tier: str, is_core: bool = False
    ) -> int:
        """
        Discover agents from a tiered directory.

        Args:
            directory: Directory to search
            tier: Agent tier (core, trait, extension)
            is_core: Whether these are core agents

        Returns:
            Number of agents discovered
        """
        count = 0

        for md_file in directory.glob("*.md"):
            try:
                config = self.parser.parse_file(md_file)
                if not config:
                    continue

                # Get agent name from frontmatter or filename
                name = config.get("name", md_file.stem)

                # Add tier information
                config["tier"] = tier
                config["is_core"] = is_core
                config["file_path"] = str(md_file)

                # Set priority based on tier
                if "priority" not in config:
                    if tier == "core":
                        config["priority"] = 1
                    elif tier == "extension":
                        config["priority"] = 2
                    else:  # trait
                        config["priority"] = 0  # Traits don't participate in selection

                # Store agent
                if tier == "trait":
                    self._traits[name] = config
                else:
                    self._agents[name] = config

                # Track by tier
                self._tier_agents[tier].append(name)

                # Track by category
                category = config.get("category", "general")
                if category not in self._categories:
                    self._categories[category] = []
                self._categories[category].append(name)

                count += 1

            except Exception as e:
                self.logger.warning(f"Failed to parse {md_file}: {e}")

        return count

    def get_all_agents(self) -> list[str]:
        """
        Get all selectable agent names (excludes traits).

        Returns:
            List of agent names
        """
        return list(self._agents.keys())

    def get_all_traits(self) -> list[str]:
        """
        Get all trait names.

        Returns:
            List of trait names
        """
        return list(self._traits.keys())

    def get_agent(self, name: str) -> Optional[dict[str, Any]]:
        """
        Get an agent by name.

        Args:
            name: Agent name

        Returns:
            Agent configuration or None
        """
        return self._agents.get(name)

    def get_agent_config(self, name: str) -> Optional[dict[str, Any]]:
        """
        Get configuration for a specific agent.

        Args:
            name: Agent name

        Returns:
            Agent configuration dictionary or None
        """
        return self._agents.get(name)

    def get_trait_config(self, trait_name: str) -> Optional[dict[str, Any]]:
        """
        Get configuration for a specific trait.

        Args:
            trait_name: Name of the trait

        Returns:
            Trait configuration dictionary or None
        """
        return self._traits.get(trait_name)

    def get_agents_by_tier(self, tier: str) -> list[str]:
        """
        Get agent names for a specific tier.

        Args:
            tier: Tier name (core, trait, extension)

        Returns:
            List of agent names in that tier
        """
        return self._tier_agents.get(tier, [])

    def get_agents_by_category(self, category: str) -> list[str]:
        """
        Get agent names for a specific category.

        Args:
            category: Category name

        Returns:
            List of agent names in that category
        """
        return self._categories.get(category, [])

    def is_valid_trait(self, trait_name: str) -> bool:
        """
        Check if a trait name is valid.

        Args:
            trait_name: Name to check

        Returns:
            True if trait exists
        """
        return trait_name in self._traits


__all__ = [
    "AgentRegistry",
    "AgentMarkdownParser",
    "SUPERCLAUDE_ROOT",
    "AGENTS_DIR",
]
