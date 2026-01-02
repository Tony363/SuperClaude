"""Tests for PAL MCP response parsing and state updates.

Validates the signal→call→response→state pipeline for PAL tools:
- mcp__pal__codereview
- mcp__pal__debug
- mcp__pal__thinkdeep
- mcp__pal__consensus
"""

from core.pal_integration import PALReviewSignal, incorporate_pal_feedback
from core.types import QualityAssessment


class TestPALCodeReviewResponseParsing:
    """Tests for parsing mcp__pal__codereview responses."""

    def test_parse_success_response(self, fake_mcp_server):
        """Should correctly parse a successful codereview response."""
        response = fake_mcp_server.invoke(
            "mcp__pal__codereview",
            {"files": ["main.py"], "review_type": "full"},
        )

        assert response["success"] is True
        data = response["data"]

        # Verify we can extract expected fields
        issues = data.get("issues_found", [])
        assert isinstance(issues, list)

        findings = data.get("findings", "")
        assert isinstance(findings, str)

        confidence = data.get("confidence", "")
        assert confidence in [
            "exploring",
            "low",
            "medium",
            "high",
            "very_high",
            "almost_certain",
            "certain",
        ]

    def test_parse_response_with_issues(self, fake_mcp_server, pal_codereview_with_issues):
        """Should correctly parse issues from codereview response."""
        fake_mcp_server.set_response("mcp__pal__codereview", pal_codereview_with_issues)

        response = fake_mcp_server.invoke(
            "mcp__pal__codereview",
            {"files": ["src/db.py"]},
        )

        data = response["data"]
        issues = data["issues_found"]

        assert len(issues) == 3

        # Verify issue severity ordering is parseable
        severities = [issue["severity"] for issue in issues]
        assert "critical" in severities
        assert "high" in severities

    def test_incorporate_codereview_feedback_critical_issues(self, pal_codereview_with_issues):
        """Critical and high severity issues should be prepended to improvements."""
        context = {"improvements_needed": ["Existing improvement"]}
        feedback = pal_codereview_with_issues.to_dict()["data"]

        result = incorporate_pal_feedback(context, feedback)

        # Critical and high issues should come before existing improvements
        # The insert(0, ...) operation reverses order: high comes first, then critical
        assert "SQL injection vulnerability" in result["improvements_needed"][:3]
        assert "Missing input validation" in result["improvements_needed"][:3]

        # Existing improvements should be preserved
        assert "Existing improvement" in result["improvements_needed"]

    def test_incorporate_codereview_feedback_high_issues(self):
        """High severity issues should be prepended after critical."""
        context = {"improvements_needed": []}
        feedback = {
            "issues_found": [
                {"severity": "high", "description": "High priority fix"},
            ]
        }

        result = incorporate_pal_feedback(context, feedback)
        assert result["improvements_needed"][0] == "High priority fix"

    def test_incorporate_codereview_feedback_medium_issues(self):
        """Medium severity issues should be appended."""
        context = {"improvements_needed": ["First item"]}
        feedback = {
            "issues_found": [
                {"severity": "medium", "description": "Medium priority fix"},
            ]
        }

        result = incorporate_pal_feedback(context, feedback)
        assert result["improvements_needed"][-1] == "Medium priority fix"
        assert result["improvements_needed"][0] == "First item"

    def test_incorporate_codereview_feedback_max_10_issues(self):
        """Improvements should be capped at 10."""
        context = {"improvements_needed": [f"Issue {i}" for i in range(8)]}
        feedback = {
            "issues_found": [
                {"severity": "critical", "description": f"Critical {i}"} for i in range(5)
            ]
        }

        result = incorporate_pal_feedback(context, feedback)
        assert len(result["improvements_needed"]) == 10

    def test_incorporate_codereview_feedback_no_duplicates(self):
        """Duplicate issues should not be added."""
        context = {"improvements_needed": ["Fix the bug"]}
        feedback = {
            "issues_found": [
                {"severity": "critical", "description": "Fix the bug"},  # Duplicate
            ]
        }

        result = incorporate_pal_feedback(context, feedback)
        assert result["improvements_needed"].count("Fix the bug") == 1

    def test_parse_error_response(self, fake_mcp_server):
        """Should handle error responses gracefully."""
        fake_mcp_server.set_error_response("mcp__pal__codereview", "Rate limit exceeded")

        response = fake_mcp_server.invoke(
            "mcp__pal__codereview",
            {"files": ["main.py"]},
        )

        assert response["success"] is False
        assert response["error"] == "Rate limit exceeded"

        # Should not have data field with issues
        data = response.get("data", {})
        assert data == {}


