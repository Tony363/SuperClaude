"""End-to-end agent orchestration tests without mocks."""

from __future__ import annotations

from pathlib import Path

import pytest

from SuperClaude.Agents.extended_loader import ExtendedAgentLoader
from SuperClaude.Agents.registry import AgentRegistry
from SuperClaude.Agents.selector import AgentSelector
from SuperClaude.Commands.executor import CommandExecutor
from SuperClaude.Commands.parser import CommandParser
from SuperClaude.Commands.registry import CommandRegistry


@pytest.fixture(scope="module")
def agent_registry() -> AgentRegistry:
    registry = AgentRegistry()
    registry.discover_agents()
    return registry


def test_registry_includes_core_agents(agent_registry: AgentRegistry) -> None:
    required = {
        "general-purpose",
        "root-cause-analyst",
        "refactoring-expert",
        "technical-writer",
        "performance-engineer",
    }

    discovered = set(agent_registry.list_agents())
    assert required.issubset(discovered)


def test_agent_selector_suggests_specialist(agent_registry: AgentRegistry) -> None:
    selector = AgentSelector(agent_registry)

    context = {"task": "Refactor this python module for maintainability"}
    scores = selector.select_agent(context, limit=5)

    assert scores
    top_agents = {name for name, _ in scores[:3]}
    assert {"refactoring-expert", "python-expert", "general-purpose"}.intersection(top_agents)


@pytest.fixture
def command_executor(tmp_path: Path) -> CommandExecutor:
    registry = CommandRegistry()
    parser = CommandParser(registry=registry)
    executor = CommandExecutor(registry, parser)
    executor.repo_root = tmp_path
    return executor


@pytest.mark.asyncio
async def test_delegate_flag_executes_real_agent(command_executor: CommandExecutor) -> None:
    result = await command_executor.execute("/sc:implement improve modularity --delegate")

    delegation = result.output.get("delegation") or {}
    assert delegation.get("requested") is True
    assert delegation.get("selected_agent")
    assert delegation.get("candidates")

    loader = ExtendedAgentLoader()
    agent = loader.load_agent(delegation["selected_agent"])
    assert agent is not None

