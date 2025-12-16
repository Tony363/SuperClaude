"""Shared pytest fixtures for executor tests."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock

import pytest

from SuperClaude.Commands import (
    CommandContext,
    CommandExecutor,
    CommandParser,
    CommandRegistry,
)
from SuperClaude.Commands.parser import ParsedCommand
from SuperClaude.Commands.registry import CommandMetadata
from SuperClaude.Modes.behavioral_manager import BehavioralMode


@pytest.fixture
def command_workspace(tmp_path, monkeypatch):
    """Create isolated workspace for command tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("SUPERCLAUDE_OFFLINE_MODE", "1")
    monkeypatch.setenv("SC_NETWORK_MODE", "offline")
    monkeypatch.setenv("PYENV_DISABLE_REHASH", "1")
    metrics_dir = workspace / ".superclaude_metrics"
    monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(metrics_dir))
    return workspace


@pytest.fixture
def temp_repo(tmp_path):
    """Create an initialized git repository for testing."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    # Create initial commit
    readme = repo / "README.md"
    readme.write_text("# Test Repo\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo


@pytest.fixture
def registry():
    """Create a CommandRegistry instance."""
    return CommandRegistry()


@pytest.fixture
def parser():
    """Create a CommandParser instance."""
    return CommandParser()


@pytest.fixture
def executor(command_workspace, registry, parser):
    """Create a CommandExecutor with mocked workspace."""
    return CommandExecutor(registry, parser, repo_root=command_workspace)


@pytest.fixture
def mock_agent_loader():
    """Create a mock AgentLoader that returns controllable agents."""
    loader = MagicMock()
    loader.load_agent.return_value = MagicMock(
        name="mock_agent",
        execute=MagicMock(return_value={"status": "success", "output": "mock output"}),
    )
    loader.list_agents.return_value = ["architect", "implementer", "reviewer"]
    return loader


@pytest.fixture
def mock_quality_scorer():
    """Create a mock QualityScorer with predictable assessments."""
    from datetime import datetime

    from SuperClaude.Quality.quality_scorer import QualityAssessment

    scorer = MagicMock()
    scorer.evaluate.return_value = QualityAssessment(
        overall_score=85.0,
        metrics=[],
        timestamp=datetime.now(),
        iteration=0,
        passed=True,
        threshold=75.0,
        context={},
        improvements_needed=[],
    )
    scorer.MAX_ITERATIONS = 3
    return scorer


@pytest.fixture
def mock_consensus_facade():
    """Create a mock ModelRouterFacade with controllable votes."""
    facade = MagicMock()
    facade.vote.return_value = {
        "decision": "approve",
        "confidence": 0.9,
        "votes": [
            {"model": "gpt-5", "vote": "approve"},
            {"model": "claude", "vote": "approve"},
        ],
    }
    return facade


@pytest.fixture
def sample_parsed_command():
    """Create a sample ParsedCommand for testing."""
    return ParsedCommand(
        name="implement",
        raw_string="/sc:implement feature --safe",
        arguments=["feature"],
        flags={"safe": True},
        parameters={},
        description="Implement a feature",
    )


@pytest.fixture
def sample_metadata():
    """Create sample CommandMetadata for testing."""
    return CommandMetadata(
        name="implement",
        description="Implement code changes",
        category="development",
        complexity="medium",
        mcp_servers=[],
        personas=["implementer", "architect"],
        triggers=["implement", "code", "build"],
        flags=[{"name": "safe", "type": "bool", "default": False}],
        parameters={},
        requires_evidence=True,
    )


@pytest.fixture
def sample_context(sample_parsed_command, sample_metadata):
    """Create a sample CommandContext for testing."""
    return CommandContext(
        command=sample_parsed_command,
        metadata=sample_metadata,
        mcp_servers=[],
        agents=["implementer"],
        agent_instances={},
        agent_outputs={},
        results={},
        errors=[],
        session_id="test-session-123",
        behavior_mode=BehavioralMode.NORMAL.value,
    )


@pytest.fixture
def executor_with_mocks(
    command_workspace,
    registry,
    parser,
    mock_agent_loader,
    mock_quality_scorer,
    mock_consensus_facade,
):
    """Create an executor with all major dependencies mocked."""
    exec_instance = CommandExecutor(registry, parser, repo_root=command_workspace)
    exec_instance.agent_loader = mock_agent_loader
    exec_instance.quality_scorer = mock_quality_scorer
    exec_instance.consensus_facade = mock_consensus_facade
    return exec_instance


@pytest.fixture
def sample_agent_output():
    """Sample output from an agent execution."""
    return {
        "status": "success",
        "changes": [
            {
                "path": "src/feature.py",
                "action": "create",
                "content": "# New feature\ndef feature():\n    pass\n",
            }
        ],
        "summary": "Created new feature module",
        "executed_operations": ["Created src/feature.py"],
    }


@pytest.fixture
def sample_test_results():
    """Sample pytest results structure."""
    return {
        "command": "pytest tests/",
        "args": ["pytest", "tests/", "-v"],
        "passed": True,
        "pass_rate": 1.0,
        "stdout": "===== 10 passed in 1.23s =====",
        "stderr": "",
        "duration_s": 1.23,
        "exit_code": 0,
        "coverage": {"total": 85.5, "files": {}},
        "summary": "10 passed",
        "tests_passed": 10,
        "tests_failed": 0,
        "tests_errored": 0,
        "tests_skipped": 0,
        "tests_collected": 10,
        "markers": [],
        "targets": ["tests/"],
    }
