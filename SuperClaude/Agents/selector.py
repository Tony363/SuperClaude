"""
Agent Selector for SuperClaude Framework

This module provides intelligent agent selection based on context,
keywords, and task requirements.

SDK Integration:
    The select_for_sdk() method provides SDK-compatible agent selection
    with SDKAgentDefinition conversion and routing decisions.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .registry import AgentRegistry

if TYPE_CHECKING:
    from ..SDK.adapter import SDKAgentDefinition


@dataclass
class SDKSelectionResult:
    """Result of SDK-compatible agent selection.

    Contains the selected agent, SDK definition, confidence score,
    and routing decision information.
    """

    agent_name: str
    """Name of the selected agent."""

    confidence: float
    """Confidence score (0.0 to 1.0)."""

    use_sdk: bool
    """Whether to route through SDK (vs fallback to legacy execution)."""

    sdk_definition: SDKAgentDefinition | None = None
    """SDK-compatible agent definition, if SDK routing is recommended."""

    ranked_alternatives: list[tuple[str, float]] = field(default_factory=list)
    """Top 5 alternative agents with scores."""

    reason: str = ""
    """Human-readable explanation of selection decision."""

    capability_tier: str = "heuristic-wrapper"
    """Agent's capability tier (strategist, heuristic-wrapper, etc.)."""


