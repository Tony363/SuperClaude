"""End-to-end agent orchestration tests without mocks.

These tests require the archived SDK to be properly installed.
Mark all tests with @pytest.mark.archived_sdk to skip in CI.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from SuperClaude.Agents.extended_loader import ExtendedAgentLoader
from SuperClaude.Agents.registry import AgentRegistry
from SuperClaude.Agents.selector import AgentSelector
from SuperClaude.Commands import CommandExecutor
from SuperClaude.Commands.parser import CommandParser
from SuperClaude.Commands.registry import CommandRegistry

# Mark all tests in this module as requiring archived SDK
pytestmark = pytest.mark.archived_sdk


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
    scores = selector.select_agent(context)

    assert scores
    top_agents = {name for name, _ in scores[:3]}
    assert {"refactoring-expert", "python-expert", "general-purpose"}.intersection(top_agents)


class _DummyRegistry:
    """Lightweight registry test double for selector edge cases."""

    def __init__(self, agents: dict[str, dict[str, object]]):
        self._agents = agents

    def discover_agents(self) -> None:  # pragma: no cover - invoked implicitly
        return None

    def get_all_agents(self) -> list[str]:
        return list(self._agents.keys())

    def list_agents(self) -> list[str]:
        return self.get_all_agents()

    def get_agent_config(self, name: str):
        return self._agents.get(name)


def test_agent_selector_falls_back_to_default_when_all_scores_low():
    registry = _DummyRegistry(
        {
            "general-purpose": {
                "name": "general-purpose",
                "triggers": [],
                "category": "core",
            },
            "ml-specialist": {
                "name": "ml-specialist",
                "triggers": ["ml"],
                "category": "ml",
            },
        }
    )

    selector = AgentSelector(registry)
    scores = selector.select_agent("totally unrelated domain with no triggers")

    assert scores[0][0] == "general-purpose"
    assert scores[0][1] == pytest.approx(0.5)


def test_agent_selector_respects_default_exclusion_when_no_candidates():
    registry = _DummyRegistry(
        {
            "general-purpose": {
                "name": "general-purpose",
                "triggers": [],
                "category": "core",
            },
            "security": {
                "name": "security",
                "triggers": ["xss"],
                "category": "security",
            },
        }
    )

    selector = AgentSelector(registry)
    scores = selector.select_agent("documentation task", exclude_agents=["general-purpose"])

    assert scores == []


@pytest.fixture
def command_executor(tmp_path: Path) -> CommandExecutor:
    registry = CommandRegistry()
    parser = CommandParser(registry=registry)
    executor = CommandExecutor(registry, parser)
    executor.repo_root = tmp_path
    return executor


def test_delegate_flag_executes_real_agent(command_executor: CommandExecutor) -> None:
    command = (
        "/sc:implement improve modularity --delegate --keywords python,refactor --languages python"
    )
    result = asyncio.run(command_executor.execute(command))

    delegation = result.output.get("delegation") or {}
    assert delegation.get("requested") is True
    assert delegation.get("selected_agent")
    assert delegation.get("candidates")

    loader = ExtendedAgentLoader()
    agent = loader.load_agent(delegation["selected_agent"])
    assert agent is not None
