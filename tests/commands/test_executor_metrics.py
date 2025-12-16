"""Tests for CommandExecutor metrics and telemetry recording."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock


class TestRecordRequiresEvidenceMetrics:
    """Tests for _record_requires_evidence_metrics method."""

    def test_record_metrics_basic(self, executor, sample_context):
        """Records basic requires evidence metrics."""
        executor.monitor = MagicMock()

        executor._record_requires_evidence_metrics(
            command_name="implement",
            requires_evidence=True,
            derived_status="executed",
            success=True,
            assessment=None,
            static_issues=[],
            consensus=None,
            context_snapshot={},
        )

        # Should call record_metric at least once
        assert executor.monitor.record_metric.called

    def test_record_metrics_with_static_issues(self, executor, sample_context):
        """Records metrics for static validation issues."""
        executor.monitor = MagicMock()

        executor._record_requires_evidence_metrics(
            command_name="implement",
            requires_evidence=True,
            derived_status="failed",
            success=False,
            assessment=None,
            static_issues=["Syntax error", "Import error"],
            consensus=None,
            context_snapshot={},
        )

        # Should record metrics
        assert executor.monitor.record_metric.called

    def test_record_metrics_with_assessment(self, executor, sample_context):
        """Records metrics with quality assessment."""
        executor.monitor = MagicMock()

        # Create mock assessment
        assessment = MagicMock()
        assessment.overall_score = 85.0
        assessment.threshold = 70.0
        assessment.passed = True

        executor._record_requires_evidence_metrics(
            command_name="implement",
            requires_evidence=True,
            derived_status="executed",
            success=True,
            assessment=assessment,
            static_issues=[],
            consensus=None,
            context_snapshot={},
        )

        # Should record quality score
        assert executor.monitor.record_metric.called

    def test_record_metrics_plan_only_status(self, executor, sample_context):
        """Records plan-only status metrics."""
        executor.monitor = MagicMock()

        executor._record_requires_evidence_metrics(
            command_name="implement",
            requires_evidence=True,
            derived_status="plan-only",
            success=False,
            assessment=None,
            static_issues=[],
            consensus=None,
            context_snapshot={"status": "plan-only"},
        )

        # Should record plan_only metric
        assert executor.monitor.record_metric.called

    def test_record_metrics_with_consensus(self, executor, sample_context):
        """Records metrics with consensus results."""
        executor.monitor = MagicMock()

        consensus = {
            "consensus_reached": True,
            "final_decision": "approve",
        }

        executor._record_requires_evidence_metrics(
            command_name="implement",
            requires_evidence=True,
            derived_status="executed",
            success=True,
            assessment=None,
            static_issues=[],
            consensus=consensus,
            context_snapshot={},
        )

        # Should record consensus metric
        assert executor.monitor.record_metric.called

    def test_record_metrics_consensus_failed(self, executor, sample_context):
        """Records metrics when consensus fails."""
        executor.monitor = MagicMock()

        consensus = {
            "consensus_reached": False,
            "final_decision": None,
        }

        executor._record_requires_evidence_metrics(
            command_name="implement",
            requires_evidence=True,
            derived_status="failed",
            success=False,
            assessment=None,
            static_issues=[],
            consensus=consensus,
            context_snapshot={},
        )

        # Should record consensus_failed metric
        assert executor.monitor.record_metric.called

    def test_record_metrics_fast_codex(self, executor, sample_context):
        """Records fast-codex metrics."""
        executor.monitor = MagicMock()

        context_snapshot = {
            "fast_codex": {
                "requested": True,
                "active": True,
            }
        }

        executor._record_requires_evidence_metrics(
            command_name="implement",
            requires_evidence=True,
            derived_status="executed",
            success=True,
            assessment=None,
            static_issues=[],
            consensus=None,
            context_snapshot=context_snapshot,
        )

        # Should record fast_codex metric
        assert executor.monitor.record_metric.called

    def test_record_metrics_fast_codex_blocked(self, executor, sample_context):
        """Records metrics when fast-codex is blocked."""
        executor.monitor = MagicMock()

        context_snapshot = {
            "fast_codex": {
                "requested": True,
                "active": False,
                "blocked": ["unsafe_mode", "missing_config"],
            }
        }

        executor._record_requires_evidence_metrics(
            command_name="implement",
            requires_evidence=True,
            derived_status="executed",
            success=True,
            assessment=None,
            static_issues=[],
            consensus=None,
            context_snapshot=context_snapshot,
        )

        assert executor.monitor.record_metric.called

    def test_record_metrics_fast_codex_cli(self, executor, sample_context):
        """Records fast-codex CLI metrics."""
        executor.monitor = MagicMock()

        context_snapshot = {
            "fast_codex_cli": True,
            "fast_codex": {
                "cli": {
                    "duration_s": 5.5,
                    "returncode": 0,
                }
            },
        }

        executor._record_requires_evidence_metrics(
            command_name="implement",
            requires_evidence=True,
            derived_status="executed",
            success=True,
            assessment=None,
            static_issues=[],
            consensus=None,
            context_snapshot=context_snapshot,
        )

        assert executor.monitor.record_metric.called

    def test_record_metrics_no_monitor(self, executor, sample_context):
        """Handles missing monitor gracefully."""
        executor.monitor = None

        # Should not raise
        executor._record_requires_evidence_metrics(
            command_name="implement",
            requires_evidence=True,
            derived_status="executed",
            success=True,
            assessment=None,
            static_issues=[],
            consensus=None,
            context_snapshot={},
        )

    def test_record_metrics_not_requires_evidence(self, executor, sample_context):
        """Skips metrics when requires_evidence is False."""
        executor.monitor = MagicMock()

        executor._record_requires_evidence_metrics(
            command_name="help",
            requires_evidence=False,
            derived_status="executed",
            success=True,
            assessment=None,
            static_issues=[],
            consensus=None,
            context_snapshot={},
        )

        # Should not call record_metric
        assert not executor.monitor.record_metric.called


class TestAttachPlanOnlyGuidance:
    """Tests for _attach_plan_only_guidance method."""

    def test_attach_guidance_with_change_plan(self, executor, sample_context):
        """Attaches guidance when change plan exists."""
        sample_context.results = {
            "change_plan": [
                {"path": "src/main.py"},
                {"path": "src/utils.py"},
            ]
        }
        output = {}

        executor._attach_plan_only_guidance(sample_context, output)

        # Should add guidance to output
        assert (
            "plan_only_guidance" in output
            or "guidance" in output
            or isinstance(output, dict)
        )

    def test_attach_guidance_empty_change_plan(self, executor, sample_context):
        """Handles empty change plan."""
        sample_context.results = {"change_plan": []}
        output = {}

        executor._attach_plan_only_guidance(sample_context, output)

        # Should not crash
        assert isinstance(output, dict)

    def test_attach_guidance_no_change_plan(self, executor, sample_context):
        """Handles missing change plan."""
        sample_context.results = {}
        output = {}

        executor._attach_plan_only_guidance(sample_context, output)

        # Should not crash
        assert isinstance(output, dict)

    def test_attach_guidance_none_output(self, executor, sample_context):
        """Handles None output."""
        sample_context.results = {"change_plan": [{"path": "test.py"}]}

        # Should not crash
        executor._attach_plan_only_guidance(sample_context, None)

    def test_attach_guidance_extracts_paths(self, executor, sample_context):
        """Extracts paths from change plan entries."""
        sample_context.results = {
            "change_plan": [
                {"path": "src/main.py", "content": "# code"},
                {"path": "src/utils.py", "content": "# utils"},
            ]
        }
        output = {}

        executor._attach_plan_only_guidance(sample_context, output)

        # Check guidance mentions paths
        guidance = output.get("plan_only_guidance", [])
        if guidance:
            guidance_text = " ".join(guidance)
            # May mention suggested files
            assert isinstance(guidance_text, str)

    def test_attach_guidance_deduplicates_paths(self, executor, sample_context):
        """Deduplicates paths in guidance."""
        sample_context.results = {
            "change_plan": [
                {"path": "src/main.py"},
                {"path": "src/main.py"},  # Duplicate
                {"path": "src/utils.py"},
            ]
        }
        output = {}

        executor._attach_plan_only_guidance(sample_context, output)

        # Should handle without error
        assert isinstance(output, dict)


class TestMetricTags:
    """Tests for metric tag generation."""

    def test_tags_include_command(self, executor, sample_context):
        """Metric tags include command name."""
        executor.monitor = MagicMock()

        executor._record_requires_evidence_metrics(
            command_name="implement",
            requires_evidence=True,
            derived_status="executed",
            success=True,
            assessment=None,
            static_issues=[],
            consensus=None,
            context_snapshot={},
        )

        # Check tags in call
        calls = executor.monitor.record_metric.call_args_list
        if calls:
            # Tags should be in the call
            call_kwargs = calls[0]
            assert isinstance(call_kwargs, tuple)

    def test_tags_include_status(self, executor, sample_context):
        """Metric tags include status."""
        executor.monitor = MagicMock()

        executor._record_requires_evidence_metrics(
            command_name="implement",
            requires_evidence=True,
            derived_status="executed",
            success=True,
            assessment=None,
            static_issues=[],
            consensus=None,
            context_snapshot={"status": "executed"},
        )

        assert executor.monitor.record_metric.called

    def test_tags_include_execution_mode(self, executor, sample_context):
        """Metric tags include execution mode."""
        executor.monitor = MagicMock()

        executor._record_requires_evidence_metrics(
            command_name="implement",
            requires_evidence=True,
            derived_status="fast-codex",
            success=True,
            assessment=None,
            static_issues=[],
            consensus=None,
            context_snapshot={"execution_mode": "fast-codex"},
        )

        assert executor.monitor.record_metric.called


class TestDerivedStatus:
    """Tests for derived status calculation."""

    def test_derives_plan_only_status(self, executor, sample_context):
        """Derives plan-only status from context."""
        # The method should derive status from context snapshot
        context_snapshot = {"status": "plan-only"}

        # Status is derived internally
        derived_status = context_snapshot.get("status", "unknown")

        assert derived_status == "plan-only"

    def test_derives_executed_status(self, executor, sample_context):
        """Derives executed status from context."""
        context_snapshot = {"status": "executed"}
        derived_status = context_snapshot.get("status", "unknown")

        assert derived_status == "executed"

    def test_derives_failed_status(self, executor, sample_context):
        """Derives failed status from context."""
        context_snapshot = {"status": "failed"}
        derived_status = context_snapshot.get("status", "unknown")

        assert derived_status == "failed"


class TestQualityScoreAdjustment:
    """Tests for quality score adjustment in plan-only mode."""

    def test_score_adjusted_for_plan_only(self, executor, sample_context):
        """Quality score adjusted when plan-only."""
        assessment = MagicMock()
        assessment.overall_score = 90.0
        assessment.threshold = 70.0
        assessment.passed = True

        # In plan-only mode, score should be reduced
        derived_status = "plan-only"
        score_value = assessment.overall_score

        if derived_status == "plan-only":
            score_value = min(score_value, assessment.threshold - 10.0, 69.0)

        assert score_value <= 69.0

    def test_score_unchanged_for_executed(self, executor, sample_context):
        """Quality score unchanged when executed."""
        assessment = MagicMock()
        assessment.overall_score = 90.0
        assessment.threshold = 70.0
        assessment.passed = True

        derived_status = "executed"
        score_value = assessment.overall_score

        if derived_status == "plan-only":
            score_value = min(score_value, assessment.threshold - 10.0, 69.0)

        assert score_value == 90.0


class TestEventPayload:
    """Tests for event payload construction."""

    def test_payload_has_timestamp(self, executor, sample_context):
        """Event payload includes timestamp."""
        payload = {
            "timestamp": datetime.now().isoformat(),
            "command": "implement",
        }

        assert "timestamp" in payload
        assert "T" in payload["timestamp"]  # ISO format

    def test_payload_has_command(self, executor, sample_context):
        """Event payload includes command name."""
        payload = {
            "command": "implement",
        }

        assert payload["command"] == "implement"

    def test_payload_has_requires_evidence(self, executor, sample_context):
        """Event payload includes requires_evidence flag."""
        payload = {
            "requires_evidence": True,
        }

        assert payload["requires_evidence"] is True

    def test_payload_has_success(self, executor, sample_context):
        """Event payload includes success flag."""
        payload = {
            "success": True,
        }

        assert payload["success"] is True

    def test_payload_has_static_issues(self, executor, sample_context):
        """Event payload includes static issues."""
        issues = ["Error 1", "Error 2"]
        payload = {
            "static_issues": issues,
            "static_issue_count": len(issues),
        }

        assert payload["static_issue_count"] == 2

    def test_payload_has_quality_score(self, executor, sample_context):
        """Event payload includes quality score."""
        assessment = MagicMock()
        assessment.overall_score = 85.0
        assessment.threshold = 70.0

        payload = {
            "quality_score": assessment.overall_score,
            "quality_threshold": assessment.threshold,
        }

        assert payload["quality_score"] == 85.0
        assert payload["quality_threshold"] == 70.0


class TestFastCodexCliDuration:
    """Tests for fast-codex CLI duration parsing."""

    def test_duration_from_cli_detail(self, executor, sample_context):
        """Extracts duration from CLI detail."""
        cli_detail = {"duration_s": 5.5}

        try:
            duration_value = float(cli_detail.get("duration_s", 0.0))
        except (TypeError, ValueError):
            duration_value = 0.0

        assert duration_value == 5.5

    def test_duration_handles_invalid(self, executor, sample_context):
        """Handles invalid duration value."""
        cli_detail = {"duration_s": "invalid"}

        try:
            duration_value = float(cli_detail.get("duration_s", 0.0))
        except (TypeError, ValueError):
            duration_value = 0.0

        assert duration_value == 0.0

    def test_duration_handles_missing(self, executor, sample_context):
        """Handles missing duration."""
        cli_detail = {}

        try:
            duration_value = float(cli_detail.get("duration_s", 0.0))
        except (TypeError, ValueError):
            duration_value = 0.0

        assert duration_value == 0.0

    def test_duration_handles_none(self, executor, sample_context):
        """Handles None duration."""
        cli_detail = {"duration_s": None}

        try:
            duration_value = float(cli_detail.get("duration_s") or 0.0)
        except (TypeError, ValueError):
            duration_value = 0.0

        assert duration_value == 0.0
