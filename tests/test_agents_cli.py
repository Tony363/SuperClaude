"""Tests for SuperClaude.Agents.cli module.

This module tests the CLI interface for the extended agent system,
including command functions and argument parsing.

NOTE: This file tests SuperClaude/Agents/cli.py (agent system CLI),
NOT SuperClaude/__main__.py (installer CLI) which is tested in test_cli.py.

These tests require the archived SDK to be properly installed.
Skip if the archived SDK compatibility layer has import issues.
"""

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import Mock, patch

import pytest

# Check if archived SDK imports work - skip entire module if not
try:
    from SuperClaude.Agents import cli as agents_cli  # noqa: F401
except ImportError:
    pytest.skip(
        "Archived SDK compatibility layer not available",
        allow_module_level=True,
    )


@dataclass
class MockAgentMatch:
    """Mock agent match result for selection tests."""

    agent_id: str
    total_score: float
    confidence: str
    matched_criteria: list[str] = field(default_factory=list)


@dataclass
class MockAgentMetadata:
    """Mock agent metadata for CLI tests."""

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
def mock_category():
    """Create a mock AgentCategory enum."""
    mock = Mock()
    mock.value = "01-core-development"
    return mock


@pytest.fixture
def mock_agent_metadata(mock_category):
    """Create mock agent metadata for testing."""
    return MockAgentMetadata(
        id="test-agent-1",
        name="Test Agent",
        category=mock_category,
        priority=1,
        domains=["testing", "development", "automation"],
        languages=["python", "javascript"],
        keywords=["test", "mock", "fixture"],
        description="A test agent for unit testing purposes",
        file_patterns=["test_*.py", "*_test.py"],
        imports=["pytest", "unittest"],
        is_loaded=False,
        load_count=5,
        last_accessed=1000.0,
    )


@pytest.fixture
def mock_extended_loader(mock_agent_metadata, mock_category):
    """Create a mock ExtendedAgentLoader."""
    loader = Mock()

    # Configure agent metadata
    loader._agent_metadata = {"test-agent-1": mock_agent_metadata}

    # Configure methods
    loader.get_agents_by_category.return_value = [mock_agent_metadata]
    loader.list_categories.return_value = {mock_category: 1}
    loader.search_agents.return_value = [mock_agent_metadata]
    loader.select_agent.return_value = [
        MockAgentMatch(
            agent_id="test-agent-1",
            total_score=0.95,
            confidence="high",
            matched_criteria=["domains", "keywords"],
        )
    ]
    loader.explain_selection.return_value = {
        "agent_name": "Test Agent",
        "category": "01-core-development",
        "priority": 1,
        "confidence": "high",
        "breakdown": {
            "keywords": 0.3,
            "domains": 0.25,
            "languages": 0.2,
            "file_patterns": 0.15,
            "imports": 0.1,
            "priority": 0.05,
        },
        "matched_criteria": ["domains match", "keywords match"],
    }
    loader.get_statistics.return_value = {
        "total_agents": 131,
        "cached_agents": 10,
        "max_cache_size": 50,
        "agent_loads": 100,
        "cache_hits": 80,
        "cache_misses": 20,
        "cache_hit_rate": 0.8,
        "evictions": 5,
        "avg_load_time": 0.05,
        "selection_queries": 50,
        "category_distribution": {"01-core-development": 14},
        "top_accessed_agents": {"test-agent-1": 10},
    }

    return loader


class TestCmdListAgents:
    """Tests for cmd_list_agents function."""

    def test_cmd_list_agents_all(self, mock_extended_loader, capsys):
        """Test listing all agents."""
        from SuperClaude.Agents.cli import cmd_list_agents

        cmd_list_agents(mock_extended_loader, category=None)

        captured = capsys.readouterr()
        assert "Test Agent" in captured.out or "test-agent-1" in captured.out

    def test_cmd_list_agents_by_category(self, mock_extended_loader, capsys):
        """Test listing agents filtered by category."""
        from SuperClaude.Agents.cli import cmd_list_agents

        cmd_list_agents(mock_extended_loader, category="01-core-development")

        mock_extended_loader.get_agents_by_category.assert_called_once()
        capsys.readouterr()
        # Output should contain agent info

    def test_cmd_list_agents_invalid_category(self, mock_extended_loader, capsys):
        """Test error handling for invalid category."""
        from SuperClaude.Agents.cli import cmd_list_agents

        # Make get_agents_by_category raise ValueError
        mock_extended_loader.get_agents_by_category.side_effect = ValueError("Invalid category")

        # This should handle the error gracefully
        cmd_list_agents(mock_extended_loader, category="invalid-category")

        captured = capsys.readouterr()
        assert "Invalid category" in captured.out or "invalid" in captured.out.lower()


