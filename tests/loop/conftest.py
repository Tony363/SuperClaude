"""Fixtures for loop invariant tests.

Provides deterministic assessors and recorded scenarios for testing:
- Loop termination logic
- PAL feedback incorporation
- Score history patterns
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from core.types import LoopConfig, QualityAssessment

# Import MCP fixtures for integration tests
# Using direct import instead of pytest_plugins to avoid double-registration
# when running tests across both directories
try:
    from tests.mcp.conftest import (  # noqa: F401
        FakeMCPServer,
        FakePALCodeReviewResponse,
        FakePALDebugResponse,
        FakeRubeSearchToolsResponse,
    )

    _MCP_FIXTURES_AVAILABLE = True
except ImportError:
    _MCP_FIXTURES_AVAILABLE = False


@dataclass
class FixtureAssessor:
    """Deterministic assessor that returns predefined scores."""

    scores: list[float]
    passed_at: float = 70.0
    improvements: list[str] = field(default_factory=list)
    _call_count: int = 0

    def assess(self, output: dict) -> QualityAssessment:
        """Return the next predefined score."""
        score = self.scores[min(self._call_count, len(self.scores) - 1)]
        self._call_count += 1

        return QualityAssessment(
            overall_score=score,
            passed=score >= self.passed_at,
            threshold=self.passed_at,
            band=self._get_band(score),
            improvements_needed=self.improvements if score < self.passed_at else [],
        )

    def _get_band(self, score: float) -> str:
        """Determine quality band from score."""
        if score >= 90:
            return "excellent"
        elif score >= 70:
            return "acceptable"
        elif score >= 50:
            return "needs_review"
        else:
            return "poor"

    def reset(self):
        """Reset call count for reuse."""
        self._call_count = 0


@dataclass
class FixtureSkillInvoker:
    """Deterministic skill invoker for testing."""

    outputs: list[dict] = field(default_factory=list)
    _call_count: int = 0

    def __post_init__(self):
        if not self.outputs:
            self.outputs = [
                {
                    "changes": ["main.py"],
                    "tests": {"ran": True, "passed": 10, "failed": 0},
                    "lint": {"ran": True, "errors": 0},
                    "changed_files": ["main.py"],
                }
            ]

    def __call__(self, context: dict) -> dict:
        """Return the next predefined output."""
        output = self.outputs[min(self._call_count, len(self.outputs) - 1)]
        self._call_count += 1
        return output

    def reset(self):
        """Reset call count for reuse."""
        self._call_count = 0


def load_fixture_scenario(name: str) -> dict:
    """Load a recorded scenario from fixtures directory."""
    fixture_path = Path(__file__).parent / "fixtures" / f"{name}.json"
    if fixture_path.exists():
        with open(fixture_path) as f:
            return json.load(f)
    return {}


@pytest.fixture
def fixture_assessor_quality_met():
    """Assessor that passes on first iteration."""
    return FixtureAssessor(scores=[85.0])


@pytest.fixture
def fixture_assessor_oscillating():
    """Assessor with oscillating scores (up/down pattern)."""
    return FixtureAssessor(scores=[50.0, 60.0, 52.0, 63.0, 55.0])


@pytest.fixture
def fixture_assessor_stagnating():
    """Assessor with stagnating scores (plateau)."""
    return FixtureAssessor(scores=[65.0, 65.5, 65.2, 65.3, 65.1])


@pytest.fixture
def fixture_assessor_improving():
    """Assessor with steadily improving scores."""
    return FixtureAssessor(scores=[50.0, 60.0, 70.0, 80.0])


@pytest.fixture
def fixture_assessor_insufficient_improvement():
    """Assessor with improvement below threshold."""
    return FixtureAssessor(scores=[50.0, 52.0, 54.0])  # Only +2 per iteration


@pytest.fixture
def fixture_skill_invoker():
    """Standard skill invoker for testing."""
    return FixtureSkillInvoker()


@pytest.fixture
def fixture_skill_invoker_with_errors():
    """Skill invoker that simulates errors."""

    def failing_invoker(context: dict) -> dict:
        raise ValueError("Skill execution failed")

    return failing_invoker


@pytest.fixture
def loop_config_default():
    """Default loop configuration."""
    return LoopConfig()


@pytest.fixture
def loop_config_strict():
    """Strict loop configuration with high thresholds."""
    return LoopConfig(
        max_iterations=3,
        quality_threshold=80.0,
        min_improvement=10.0,
    )


@pytest.fixture
def loop_config_lenient():
    """Lenient loop configuration with low thresholds."""
    return LoopConfig(
        max_iterations=5,
        quality_threshold=50.0,
        min_improvement=2.0,
    )


@pytest.fixture
def loop_config_with_timeout():
    """Loop configuration with short timeout for testing."""
    return LoopConfig(
        max_iterations=10,
        quality_threshold=95.0,
        timeout_seconds=0.1,
    )


@pytest.fixture
def oscillating_scenario():
    """Load oscillating scores scenario."""
    return load_fixture_scenario("oscillating_scores")


@pytest.fixture
def stagnating_scenario():
    """Load stagnating scores scenario."""
    return load_fixture_scenario("stagnating_scores")


@pytest.fixture
def improving_scenario():
    """Load improving scores scenario."""
    return load_fixture_scenario("improving_scores")


# MCP fixtures for loop integration tests
# These are only defined if the MCP conftest is available


@pytest.fixture
def fake_mcp_server():
    """Provide a fresh fake MCP server for each test."""
    if not _MCP_FIXTURES_AVAILABLE:
        pytest.skip("MCP fixtures not available")
    server = FakeMCPServer()
    yield server
    server.reset()


@pytest.fixture
def pal_codereview_with_issues():
    """Provide a PAL codereview response with issues found."""
    if not _MCP_FIXTURES_AVAILABLE:
        pytest.skip("MCP fixtures not available")
    return FakePALCodeReviewResponse(
        data={
            "issues_found": [
                {"severity": "critical", "description": "SQL injection vulnerability"},
                {"severity": "high", "description": "Missing input validation"},
                {"severity": "medium", "description": "Inconsistent error handling"},
            ],
            "review_type": "full",
            "step_number": 1,
            "total_steps": 2,
            "next_step_required": True,
            "findings": "Found 3 issues requiring attention.",
            "confidence": "high",
            "relevant_files": ["src/db.py", "src/api.py"],
        }
    )
