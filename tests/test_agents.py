"""
Test agent system functionality (preparation for v5.0.0).

These tests are written in advance to guide the implementation
of the agent system in Phase 2.
"""

import sys
from abc import ABC, abstractmethod
from pathlib import Path
from types import SimpleNamespace

import pytest

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from SuperClaude.Commands import CommandMetadata
from SuperClaude.Commands.executor import CommandExecutor
from SuperClaude.Commands.parser import CommandParser
from SuperClaude.Agents.extended_loader import MatchScore, AgentCategory


@pytest.mark.integration
class TestAgentSystem:
    """Test the agent system when it's implemented."""

    def test_base_agent_interface(self):
        """Test that BaseAgent provides the required interface."""
        from SuperClaude.Agents.base import BaseAgent

        # BaseAgent should be abstract
        assert issubclass(BaseAgent, ABC)

        # Check required methods
        required_methods = [
            'execute',
            'validate',
            'get_capabilities'
        ]

        for method in required_methods:
            assert hasattr(BaseAgent, method)

    def test_agent_registry(self):
        """Test that agent registry can discover and load agents."""
        from SuperClaude.Agents.registry import AgentRegistry

        registry = AgentRegistry()

        # Should auto-discover agents
        agents = registry.list_agents()
        assert len(agents) > 0

        # Should be able to get agent config by name
        config = registry.get_agent_config("general-purpose")
        assert config is not None

    def test_agent_selection(self):
        """Test that the system can select appropriate agent based on context."""
        from SuperClaude.Agents.selector import AgentSelector
        from SuperClaude.Agents.registry import AgentRegistry

        registry = AgentRegistry()
        selector = AgentSelector(registry)

        # Test different contexts
        contexts = [
            ({"task": "debug this code"}, ["root-cause-analyst"]),
            ({"task": "refactor this function"}, ["refactoring-expert"]),
            ({"task": "write documentation"}, ["technical-writer"]),
            ({"task": "improve performance"}, ["performance-engineer"])
        ]

        for context, expected_agents in contexts:
            scores = selector.select_agent(context)
            assert len(scores) > 0
            # Check if expected agent is in top 3
            top_agents = [agent_name for agent_name, _ in scores[:3]]
            assert any(agent in top_agents for agent in expected_agents)

    def test_demo_agents(self):
        """Test that at least 5 demo agents are implemented."""
        from SuperClaude.Agents.registry import AgentRegistry

        registry = AgentRegistry()
        agents = registry.list_agents()

        # Should have at least 5 demo agents as promised
        assert len(agents) >= 5

        # Check core agents exist
        core_agents = [
            "general-purpose",
            "root-cause-analyst",
            "refactoring-expert",
            "technical-writer",
            "performance-engineer"
        ]

        for agent_name in core_agents:
            config = registry.get_agent_config(agent_name)
            assert config is not None, f"Core agent '{agent_name}' not found"


@pytest.mark.unit
class TestAgentPreparation:
    """Tests that can run now to prepare for agent system."""

    def test_agents_directory_exists(self):
        """Test that the Agents directory structure exists."""
        agents_dir = Path(__file__).parent.parent / "SuperClaude" / "Agents"
        assert agents_dir.exists(), "Agents directory should exist"
        assert agents_dir.is_dir(), "Agents should be a directory"

    def test_agents_init_exists(self):
        """Test that Agents/__init__.py exists."""
        init_file = Path(__file__).parent.parent / "SuperClaude" / "Agents" / "__init__.py"
        assert init_file.exists(), "Agents/__init__.py should exist"

    def test_agent_template_structure(self):
        """Test the expected structure for future agent implementation."""
        # This documents the expected structure
        expected_structure = {
            "base.py": "BaseAgent abstract class",
            "registry.py": "Agent discovery and registration",
            "selector.py": "Agent selection logic",
            "core/": "Core agent implementations",
            "extended/": "Extended specialist agents"
        }

        agents_dir = Path(__file__).parent.parent / "SuperClaude" / "Agents"

        # Document expected structure (doesn't fail if not present)
        for item, description in expected_structure.items():
            path = agents_dir / item
            if not path.exists():
                print(f"TODO: Create {item} - {description}")


