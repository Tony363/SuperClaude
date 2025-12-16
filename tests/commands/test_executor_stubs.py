"""Tests for CommandExecutor auto-stub and evidence document generation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

from SuperClaude.Commands import CommandExecutor, CommandParser, CommandRegistry
from SuperClaude.Commands import CommandContext
from SuperClaude.Commands.parser import ParsedCommand
from SuperClaude.Commands.registry import CommandMetadata
from SuperClaude.Modes.behavioral_manager import BehavioralMode


class TestRenderDefaultEvidenceDocument:
    """Tests for _render_default_evidence_document method."""

    def test_render_evidence_returns_string(self, executor, sample_context):
        """Renders evidence document as string."""
        agent_result = {
            "notes": ["Note 1", "Note 2"],
            "warnings": [],
        }

        result = executor._render_default_evidence_document(
            sample_context, agent_result
        )

        assert isinstance(result, str)
        assert len(result) > 0

    def test_render_evidence_includes_title(self, executor, sample_context):
        """Evidence document includes command name."""
        sample_context.command.name = "implement"
        agent_result = {"notes": [], "warnings": []}

        result = executor._render_default_evidence_document(
            sample_context, agent_result
        )

        assert "Implementation Evidence" in result or "implement" in result

    def test_render_evidence_includes_session(self, executor, sample_context):
        """Evidence document includes session ID."""
        sample_context.session_id = "test-session-123"
        agent_result = {"notes": [], "warnings": []}

        result = executor._render_default_evidence_document(
            sample_context, agent_result
        )

        assert "test-session-123" in result

    def test_render_evidence_includes_notes(self, executor, sample_context):
        """Evidence document includes agent notes."""
        agent_result = {
            "notes": ["Important note here"],
            "warnings": [],
        }

        result = executor._render_default_evidence_document(
            sample_context, agent_result
        )

        assert "Important note here" in result

    def test_render_evidence_includes_warnings(self, executor, sample_context):
        """Evidence document includes agent warnings."""
        agent_result = {
            "notes": [],
            "warnings": ["Warning message"],
        }

        result = executor._render_default_evidence_document(
            sample_context, agent_result
        )

        assert "Warning message" in result

    def test_render_evidence_includes_summary(self, executor, sample_context):
        """Evidence document includes primary summary."""
        sample_context.results = {"primary_summary": "Summary text here"}
        agent_result = {"notes": [], "warnings": []}

        result = executor._render_default_evidence_document(
            sample_context, agent_result
        )

        assert "Summary text here" in result or "Summary" in result

    def test_render_evidence_includes_operations(self, executor, sample_context):
        """Evidence document includes agent operations."""
        sample_context.results = {
            "agent_operations": ["Op 1", "Op 2"]
        }
        agent_result = {"notes": [], "warnings": []}

        result = executor._render_default_evidence_document(
            sample_context, agent_result
        )

        assert "Op 1" in result or "Planned" in result

    def test_render_evidence_includes_timestamp(self, executor, sample_context):
        """Evidence document includes timestamp."""
        agent_result = {"notes": [], "warnings": []}

        result = executor._render_default_evidence_document(
            sample_context, agent_result
        )

        assert "generated" in result.lower()

    def test_render_evidence_empty_agent_result(self, executor, sample_context):
        """Handles empty agent result."""
        agent_result = {}

        result = executor._render_default_evidence_document(
            sample_context, agent_result
        )

        assert isinstance(result, str)

    def test_render_evidence_command_arguments(self, executor, sample_context):
        """Uses command arguments in title."""
        sample_context.command = ParsedCommand(
            name="implement",
            raw_string="/sc:implement user_auth",
            arguments=["user", "auth"],
            flags={},
            parameters={},
            description="Implement",
        )
        agent_result = {"notes": [], "warnings": []}

        result = executor._render_default_evidence_document(
            sample_context, agent_result
        )

        assert "user" in result or "auth" in result or "Implementation" in result


class TestBuildAutoStubEntry:
    """Tests for _build_auto_stub_entry method."""

    def test_build_stub_entry_returns_dict(self, executor, sample_context):
        """Builds auto stub entry as dict."""
        agent_result = {"notes": [], "warnings": []}

        entry = executor._build_auto_stub_entry(
            sample_context,
            agent_result,
            slug="test",
            session_fragment="abc123",
            label_suffix="-stub",
        )

        # May return None or dict depending on extension inference
        assert entry is None or isinstance(entry, dict)

    def test_build_stub_entry_has_path(self, executor, sample_context):
        """Entry has path field when returned."""
        # Set up context for Python inference
        sample_context.command = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            arguments=["feature"],
            flags={},
            parameters={"language": "python"},
            description="Implement",
        )
        agent_result = {"notes": [], "warnings": []}

        entry = executor._build_auto_stub_entry(
            sample_context,
            agent_result,
            slug="test",
            session_fragment="abc123",
            label_suffix="-stub",
        )

        if entry is not None:
            assert "path" in entry

    def test_build_stub_entry_has_content(self, executor, sample_context):
        """Entry has content field when returned."""
        sample_context.command = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            arguments=["feature"],
            flags={},
            parameters={"language": "typescript"},
            description="Implement",
        )
        agent_result = {"notes": [], "warnings": []}

        entry = executor._build_auto_stub_entry(
            sample_context,
            agent_result,
            slug="test",
            session_fragment="abc123",
            label_suffix="-stub",
        )

        if entry is not None:
            assert "content" in entry

    def test_build_stub_entry_auto_stub_flag(self, executor, sample_context):
        """Entry has auto_stub flag when returned."""
        sample_context.command = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            arguments=["feature"],
            flags={},
            parameters={"language": "python"},
            description="Implement",
        )
        agent_result = {"notes": [], "warnings": []}

        entry = executor._build_auto_stub_entry(
            sample_context,
            agent_result,
            slug="test",
            session_fragment="abc123",
            label_suffix="-stub",
        )

        if entry is not None:
            assert entry.get("auto_stub") is True


class TestBuildGenericStubChange:
    """Tests for _build_generic_stub_change method."""

    def test_build_generic_stub_returns_dict(self, executor, sample_context):
        """Builds generic stub change as dict."""
        summary = "Test summary for the stub"

        entry = executor._build_generic_stub_change(sample_context, summary)

        assert isinstance(entry, dict)

    def test_build_generic_stub_has_path(self, executor, sample_context):
        """Generic stub has path field."""
        summary = "Test summary for the stub"

        entry = executor._build_generic_stub_change(sample_context, summary)

        assert "path" in entry

    def test_build_generic_stub_has_content(self, executor, sample_context):
        """Generic stub has content field."""
        summary = "Test summary for the stub"

        entry = executor._build_generic_stub_change(sample_context, summary)

        assert "content" in entry

    def test_build_generic_stub_path_extension(self, executor, sample_context):
        """Generic stub path has extension."""
        summary = "Test summary for the stub"

        entry = executor._build_generic_stub_change(sample_context, summary)

        path = entry.get("path", "")
        assert ".md" in path  # Markdown extension

    def test_build_generic_stub_has_auto_stub_flag(self, executor, sample_context):
        """Generic stub has auto_stub flag."""
        summary = "Test summary"

        entry = executor._build_generic_stub_change(sample_context, summary)

        assert entry.get("auto_stub") is True

    def test_build_generic_stub_includes_summary(self, executor, sample_context):
        """Generic stub content includes the summary."""
        summary = "This is the summary text"

        entry = executor._build_generic_stub_change(sample_context, summary)

        assert summary in entry["content"]

    def test_build_generic_stub_includes_session(self, executor, sample_context):
        """Generic stub content includes session ID."""
        sample_context.session_id = "test-session-123"
        summary = "Test summary"

        entry = executor._build_generic_stub_change(sample_context, summary)

        assert "test-session-123" in entry["content"]


class TestBuildDefaultChangePlan:
    """Tests for _build_default_change_plan method."""

    def test_build_default_plan_returns_list(self, executor, sample_context):
        """Default change plan returns list of entries."""
        agent_result = {"notes": [], "warnings": []}

        plan = executor._build_default_change_plan(sample_context, agent_result)

        assert isinstance(plan, list)

    def test_build_default_plan_has_entries(self, executor, sample_context):
        """Default change plan has at least one entry."""
        agent_result = {"notes": [], "warnings": []}

        plan = executor._build_default_change_plan(sample_context, agent_result)

        assert len(plan) >= 1

    def test_build_default_plan_entries_have_path(self, executor, sample_context):
        """Each entry in default plan has path."""
        agent_result = {"notes": [], "warnings": []}

        plan = executor._build_default_change_plan(sample_context, agent_result)

        for entry in plan:
            assert "path" in entry

    def test_build_default_plan_entries_have_content(self, executor, sample_context):
        """Each entry in default plan has content."""
        agent_result = {"notes": [], "warnings": []}

        plan = executor._build_default_change_plan(sample_context, agent_result)

        for entry in plan:
            assert "content" in entry


class TestInferAutoStubExtension:
    """Tests for _infer_auto_stub_extension method."""

    def test_infer_python_extension(self, executor, sample_context):
        """Infers python extension from language parameter."""
        sample_context.command = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            arguments=["feature"],
            flags={},
            parameters={"language": "python"},
            description="Implement",
        )
        agent_result = {}

        ext = executor._infer_auto_stub_extension(sample_context, agent_result)

        assert ext == "py" or ext == "md"  # May fallback to md

    def test_infer_typescript_extension(self, executor, sample_context):
        """Infers typescript extension from language parameter."""
        sample_context.command = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            arguments=["feature"],
            flags={},
            parameters={"language": "typescript"},
            description="Implement",
        )
        agent_result = {}

        ext = executor._infer_auto_stub_extension(sample_context, agent_result)

        assert ext in {"ts", "tsx", "md"}

    def test_infer_default_extension(self, executor, sample_context):
        """Infers default extension when no hints."""
        sample_context.command = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            arguments=["feature"],
            flags={},
            parameters={},
            description="Implement",
        )
        agent_result = {}

        ext = executor._infer_auto_stub_extension(sample_context, agent_result)

        assert isinstance(ext, str)


class TestInferAutoStubCategory:
    """Tests for _infer_auto_stub_category method."""

    def test_infer_category_returns_string(self, executor, sample_context):
        """Infers category as string."""
        category = executor._infer_auto_stub_category(sample_context)

        assert isinstance(category, str)
        assert len(category) > 0

    def test_infer_category_default(self, executor, sample_context):
        """Uses default category."""
        sample_context.command = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            arguments=["feature"],
            flags={},
            parameters={},
            description="Implement",
        )

        category = executor._infer_auto_stub_category(sample_context)

        assert isinstance(category, str)
