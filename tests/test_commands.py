from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest

from SuperClaude.Commands import CommandRegistry, CommandParser, CommandExecutor


@pytest.fixture
def command_workspace(tmp_path, monkeypatch):
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
def executor(command_workspace):
    registry = CommandRegistry()
    parser = CommandParser()
    return CommandExecutor(registry, parser)


def test_implement_fast_codex_requires_evidence(executor):
    result = asyncio.run(executor.execute("/sc:implement telemetry guardrail --fast-codex"))

    assert result.status == "failed"
    assert result.success is False
    assert any("no concrete change plan" in error.lower() for error in result.errors)

    fast_state = result.output.get("fast_codex") or {}
    assert fast_state.get("requested") is True
    assert fast_state.get("active") is True
    assert not fast_state.get("blocked")

    consensus = result.consensus or {}
    assert consensus.get("vote_type") == "quorum"
    assert consensus.get("quorum_size") == 3
    assert consensus.get("offline") is True

    # Artefacts still recorded for tracing purposes
    assert result.artifacts
    for artifact in result.artifacts:
        assert Path(artifact).exists()


def test_implement_safe_apply_fails_without_plan(executor, command_workspace):
    result = asyncio.run(
        executor.execute("/sc:implement snapshot stub --fast-codex --safe-apply")
    )

    assert result.status == "failed"
    assert result.success is False
    assert any("no concrete change plan" in error.lower() for error in result.errors)

    metrics_dir = command_workspace / ".superclaude_metrics"
    safe_root = metrics_dir / "safe_apply"
    assert not safe_root.exists()


def test_fast_codex_respects_safe_flag(executor):
    result = asyncio.run(executor.execute("/sc:implement guarded flow --fast-codex --safe"))

    fast_state = result.output.get("fast_codex") or {}
    assert fast_state.get("requested") is True
    assert fast_state.get("active") is False
    assert "safety-requested" in (fast_state.get("blocked") or [])
    assert any("no concrete change plan" in error.lower() for error in result.errors)


def test_business_panel_produces_artifact(executor):
    result = asyncio.run(executor.execute("/sc:business-panel go-to-market expansion"))

    assert any("Agent loading failed" in err for err in result.errors)
    panel = result.output.get("panel") or {}
    assert panel.get("experts"), "panel metadata should include engaged experts"
    assert result.artifacts, "business panel should record an artifact"
    for artifact in result.artifacts:
        assert Path(artifact).exists()


def test_workflow_command_generates_steps(executor, command_workspace):
    prd_path = command_workspace / "workflow-spec.md"
    prd_path.write_text(
        "# Feature Rollout\n\n## Goals\n- deliver value\n\n## Acceptance\n- measurable outcome\n",
        encoding="utf-8",
    )

    result = asyncio.run(
        executor.execute(
            f"/sc:workflow {prd_path.name} --strategy agile --depth deep --parallel"
        )
    )

    assert result.success is True
    assert result.output.get("status") == "workflow_generated"
    assert result.output.get("steps")
    for artifact in result.artifacts:
        assert Path(artifact).exists()


def test_git_status_summarizes_repository(executor, command_workspace):
    subprocess.run(["git", "init"], cwd=command_workspace, check=True, stdout=subprocess.PIPE)
    subprocess.run(
        ["git", "config", "user.name", "Test Runner"],
        cwd=command_workspace,
        check=True,
        stdout=subprocess.PIPE,
    )
    subprocess.run(
        ["git", "config", "user.email", "ci@example.com"],
        cwd=command_workspace,
        check=True,
        stdout=subprocess.PIPE,
    )
    tracked = command_workspace / "tracked.txt"
    tracked.write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=command_workspace, check=True, stdout=subprocess.PIPE)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=command_workspace,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    tracked.write_text("initial\nupdated\n", encoding="utf-8")
    (command_workspace / "new-file.txt").write_text("hello\n", encoding="utf-8")

    result = asyncio.run(executor.execute("/sc:git status"))
    summary = result.output.get("summary") or {}

    assert summary.get("branch")
    assert summary.get("unstaged_changes", 0) >= 1
    assert summary.get("untracked_files", 0) >= 1
    for artifact in result.artifacts:
        assert Path(artifact).exists()


def test_test_command_reports_parameters(executor):
    result = asyncio.run(
        executor.execute(
            "/sc:test --type integration --coverage --markers smoke,integration --targets tests/unit"
        )
    )

    output = result.output
    assert output.get("status") == "tests_started"
    assert output.get("type") == "integration"
    assert output.get("coverage") is True