class TestPALDebugResponseParsing:
    """Tests for parsing mcp__pal__debug responses."""

    def test_parse_success_response(self, fake_mcp_server):
        """Should correctly parse a successful debug response."""
        response = fake_mcp_server.invoke(
            "mcp__pal__debug",
            {"issue": "Application crash on startup"},
        )

        assert response["success"] is True
        data = response["data"]

        hypothesis = data.get("hypothesis", "")
        assert isinstance(hypothesis, str)
        assert len(hypothesis) > 0

        confidence = data.get("confidence", "")
        assert confidence in [
            "exploring",
            "low",
            "medium",
            "high",
            "very_high",
            "almost_certain",
            "certain",
        ]

    def test_parse_debug_with_relevant_files(self, fake_mcp_server):
        """Should parse relevant_files from debug response."""
        response = fake_mcp_server.invoke(
            "mcp__pal__debug",
            {"issue": "Memory leak"},
        )

        data = response["data"]
        relevant_files = data.get("relevant_files", [])
        assert isinstance(relevant_files, list)

    def test_generate_debug_signal_for_oscillation(self):
        """Should generate correct debug signal for oscillation."""
        signal = PALReviewSignal.generate_debug_signal(
            iteration=3,
            termination_reason="oscillation",
            score_history=[50.0, 60.0, 52.0, 61.0],
        )

        assert signal["action_required"] is True
        assert signal["tool"] == "mcp__pal__debug"
        assert signal["iteration"] == 3
        assert "oscillation" in signal["instruction"]
        assert signal["context"]["termination_reason"] == "oscillation"

    def test_generate_debug_signal_for_stagnation(self):
        """Should generate correct debug signal for stagnation."""
        signal = PALReviewSignal.generate_debug_signal(
            iteration=4,
            termination_reason="stagnation",
            score_history=[65.0, 65.5, 65.2, 65.3],
        )

        assert signal["tool"] == "mcp__pal__debug"
        assert signal["context"]["termination_reason"] == "stagnation"
        assert signal["context"]["score_history"] == [65.0, 65.5, 65.2, 65.3]


class TestPALReviewSignalGeneration:
    """Tests for PAL review signal generation and structure."""

    def test_generate_review_signal_basic(self):
        """Should generate correct review signal structure."""
        assessment = QualityAssessment(overall_score=60.0, passed=False)
        signal = PALReviewSignal.generate_review_signal(
            iteration=0,
            changed_files=["main.py"],
            quality_assessment=assessment,
        )

        assert signal["action_required"] is True
        assert signal["tool"] == "mcp__pal__codereview"
        assert signal["iteration"] == 0
        assert signal["files"] == ["main.py"]

    def test_generate_review_signal_includes_quality_context(self):
        """Signal context should include quality assessment info."""
        assessment = QualityAssessment(
            overall_score=55.0,
            passed=False,
            threshold=70.0,
            band="needs_review",
            improvements_needed=["Add tests", "Fix lint"],
        )
        signal = PALReviewSignal.generate_review_signal(
            iteration=1,
            changed_files=["src/app.py"],
            quality_assessment=assessment,
        )

        context = signal["context"]
        assert context["current_score"] == 55.0
        assert context["target_score"] == 70.0
        assert "Add tests" in context["improvements_needed"]

    def test_generate_review_signal_auto_type_low_score(self):
        """Auto review type should be 'full' for low scores."""
        assessment = QualityAssessment(overall_score=40.0, passed=False)
        signal = PALReviewSignal.generate_review_signal(
            iteration=0,
            changed_files=["main.py"],
            quality_assessment=assessment,
            review_type="auto",
        )

        assert signal["review_type"] == "full"

    def test_generate_review_signal_auto_type_later_iteration(self):
        """Auto review type should be 'full' for later iterations."""
        assessment = QualityAssessment(overall_score=60.0, passed=False)
        signal = PALReviewSignal.generate_review_signal(
            iteration=3,
            changed_files=["main.py"],
            quality_assessment=assessment,
            review_type="auto",
        )

        assert signal["review_type"] == "full"

    def test_generate_review_signal_custom_model(self):
        """Custom model should be included in signal."""
        assessment = QualityAssessment(overall_score=60.0, passed=False)
        signal = PALReviewSignal.generate_review_signal(
            iteration=0,
            changed_files=["main.py"],
            quality_assessment=assessment,
            model="gpt-5.2",
        )

        assert signal["model"] == "gpt-5.2"

    def test_generate_final_validation_signal(self):
        """Should generate correct final validation signal."""
        assessment = QualityAssessment(overall_score=85.0, passed=True)
        signal = PALReviewSignal.generate_final_validation_signal(
            changed_files=["main.py", "tests/test_main.py"],
            quality_assessment=assessment,
            iteration_count=3,
        )

        assert signal["action_required"] is True
        assert signal["tool"] == "mcp__pal__codereview"
        assert signal["is_final"] is True
        assert signal["review_type"] == "full"
        assert signal["context"]["final_score"] == 85.0
        assert signal["context"]["total_iterations"] == 3


class TestPALResponseStateUpdate:
    """Tests for updating state based on PAL responses."""

    def test_state_update_with_issues(self, fake_mcp_server, pal_codereview_with_issues):
        """State should be updated with issues from PAL response."""
        fake_mcp_server.set_response("mcp__pal__codereview", pal_codereview_with_issues)

        # Simulate the signal→call→response→state pipeline
        response = fake_mcp_server.invoke(
            "mcp__pal__codereview",
            {"files": ["src/db.py"]},
        )

        # Parse and incorporate into context
        context = {"improvements_needed": []}
        updated_context = incorporate_pal_feedback(context, response["data"])

        # Verify state was updated
        assert len(updated_context["improvements_needed"]) > 0
        assert "SQL injection vulnerability" in updated_context["improvements_needed"]

    def test_state_update_stores_pal_feedback(self):
        """PAL feedback should be stored in context."""
        context = {}
        feedback = {"tool": "codereview", "score": 80}

        result = incorporate_pal_feedback(context, feedback)
        assert result["pal_feedback"] == feedback

    def test_state_update_empty_feedback(self):
        """Empty feedback should not modify context."""
        context = {"task": "implement feature"}
        result = incorporate_pal_feedback(context, {})

        assert result["task"] == "implement feature"

    def test_state_update_no_issues(self):
        """Feedback without issues should not add improvements."""
        context = {"improvements_needed": []}
        result = incorporate_pal_feedback(context, {"issues_found": []})

        assert result["improvements_needed"] == []
