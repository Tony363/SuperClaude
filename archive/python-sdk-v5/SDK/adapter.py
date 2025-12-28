"""
Adapter for converting SuperClaude agents to Claude Agent SDK format.

This module provides bidirectional conversion between SuperClaude's BaseAgent
instances and the Claude Agent SDK's AgentDefinition format, enabling
SuperClaude's 131+ specialized agents to execute via the SDK.

Key Mappings:
    - agent.description → AgentDefinition.description
    - agent markdown content → AgentDefinition.prompt
    - agent.tools → AgentDefinition.tools (with name mapping)
    - agent mindset/boundaries → embedded in prompt

Example:
    adapter = AgentToSDKAdapter(registry)
    sdk_agents = adapter.build_agents("Fix auth bug", context, max_agents=3)
    # Returns: {"security-agent": AgentDefinition(...), ...}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..Agents.base import BaseAgent
    from ..Agents.registry import AgentRegistry

logger = logging.getLogger(__name__)


@dataclass
class SDKAgentDefinition:
    """
    SDK-compatible agent definition.

    This is a local representation that matches the Claude Agent SDK's
    AgentDefinition structure. When claude-agent-sdk is installed,
    instances can be converted to native AgentDefinition objects.
    """

    description: str
    prompt: str
    tools: list[str] = field(default_factory=list)
    model: str = "sonnet"  # Default model, can be: sonnet, opus, haiku, inherit

    def to_sdk_definition(self) -> Any:
        """
        Convert to native Claude Agent SDK AgentDefinition.

        Returns:
            Native AgentDefinition if SDK is installed, else self.

        Raises:
            ImportError: If claude-agent-sdk is not installed.
        """
        try:
            from claude_agent_sdk import AgentDefinition

            return AgentDefinition(
                description=self.description,
                prompt=self.prompt,
                tools=self.tools,
                model=self.model,
            )
        except ImportError:
            logger.warning("claude-agent-sdk not installed, returning local definition")
            return self


class AgentToSDKAdapter:
    """
    Adapter for converting SuperClaude agents to SDK AgentDefinition format.

    This adapter handles:
    - Tool name mapping (SuperClaude names → SDK names)
    - Prompt construction from agent metadata
    - Capability tier-based model selection
    - Batch conversion for multi-agent scenarios
    """

    # Mapping from SuperClaude tool names to SDK-compatible names
    TOOL_MAPPING: dict[str, str] = {
        # Core file tools
        "Read": "Read",
        "Write": "Write",
        "Edit": "Edit",
        "MultiEdit": "Edit",  # MultiEdit maps to Edit in SDK
        # Search tools
        "Glob": "Glob",
        "Grep": "Grep",
        # Terminal tools
        "Bash": "Bash",
        "bash": "Bash",
        # Web tools
        "WebSearch": "WebSearch",
        "WebFetch": "WebFetch",
        # Subagent tools
        "Task": "Task",
        # Common CLI tools (run via Bash)
        "git": "Bash",
        "npm": "Bash",
        "pip": "Bash",
        "poetry": "Bash",
        "pytest": "Bash",
        "black": "Bash",
        "mypy": "Bash",
        "ruff": "Bash",
        "bandit": "Bash",
        "eslint": "Bash",
        "tsc": "Bash",
        "typescript": "Bash",
        "nodejs": "Bash",
        "docker": "Bash",
        # MCP tools pass through with prefix
        # Pattern: mcp__server__tool → mcp__server__tool
    }

    # Model selection based on capability tier
    TIER_MODELS: dict[str, str] = {
        "strategist": "sonnet",  # Core agents get default model
        "heuristic-wrapper": "haiku",  # Extended agents can use faster model
    }

    def __init__(self, registry: AgentRegistry | None = None):
        """
        Initialize the adapter.

        Args:
            registry: Optional AgentRegistry for batch operations.
        """
        self.registry = registry

    def to_agent_definition(
        self,
        agent: BaseAgent,
        model_override: str | None = None,
    ) -> SDKAgentDefinition:
        """
        Convert a SuperClaude agent to SDK AgentDefinition format.

        Args:
            agent: SuperClaude BaseAgent instance.
            model_override: Optional model to use instead of tier default.

        Returns:
            SDKAgentDefinition compatible with Claude Agent SDK.
        """
        # Map tools to SDK-compatible names
        sdk_tools = self._map_tools(agent.tools)

        # Build prompt from agent configuration
        prompt = self._build_agent_prompt(agent)

        # Select model based on tier or override
        model = model_override or self._select_model(agent)

        return SDKAgentDefinition(
            description=agent.description,
            prompt=prompt,
            tools=sdk_tools,
            model=model,
        )

    def _map_tools(self, tools: list[str]) -> list[str]:
        """
        Map SuperClaude tool names to SDK-compatible names.

        Args:
            tools: List of SuperClaude tool names.

        Returns:
            Deduplicated list of SDK tool names.
        """
        mapped = set()
        for tool in tools:
            # Check if it's an MCP tool (starts with mcp__)
            if tool.startswith("mcp__"):
                mapped.add(tool)
            # Check direct mapping
            elif tool in self.TOOL_MAPPING:
                mapped.add(self.TOOL_MAPPING[tool])
            else:
                # Unknown tools logged but not included
                logger.debug(f"Unknown tool '{tool}' not mapped to SDK")

        return sorted(mapped)

    def _build_agent_prompt(self, agent: BaseAgent) -> str:
        """
        Build SDK-compatible prompt from agent configuration.

        The prompt incorporates:
        - Agent identity and description
        - Behavioral mindset
        - Focus areas
        - Boundaries (what agent will/won't do)

        Args:
            agent: SuperClaude BaseAgent instance.

        Returns:
            Formatted prompt string for SDK.
        """
        sections = []

        # Identity
        agent_title = agent.name.replace("-", " ").title()
        sections.append(f"You are {agent_title}.")
        sections.append("")
        sections.append(agent.description)
        sections.append("")

        # Behavioral mindset
        if agent.mindset:
            sections.append("## Behavioral Mindset")
            sections.append(agent.mindset)
            sections.append("")

        # Focus areas
        if agent.focus_areas:
            sections.append("## Focus Areas")
            for area, details in agent.focus_areas.items():
                sections.append(f"- **{area}**: {details}")
            sections.append("")

        # Boundaries - what agent will do
        will_do = agent.boundaries.get("will", [])
        if will_do:
            sections.append("## What You Will Do")
            for item in will_do:
                sections.append(f"- {item}")
            sections.append("")

        # Boundaries - what agent won't do
        will_not = agent.boundaries.get("will_not", [])
        if will_not:
            sections.append("## Boundaries")
            sections.append("You will NOT:")
            for boundary in will_not:
                sections.append(f"- {boundary}")
            sections.append("")

        # Available tools reminder
        if agent.tools:
            mapped_tools = self._map_tools(agent.tools)
            sections.append("## Available Tools")
            sections.append(f"You have access to: {', '.join(mapped_tools)}")

        return "\n".join(sections)

    def _select_model(self, agent: BaseAgent) -> str:
        """
        Select appropriate model based on agent's capability tier.

        Args:
            agent: SuperClaude BaseAgent instance.

        Returns:
            Model identifier (sonnet, opus, haiku, or inherit).
        """
        # Check for explicit tier in config
        tier = agent.config.get("capability_tier", "heuristic-wrapper")
        return self.TIER_MODELS.get(tier, "sonnet")

    def build_agents(
        self,
        task: str,
        context: dict[str, Any],
        max_agents: int = 3,
    ) -> dict[str, SDKAgentDefinition]:
        """
        Build AgentDefinition dictionary for SDK from task context.

        This method:
        1. Uses the registry to find relevant agents
        2. Converts top agents to SDK format
        3. Returns dict suitable for SDK's agents parameter

        Args:
            task: Task description for agent selection.
            context: Additional context for selection.
            max_agents: Maximum number of agents to include.

        Returns:
            Dictionary mapping agent names to SDKAgentDefinition.

        Raises:
            ValueError: If no registry is configured.
        """
        if not self.registry:
            raise ValueError("Registry required for build_agents()")

        agents: dict[str, SDKAgentDefinition] = {}

        # Get relevant agents from registry
        try:
            # Try selector-based approach if available
            from ..Agents.selector import AgentSelector

            selector = AgentSelector(self.registry)
            scores = selector.select_agent({"task": task, **context})

            for agent_name, score in scores[:max_agents]:
                agent = self.registry.get_agent(agent_name)
                if agent:
                    agents[agent_name] = self.to_agent_definition(agent)

        except Exception as e:
            logger.warning(f"Selector-based selection failed: {e}")
            # Fallback: use general-purpose agent
            agent = self.registry.get_agent("general-purpose")
            if agent:
                agents["general-purpose"] = self.to_agent_definition(agent)

        return agents

    def from_markdown_config(self, config: dict[str, Any]) -> SDKAgentDefinition:
        """
        Create SDKAgentDefinition directly from markdown-parsed config.

        This is useful for converting agents without instantiating BaseAgent.

        Args:
            config: Dictionary from parsed markdown frontmatter.

        Returns:
            SDKAgentDefinition for the agent.
        """
        # Build a minimal agent-like structure
        name = config.get("name", "unnamed")
        description = config.get("description", "")
        tools = config.get("tools", [])
        mindset = config.get("behavioral_mindset", "")
        focus_areas = config.get("focus_areas", {})
        boundaries = config.get("boundaries", {})

        # Map tools
        sdk_tools = self._map_tools(tools)

        # Build prompt sections
        sections = [
            f"You are {name.replace('-', ' ').title()}.",
            "",
            description,
            "",
        ]

        if mindset:
            sections.extend(["## Behavioral Mindset", mindset, ""])

        if focus_areas:
            sections.append("## Focus Areas")
            for area, details in focus_areas.items():
                sections.append(f"- **{area}**: {details}")
            sections.append("")

        will_not = boundaries.get("will_not", [])
        if will_not:
            sections.append("## Boundaries")
            sections.append("You will NOT:")
            for boundary in will_not:
                sections.append(f"- {boundary}")

        prompt = "\n".join(sections)

        # Select model based on tier
        tier = config.get("capability_tier", "heuristic-wrapper")
        model = self.TIER_MODELS.get(tier, "sonnet")

        return SDKAgentDefinition(
            description=description,
            prompt=prompt,
            tools=sdk_tools,
            model=model,
        )
