"""Scenario-style tests that exercise multiple commands end-to-end."""

from __future__ import annotations

from pathlib import Path

import pytest

from SuperClaude.Commands import CommandExecutor, CommandParser, CommandRegistry


@pytest.fixture
def integration_workspace(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    monkeypatch.chdir(workspace)
    monkeypatch.setenv("SUPERCLAUDE_OFFLINE_MODE", "1")
    monkeypatch.setenv("SC_NETWORK_MODE", "offline")
    monkeypatch.setenv("PYENV_DISABLE_REHASH", "1")
    monkeypatch.setenv(
        "SUPERCLAUDE_METRICS_DIR", str(workspace / ".superclaude_metrics")
    )

    registry = CommandRegistry()
    parser = CommandParser(registry=registry)
    executor = CommandExecutor(registry, parser)
    executor.repo_root = workspace
    return executor, workspace


@pytest.mark.asyncio
async def test_workflow_command_integration_journey(integration_workspace):
    executor, workspace = integration_workspace

    prd_path = workspace / "workflow-spec.md"
    prd_path.write_text(
        "# Feature Rollout\n\n## Goals\n- deliver value\n", encoding="utf-8"
    )

    result = await executor.execute(
        f"/sc:workflow {prd_path.name} --strategy agile --depth deep --parallel"
    )

    assert result.success is True
    assert result.output.get("status") == "workflow_generated"
    assert result.output.get("steps")
    assert all(Path(artifact).exists() for artifact in result.artifacts)


@pytest.mark.asyncio
async def test_end_to_end_cli_journey(integration_workspace):
    executor, workspace = integration_workspace

    # Run workflow first to populate artifacts
    prd_path = workspace / "roadmap.md"
    prd_path.write_text("# Milestone\n\n- item\n", encoding="utf-8")
    await executor.execute(f"/sc:workflow {prd_path.name} --strategy agile")

    # Then trigger the test command with coverage to ensure shared context works
    result = await executor.execute(
        "/sc:test --type integration --coverage --markers smoke --targets tests/unit"
    )

    output = result.output
    assert output.get("status") == "tests_started"
    assert output.get("type") == "integration"
    assert output.get("coverage") is True

    # Journey should record metrics/artifacts from both commands
    assert result.artifacts
    assert all(Path(artifact).exists() for artifact in result.artifacts)
