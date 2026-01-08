"""
Tests for sc-pr-fix skill scripts.

Tests cover:
- check_pr_status.py - PR check status polling via gh CLI
- parse_check_failures.py - CI failure log parsing
- fix_orchestrator.py - Fix loop coordination
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add skill scripts to path
SKILL_SCRIPTS_PATH = Path(__file__).parent.parent.parent / ".claude/skills/sc-pr-fix/scripts"
sys.path.insert(0, str(SKILL_SCRIPTS_PATH))

# Imports from skill scripts - must be after path modification
# ruff: noqa: E402
from check_pr_status import (
    CheckResult,
    PRCheckStatus,
    format_status_summary,
    get_failed_checks,
    get_pr_checks,
)
from fix_orchestrator import (
    HARD_MAX_ITERATIONS,
    STAGNATION_THRESHOLD,
    FixAction,
    FixAttempt,
    FixLoopState,
    TerminationReason,
    detect_oscillation,
    detect_stagnation,
    format_prompt,
    get_error_signature,
    parse_user_input,
    should_auto_fix,
)
from parse_check_failures import (
    FailureType,
    ParsedError,
    ParsedFailure,
    RiskLevel,
    detect_failure_type,
    parse_eslint_errors,
    parse_failure_logs,
    parse_jest_errors,
    parse_pytest_errors,
    parse_ruff_errors,
)

# Fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "pr_fix"


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def gh_checks_success() -> list[dict]:
    """Load successful checks fixture."""
    with open(FIXTURES_DIR / "gh_pr_checks_success.json") as f:
        return json.load(f)


@pytest.fixture
def gh_checks_failed() -> list[dict]:
    """Load failed checks fixture."""
    with open(FIXTURES_DIR / "gh_pr_checks_failed.json") as f:
        return json.load(f)


@pytest.fixture
def gh_checks_pending() -> list[dict]:
    """Load pending checks fixture."""
    with open(FIXTURES_DIR / "gh_pr_checks_pending.json") as f:
        return json.load(f)


@pytest.fixture
def eslint_log() -> str:
    """Load ESLint failure log fixture."""
    return (FIXTURES_DIR / "eslint_failure.log").read_text()


@pytest.fixture
def ruff_log() -> str:
    """Load ruff failure log fixture."""
    return (FIXTURES_DIR / "ruff_failure.log").read_text()


@pytest.fixture
def pytest_log() -> str:
    """Load pytest failure log fixture."""
    return (FIXTURES_DIR / "pytest_failure.log").read_text()


@pytest.fixture
def jest_log() -> str:
    """Load Jest failure log fixture."""
    return (FIXTURES_DIR / "jest_failure.log").read_text()


# =============================================================================
# Tests for check_pr_status.py
# =============================================================================


class TestCheckResult:
    """Tests for CheckResult dataclass."""

    def test_is_passed_with_success(self) -> None:
        """CheckResult.is_passed returns True for success conclusion."""
        check = CheckResult(
            name="test",
            state="completed",
            conclusion="success",
            url="https://example.com",
        )
        assert check.is_passed is True
        assert check.is_failed is False
        assert check.is_pending is False

    def test_is_failed_with_failure(self) -> None:
        """CheckResult.is_failed returns True for failure conclusion."""
        check = CheckResult(
            name="test",
            state="completed",
            conclusion="failure",
            url="https://example.com",
        )
        assert check.is_failed is True
        assert check.is_passed is False
        assert check.is_pending is False

    def test_is_failed_with_timed_out(self) -> None:
        """CheckResult.is_failed returns True for timed_out conclusion."""
        check = CheckResult(
            name="test",
            state="completed",
            conclusion="timed_out",
            url=None,
        )
        assert check.is_failed is True

    def test_is_pending_with_in_progress(self) -> None:
        """CheckResult.is_pending returns True for in_progress state."""
        check = CheckResult(
            name="test",
            state="in_progress",
            conclusion=None,
            url="https://example.com",
        )
        assert check.is_pending is True
        assert check.is_passed is False
        assert check.is_failed is False

    def test_is_pending_with_queued(self) -> None:
        """CheckResult.is_pending returns True for queued state."""
        check = CheckResult(
            name="test",
            state="queued",
            conclusion=None,
            url=None,
        )
        assert check.is_pending is True

    def test_to_dict(self) -> None:
        """CheckResult.to_dict returns correct dictionary."""
        check = CheckResult(
            name="lint",
            state="completed",
            conclusion="success",
            url="https://example.com",
        )
        result = check.to_dict()
        assert result["name"] == "lint"
        assert result["state"] == "completed"
        assert result["conclusion"] == "success"
        assert result["is_passed"] is True
        assert result["is_failed"] is False
        assert result["is_pending"] is False


class TestPRCheckStatus:
    """Tests for PRCheckStatus dataclass."""

    def test_all_passed_when_all_success(self, gh_checks_success: list[dict]) -> None:
        """PRCheckStatus.all_passed is True when all checks succeed."""
        checks = [
            CheckResult(
                name=c["name"],
                state=c["state"],
                conclusion=c["conclusion"],
                url=c.get("detailsUrl"),
            )
            for c in gh_checks_success
        ]
        status = PRCheckStatus(
            pr_number=42,
            checks=checks,
            all_passed=True,
            any_failed=False,
            any_pending=False,
            passed_count=3,
            failed_count=0,
            pending_count=0,
        )
        assert status.all_passed is True
        assert status.any_failed is False

    def test_any_failed_when_some_fail(self, gh_checks_failed: list[dict]) -> None:
        """PRCheckStatus.any_failed is True when some checks fail."""
        checks = [
            CheckResult(
                name=c["name"],
                state=c["state"],
                conclusion=c["conclusion"],
                url=c.get("detailsUrl"),
            )
            for c in gh_checks_failed
        ]
        failed = [c for c in checks if c.is_failed]
        passed = [c for c in checks if c.is_passed]

        status = PRCheckStatus(
            pr_number=42,
            checks=checks,
            all_passed=False,
            any_failed=True,
            any_pending=False,
            passed_count=len(passed),
            failed_count=len(failed),
            pending_count=0,
        )
        assert status.any_failed is True
        assert status.all_passed is False
        assert status.failed_count == 2

    def test_to_dict_includes_status(self) -> None:
        """PRCheckStatus.to_dict includes computed status field."""
        status = PRCheckStatus(
            pr_number=42,
            checks=[],
            all_passed=False,
            any_failed=True,
            any_pending=False,
            passed_count=1,
            failed_count=2,
            pending_count=0,
        )
        result = status.to_dict()
        assert result["status"] == "failed"
        assert result["pr_number"] == 42


class TestGetPRChecks:
    """Tests for get_pr_checks function."""

    @patch("check_pr_status.subprocess.run")
    def test_get_pr_checks_success(
        self, mock_run: MagicMock, gh_checks_success: list[dict]
    ) -> None:
        """get_pr_checks parses successful gh CLI output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(gh_checks_success),
            stderr="",
        )

        result = get_pr_checks(42)

        assert result.pr_number == 42
        assert result.all_passed is True
        assert result.passed_count == 3
        assert result.error is None
        mock_run.assert_called_once()

    @patch("check_pr_status.subprocess.run")
    def test_get_pr_checks_with_failures(
        self, mock_run: MagicMock, gh_checks_failed: list[dict]
    ) -> None:
        """get_pr_checks correctly identifies failed checks."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(gh_checks_failed),
            stderr="",
        )

        result = get_pr_checks(42)

        assert result.any_failed is True
        assert result.failed_count == 2
        assert result.passed_count == 1

    @patch("check_pr_status.subprocess.run")
    def test_get_pr_checks_cli_error(self, mock_run: MagicMock) -> None:
        """get_pr_checks handles gh CLI errors."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="gh: Not Found (HTTP 404)",
        )

        result = get_pr_checks(999)

        assert result.error is not None
        assert "Not Found" in result.error
        assert len(result.checks) == 0

    @patch("check_pr_status.subprocess.run")
    def test_get_pr_checks_with_repo(self, mock_run: MagicMock) -> None:
        """get_pr_checks passes repo argument to gh CLI."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="[]",
            stderr="",
        )

        get_pr_checks(42, repo="owner/repo")

        call_args = mock_run.call_args[0][0]
        assert "--repo" in call_args
        assert "owner/repo" in call_args


class TestGetFailedChecks:
    """Tests for get_failed_checks helper."""

    def test_extracts_only_failed(self, gh_checks_failed: list[dict]) -> None:
        """get_failed_checks returns only failed checks."""
        checks = [
            CheckResult(
                name=c["name"],
                state=c["state"],
                conclusion=c["conclusion"],
                url=c.get("detailsUrl"),
            )
            for c in gh_checks_failed
        ]
        status = PRCheckStatus(
            pr_number=42,
            checks=checks,
            all_passed=False,
            any_failed=True,
            any_pending=False,
            passed_count=1,
            failed_count=2,
            pending_count=0,
        )

        failed = get_failed_checks(status)

        assert len(failed) == 2
        assert all(c.is_failed for c in failed)


class TestFormatStatusSummary:
    """Tests for format_status_summary function."""

    def test_format_all_passed(self) -> None:
        """format_status_summary shows success message when all pass."""
        status = PRCheckStatus(
            pr_number=42,
            checks=[],
            all_passed=True,
            any_failed=False,
            any_pending=False,
            passed_count=3,
            failed_count=0,
            pending_count=0,
        )

        summary = format_status_summary(status)

        assert "All 3 checks passed" in summary
        assert "#42" in summary

    def test_format_with_failures(self) -> None:
        """format_status_summary lists failed checks."""
        check = CheckResult(
            name="lint",
            state="completed",
            conclusion="failure",
            url="https://example.com",
        )
        status = PRCheckStatus(
            pr_number=42,
            checks=[check],
            all_passed=False,
            any_failed=True,
            any_pending=False,
            passed_count=0,
            failed_count=1,
            pending_count=0,
        )

        summary = format_status_summary(status)

        assert "Failed: 1" in summary
        assert "lint" in summary


# =============================================================================
# Tests for parse_check_failures.py
# =============================================================================


class TestDetectFailureType:
    """Tests for detect_failure_type function."""

    def test_detect_lint_from_name(self) -> None:
        """detect_failure_type identifies lint from check name."""
        assert detect_failure_type("lint", "") == FailureType.LINT
        assert detect_failure_type("eslint", "") == FailureType.LINT
        assert detect_failure_type("ruff check", "") == FailureType.LINT

    def test_detect_test_from_name(self) -> None:
        """detect_failure_type identifies test from check name."""
        assert detect_failure_type("test", "") == FailureType.TEST
        assert detect_failure_type("pytest", "") == FailureType.TEST
        assert detect_failure_type("jest", "") == FailureType.TEST

    def test_detect_build_from_name(self) -> None:
        """detect_failure_type identifies build from check name."""
        assert detect_failure_type("build", "") == FailureType.BUILD
        assert detect_failure_type("compile", "") == FailureType.BUILD
        assert detect_failure_type("tsc", "") == FailureType.BUILD

    def test_detect_security_from_name(self) -> None:
        """detect_failure_type identifies security from check name."""
        assert detect_failure_type("security", "") == FailureType.SECURITY
        assert detect_failure_type("snyk", "") == FailureType.SECURITY
        assert detect_failure_type("codeql", "") == FailureType.SECURITY

    def test_detect_from_logs_fallback(self) -> None:
        """detect_failure_type falls back to log content."""
        assert detect_failure_type("ci", "eslint errors") == FailureType.LINT
        assert detect_failure_type("ci", "ruff found 5 errors") == FailureType.LINT
        assert detect_failure_type("ci", "pytest collected") == FailureType.TEST

    def test_unknown_type(self) -> None:
        """detect_failure_type returns UNKNOWN for unrecognized."""
        assert detect_failure_type("random-job", "no clues") == FailureType.UNKNOWN


class TestParseEslintErrors:
    """Tests for parse_eslint_errors function."""

    def test_parse_eslint_log(self, eslint_log: str) -> None:
        """parse_eslint_errors extracts errors from ESLint output."""
        errors = parse_eslint_errors(eslint_log)

        assert len(errors) >= 3
        # Check first error
        semi_errors = [e for e in errors if e.rule == "semi"]
        assert len(semi_errors) >= 1
        assert semi_errors[0].line == 42
        assert semi_errors[0].column == 15
        assert semi_errors[0].severity == "error"

    def test_parse_eslint_extracts_file(self, eslint_log: str) -> None:
        """parse_eslint_errors extracts file paths."""
        errors = parse_eslint_errors(eslint_log)

        files = {e.file for e in errors}
        assert any("Button.tsx" in f for f in files)

    def test_parse_eslint_marks_fixable(self, eslint_log: str) -> None:
        """parse_eslint_errors marks errors as fixable."""
        errors = parse_eslint_errors(eslint_log)

        assert all(e.fixable for e in errors)
        assert all(e.risk_level == RiskLevel.LOW for e in errors)


class TestParseRuffErrors:
    """Tests for parse_ruff_errors function."""

    def test_parse_ruff_log(self, ruff_log: str) -> None:
        """parse_ruff_errors extracts errors from ruff output."""
        errors = parse_ruff_errors(ruff_log)

        assert len(errors) == 4
        # Check E501 error
        e501_errors = [e for e in errors if e.rule == "E501"]
        assert len(e501_errors) == 1
        assert e501_errors[0].line == 42
        assert "too long" in e501_errors[0].message.lower()

    def test_parse_ruff_extracts_codes(self, ruff_log: str) -> None:
        """parse_ruff_errors extracts error codes."""
        errors = parse_ruff_errors(ruff_log)

        rules = {e.rule for e in errors}
        assert "E501" in rules
        assert "F401" in rules
        assert "E302" in rules
        assert "I001" in rules


class TestParsePytestErrors:
    """Tests for parse_pytest_errors function."""

    def test_parse_pytest_log(self, pytest_log: str) -> None:
        """parse_pytest_errors extracts failures from pytest output."""
        errors = parse_pytest_errors(pytest_log)

        assert len(errors) >= 2
        # Check for test names
        messages = " ".join(e.message for e in errors)
        assert "validate_token" in messages or "test_auth" in messages.lower()

    def test_parse_pytest_risk_level(self, pytest_log: str) -> None:
        """parse_pytest_errors marks test failures as MEDIUM risk."""
        errors = parse_pytest_errors(pytest_log)

        assert all(e.risk_level == RiskLevel.MEDIUM for e in errors)
        assert all(e.fixable is False for e in errors)


class TestParseJestErrors:
    """Tests for parse_jest_errors function."""

    def test_parse_jest_log(self, jest_log: str) -> None:
        """parse_jest_errors extracts failures from Jest output."""
        errors = parse_jest_errors(jest_log)

        # Should find at least the FAIL files
        assert len(errors) >= 1


class TestParseFailureLogs:
    """Tests for parse_failure_logs function."""

    def test_parse_lint_failure(self, eslint_log: str) -> None:
        """parse_failure_logs correctly parses lint failures."""
        result = parse_failure_logs("lint", logs=eslint_log)

        assert result.failure_type == FailureType.LINT
        assert len(result.errors) >= 3
        assert result.confidence == "high"
        assert result.error is None

    def test_parse_test_failure(self, pytest_log: str) -> None:
        """parse_failure_logs correctly parses test failures."""
        result = parse_failure_logs("pytest", logs=pytest_log)

        assert result.failure_type == FailureType.TEST
        assert len(result.errors) >= 1

    def test_parse_no_logs_error(self) -> None:
        """parse_failure_logs returns error when no logs provided."""
        result = parse_failure_logs("test", run_url=None, logs=None)

        assert result.error is not None
        assert "No run_url or logs provided" in result.error


class TestParsedError:
    """Tests for ParsedError dataclass."""

    def test_to_dict(self) -> None:
        """ParsedError.to_dict returns correct dictionary."""
        error = ParsedError(
            file="src/test.py",
            line=42,
            column=15,
            rule="E501",
            message="Line too long",
            severity="error",
            fixable=True,
            suggested_fix="Wrap line",
            risk_level=RiskLevel.LOW,
        )

        result = error.to_dict()

        assert result["file"] == "src/test.py"
        assert result["line"] == 42
        assert result["risk_level"] == "low"


# =============================================================================
# Tests for fix_orchestrator.py
# =============================================================================


class TestDetectStagnation:
    """Tests for detect_stagnation function."""

    def test_stagnation_same_error_three_times(self) -> None:
        """detect_stagnation returns True when same error appears 3 times."""
        history = ["error_a", "error_a", "error_a"]
        assert detect_stagnation(history) is True

    def test_no_stagnation_different_errors(self) -> None:
        """detect_stagnation returns False for different errors."""
        history = ["error_a", "error_b", "error_c"]
        assert detect_stagnation(history) is False

    def test_no_stagnation_short_history(self) -> None:
        """detect_stagnation returns False for short history."""
        history = ["error_a", "error_a"]
        assert detect_stagnation(history) is False

    def test_stagnation_threshold(self) -> None:
        """detect_stagnation respects custom threshold."""
        history = ["error_a", "error_a", "error_a", "error_a", "error_a"]
        assert detect_stagnation(history, threshold=5) is True
        assert detect_stagnation(history[:4], threshold=5) is False


class TestDetectOscillation:
    """Tests for detect_oscillation function."""

    def test_oscillation_abab_pattern(self) -> None:
        """detect_oscillation returns True for A-B-A-B pattern."""
        history = ["error_a", "error_b", "error_a", "error_b"]
        assert detect_oscillation(history) is True

    def test_no_oscillation_different_errors(self) -> None:
        """detect_oscillation returns False for varied errors."""
        history = ["error_a", "error_b", "error_c", "error_d"]
        assert detect_oscillation(history) is False

    def test_no_oscillation_short_history(self) -> None:
        """detect_oscillation returns False for short history."""
        history = ["error_a", "error_b"]
        assert detect_oscillation(history) is False


class TestGetErrorSignature:
    """Tests for get_error_signature function."""

    def test_signature_no_errors(self) -> None:
        """get_error_signature returns 'no_errors' for empty list."""
        assert get_error_signature([]) == "no_errors"

    def test_signature_consistent(self) -> None:
        """get_error_signature returns consistent signature."""
        error = ParsedError(
            file="test.py",
            line=42,
            column=1,
            rule="E501",
            message="Line too long",
            severity="error",
            fixable=True,
            suggested_fix=None,
            risk_level=RiskLevel.LOW,
        )
        failure = ParsedFailure(
            check_name="lint",
            failure_type=FailureType.LINT,
            errors=[error],
        )

        sig1 = get_error_signature([failure])
        sig2 = get_error_signature([failure])

        assert sig1 == sig2
        assert "test.py:42" in sig1


class TestShouldAutoFix:
    """Tests for should_auto_fix function."""

    def test_auto_fix_lint_errors(self) -> None:
        """should_auto_fix returns True for low-risk lint errors."""
        error = ParsedError(
            file="test.py",
            line=42,
            column=1,
            rule="E501",
            message="Line too long",
            severity="error",
            fixable=True,
            suggested_fix="Wrap line",
            risk_level=RiskLevel.LOW,
        )
        failure = ParsedFailure(
            check_name="lint",
            failure_type=FailureType.LINT,
            errors=[error],
        )

        assert should_auto_fix(failure, failure.errors) is True

    def test_no_auto_fix_test_failures(self) -> None:
        """should_auto_fix returns False for test failures."""
        error = ParsedError(
            file="test.py",
            line=42,
            column=1,
            rule=None,
            message="AssertionError",
            severity="error",
            fixable=False,
            suggested_fix=None,
            risk_level=RiskLevel.MEDIUM,
        )
        failure = ParsedFailure(
            check_name="test",
            failure_type=FailureType.TEST,
            errors=[error],
        )

        assert should_auto_fix(failure, failure.errors) is False

    def test_no_auto_fix_high_risk(self) -> None:
        """should_auto_fix returns False for high-risk errors."""
        error = ParsedError(
            file="auth.py",
            line=42,
            column=1,
            rule="security",
            message="Hardcoded secret",
            severity="error",
            fixable=True,
            suggested_fix="Remove secret",
            risk_level=RiskLevel.HIGH,
        )
        failure = ParsedFailure(
            check_name="lint",
            failure_type=FailureType.LINT,
            errors=[error],
        )

        assert should_auto_fix(failure, failure.errors) is False


class TestParseUserInput:
    """Tests for parse_user_input function."""

    def test_apply_inputs(self) -> None:
        """parse_user_input recognizes apply commands."""
        assert parse_user_input("a") == FixAction.APPLY
        assert parse_user_input("A") == FixAction.APPLY
        assert parse_user_input("apply") == FixAction.APPLY
        assert parse_user_input("yes") == FixAction.APPLY
        assert parse_user_input("y") == FixAction.APPLY

    def test_skip_inputs(self) -> None:
        """parse_user_input recognizes skip commands."""
        assert parse_user_input("s") == FixAction.SKIP
        assert parse_user_input("S") == FixAction.SKIP
        assert parse_user_input("skip") == FixAction.SKIP

    def test_view_inputs(self) -> None:
        """parse_user_input recognizes view commands."""
        assert parse_user_input("v") == FixAction.VIEW_LOG
        assert parse_user_input("view") == FixAction.VIEW_LOG
        assert parse_user_input("log") == FixAction.VIEW_LOG

    def test_quit_inputs(self) -> None:
        """parse_user_input recognizes quit commands."""
        assert parse_user_input("q") == FixAction.QUIT
        assert parse_user_input("quit") == FixAction.QUIT
        assert parse_user_input("exit") == FixAction.QUIT
        assert parse_user_input("abort") == FixAction.QUIT

    def test_debug_inputs(self) -> None:
        """parse_user_input recognizes debug commands."""
        assert parse_user_input("d") == FixAction.DEBUG_PAL
        assert parse_user_input("debug") == FixAction.DEBUG_PAL
        assert parse_user_input("pal") == FixAction.DEBUG_PAL

    def test_default_to_apply(self) -> None:
        """parse_user_input defaults to APPLY for unknown input."""
        assert parse_user_input("unknown") == FixAction.APPLY
        assert parse_user_input("") == FixAction.APPLY


class TestFormatPrompt:
    """Tests for format_prompt function."""

    def test_prompt_contains_check_name(self) -> None:
        """format_prompt includes check name."""
        error = ParsedError(
            file="test.py",
            line=42,
            column=1,
            rule="E501",
            message="Line too long",
            severity="error",
            fixable=True,
            suggested_fix="Wrap line",
            risk_level=RiskLevel.LOW,
        )
        failure = ParsedFailure(
            check_name="lint-check",
            failure_type=FailureType.LINT,
            errors=[error],
        )

        prompt = format_prompt(failure, 1, 5)

        assert "lint-check" in prompt

    def test_prompt_shows_iteration(self) -> None:
        """format_prompt shows current iteration."""
        failure = ParsedFailure(
            check_name="lint",
            failure_type=FailureType.LINT,
            errors=[],
        )

        prompt = format_prompt(failure, 3, 5)

        assert "3 of 5" in prompt or "Attempt 3" in prompt

    def test_prompt_shows_error_summary(self) -> None:
        """format_prompt includes error summary."""
        error = ParsedError(
            file="test.py",
            line=42,
            column=15,
            rule="E501",
            message="Line too long",
            severity="error",
            fixable=True,
            suggested_fix="Wrap line",
            risk_level=RiskLevel.LOW,
        )
        failure = ParsedFailure(
            check_name="lint",
            failure_type=FailureType.LINT,
            errors=[error],
        )

        prompt = format_prompt(failure, 1, 5)

        assert "test.py" in prompt
        assert "42" in prompt


class TestFixLoopState:
    """Tests for FixLoopState dataclass."""

    def test_initial_state(self) -> None:
        """FixLoopState initializes with correct defaults."""
        state = FixLoopState(
            pr_number=42,
            repo="owner/repo",
            max_attempts=5,
            auto_fix=False,
        )

        assert state.current_iteration == 0
        assert state.fixes_applied == []
        assert state.error_history == []
        assert state.termination_reason is None

    def test_to_dict(self) -> None:
        """FixLoopState.to_dict returns correct dictionary."""
        state = FixLoopState(
            pr_number=42,
            repo="owner/repo",
            max_attempts=5,
            auto_fix=True,
        )
        state.termination_reason = TerminationReason.ALL_PASSED

        result = state.to_dict()

        assert result["pr_number"] == 42
        assert result["repo"] == "owner/repo"
        assert result["auto_fix"] is True
        assert result["termination_reason"] == "all_passed"


class TestFixAttempt:
    """Tests for FixAttempt dataclass."""

    def test_to_dict(self) -> None:
        """FixAttempt.to_dict returns correct dictionary."""
        attempt = FixAttempt(
            iteration=1,
            check_name="lint",
            errors_count=3,
            fix_type="auto",
            files_changed=["test.py"],
            user_approved=True,
            success=True,
        )

        result = attempt.to_dict()

        assert result["iteration"] == 1
        assert result["check_name"] == "lint"
        assert result["errors_count"] == 3
        assert result["fix_type"] == "auto"


class TestHardMaxIterations:
    """Tests for hard iteration cap."""

    def test_hard_max_is_five(self) -> None:
        """HARD_MAX_ITERATIONS is 5."""
        assert HARD_MAX_ITERATIONS == 5

    def test_stagnation_threshold_is_three(self) -> None:
        """STAGNATION_THRESHOLD is 3."""
        assert STAGNATION_THRESHOLD == 3


class TestTerminationReason:
    """Tests for TerminationReason enum."""

    def test_all_reasons_exist(self) -> None:
        """All termination reasons are defined."""
        assert TerminationReason.ALL_PASSED.value == "all_passed"
        assert TerminationReason.MAX_ATTEMPTS.value == "max_attempts"
        assert TerminationReason.STAGNATION.value == "stagnation"
        assert TerminationReason.OSCILLATION.value == "oscillation"
        assert TerminationReason.USER_ABORT.value == "user_abort"
        assert TerminationReason.ERROR.value == "error"
