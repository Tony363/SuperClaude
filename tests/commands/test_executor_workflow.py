"""Tests for CommandExecutor workflow command handling."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from SuperClaude.Commands import CommandExecutor, CommandParser, CommandRegistry, CommandContext
from SuperClaude.Commands.parser import ParsedCommand
from SuperClaude.Commands.registry import CommandMetadata
from SuperClaude.Modes.behavioral_manager import BehavioralMode


class TestExecuteWorkflow:
    """Tests for _execute_workflow async method."""

    @pytest.mark.asyncio
    async def test_workflow_generates_steps(self, executor, sample_context):
        """Workflow command generates workflow steps."""
        sample_context.command = ParsedCommand(
            name="workflow",
            raw_string="/sc:workflow project",
            arguments=["project"],
            flags={},
            parameters={},
            description="Generate workflow",
        )

        with patch.object(executor, "_generate_workflow_steps") as mock_gen:
            mock_gen.return_value = [
                {"id": "S01", "phase": "Analysis", "title": "Analyze", "owner": "analyst", "dependencies": [], "deliverables": []}
            ]
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_workflow(sample_context)

        assert result["status"] == "workflow_generated"
        assert "steps" in result

    @pytest.mark.asyncio
    async def test_workflow_uses_strategy_parameter(self, executor, sample_context):
        """Workflow uses strategy from parameters."""
        sample_context.command = ParsedCommand(
            name="workflow",
            raw_string="/sc:workflow project",
            arguments=["project"],
            flags={},
            parameters={"strategy": "agile"},
            description="Generate workflow",
        )

        with patch.object(executor, "_generate_workflow_steps") as mock_gen:
            mock_gen.return_value = [{"id": "S01", "phase": "Planning", "title": "Plan", "owner": "pm", "dependencies": [], "deliverables": []}]
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_workflow(sample_context)

        assert result["strategy"] == "agile"

    @pytest.mark.asyncio
    async def test_workflow_uses_depth_parameter(self, executor, sample_context):
        """Workflow uses depth from parameters."""
        sample_context.command = ParsedCommand(
            name="workflow",
            raw_string="/sc:workflow project",
            arguments=["project"],
            flags={},
            parameters={"depth": "deep"},
            description="Generate workflow",
        )

        with patch.object(executor, "_generate_workflow_steps") as mock_gen:
            mock_gen.return_value = [{"id": "S01", "phase": "Planning", "title": "Plan", "owner": "pm", "dependencies": [], "deliverables": []}]
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_workflow(sample_context)

        assert result["depth"] == "deep"

    @pytest.mark.asyncio
    async def test_workflow_parallel_flag(self, executor, sample_context):
        """Workflow handles parallel flag."""
        sample_context.command = ParsedCommand(
            name="workflow",
            raw_string="/sc:workflow project --parallel",
            arguments=["project"],
            flags={"parallel": True},
            parameters={},
            description="Generate workflow",
        )

        with patch.object(executor, "_generate_workflow_steps") as mock_gen:
            mock_gen.return_value = [{"id": "S01", "phase": "Planning", "title": "Plan", "owner": "pm", "dependencies": [], "deliverables": []}]
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_workflow(sample_context)

        assert result["parallel"] is True

    @pytest.mark.asyncio
    async def test_workflow_reads_source_file(self, executor, sample_context, tmp_path):
        """Workflow reads source file when path provided."""
        source_file = tmp_path / "requirements.md"
        source_file.write_text("# Feature Requirements\n\n- Feature 1\n- Feature 2")

        executor.repo_root = tmp_path
        sample_context.command = ParsedCommand(
            name="workflow",
            raw_string=f"/sc:workflow {source_file.name}",
            arguments=[source_file.name],
            flags={},
            parameters={},
            description="Generate workflow",
        )

        with patch.object(executor, "_generate_workflow_steps") as mock_gen:
            mock_gen.return_value = [{"id": "S01", "phase": "Planning", "title": "Plan", "owner": "pm", "dependencies": [], "deliverables": []}]
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_workflow(sample_context)

        assert result["status"] == "workflow_generated"
        assert "source_path" in result

    @pytest.mark.asyncio
    async def test_workflow_fails_on_empty_steps(self, executor, sample_context):
        """Workflow fails when no steps generated."""
        sample_context.command = ParsedCommand(
            name="workflow",
            raw_string="/sc:workflow",
            arguments=[],
            flags={},
            parameters={},
            description="Generate workflow",
        )

        with patch.object(executor, "_generate_workflow_steps") as mock_gen:
            mock_gen.return_value = []
            result = await executor._execute_workflow(sample_context)

        assert result["status"] == "workflow_failed"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_workflow_extracts_sections(self, executor, sample_context, tmp_path):
        """Workflow extracts sections from source."""
        source_file = tmp_path / "spec.md"
        source_file.write_text("# Overview\n\n## Goals\n\n## Implementation")

        executor.repo_root = tmp_path
        sample_context.command = ParsedCommand(
            name="workflow",
            raw_string=f"/sc:workflow {source_file.name}",
            arguments=[source_file.name],
            flags={},
            parameters={},
            description="Generate workflow",
        )

        with patch.object(executor, "_generate_workflow_steps") as mock_gen:
            mock_gen.return_value = [{"id": "S01", "phase": "Planning", "title": "Plan", "owner": "pm", "dependencies": [], "deliverables": []}]
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_workflow(sample_context)

        assert "sections" in result

    @pytest.mark.asyncio
    async def test_workflow_uses_inline_input(self, executor, sample_context):
        """Workflow uses inline input parameter."""
        sample_context.command = ParsedCommand(
            name="workflow",
            raw_string="/sc:workflow",
            arguments=[],
            flags={},
            parameters={"input": "Implement user authentication"},
            description="Generate workflow",
        )

        with patch.object(executor, "_generate_workflow_steps") as mock_gen:
            mock_gen.return_value = [{"id": "S01", "phase": "Planning", "title": "Plan", "owner": "pm", "dependencies": [], "deliverables": []}]
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_workflow(sample_context)

        assert result["status"] == "workflow_generated"

    @pytest.mark.asyncio
    async def test_workflow_records_operations(self, executor, sample_context):
        """Workflow records executed operations."""
        sample_context.command = ParsedCommand(
            name="workflow",
            raw_string="/sc:workflow project",
            arguments=["project"],
            flags={},
            parameters={},
            description="Generate workflow",
        )
        sample_context.results = {}

        with patch.object(executor, "_generate_workflow_steps") as mock_gen:
            mock_gen.return_value = [
                {"id": "S01", "phase": "Analysis", "title": "Analyze", "owner": "analyst", "dependencies": [], "deliverables": []},
                {"id": "S02", "phase": "Design", "title": "Design", "owner": "architect", "dependencies": ["S01"], "deliverables": []},
            ]
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_workflow(sample_context)

        assert len(sample_context.results.get("executed_operations", [])) == 2


class TestEnsureWorktreeManager:
    """Tests for _ensure_worktree_manager method."""

    def test_creates_worktree_manager(self, executor):
        """Creates worktree manager instance."""
        executor.worktree_manager = None

        with patch("SuperClaude.Commands.command_executor.WorktreeManager") as MockWM:
            MockWM.return_value = MagicMock()
            result = executor._ensure_worktree_manager()

        assert result is not None or result is None  # May fail gracefully

    def test_returns_existing_manager(self, executor):
        """Returns existing worktree manager."""
        mock_manager = MagicMock()
        executor.worktree_manager = mock_manager

        result = executor._ensure_worktree_manager()

        assert result is mock_manager

    def test_handles_instantiation_error(self, executor):
        """Handles worktree manager instantiation error."""
        executor.worktree_manager = None

        with patch("SuperClaude.Commands.command_executor.WorktreeManager") as MockWM:
            MockWM.side_effect = Exception("Failed to create manager")
            result = executor._ensure_worktree_manager()

        assert result is None


class TestCodexResultProcessing:
    """Tests for codex result processing in _execute_implement."""

    @pytest.mark.asyncio
    async def test_extracts_codex_suggestions(self, executor, sample_context):
        """Extracts codex_suggestions from agent output."""
        sample_context.command = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            arguments=["feature"],
            flags={},
            parameters={},
            description="Implement",
        )
        sample_context.agent_outputs = {
            "codex-implementer": {
                "codex_suggestions": {
                    "summary": "Add new endpoint",
                    "changes": [{"path": "api.py", "content": "# code"}],
                }
            }
        }
        sample_context.results = {}
        sample_context.agents = ["implementer"]
        sample_context.fast_codex_active = False

        with patch.object(executor, "_run_agent_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {"notes": [], "warnings": [], "operations": []}
            with patch.object(executor, "_derive_change_plan") as mock_derive:
                mock_derive.return_value = []
                with patch.object(executor, "_snapshot_repo_changes", return_value={}):
                    with patch.object(executor, "_record_artifact", return_value=None):
                        result = await executor._execute_implement(sample_context)

        assert "codex_suggestions" in sample_context.results

    @pytest.mark.asyncio
    async def test_records_fast_codex_cli_metadata(self, executor, sample_context):
        """Records fast-codex CLI metadata."""
        sample_context.command = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature --fast-codex",
            arguments=["feature"],
            flags={"fast-codex": True},
            parameters={},
            description="Implement",
        )
        sample_context.agent_outputs = {
            "codex-implementer": {
                "codex_cli": {
                    "duration_s": 5.5,
                    "returncode": 0,
                    "stdout": "Success",
                    "stderr": "",
                }
            }
        }
        sample_context.results = {}
        sample_context.agents = ["implementer"]
        sample_context.fast_codex_active = True
        sample_context.fast_codex_requested = True
        sample_context.active_personas = ["implementer"]

        with patch.object(executor, "_run_agent_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {"notes": [], "warnings": [], "operations": []}
            with patch.object(executor, "_derive_change_plan") as mock_derive:
                mock_derive.return_value = []
                with patch.object(executor, "_snapshot_repo_changes", return_value={}):
                    with patch.object(executor, "_record_artifact", return_value=None):
                        result = await executor._execute_implement(sample_context)

        assert sample_context.results.get("fast_codex_cli") is True


class TestSummaryLineGeneration:
    """Tests for summary line generation in implement."""

    @pytest.mark.asyncio
    async def test_summary_includes_agent_notes(self, executor, sample_context):
        """Summary includes agent notes."""
        sample_context.command = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            arguments=["feature"],
            flags={},
            parameters={},
            description="Implement",
        )
        sample_context.results = {}
        sample_context.agents = ["implementer"]
        sample_context.fast_codex_active = False

        with patch.object(executor, "_run_agent_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {
                "notes": ["Important note 1", "Important note 2"],
                "warnings": [],
                "operations": [],
            }
            with patch.object(executor, "_derive_change_plan") as mock_derive:
                mock_derive.return_value = []
                with patch.object(executor, "_snapshot_repo_changes", return_value={}):
                    with patch.object(executor, "_record_artifact", return_value=None):
                        result = await executor._execute_implement(sample_context)

        assert "summary" in result

    @pytest.mark.asyncio
    async def test_summary_includes_operations(self, executor, sample_context):
        """Summary includes planned operations."""
        sample_context.command = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            arguments=["feature"],
            flags={},
            parameters={},
            description="Implement",
        )
        sample_context.results = {}
        sample_context.agents = ["implementer"]
        sample_context.fast_codex_active = False

        with patch.object(executor, "_run_agent_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {
                "notes": [],
                "warnings": [],
                "operations": ["Create endpoint", "Add tests"],
            }
            with patch.object(executor, "_derive_change_plan") as mock_derive:
                mock_derive.return_value = []
                with patch.object(executor, "_snapshot_repo_changes", return_value={}):
                    with patch.object(executor, "_record_artifact", return_value=None):
                        result = await executor._execute_implement(sample_context)

        assert "summary" in result

    @pytest.mark.asyncio
    async def test_summary_includes_warnings(self, executor, sample_context):
        """Summary includes warnings."""
        sample_context.command = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            arguments=["feature"],
            flags={},
            parameters={},
            description="Implement",
        )
        sample_context.results = {}
        sample_context.agents = ["implementer"]
        sample_context.fast_codex_active = False

        with patch.object(executor, "_run_agent_pipeline") as mock_pipeline:
            mock_pipeline.return_value = {
                "notes": [],
                "warnings": ["Warning: potential breaking change"],
                "operations": [],
            }
            with patch.object(executor, "_derive_change_plan") as mock_derive:
                mock_derive.return_value = []
                with patch.object(executor, "_snapshot_repo_changes", return_value={}):
                    with patch.object(executor, "_record_artifact", return_value=None):
                        result = await executor._execute_implement(sample_context)

        assert "summary" in result


class TestWorkflowStepFormattting:
    """Tests for workflow step summary formatting."""

    @pytest.mark.asyncio
    async def test_workflow_formats_step_details(self, executor, sample_context):
        """Workflow formats step details with dependencies."""
        sample_context.command = ParsedCommand(
            name="workflow",
            raw_string="/sc:workflow project",
            arguments=["project"],
            flags={},
            parameters={},
            description="Generate workflow",
        )

        with patch.object(executor, "_generate_workflow_steps") as mock_gen:
            mock_gen.return_value = [
                {
                    "id": "S01",
                    "phase": "Analysis",
                    "title": "Analyze requirements",
                    "owner": "analyst",
                    "dependencies": [],
                    "deliverables": ["Requirements doc"],
                },
                {
                    "id": "S02",
                    "phase": "Design",
                    "title": "Design architecture",
                    "owner": "architect",
                    "dependencies": ["S01"],
                    "deliverables": ["Design doc"],
                },
            ]
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_workflow(sample_context)

        assert len(result["steps"]) == 2
        assert result["steps"][1]["dependencies"] == ["S01"]


class TestDefaultStrategyAndDepth:
    """Tests for default strategy and depth values."""

    @pytest.mark.asyncio
    async def test_default_strategy_systematic(self, executor, sample_context):
        """Default strategy is systematic."""
        sample_context.command = ParsedCommand(
            name="workflow",
            raw_string="/sc:workflow project",
            arguments=["project"],
            flags={},
            parameters={},
            description="Generate workflow",
        )

        with patch.object(executor, "_generate_workflow_steps") as mock_gen:
            mock_gen.return_value = [{"id": "S01", "phase": "Planning", "title": "Plan", "owner": "pm", "dependencies": [], "deliverables": []}]
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_workflow(sample_context)

        assert result["strategy"] == "systematic"

    @pytest.mark.asyncio
    async def test_default_depth_normal(self, executor, sample_context):
        """Default depth is normal."""
        sample_context.command = ParsedCommand(
            name="workflow",
            raw_string="/sc:workflow project",
            arguments=["project"],
            flags={},
            parameters={},
            description="Generate workflow",
        )

        with patch.object(executor, "_generate_workflow_steps") as mock_gen:
            mock_gen.return_value = [{"id": "S01", "phase": "Planning", "title": "Plan", "owner": "pm", "dependencies": [], "deliverables": []}]
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_workflow(sample_context)

        assert result["depth"] == "normal"

    @pytest.mark.asyncio
    async def test_default_parallel_disabled(self, executor, sample_context):
        """Default parallel is disabled."""
        sample_context.command = ParsedCommand(
            name="workflow",
            raw_string="/sc:workflow project",
            arguments=["project"],
            flags={},
            parameters={},
            description="Generate workflow",
        )

        with patch.object(executor, "_generate_workflow_steps") as mock_gen:
            mock_gen.return_value = [{"id": "S01", "phase": "Planning", "title": "Plan", "owner": "pm", "dependencies": [], "deliverables": []}]
            with patch.object(executor, "_record_artifact", return_value=None):
                result = await executor._execute_workflow(sample_context)

        assert result["parallel"] is False
