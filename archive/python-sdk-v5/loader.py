"""
Dynamic Agent Loader for SuperClaude Framework

This module provides on-demand agent loading with caching and
performance optimization.
"""

import json
import logging
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any

from . import usage_tracker
from .base import BaseAgent
from .registry import AgentRegistry


class AgentLoader:
    """
    Dynamic loader for agents with LRU caching.

    Provides on-demand loading of agents with caching to optimize
    performance and memory usage.
    """

    def __init__(
        self,
        registry: AgentRegistry | None = None,
        cache_size: int = 10,
        ttl_seconds: int = 3600,
    ):
        """
        Initialize the agent loader.

        Args:
            registry: Agent registry instance
            cache_size: Maximum number of agents to cache
            ttl_seconds: Time-to-live for cached agents in seconds
        """
        self.registry = registry or AgentRegistry()
        self.cache_size = cache_size
        self.ttl = ttl_seconds
        self.logger = logging.getLogger("agent.loader")

        # LRU cache implementation
        self._cache: OrderedDict[str, dict[str, Any]] = OrderedDict()

        # Load statistics
        self._stats = {
            "loads": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "evictions": 0,
            "total_load_time": 0.0,
        }

        # Ensure agents are discovered
        self.registry.discover_agents()

        try:
            self.registry.load_core_agent_classes()
        except Exception as exc:  # pragma: no cover - defensive guard
            self.logger.debug(f"Unable to load core agent classes: {exc}")

        # Load trigger configuration if available
        self.triggers = self._load_triggers()

    def load_agent(self, name: str, force_reload: bool = False) -> BaseAgent | None:
        """
        Load an agent by name.

        Args:
            name: Agent name
            force_reload: Force reload even if cached

        Returns:
            Agent instance or None
        """
        self._stats["loads"] += 1
        start_time = time.time()

        config = self.registry.get_agent_config(name) if self.registry else None
        source = "core" if config and config.get("is_core") else "extended"

        # Check cache first
        if not force_reload and name in self._cache:
            cache_entry = self._cache[name]

            # Check TTL
            if time.time() - cache_entry["timestamp"] < self.ttl:
                # Move to end (most recently used)
                self._cache.move_to_end(name)
                self._stats["cache_hits"] += 1
                self.logger.debug(f"Cache hit for agent: {name}")
                usage_tracker.record_load(name, source=source)

                load_time = time.time() - start_time
                self._stats["total_load_time"] += load_time

                return cache_entry["agent"]
            else:
                # Expired, remove from cache
                del self._cache[name]
                self.logger.debug(f"Cache expired for agent: {name}")

        # Cache miss - load from registry
        self._stats["cache_misses"] += 1
        self.logger.debug(f"Loading agent: {name}")

        agent = self.registry.get_agent(name)

        if agent:
            # Initialize agent
            if agent.initialize():
                # Add to cache
                self._add_to_cache(name, agent)
                usage_tracker.record_load(name, source=source)
            else:
                self.logger.warning(f"Failed to initialize agent: {name}")
                agent = None

        load_time = time.time() - start_time
        self._stats["total_load_time"] += load_time

        if agent:
            self.logger.info(f"Loaded agent {name} in {load_time:.3f}s")
        else:
            self.logger.error(f"Failed to load agent: {name}")

        return agent

    def _add_to_cache(self, name: str, agent: BaseAgent):
        """
        Add agent to cache with LRU eviction.

        Args:
            name: Agent name
            agent: Agent instance
        """
        # Check if cache is full
        if len(self._cache) >= self.cache_size:
            # Evict least recently used
            evicted_name = next(iter(self._cache))
            evicted_entry = self._cache.pop(evicted_name)

            # Clean up evicted agent
            evicted_agent = evicted_entry["agent"]
            evicted_agent.reset()

            self._stats["evictions"] += 1
            self.logger.debug(f"Evicted agent from cache: {evicted_name}")

        # Add new entry
        self._cache[name] = {"agent": agent, "timestamp": time.time()}
        self._cache.move_to_end(name)

    def preload_agents(self, agent_names: list[str]) -> int:
        """
        Preload multiple agents into cache.

        Args:
            agent_names: List of agent names to preload

        Returns:
            Number of agents successfully loaded
        """
        loaded = 0

        for name in agent_names:
            agent = self.load_agent(name)
            if agent:
                loaded += 1

        self.logger.info(f"Preloaded {loaded}/{len(agent_names)} agents")
        return loaded

    def load_by_trigger(self, trigger: str) -> BaseAgent | None:
        """
        Load agent based on trigger keyword.

        Args:
            trigger: Trigger keyword

        Returns:
            Agent instance or None
        """
        # Check trigger configuration
        if trigger in self.triggers:
            agent_name = self.triggers[trigger].get("agent")
            if agent_name:
                return self.load_agent(agent_name)

        # Fall back to searching by trigger
        for agent_name in self.registry.get_all_agents():
            config = self.registry.get_agent_config(agent_name)
            if config:
                triggers = config.get("triggers", [])
                if any(t.lower() == trigger.lower() for t in triggers):
                    return self.load_agent(agent_name)

        return None

    def _load_triggers(self) -> dict[str, Any]:
        """
        Load trigger configuration from TRIGGERS.json.

        Returns:
            Dictionary of trigger configurations
        """
        triggers_file = Path(__file__).parent / "TRIGGERS.json"

        if not triggers_file.exists():
            # Create default triggers file
            default_triggers = self._create_default_triggers()
            try:
                with open(triggers_file, "w") as f:
                    json.dump(default_triggers, f, indent=2)
                self.logger.info("Created default TRIGGERS.json")
            except Exception as e:
                self.logger.warning(f"Failed to create TRIGGERS.json: {e}")

            return default_triggers.get("triggers", {})

        try:
            with open(triggers_file) as f:
                data = json.load(f)
                return data.get("triggers", {})
        except Exception as e:
            self.logger.error(f"Failed to load TRIGGERS.json: {e}")
            return {}

    def _create_default_triggers(self) -> dict[str, Any]:
        """
        Create default trigger configuration.

        Returns:
            Default trigger configuration
        """
        return {
            "version": "1.0.0",
            "triggers": {
                "--delegate": {
                    "agent": "general-purpose",
                    "description": "Delegate to appropriate agent",
                },
                "debug": {
                    "agent": "root-cause-analyst",
                    "description": "Debug and analyze issues",
                },
                "refactor": {
                    "agent": "refactoring-expert",
                    "description": "Refactor and improve code",
                },
                "document": {
                    "agent": "technical-writer",
                    "description": "Create documentation",
                },
                "performance": {
                    "agent": "performance-engineer",
                    "description": "Optimize performance",
                },
                "test": {
                    "agent": "quality-engineer",
                    "description": "Test and validate",
                },
                "secure": {
                    "agent": "security-engineer",
                    "description": "Security analysis",
                },
                "architect": {
                    "agent": "system-architect",
                    "description": "System design",
                },
            },
            "thresholds": {"auto_load": 0.7, "min_confidence": 0.3},
        }

    def clear_cache(self):
        """Clear the agent cache."""
        for entry in self._cache.values():
            entry["agent"].reset()

        self._cache.clear()
        self.logger.info("Agent cache cleared")

    def get_cached_agents(self) -> list[str]:
        """
        Get list of currently cached agents.

        Returns:
            List of cached agent names
        """
        return list(self._cache.keys())

    def get_statistics(self) -> dict[str, Any]:
        """
        Get loader statistics.

        Returns:
            Dictionary of statistics
        """
        stats = self._stats.copy()

        # Calculate derived metrics
        if stats["loads"] > 0:
            stats["cache_hit_rate"] = stats["cache_hits"] / stats["loads"]
            stats["avg_load_time"] = stats["total_load_time"] / stats["loads"]
        else:
            stats["cache_hit_rate"] = 0.0
            stats["avg_load_time"] = 0.0

        stats["cache_size"] = len(self._cache)
        stats["max_cache_size"] = self.cache_size

        return stats

    def optimize_cache(self, access_patterns: list[str]):
        """
        Optimize cache based on access patterns.

        Args:
            access_patterns: List of agent names in access order
        """
        # Analyze patterns
        frequency = {}
        for name in access_patterns:
            frequency[name] = frequency.get(name, 0) + 1

        # Sort by frequency
        sorted_agents = sorted(frequency.items(), key=lambda x: x[1], reverse=True)

        # Preload most frequently used agents
        top_agents = [name for name, _ in sorted_agents[: self.cache_size]]
        self.preload_agents(top_agents)

        self.logger.info(f"Cache optimized for access patterns: {top_agents[:5]}")

    def __str__(self) -> str:
        """String representation."""
        return (
            f"AgentLoader(cache={len(self._cache)}/{self.cache_size}, "
            f"hit_rate={self.get_statistics()['cache_hit_rate']:.2%})"
        )