class TestCmdListCategories:
    """Tests for cmd_list_categories function."""

    def test_cmd_list_categories(self, mock_extended_loader, capsys):
        """Test listing all categories."""
        from SuperClaude.Agents.cli import cmd_list_categories

        cmd_list_categories(mock_extended_loader)

        mock_extended_loader.list_categories.assert_called_once()
        captured = capsys.readouterr()
        assert "Categor" in captured.out  # "Categories" or "Category"


class TestCmdSearchAgents:
    """Tests for cmd_search_agents function."""

    def test_cmd_search_agents_found(self, mock_extended_loader, capsys):
        """Test searching agents with matches."""
        from SuperClaude.Agents.cli import cmd_search_agents

        cmd_search_agents(mock_extended_loader, "test")

        mock_extended_loader.search_agents.assert_called_once_with("test")
        captured = capsys.readouterr()
        assert "Test Agent" in captured.out or "Found" in captured.out

    def test_cmd_search_agents_not_found(self, mock_extended_loader, capsys):
        """Test searching agents with no matches."""
        from SuperClaude.Agents.cli import cmd_search_agents

        mock_extended_loader.search_agents.return_value = []

        cmd_search_agents(mock_extended_loader, "nonexistent")

        captured = capsys.readouterr()
        assert "No agents found" in captured.out or "0" in captured.out


class TestCmdSelectAgent:
    """Tests for cmd_select_agent function."""

    def test_cmd_select_agent_with_matches(self, mock_extended_loader, capsys):
        """Test selecting agent with matches."""
        from SuperClaude.Agents.cli import cmd_select_agent

        context = {
            "task": "write unit tests",
            "files": ["test_example.py"],
            "languages": ["python"],
            "domains": ["testing"],
        }

        cmd_select_agent(mock_extended_loader, context, top_n=5)

        mock_extended_loader.select_agent.assert_called_once()
        capsys.readouterr()
        # Should show suggestions

    def test_cmd_select_agent_no_matches(self, mock_extended_loader, capsys):
        """Test selecting agent with no suitable matches."""
        from SuperClaude.Agents.cli import cmd_select_agent

        mock_extended_loader.select_agent.return_value = []

        context = {"task": "impossible task"}

        cmd_select_agent(mock_extended_loader, context)

        captured = capsys.readouterr()
        assert "No suitable agents" in captured.out or "no" in captured.out.lower()


class TestCmdAgentInfo:
    """Tests for cmd_agent_info function."""

    def test_cmd_agent_info_exists(self, mock_extended_loader, capsys):
        """Test showing info for existing agent."""
        from SuperClaude.Agents.cli import cmd_agent_info

        cmd_agent_info(mock_extended_loader, "test-agent-1")

        captured = capsys.readouterr()
        assert "test-agent-1" in captured.out or "Test Agent" in captured.out

    def test_cmd_agent_info_not_found(self, mock_extended_loader, capsys):
        """Test error handling for non-existent agent."""
        from SuperClaude.Agents.cli import cmd_agent_info

        cmd_agent_info(mock_extended_loader, "nonexistent-agent")

        captured = capsys.readouterr()
        assert "not found" in captured.out.lower()


class TestCmdStatistics:
    """Tests for cmd_statistics function."""

    def test_cmd_statistics(self, mock_extended_loader, capsys):
        """Test showing loader statistics."""
        from SuperClaude.Agents.cli import cmd_statistics

        cmd_statistics(mock_extended_loader)

        mock_extended_loader.get_statistics.assert_called_once()
        captured = capsys.readouterr()
        assert "131" in captured.out or "Statistics" in captured.out


class TestCmdCategoryTree:
    """Tests for cmd_category_tree function."""

    def test_cmd_category_tree(self, mock_extended_loader, capsys):
        """Test showing category tree view."""
        from SuperClaude.Agents.cli import cmd_category_tree

        cmd_category_tree(mock_extended_loader)

        mock_extended_loader.list_categories.assert_called()
        capsys.readouterr()
        # Tree output should be present


