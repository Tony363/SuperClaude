"""
Agent Registry for SuperClaude Framework

This module provides agent discovery, registration, and management functionality.
It automatically discovers agents from markdown files and maintains a catalog
of available agents with their capabilities.
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
import importlib.util
import json

from .base import BaseAgent
from .parser import AgentMarkdownParser


class AgentRegistry:
    """
    Registry for discovering and managing SuperClaude agents.

    The registry automatically discovers agents from markdown files,
    maintains a catalog of available agents, and provides methods
    for agent lookup and instantiation.
    """

    def __init__(self, agents_dir: Optional[Path] = None):
        """
        Initialize the agent registry.

        Args:
            agents_dir: Directory containing agent definitions.
                       Defaults to SuperClaude/Agents directory.
        """
        if agents_dir is None:
            agents_dir = Path(__file__).parent

        self.agents_dir = agents_dir
        self.logger = logging.getLogger("agent.registry")

        # Agent storage
        self._agents: Dict[str, Dict[str, Any]] = {}  # name -> config
        self._agent_classes: Dict[str, Type[BaseAgent]] = {}  # name -> class
        self._categories: Dict[str, List[str]] = {}  # category -> [agent_names]

        # Parser for markdown files
        self.parser = AgentMarkdownParser()

        # Discovery flags
        self._discovered = False
        self._core_agents_loaded = False

    def discover_agents(self, force: bool = False) -> int:
        """
        Discover all agents from markdown files.

        Args:
            force: Force re-discovery even if already discovered

        Returns:
            Number of agents discovered
        """
        if self._discovered and not force:
            return len(self._agents)

        self._agents.clear()
        self._categories.clear()

        # Discover core agents (markdown files in main directory)
        core_count = self._discover_markdown_agents(self.agents_dir, is_core=True)

        # Discover extended agents (in Extended subdirectory)
        extended_dir = self.agents_dir / "Extended"
        extended_count = 0
        if extended_dir.exists():
            for subdir in extended_dir.iterdir():
                if subdir.is_dir():
                    extended_count += self._discover_markdown_agents(subdir, is_core=False)

        self._discovered = True
        total = core_count + extended_count

        self.logger.info(
            f"Discovered {total} agents: {core_count} core, {extended_count} extended"
        )

        return total

    def _discover_markdown_agents(self, directory: Path, is_core: bool = True) -> int:
        """
        Discover agents from markdown files in a directory.

        Args:
            directory: Directory to search for markdown files
            is_core: Whether these are core agents

        Returns:
            Number of agents discovered
        """
        count = 0

        for md_file in directory.glob("*.md"):
            try:
                # Parse the markdown file
                config = self.parser.parse(md_file)

                if config and 'name' in config:
                    # Add metadata
                    config['is_core'] = is_core
                    config['source_file'] = md_file

                    # Register the agent
                    self._register_agent(config)
                    count += 1

            except Exception as e:
                self.logger.warning(f"Failed to parse agent file {md_file}: {e}")

        return count

    def _register_agent(self, config: Dict[str, Any]):
        """
        Register an agent configuration.

        Args:
            config: Agent configuration dictionary
        """
        name = config['name']
        category = config.get('category', 'general')

        # Store configuration
        self._agents[name] = config

        # Update category index
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(name)

        self.logger.debug(f"Registered agent: {name} (category: {category})")

    def load_core_agent_classes(self) -> bool:
        """
        Load Python implementation classes for core agents.

        Returns:
            True if core agents loaded successfully
        """
        if self._core_agents_loaded:
            return True

        core_dir = self.agents_dir / "core"
        if not core_dir.exists():
            self.logger.warning(f"Core agents directory not found: {core_dir}")
            return False

        # Map of agent names to module names
        core_agent_modules = {
            'general-purpose': 'general_purpose',
            'root-cause-analyst': 'root_cause',
            'refactoring-expert': 'refactoring',
            'technical-writer': 'technical_writer',
            'performance-engineer': 'performance'
        }

        loaded = 0
        for agent_name, module_name in core_agent_modules.items():
            module_path = core_dir / f"{module_name}.py"

            if module_path.exists():
                try:
                    # Load the module
                    spec = importlib.util.spec_from_file_location(
                        f"SuperClaude.Agents.core.{module_name}",
                        module_path
                    )
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        # Find the agent class
                        class_name = self._get_class_name(agent_name)
                        if hasattr(module, class_name):
                            agent_class = getattr(module, class_name)
                            self._agent_classes[agent_name] = agent_class
                            loaded += 1
                            self.logger.debug(f"Loaded class for {agent_name}")

                except Exception as e:
                    self.logger.error(f"Failed to load {agent_name}: {e}")

        self._core_agents_loaded = loaded > 0
        self.logger.info(f"Loaded {loaded}/{len(core_agent_modules)} core agent classes")

        return self._core_agents_loaded

    def _get_class_name(self, agent_name: str) -> str:
        """
        Convert agent name to class name.

        Args:
            agent_name: Agent name (e.g., 'root-cause-analyst')

        Returns:
            Class name (e.g., 'RootCauseAnalyst')
        """
        parts = agent_name.split('-')
        return ''.join(word.capitalize() for word in parts)

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """
        Get an agent instance by name.

        Args:
            name: Agent name

        Returns:
            Agent instance or None if not found
        """
        if not self._discovered:
            self.discover_agents()

        if name not in self._agents:
            self.logger.warning(f"Agent not found: {name}")
            return None

        config = self._agents[name]

        # Try to get Python implementation
        if name in self._agent_classes:
            agent_class = self._agent_classes[name]
            return agent_class(config)

        # Fallback to generic agent with markdown config
        from .generic import GenericMarkdownAgent
        return GenericMarkdownAgent(config)

    def get_all_agents(self) -> List[str]:
        """
        Get list of all available agent names.

        Returns:
            List of agent names
        """
        if not self._discovered:
            self.discover_agents()

        return list(self._agents.keys())

    def list_agents(self, category: str = None) -> List[str]:
        """
        List all available agent names, optionally filtered by category.

        Args:
            category: Optional category to filter by

        Returns:
            List of agent names
        """
        if not self._discovered:
            self.discover_agents()

        if category:
            return self.get_agents_by_category(category)
        return self.get_all_agents()

    def get_agents_by_category(self, category: str) -> List[str]:
        """
        Get agents in a specific category.

        Args:
            category: Category name

        Returns:
            List of agent names in the category
        """
        if not self._discovered:
            self.discover_agents()

        return self._categories.get(category, [])

    def get_categories(self) -> List[str]:
        """
        Get all available categories.

        Returns:
            List of category names
        """
        if not self._discovered:
            self.discover_agents()

        return list(self._categories.keys())

    def get_agent_config(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get agent configuration by name.

        Args:
            name: Agent name

        Returns:
            Agent configuration dictionary or None
        """
        if not self._discovered:
            self.discover_agents()

        return self._agents.get(name)

    def search_agents(self, query: str) -> List[str]:
        """
        Search for agents by keyword.

        Args:
            query: Search query

        Returns:
            List of matching agent names
        """
        if not self._discovered:
            self.discover_agents()

        query_lower = query.lower()
        matches = []

        for name, config in self._agents.items():
            # Search in name
            if query_lower in name.lower():
                matches.append(name)
                continue

            # Search in description
            if query_lower in config.get('description', '').lower():
                matches.append(name)
                continue

            # Search in triggers
            for trigger in config.get('triggers', []):
                if query_lower in trigger.lower():
                    matches.append(name)
                    break

        return matches

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dictionary with registry statistics
        """
        if not self._discovered:
            self.discover_agents()

        core_agents = [n for n, c in self._agents.items() if c.get('is_core', False)]
        extended_agents = [n for n, c in self._agents.items() if not c.get('is_core', False)]

        return {
            'total_agents': len(self._agents),
            'core_agents': len(core_agents),
            'extended_agents': len(extended_agents),
            'categories': len(self._categories),
            'loaded_classes': len(self._agent_classes),
            'category_distribution': {
                cat: len(agents) for cat, agents in self._categories.items()
            }
        }

    def export_catalog(self, output_path: Optional[Path] = None) -> Path:
        """
        Export agent catalog to JSON file.

        Args:
            output_path: Output file path

        Returns:
            Path to exported file
        """
        if not self._discovered:
            self.discover_agents()

        if output_path is None:
            output_path = Path("agent_catalog.json")

        catalog = {
            'agents': {
                name: {
                    'description': config.get('description', ''),
                    'category': config.get('category', 'general'),
                    'tools': config.get('tools', []),
                    'triggers': config.get('triggers', []),
                    'is_core': config.get('is_core', False)
                }
                for name, config in self._agents.items()
            },
            'statistics': self.get_statistics()
        }

        with open(output_path, 'w') as f:
            json.dump(catalog, f, indent=2)

        self.logger.info(f"Exported agent catalog to {output_path}")
        return output_path