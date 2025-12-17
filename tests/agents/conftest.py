"""Shared fixtures for SuperClaude Agents module tests."""

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import Mock

import pytest


@dataclass
class MockAgentMetadata:
    """Mock agent metadata for testing."""

    id: str
    name: str
    category: Any = None
    priority: int = 1
    domains: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    description: str = ""
    file_patterns: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    is_loaded: bool = False
    load_count: int = 0
    last_accessed: float = 0.0


@pytest.fixture
def mock_agent():
    """Create a mock agent with configurable behavior.

    Returns:
        Mock: A mock agent that returns success by default.
    """
    agent = Mock()
    agent.name = "test-agent"
    agent.execute.return_value = {"success": True, "output": "result"}
    return agent


@pytest.fixture
def mock_failing_agent():
    """Create a mock agent that fails execution.

    Returns:
        Mock: A mock agent that returns failure.
    """
    agent = Mock()
    agent.name = "failing-agent"
    agent.execute.return_value = {"success": False, "error": "Test failure"}
    return agent


@pytest.fixture
def mock_delegating_agent():
    """Create a mock agent that requests delegation.

    Returns:
        Mock: A mock agent that requests delegation to another agent.
    """
    agent = Mock()
    agent.name = "delegating-agent"
    agent.execute.return_value = {
        "success": True,
        "delegate_to": "target-agent",
        "delegation_task": "delegated task",
    }
    return agent


@pytest.fixture
def mock_loader(mock_agent):
    """Create a mock AgentLoader that returns mock agents.

    Args:
        mock_agent: The mock agent to return.

    Returns:
        Mock: A mock loader.
    """
    loader = Mock()
    loader.load_agent.return_value = mock_agent
    return loader


@pytest.fixture
def mock_loader_factory():
    """Create a factory for mock loaders with custom agent behavior.

    Returns:
        callable: A factory function that creates configured mock loaders.
    """

    def create_loader(agent_map: dict[str, Mock] | None = None):
        loader = Mock()
        if agent_map:

            def load_agent(name):
                return agent_map.get(name)

            loader.load_agent.side_effect = load_agent
        else:
            loader.load_agent.return_value = None
        return loader

    return create_loader


@pytest.fixture
def mock_registry():
    """Create a mock AgentRegistry with sample metadata.

    Returns:
        Mock: A mock registry.
    """
    registry = Mock()
    registry.get_agent_metadata.return_value = {
        "id": "test-agent",
        "name": "Test Agent",
        "category": "core",
        "priority": 1,
    }
    return registry


@pytest.fixture
def mock_selector():
    """Create a mock AgentSelector returning fixed scores.

    Returns:
        Mock: A mock selector.
    """
    selector = Mock()
    selector.select_agent.return_value = [("test-agent", 0.95)]
    return selector


@pytest.fixture
def coordination_manager(mock_registry, mock_selector, mock_loader):
    """Create a fully mocked CoordinationManager.

    Args:
        mock_registry: Mock registry fixture.
        mock_selector: Mock selector fixture.
        mock_loader: Mock loader fixture.

    Returns:
        CoordinationManager: A manager with all dependencies mocked.
    """
    from SuperClaude.Agents.coordination import CoordinationManager

    return CoordinationManager(mock_registry, mock_selector, mock_loader)


@pytest.fixture
def coordination_manager_factory(mock_registry, mock_selector):
    """Create a factory for CoordinationManager with custom loader.

    Returns:
        callable: A factory function.
    """
    from SuperClaude.Agents.coordination import CoordinationManager

    def create_manager(loader):
        return CoordinationManager(mock_registry, mock_selector, loader)

    return create_manager