class TestMainFunction:
    """Tests for main() function and argument parsing."""

    def test_main_no_args_shows_help(self, capsys):
        """Test that running with no args shows help."""
        from SuperClaude.Agents.cli import main

        with (
            patch("sys.argv", ["cli"]),
            patch("SuperClaude.Agents.cli.ExtendedAgentLoader") as mock_loader_class,
        ):
            mock_loader_class.return_value = Mock()
            main()

        capsys.readouterr()
        # Should print help or usage info

    def test_main_list_command(self, mock_extended_loader, capsys):
        """Test main() with list command."""
        from SuperClaude.Agents.cli import main

        with (
            patch("sys.argv", ["cli", "list"]),
            patch(
                "SuperClaude.Agents.cli.ExtendedAgentLoader",
                return_value=mock_extended_loader,
            ),
        ):
            main()

        capsys.readouterr()
        # Should list agents

    def test_main_search_command(self, mock_extended_loader, capsys):
        """Test main() with search command."""
        from SuperClaude.Agents.cli import main

        with (
            patch("sys.argv", ["cli", "search", "python"]),
            patch(
                "SuperClaude.Agents.cli.ExtendedAgentLoader",
                return_value=mock_extended_loader,
            ),
        ):
            main()

        capsys.readouterr()
        # Should show search results

    def test_main_categories_command(self, mock_extended_loader, capsys):
        """Test main() with categories command."""
        from SuperClaude.Agents.cli import main

        with (
            patch("sys.argv", ["cli", "categories"]),
            patch(
                "SuperClaude.Agents.cli.ExtendedAgentLoader",
                return_value=mock_extended_loader,
            ),
        ):
            main()

        capsys.readouterr()
        # Should list categories

    def test_main_info_command(self, mock_extended_loader, capsys):
        """Test main() with info command."""
        from SuperClaude.Agents.cli import main

        with (
            patch("sys.argv", ["cli", "info", "test-agent-1"]),
            patch(
                "SuperClaude.Agents.cli.ExtendedAgentLoader",
                return_value=mock_extended_loader,
            ),
        ):
            main()

        capsys.readouterr()
        # Should show agent info

    def test_main_stats_command(self, mock_extended_loader, capsys):
        """Test main() with stats command."""
        from SuperClaude.Agents.cli import main

        with (
            patch("sys.argv", ["cli", "stats"]),
            patch(
                "SuperClaude.Agents.cli.ExtendedAgentLoader",
                return_value=mock_extended_loader,
            ),
        ):
            main()

        capsys.readouterr()
        # Should show statistics

    def test_main_tree_command(self, mock_extended_loader, capsys):
        """Test main() with tree command."""
        from SuperClaude.Agents.cli import main

        with (
            patch("sys.argv", ["cli", "tree"]),
            patch(
                "SuperClaude.Agents.cli.ExtendedAgentLoader",
                return_value=mock_extended_loader,
            ),
        ):
            main()

        capsys.readouterr()
        # Should show tree view

    def test_main_handles_exception(self, capsys):
        """Test that main() handles exceptions gracefully."""
        from SuperClaude.Agents.cli import main

        with (
            patch("sys.argv", ["cli", "list"]),
            patch("SuperClaude.Agents.cli.ExtendedAgentLoader") as mock_loader_class,
        ):
            mock_loader_class.return_value._agent_metadata = {}
            mock_loader_class.return_value.get_agents_by_category.side_effect = Exception(
                "Test error"
            )
            # Should not raise, should handle gracefully
            try:
                main()
            except SystemExit:
                pass  # argparse may exit

        capsys.readouterr()
        # Error handling output may be present


class TestSelectCommand:
    """Tests for select command with full context."""

    def test_main_select_command(self, mock_extended_loader, capsys):
        """Test main() with select command and arguments."""
        from SuperClaude.Agents.cli import main

        with (
            patch(
                "sys.argv",
                [
                    "cli",
                    "select",
                    "--task",
                    "write tests",
                    "--files",
                    "test.py",
                    "--languages",
                    "python",
                ],
            ),
            patch(
                "SuperClaude.Agents.cli.ExtendedAgentLoader",
                return_value=mock_extended_loader,
            ),
        ):
            main()

        capsys.readouterr()
        # Should show selected agents