@pytest.mark.unit
def test_triggers_json_schema():
    """Test the expected schema for TRIGGERS.json (v5.0.0 feature)."""
    # Document the expected schema
    expected_schema = {
        "version": "1.0.0",
        "components": {
            "agents": {
                "general-purpose": {
                    "triggers": ["Task()", "--delegate"],
                    "module": "SuperClaude.Agents.core.general",
                    "class": "GeneralPurposeAgent"
                }
            },
            "modes": {
                "brainstorming": {
                    "triggers": ["--brainstorm", "explore", "discuss"],
                    "module": "SuperClaude.Modes.brainstorming",
                    "activate": "activate_brainstorming_mode"
                }
            }
        }
    }

    # This documents the expected structure
    triggers_file = Path(__file__).parent.parent / "SuperClaude" / "TRIGGERS.json"
    if not triggers_file.exists():
        print(f"TODO: Create TRIGGERS.json with schema: {expected_schema}")


class _StubRegistry:
    """Minimal registry stub for command executor tests."""

    def __init__(self):
        self._commands = {
            'implement': CommandMetadata(
                name='implement',
                description='',
                category='general',
                complexity='standard'
            )
        }

    def get_command(self, name: str):
        return self._commands.get(name)
@pytest.mark.asyncio
async def test_delegate_flag_auto_selects_agent(monkeypatch):
    """Command executor should auto-select an agent when --delegate is provided."""
    parser = CommandParser()
    executor = CommandExecutor(_StubRegistry(), parser)

    class DummyAgent:
        def __init__(self, agent_name: str) -> None:
            self.agent_name = agent_name

        def execute(self, payload):
            return {
                'output': f"handled by {self.agent_name}",
                'actions_taken': [f"{self.agent_name}-action"],
                'warnings': []
            }

    dummy_match = MatchScore(
        agent_id='refactoring-expert',
        total_score=0.9,
        breakdown={'keywords': 0.3},
        matched_criteria=['refactor'],
        confidence='high'
    )

    monkeypatch.setattr(
        executor.extended_agent_loader,
        'select_agent',
        lambda *args, **kwargs: [dummy_match]
    )

    executor.agent_loader.load_agent = lambda name: DummyAgent(name)

    result = await executor.execute('/sc:implement improve modularity --delegate')

    assert result.success is True
    assert 'refactoring-expert' in result.agents_used
    delegation = result.output.get('delegation', {})
    assert delegation.get('selected_agent') == 'refactoring-expert'
    assert delegation.get('strategy') == 'auto'
    assert delegation.get('candidates'), "Delegation should expose candidate shortlist"
    assert delegation['candidates'][0]['agent'] == 'refactoring-expert'
    assert result.output.get('think_level') == 2


@pytest.mark.asyncio
async def test_delegate_extended_prefers_specialist(monkeypatch):
    """--delegate-extended should prefer extended catalogue agents when available."""
    parser = CommandParser()
    executor = CommandExecutor(_StubRegistry(), parser)

    class DummyAgent:
        def __init__(self, agent_name: str) -> None:
            self.agent_name = agent_name

        def execute(self, payload):
            return {
                'output': f"handled by {self.agent_name}",
                'actions_taken': [f"{self.agent_name}-action"],
                'warnings': []
            }

    base_match = MatchScore(
        agent_id='general-purpose',
        total_score=0.82,
        breakdown={'keywords': 0.3},
        matched_criteria=['general'],
        confidence='medium'
    )
    specialist_match = MatchScore(
        agent_id='quality-specialist',
        total_score=0.8,
        breakdown={'keywords': 0.4},
        matched_criteria=['quality'],
        confidence='high'
    )

    executor.extended_agent_loader._agent_metadata['general-purpose'] = SimpleNamespace(
        category=AgentCategory.CORE_DEVELOPMENT
    )
    executor.extended_agent_loader._agent_metadata['quality-specialist'] = SimpleNamespace(
        category=AgentCategory.QUALITY_SECURITY
    )

    monkeypatch.setattr(
        executor.extended_agent_loader,
        'select_agent',
        lambda *args, **kwargs: [base_match, specialist_match]
    )
    executor.agent_loader.load_agent = lambda name: DummyAgent(name)

    result = await executor.execute('/sc:implement tighten monitoring --delegate-extended')

    assert result.success is True
    assert 'quality-specialist' in result.agents_used

    delegation = result.output.get('delegation', {})
    assert delegation.get('strategy') == 'extended'
    assert delegation.get('selected_agent') == 'quality-specialist'
    assert delegation['candidates'][0]['agent'] == 'quality-specialist'


if __name__ == "__main__":
    # Run tests if executed directly
    pytest.main([__file__, "-v"])