class AgentSelector:
    """
    Intelligent agent selector for context-based agent matching.

    The selector analyzes task context and selects the most appropriate
    agent based on keywords, categories, and confidence scoring.
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
        self.min_confidence = 0.3
        self.high_confidence = 0.7

    def select_agent(
        self,
        context: Any,
        category_hint: str | None = None,
        exclude_agents: list[str] | None = None,
    ) -> list[tuple[str, float]]:
        """
        Select agents for the given context, ordered by relevance.

        Args:
            context: Task context or description (string or dict)
            category_hint: Optional category preference
            exclude_agents: Optional list of agents to exclude

        Returns:
            List of (agent_name, score) tuples, sorted by score
        """
        if exclude_agents is None:
            exclude_agents = []

        # Score all agents
        scores = []

        for agent_name in self.registry.get_all_agents():
            # Skip excluded agents
            if agent_name in exclude_agents:
                continue

            # Get agent configuration
            config = self.registry.get_agent_config(agent_name)
            if not config:
                continue

            # Calculate score
            score = self._calculate_agent_score(context, config, category_hint)
            if score >= self.min_confidence:
                scores.append((agent_name, score))

        # Sort by score (highest first)
        scores.sort(key=lambda x: x[1], reverse=True)

        if not scores and self.default_agent not in exclude_agents:
            # Fallback to default agent
            scores = [(self.default_agent, 0.5)]

        if scores:
            best_agent = scores[0][0]
            best_score = scores[0][1]
            self.logger.info(f"Top agent: {best_agent} (confidence: {best_score:.2f})")
        else:
            self.logger.warning("No suitable agent found for context")

        return scores

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
        if exclude_agents is None:
            exclude_agents = []

        # Score all agents
        scores = {}

        for agent_name in self.registry.get_all_agents():
            # Skip excluded agents
            if agent_name in exclude_agents:
                continue

            # Get agent configuration
            config = self.registry.get_agent_config(agent_name)
            if not config:
                continue

            # Calculate score
            score = self._calculate_agent_score(context, config, category_hint)
            scores[agent_name] = score

        # Find best match
        if not scores:
            # Fallback to default agent
            if self.default_agent not in exclude_agents:
                return self.default_agent, 0.5
            return None, 0.0

        # Sort by score
        sorted_agents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        best_agent, best_score = sorted_agents[0]

        # Log top matches
        self.logger.debug("Top agent matches:")
        for agent, score in sorted_agents[:5]:
            self.logger.debug(f"  {agent}: {score:.3f}")

        # Use default agent if confidence too low
        if best_score < self.min_confidence:
            if self.default_agent not in exclude_agents:
                self.logger.info(
                    f"Low confidence ({best_score:.2f}), using default agent"
                )
                return self.default_agent, 0.5

        return best_agent, best_score

    def _calculate_agent_score(
        self, context: Any, config: dict[str, Any], category_hint: str | None = None
    ) -> float:
        """
        Calculate confidence score for an agent.

        Args:
            context: Task context (string or dict)
            config: Agent configuration
            category_hint: Optional category preference

        Returns:
            Confidence score between 0 and 1
        """
        score = 0.0
        # Handle both string and dict context
        if isinstance(context, dict):
            context_str = (
                context.get("task", "")
                + " "
                + context.get("description", "")
                + " "
                + " ".join(context.get("files", []))
            )
        else:
            context_str = str(context)
        context_lower = context_str.lower()
        complex_context = self._is_complex_context(context_str)

        # 1. Trigger keyword matching (40% weight)
        trigger_score = self._score_triggers(context_lower, config.get("triggers", []))
        score += trigger_score * 0.4

        # 2. Category matching (20% weight)
        category_score = self._score_category(
            context_lower, config.get("category", ""), category_hint
        )
        score += category_score * 0.2

        # 3. Description relevance (15% weight)
        desc_score = self._score_description(
            context_lower, config.get("description", "")
        )
        score += desc_score * 0.15

        # 4. Tool relevance (15% weight)
        tool_score = self._score_tools(context_lower, config.get("tools", []))
        score += tool_score * 0.15

        # 5. Focus area matching (10% weight)
        focus_score = self._score_focus_areas(
            context_lower, config.get("focus_areas", {})
        )
        score += focus_score * 0.1

        # 6. Capability tier bias (±20%)
        tier_score = self._score_capability_tier(
            config.get("capability_tier", "wrapper"), complex_context
        )
        score += tier_score

        # 7. Boost for core agents (5% bonus)
        if config.get("is_core", False):
            score += 0.05

        # 8. Keyword-to-core-agent boost to ensure intuitive defaults
        score += self._keyword_core_boost(config.get("name", ""), context_lower)

        return min(score, 1.0)

    def _is_complex_context(self, context_str: str) -> bool:
        """Heuristic to detect complex, multi-domain requests."""
        lowered = context_str.lower()
        complexity_signals = [
            "architecture",
            "migration",
            "fullstack",
            "end-to-end",
            "multi-step",
            "integration",
            "refactor",
            "compliance",
            "staging",
            "rollout",
        ]
        signal_hits = sum(1 for token in complexity_signals if token in lowered)
        return len(lowered) > 160 or signal_hits >= 2

    def _score_capability_tier(self, tier: str, complex_context: bool) -> float:
        """Bias the match score towards strategist-tier agents for complex work."""
        tier_normalized = (tier or "wrapper").lower()
        base = 0.0
        if tier_normalized == "strategist":
            base = 0.12
        elif tier_normalized in {"heuristic-wrapper", "enhanced-wrapper"}:
            base = 0.05

        if complex_context:
            if tier_normalized == "strategist":
                base += 0.1
            else:
                base -= 0.1

        return base

    def _keyword_core_boost(self, agent_name: str, context_lower: str) -> float:
        """Apply small heuristic boosts to ensure intuitive core agent matches."""
        boosts = 0.0
        try:
            if agent_name == "root-cause-analyst":
                if any(
                    k in context_lower
                    for k in ["debug", "bug", "issue", "error", "problem", "crash"]
                ):
                    boosts += 0.5
            elif agent_name == "refactoring-expert":
                if any(
                    k in context_lower
                    for k in ["refactor", "clean up", "improve code", "restructure"]
                ):
                    boosts += 0.5
            elif agent_name == "technical-writer":
                if any(
                    k in context_lower
                    for k in ["write documentation", "docs", "documentation", "explain"]
                ):
                    boosts += 0.5
            elif agent_name == "performance-engineer":
                if any(
                    k in context_lower
                    for k in ["performance", "optimize", "slow", "speed up"]
                ):
                    boosts += 0.5
        except Exception as e:
            # Agent scoring calculation error; continue with default score
            self.logger.debug(f"Error calculating agent boost for {agent_name}: {e}")
        return boosts

    def _score_triggers(self, context: str, triggers: list[str]) -> float:
        """Score based on trigger keyword matches."""
        if not triggers:
            return 0.0

        matches = 0
        total_weight = 0

        for trigger in triggers:
            trigger_lower = trigger.lower()

            # Exact phrase match (higher weight)
            if trigger_lower in context:
                matches += 2
                total_weight += 2
            # Word boundary match
            elif re.search(r"\b" + re.escape(trigger_lower) + r"\b", context):
                matches += 1.5
                total_weight += 1.5
            # Partial match
            elif any(word in context for word in trigger_lower.split()):
                matches += 0.5
                total_weight += 0.5

        max_possible = len(triggers) * 2
        return matches / max_possible if max_possible > 0 else 0.0

    def _score_category(
        self, context: str, category: str, hint: str | None = None
    ) -> float:
        """Score based on category matching."""
        score = 0.0

        if hint and category.lower() == hint.lower():
            score = 1.0
        elif category:
            category_lower = category.lower()

            # Check for category mention in context
            if category_lower in context:
                score = 0.7
            # Check for related terms
            elif self._has_related_terms(context, category_lower):
                score = 0.4

        return score

    def _score_description(self, context: str, description: str) -> float:
        """Score based on description relevance."""
        if not description:
            return 0.0

        desc_lower = description.lower()

        # Extract key terms from description
        key_terms = re.findall(r"\b[a-z]{4,}\b", desc_lower)

        # Count matching terms
        matches = sum(1 for term in key_terms if term in context)

        return min(matches / max(len(key_terms), 1), 1.0)

    def _score_tools(self, context: str, tools: list[str]) -> float:
        """Score based on tool mentions."""
        if not tools:
            return 0.0

        matches = 0
        for tool in tools:
            tool_lower = tool.lower()
            if tool_lower in context:
                matches += 1

        return matches / len(tools)

    def _score_focus_areas(self, context: str, focus_areas: dict[str, str]) -> float:
        """Score based on focus area matching."""
        if not focus_areas:
            return 0.0

        total_score = 0.0

        for area, description in focus_areas.items():
            area_lower = area.lower()
            desc_lower = description.lower() if description else ""

            # Check area name
            if area_lower in context:
                total_score += 0.5

            # Check area description keywords
            if desc_lower:
                keywords = re.findall(r"\b[a-z]{4,}\b", desc_lower)[
                    :5
                ]  # Top 5 keywords
                for keyword in keywords:
                    if keyword in context:
                        total_score += 0.1

        return min(total_score / max(len(focus_areas), 1), 1.0)

    def _has_related_terms(self, context: str, category: str) -> bool:
        """Check if context has terms related to category."""
        # Define related terms for common categories
        related_terms = {
            "debugging": ["bug", "error", "issue", "problem", "fix", "debug"],
            "refactoring": ["refactor", "improve", "clean", "optimize", "restructure"],
            "documentation": ["document", "docs", "readme", "comment", "explain"],
            "testing": ["test", "validate", "verify", "check", "assert"],
            "performance": ["speed", "slow", "optimize", "performance", "efficient"],
            "security": ["secure", "vulnerability", "auth", "permission", "safety"],
            "architecture": [
                "design",
                "structure",
                "pattern",
                "architecture",
                "system",
            ],
            "analysis": ["analyze", "investigate", "examine", "review", "assess"],
        }

        if category in related_terms:
            return any(term in context for term in related_terms[category])

        return False

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
        scores = {}

        for agent_name in self.registry.get_all_agents():
            config = self.registry.get_agent_config(agent_name)
            if config:
                score = self._calculate_agent_score(context, config)
                if score > 0:
                    scores[agent_name] = score

        # Sort and return top N
        sorted_agents = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_agents[:top_n]

    def explain_selection(self, context: str, agent_name: str) -> dict[str, Any]:
        """
        Explain why an agent was selected.

        Args:
            context: Task context
            agent_name: Selected agent name

        Returns:
            Dictionary with scoring breakdown
        """
        config = self.registry.get_agent_config(agent_name)
        if not config:
            return {"error": "Agent not found"}

        context_lower = context.lower()

        explanation = {
            "agent": agent_name,
            "category": config.get("category", "general"),
            "total_score": self._calculate_agent_score(context, config),
            "breakdown": {
                "triggers": self._score_triggers(
                    context_lower, config.get("triggers", [])
                ),
                "category": self._score_category(
                    context_lower, config.get("category", "")
                ),
                "description": self._score_description(
                    context_lower, config.get("description", "")
                ),
                "tools": self._score_tools(context_lower, config.get("tools", [])),
                "focus_areas": self._score_focus_areas(
                    context_lower, config.get("focus_areas", {})
                ),
                "core_bonus": 0.05 if config.get("is_core", False) else 0.0,
            },
            "matched_triggers": [
                t for t in config.get("triggers", []) if t.lower() in context_lower
            ],
        }

        return explanation

    def select_for_sdk(
        self,
        context: Any,
        category_hint: str | None = None,
        exclude_agents: list[str] | None = None,
        min_confidence_for_sdk: float = 0.5,
    ) -> SDKSelectionResult:
        """
        Select agent with SDK-compatible output for Claude Agent SDK integration.

        This method extends select_agent() by:
        1. Converting the selected agent to SDKAgentDefinition format
        2. Making a routing decision (SDK vs legacy execution)
        3. Providing ranked alternatives for multi-agent scenarios

        Args:
            context: Task context (string or dict with 'task', 'description', 'files')
            category_hint: Optional category preference
            exclude_agents: Optional list of agents to exclude
            min_confidence_for_sdk: Minimum confidence to recommend SDK routing

        Returns:
            SDKSelectionResult with agent selection and SDK routing decision.

        Example:
            result = selector.select_for_sdk({"task": "Fix auth bug"})
            if result.use_sdk and result.sdk_definition:
                # Use Claude Agent SDK
                sdk_client.execute(result.sdk_definition, ...)
            else:
                # Fallback to legacy execution
                legacy_execute(result.agent_name, ...)
        """
        # Use existing selection logic
        scores = self.select_agent(context, category_hint, exclude_agents)

        if not scores:
            # No suitable agent found
            return SDKSelectionResult(
                agent_name=self.default_agent,
                confidence=0.0,
                use_sdk=False,
                reason="No suitable agent found, using default",
            )

        # Get top agent
        top_agent_name, top_score = scores[0]

        # Get agent config for tier info
        config = self.registry.get_agent_config(top_agent_name) or {}
        capability_tier = config.get("capability_tier", "heuristic-wrapper")

        # Determine if SDK routing is recommended
        use_sdk = top_score >= min_confidence_for_sdk

        # Build reason string
        if use_sdk:
            reason = f"Selected {top_agent_name} with confidence {top_score:.2f} (>= {min_confidence_for_sdk})"
        else:
            reason = f"Low confidence {top_score:.2f} (< {min_confidence_for_sdk}), recommend legacy execution"

        # Convert to SDK definition if SDK routing is recommended
        sdk_definition = None
        if use_sdk:
            try:
                sdk_definition = self._convert_to_sdk_definition(top_agent_name)
            except Exception as e:
                self.logger.warning(f"Failed to convert to SDK definition: {e}")
                use_sdk = False
                reason += f" (SDK conversion failed: {e})"

        return SDKSelectionResult(
            agent_name=top_agent_name,
            confidence=top_score,
            use_sdk=use_sdk,
            sdk_definition=sdk_definition,
            ranked_alternatives=scores[1:6],  # Top 5 alternatives
            reason=reason,
            capability_tier=capability_tier,
        )

    def _convert_to_sdk_definition(self, agent_name: str) -> SDKAgentDefinition | None:
        """
        Convert agent to SDK definition format.

        Args:
            agent_name: Name of agent to convert

        Returns:
            SDKAgentDefinition or None if conversion fails
        """
        # Import adapter lazily to avoid circular imports
        from ..SDK.adapter import AgentToSDKAdapter

        agent = self.registry.get_agent(agent_name)
        if not agent:
            return None

        adapter = AgentToSDKAdapter(self.registry)
        return adapter.to_agent_definition(agent)
