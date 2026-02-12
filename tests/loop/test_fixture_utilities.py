"""Tests for loop test fixture utilities.

Validates that FixtureAssessor and FixtureSkillInvoker behave correctly,
since other tests depend on their deterministic behavior.
"""

from tests.loop.conftest import (
    FixtureAssessor,
    FixtureSkillInvoker,
    load_fixture_scenario,
)


class TestFixtureAssessor:
    """Tests for FixtureAssessor deterministic assessor."""

    def test_returns_first_score(self):
        """First call should return first score."""
        assessor = FixtureAssessor(scores=[50.0, 60.0, 70.0])
        result = assessor.assess({})
        assert result.overall_score == 50.0

    def test_returns_sequential_scores(self):
        """Sequential calls should return sequential scores."""
        assessor = FixtureAssessor(scores=[50.0, 60.0, 70.0])
        r1 = assessor.assess({})
        r2 = assessor.assess({})
        r3 = assessor.assess({})
        assert r1.overall_score == 50.0
        assert r2.overall_score == 60.0
        assert r3.overall_score == 70.0

    def test_clamps_to_last_score(self):
        """Calls beyond score list should return the last score."""
        assessor = FixtureAssessor(scores=[50.0])
        r1 = assessor.assess({})
        r2 = assessor.assess({})
        assert r1.overall_score == 50.0
        assert r2.overall_score == 50.0

    def test_passed_when_score_meets_threshold(self):
        """Should return passed=True when score >= passed_at."""
        assessor = FixtureAssessor(scores=[75.0], passed_at=70.0)
        result = assessor.assess({})
        assert result.passed is True

    def test_not_passed_when_score_below_threshold(self):
        """Should return passed=False when score < passed_at."""
        assessor = FixtureAssessor(scores=[60.0], passed_at=70.0)
        result = assessor.assess({})
        assert result.passed is False

    def test_passed_at_exact_threshold(self):
        """Should return passed=True when score equals passed_at."""
        assessor = FixtureAssessor(scores=[70.0], passed_at=70.0)
        result = assessor.assess({})
        assert result.passed is True

    def test_custom_passed_at(self):
        """Should respect custom passed_at threshold."""
        assessor = FixtureAssessor(scores=[80.0], passed_at=85.0)
        result = assessor.assess({})
        assert result.passed is False

    def test_improvements_returned_when_not_passed(self):
        """Should return improvements when score below threshold."""
        assessor = FixtureAssessor(scores=[50.0], passed_at=70.0, improvements=["Fix A", "Fix B"])
        result = assessor.assess({})
        assert result.improvements_needed == ["Fix A", "Fix B"]

    def test_no_improvements_when_passed(self):
        """Should return empty improvements when score meets threshold."""
        assessor = FixtureAssessor(scores=[80.0], passed_at=70.0, improvements=["Fix A"])
        result = assessor.assess({})
        assert result.improvements_needed == []

    def test_band_excellent(self):
        """Score >= 90 should be 'excellent' band."""
        assessor = FixtureAssessor(scores=[95.0])
        result = assessor.assess({})
        assert result.band == "excellent"

    def test_band_acceptable(self):
        """Score 70-89 should be 'acceptable' band."""
        assessor = FixtureAssessor(scores=[75.0])
        result = assessor.assess({})
        assert result.band == "acceptable"

    def test_band_needs_review(self):
        """Score 50-69 should be 'needs_review' band."""
        assessor = FixtureAssessor(scores=[55.0])
        result = assessor.assess({})
        assert result.band == "needs_review"

    def test_band_poor(self):
        """Score < 50 should be 'poor' band."""
        assessor = FixtureAssessor(scores=[30.0])
        result = assessor.assess({})
        assert result.band == "poor"

    def test_threshold_in_result(self):
        """Result threshold should match passed_at."""
        assessor = FixtureAssessor(scores=[60.0], passed_at=80.0)
        result = assessor.assess({})
        assert result.threshold == 80.0

    def test_reset(self):
        """Reset should allow re-use of scores from the start."""
        assessor = FixtureAssessor(scores=[50.0, 80.0])
        assessor.assess({})  # Returns 50
        assessor.assess({})  # Returns 80
        assessor.reset()
        result = assessor.assess({})
        assert result.overall_score == 50.0

    def test_call_count_tracked(self):
        """Internal call count should track invocations."""
        assessor = FixtureAssessor(scores=[50.0, 60.0])
        assert assessor._call_count == 0
        assessor.assess({})
        assert assessor._call_count == 1
        assessor.assess({})
        assert assessor._call_count == 2


class TestFixtureSkillInvoker:
    """Tests for FixtureSkillInvoker deterministic skill invoker."""

    def test_default_output(self):
        """Default output should include standard evidence fields."""
        invoker = FixtureSkillInvoker()
        result = invoker({})
        assert "changes" in result
        assert "tests" in result
        assert "lint" in result
        assert "changed_files" in result

    def test_callable(self):
        """Should be callable."""
        invoker = FixtureSkillInvoker()
        assert callable(invoker)

    def test_custom_outputs(self):
        """Should return custom outputs sequentially."""
        outputs = [
            {"changes": ["a.py"], "changed_files": ["a.py"]},
            {"changes": ["b.py"], "changed_files": ["b.py"]},
        ]
        invoker = FixtureSkillInvoker(outputs=outputs)
        r1 = invoker({})
        r2 = invoker({})
        assert r1["changes"] == ["a.py"]
        assert r2["changes"] == ["b.py"]

    def test_clamps_to_last_output(self):
        """Calls beyond output list should return the last output."""
        outputs = [{"changes": ["only.py"], "changed_files": ["only.py"]}]
        invoker = FixtureSkillInvoker(outputs=outputs)
        r1 = invoker({})
        r2 = invoker({})
        assert r1["changes"] == ["only.py"]
        assert r2["changes"] == ["only.py"]

    def test_reset(self):
        """Reset should allow re-use of outputs from the start."""
        outputs = [
            {"changes": ["a.py"], "changed_files": ["a.py"]},
            {"changes": ["b.py"], "changed_files": ["b.py"]},
        ]
        invoker = FixtureSkillInvoker(outputs=outputs)
        invoker({})  # Returns a.py
        invoker({})  # Returns b.py
        invoker.reset()
        result = invoker({})
        assert result["changes"] == ["a.py"]

    def test_call_count_tracked(self):
        """Internal call count should track invocations."""
        invoker = FixtureSkillInvoker()
        assert invoker._call_count == 0
        invoker({})
        assert invoker._call_count == 1


class TestLoadFixtureScenario:
    """Tests for load_fixture_scenario()."""

    def test_missing_scenario_returns_empty(self):
        """Missing scenario file should return empty dict."""
        result = load_fixture_scenario("nonexistent_scenario")
        assert result == {}

    def test_returns_dict(self):
        """Should always return a dict."""
        result = load_fixture_scenario("whatever")
        assert isinstance(result, dict)
