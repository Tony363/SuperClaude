"""
Agent Selector for SuperClaude Framework.

Updated to work with the v7 tiered architecture.
Provides intelligent agent selection based on context, keywords, and task requirements.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .registry import AgentRegistry


@dataclass
class SelectionResult:
    """Result of agent selection with detailed breakdown."""

    agent_name: str
    """Name of the selected agent."""

    confidence: float
    """Confidence score (0.0 to 1.0)."""

    breakdown: dict[str, float] = field(default_factory=dict)
    """Score breakdown by component."""

    matched_criteria: list[str] = field(default_factory=list)
    """List of matched criteria."""

    alternatives: list[tuple[str, float]] = field(default_factory=list)
    """Alternative agents with scores."""

    traits_applied: list[str] = field(default_factory=list)
    """Traits applied to the selection."""

    agent_path: str = ""
    """Path to the agent file."""

    trait_paths: list[str] = field(default_factory=list)
    """Paths to trait files."""


# Trait conflict detection
TRAIT_CONFLICTS: dict[str, set[str]] = {
    "minimal-changes": {"rapid-prototype"},
    "rapid-prototype": {"minimal-changes"},
}

TRAIT_TENSIONS: dict[str, set[str]] = {
    "legacy-friendly": {"cloud-native"},
    "cloud-native": {"legacy-friendly"},
}


class AgentSelector:
    """
    Intelligent agent selector for context-based agent matching.

    Supports the v7 tiered architecture with composable traits.
    """

    def __init__(self, registry: AgentRegistry | None = None):
        """
        Initialize the agent selector.

        Args:
            registry: Agent registry instance. Creates new one if not provided.
        """
        self.registry = registry or AgentRegistry()
        self.logger = logging.getLogger("agent.selector")

        # Ensure agents are discovered
        self.registry.discover_agents()

        # Default agent name for fallback
        self.default_agent = "general-purpose"

        # Confidence thresholds
        self.min_confidence = 0.15  # Lowered to allow more agent matches
        self.high_confidence = 0.5

    def select_agent(
        self,
        context: Any,
        traits: list[str] | None = None,
        category_hint: str | None = None,
        exclude_agents: list[str] | None = None,
        top_n: int = 3,
    ) -> SelectionResult:
        """
        Select the best agent for the given context.

        Args:
            context: Task context (string or dict with 'task', 'description', 'files')
            traits: Optional traits to apply
            category_hint: Optional category preference
            exclude_agents: Optional list of agents to exclude
            top_n: Number of alternatives to include

        Returns:
            SelectionResult with selection details
        """
        if exclude_agents is None:
            exclude_agents = []
        if traits is None:
            traits = []

        # Score all agents
        scores = []

        for agent_name in self.registry.get_all_agents():
            if agent_name in exclude_agents:
                continue

            config = self.registry.get_agent_config(agent_name)
            if not config:
                continue

            score, breakdown, matched = self._calculate_score(
                context, config, category_hint
            )
            if score >= self.min_confidence:
                scores.append((agent_name, score, breakdown, matched, config))

        # Sort by score
        scores.sort(key=lambda x: x[1], reverse=True)

        # Fallback to default
        if not scores and self.default_agent not in exclude_agents:
            default_config = self.registry.get_agent_config(self.default_agent) or {}
            scores = [(
                self.default_agent,
                0.5,
                {"fallback": 0.5},
                ["default selection"],
                default_config
            )]

        if not scores:
            return SelectionResult(
                agent_name="general-purpose",
                confidence=0.0,
                matched_criteria=["no matching agent"],
                agent_path="agents/core/general-purpose.md",
            )

        # Get top selection
        top_name, top_score, top_breakdown, top_matched, top_config = scores[0]

        # Process traits
        valid_traits, invalid_traits, conflicts, tensions = self._process_traits(traits)

        # Build trait paths
        trait_paths = []
        for trait_name in valid_traits:
            trait_config = self.registry.get_trait_config(trait_name)
            if trait_config:
                trait_paths.append(trait_config.get("file_path", ""))

        # Determine confidence level
        if top_score >= 0.7:
            confidence_str = "excellent"
        elif top_score >= 0.5:
            confidence_str = "high"
        elif top_score >= 0.3:
            confidence_str = "medium"
        else:
            confidence_str = "low"

        result = SelectionResult(
            agent_name=top_name,
            confidence=top_score,
            breakdown=top_breakdown,
            matched_criteria=top_matched,
            alternatives=[(s[0], s[1]) for s in scores[1:top_n + 1]],
            traits_applied=valid_traits,
            agent_path=top_config.get("file_path", ""),
            trait_paths=trait_paths,
        )

        return result

    def _calculate_score(
        self,
        context: Any,
        config: dict[str, Any],
        category_hint: str | None = None
    ) -> tuple[float, dict[str, float], list[str]]:
        """Calculate match score with detailed breakdown."""
        score = 0.0
        breakdown = {}
        matched = []

        # Normalize context
        if isinstance(context, dict):
            context_str = (
                context.get("task", "") + " " +
                context.get("description", "") + " " +
                " ".join(context.get("files", []))
            )
        else:
            context_str = str(context)
        context_lower = context_str.lower()

        # 1. Trigger matching (35% weight)
        triggers = config.get("triggers", [])
        trigger_score = 0.0
        matched_triggers = []
        if triggers:
            for trigger in triggers:
                trigger_lower = trigger.lower()
                if trigger_lower in context_lower:
                    trigger_score += 1.0
                    matched_triggers.append(trigger)
                elif any(t in context_lower for t in trigger_lower.split()):
                    trigger_score += 0.3

            trigger_score = min(trigger_score / max(len(triggers), 1), 1.0)
            if matched_triggers:
                matched.append(f"triggers: {', '.join(matched_triggers[:3])}")

        breakdown["triggers"] = trigger_score * 0.35
        score += breakdown["triggers"]

        # 2. Category matching (25% weight)
        category = config.get("category", "")
        category_score = 0.0
        if category_hint and category.lower() == category_hint.lower():
            category_score = 1.0
            matched.append(f"category: {category}")
        elif category and category.lower() in context_lower:
            category_score = 0.7
            matched.append(f"category: {category}")

        breakdown["category"] = category_score * 0.25
        score += breakdown["category"]

        # 3. Task text matching (20% weight)
        name = config.get("name", "")
        task_score = 0.0
        name_parts = name.replace("-", " ").split()
        for part in name_parts:
            if len(part) > 2 and part.lower() in context_lower:
                task_score += 0.5
        task_score = min(task_score, 1.0)
        if task_score > 0:
            matched.append(f"name match: {name}")

        breakdown["task_match"] = task_score * 0.20
        score += breakdown["task_match"]

        # 4. File pattern matching (10% weight)
        file_patterns = config.get("file_patterns", [])
        file_score = 0.0
        files = context.get("files", []) if isinstance(context, dict) else []
        for pattern in file_patterns:
            pattern_lower = pattern.lower()
            for file in files:
                if pattern_lower in file.lower():
                    file_score = 1.0
                    matched.append(f"file: {pattern}")
                    break
            if file_score > 0:
                break

        breakdown["file_patterns"] = file_score * 0.10
        score += breakdown["file_patterns"]

        # 5. Priority bonus (10% weight)
        priority = config.get("priority", 2)
        priority_bonus = (4 - priority) / 3 * 0.10
        breakdown["priority"] = priority_bonus
        score += priority_bonus

        return min(score, 1.0), breakdown, matched

    def _process_traits(
        self, requested_traits: list[str]
    ) -> tuple[list[str], list[str], list[tuple[str, str]], list[tuple[str, str]]]:
        """
        Process and validate requested traits.

        Returns:
            Tuple of (valid_traits, invalid_traits, conflicts, tensions)
        """
        valid = []
        invalid = []

        # Validate traits exist
        for trait in requested_traits:
            if self.registry.is_valid_trait(trait):
                valid.append(trait)
            else:
                invalid.append(trait)

        # Check for conflicts
        conflicts = []
        tensions = []

        for i, trait1 in enumerate(valid):
            for trait2 in valid[i + 1:]:
                if trait1 in TRAIT_CONFLICTS and trait2 in TRAIT_CONFLICTS[trait1]:
                    conflicts.append((trait1, trait2))
                elif trait1 in TRAIT_TENSIONS and trait2 in TRAIT_TENSIONS[trait1]:
                    tensions.append((trait1, trait2))

        return valid, invalid, conflicts, tensions

    def find_best_match(
        self,
        context: str,
        category_hint: str | None = None,
        exclude_agents: list[str] | None = None,
    ) -> tuple[str | None, float]:
        """
        Find the best matching agent for context.

        Args:
            context: Task context
            category_hint: Optional category preference
            exclude_agents: Agents to exclude from selection

        Returns:
            Tuple of (agent_name, confidence_score)
        """
        result = self.select_agent(
            context,
            category_hint=category_hint,
            exclude_agents=exclude_agents,
        )
        return result.agent_name, result.confidence

    def get_agent_suggestions(
        self, context: str, top_n: int = 5
    ) -> list[tuple[str, float]]:
        """
        Get top N agent suggestions for context.

        Args:
            context: Task context
            top_n: Number of suggestions to return

        Returns:
            List of (agent_name, confidence) tuples
        """
        result = self.select_agent(context, top_n=top_n)
        suggestions = [(result.agent_name, result.confidence)]
        suggestions.extend(result.alternatives)
        return suggestions[:top_n]


__all__ = [
    "AgentSelector",
    "SelectionResult",
    "TRAIT_CONFLICTS",
    "TRAIT_TENSIONS",
]
