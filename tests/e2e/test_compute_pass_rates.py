"""Tests for the E2E pass rate computation script."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

# Import from the script directly
import sys

_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.compute_e2e_pass_rates import (
    compute_pass_rates,
    format_console,
    format_json,
    format_markdown,
    load_results,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    app_name: str = "test-app",
    passed: bool = True,
    gen_time: float = 10.0,
    val_time: float = 5.0,
    total_time: float = 15.0,
) -> dict:
    """Create a mock E2E result dict."""
    return {
        "app_name": app_name,
        "passed": passed,
        "generation_time_seconds": gen_time,
        "validation_time_seconds": val_time,
        "total_time_seconds": total_time,
        "reason": "All checks passed" if passed else "Tests failed",
    }


def _write_result(
    base_dir: Path,
    app_name: str,
    run: int,
    passed: bool = True,
) -> Path:
    """Write a result file to disk and return its path."""
    result_dir = base_dir / f"result-{app_name}-run{run}"
    result_dir.mkdir(parents=True, exist_ok=True)
    result_file = result_dir / "e2e-result.json"
    result_file.write_text(json.dumps(_make_result(app_name, passed)))
    return result_file


# ===========================================================================
# load_results
# ===========================================================================


class TestLoadResults:
    """Tests for load_results function."""

    def test_loads_valid_results(self, tmp_path: Path):
        """Test loading valid result files."""
        _write_result(tmp_path, "app-a", 1, passed=True)
        _write_result(tmp_path, "app-a", 2, passed=False)
        _write_result(tmp_path, "app-b", 1, passed=True)

        results = load_results(tmp_path)

        assert "app-a" in results
        assert "app-b" in results
        assert len(results["app-a"]) == 2
        assert len(results["app-b"]) == 1

    def test_handles_missing_result_file(self, tmp_path: Path):
        """Test gracefully handles directories without e2e-result.json."""
        (tmp_path / "result-missing-run1").mkdir()
        # No e2e-result.json inside

        results = load_results(tmp_path)

        assert results == {}

    def test_handles_invalid_json(self, tmp_path: Path):
        """Test gracefully handles malformed JSON."""
        result_dir = tmp_path / "result-bad-run1"
        result_dir.mkdir()
        (result_dir / "e2e-result.json").write_text("{not valid json")

        results = load_results(tmp_path)

        assert results == {}

    def test_empty_directory(self, tmp_path: Path):
        """Test returns empty dict for empty directory."""
        results = load_results(tmp_path)
        assert results == {}

    def test_ignores_non_result_directories(self, tmp_path: Path):
        """Test ignores directories not matching result-* pattern."""
        (tmp_path / "other-dir").mkdir()
        (tmp_path / "other-dir" / "e2e-result.json").write_text(
            json.dumps(_make_result("other"))
        )

        results = load_results(tmp_path)

        assert results == {}

    def test_ignores_result_files_not_in_dirs(self, tmp_path: Path):
        """Test ignores result-* that are files, not directories."""
        (tmp_path / "result-app-run1").write_text("not a dir")

        results = load_results(tmp_path)

        assert results == {}


# ===========================================================================
# compute_pass_rates
# ===========================================================================


class TestComputePassRates:
    """Tests for compute_pass_rates function."""

    def test_all_passing(self):
        """Test pass rate computation when all runs pass."""
        results = {
            "app-a": [
                _make_result("app-a", passed=True),
                _make_result("app-a", passed=True),
                _make_result("app-a", passed=True),
            ]
        }

        rates = compute_pass_rates(results, threshold=0.67)

        assert rates["app-a"]["pass_rate"] == 1.0
        assert rates["app-a"]["met_threshold"] is True
        assert rates["app-a"]["total_runs"] == 3
        assert rates["app-a"]["passed_runs"] == 3

    def test_all_failing(self):
        """Test pass rate computation when all runs fail."""
        results = {
            "app-a": [
                _make_result("app-a", passed=False),
                _make_result("app-a", passed=False),
            ]
        }

        rates = compute_pass_rates(results, threshold=0.67)

        assert rates["app-a"]["pass_rate"] == 0.0
        assert rates["app-a"]["met_threshold"] is False

    def test_mixed_results(self):
        """Test pass rate with mixed pass/fail."""
        results = {
            "app-a": [
                _make_result("app-a", passed=True),
                _make_result("app-a", passed=True),
                _make_result("app-a", passed=False),
            ]
        }

        rates = compute_pass_rates(results, threshold=0.66)

        assert abs(rates["app-a"]["pass_rate"] - 2 / 3) < 0.001
        assert rates["app-a"]["met_threshold"] is True  # 0.667 >= 0.66

    def test_threshold_boundary_fail(self):
        """Test pass rate at threshold boundary (just below)."""
        results = {
            "app-a": [
                _make_result("app-a", passed=True),
                _make_result("app-a", passed=False),
                _make_result("app-a", passed=False),
            ]
        }

        rates = compute_pass_rates(results, threshold=0.67)

        assert abs(rates["app-a"]["pass_rate"] - 1 / 3) < 0.001
        assert rates["app-a"]["met_threshold"] is False

    def test_multiple_apps(self):
        """Test pass rates for multiple apps."""
        results = {
            "app-a": [_make_result("app-a", passed=True)],
            "app-b": [_make_result("app-b", passed=False)],
        }

        rates = compute_pass_rates(results, threshold=0.5)

        assert rates["app-a"]["met_threshold"] is True
        assert rates["app-b"]["met_threshold"] is False

    def test_computes_average_times(self):
        """Test average time computation."""
        results = {
            "app-a": [
                _make_result("app-a", gen_time=10.0, val_time=5.0, total_time=15.0),
                _make_result("app-a", gen_time=20.0, val_time=10.0, total_time=30.0),
            ]
        }

        rates = compute_pass_rates(results, threshold=0.5)

        assert rates["app-a"]["avg_generation_time"] == 15.0
        assert rates["app-a"]["avg_validation_time"] == 7.5
        assert rates["app-a"]["avg_total_time"] == 22.5

    def test_threshold_stored_in_output(self):
        """Test threshold is stored in output for each app."""
        results = {"app-a": [_make_result("app-a")]}

        rates = compute_pass_rates(results, threshold=0.8)

        assert rates["app-a"]["threshold"] == 0.8


# ===========================================================================
# format_console
# ===========================================================================


class TestFormatConsole:
    """Tests for console output formatting."""

    def test_basic_output(self):
        """Test basic console output structure."""
        pass_rates = {
            "app-a": {
                "total_runs": 3,
                "passed_runs": 3,
                "pass_rate": 1.0,
                "threshold": 0.67,
                "met_threshold": True,
                "avg_generation_time": 10.0,
                "avg_validation_time": 5.0,
                "avg_total_time": 15.0,
            }
        }

        output = format_console(pass_rates)

        assert "E2E Application Generation Test Results" in output
        assert "app-a:" in output
        assert "PASS" in output

    def test_shows_fail_status(self):
        """Test console output shows FAIL for failing apps."""
        pass_rates = {
            "app-fail": {
                "total_runs": 3,
                "passed_runs": 1,
                "pass_rate": 1 / 3,
                "threshold": 0.67,
                "met_threshold": False,
                "avg_generation_time": 10.0,
                "avg_validation_time": 5.0,
                "avg_total_time": 15.0,
            }
        }

        output = format_console(pass_rates)

        assert "FAIL" in output
        assert "FAILED" in output  # Overall status

    def test_shows_pass_rate(self):
        """Test console output includes pass rate."""
        pass_rates = {
            "app-a": {
                "total_runs": 3,
                "passed_runs": 2,
                "pass_rate": 2 / 3,
                "threshold": 0.5,
                "met_threshold": True,
                "avg_generation_time": 0,
                "avg_validation_time": 0,
                "avg_total_time": 0,
            }
        }

        output = format_console(pass_rates)

        assert "2/3" in output


# ===========================================================================
# format_markdown
# ===========================================================================


class TestFormatMarkdown:
    """Tests for markdown output formatting."""

    def test_basic_table(self):
        """Test markdown table structure."""
        pass_rates = {
            "app-a": {
                "total_runs": 3,
                "passed_runs": 3,
                "pass_rate": 1.0,
                "threshold": 0.67,
                "met_threshold": True,
                "avg_generation_time": 10.0,
                "avg_validation_time": 5.0,
                "avg_total_time": 15.0,
            }
        }

        output = format_markdown(pass_rates)

        assert "| App |" in output
        assert "| app-a |" in output
        assert ":white_check_mark:" in output

    def test_all_passed_message(self):
        """Test overall pass message in markdown."""
        pass_rates = {
            "app-a": {
                "total_runs": 1,
                "passed_runs": 1,
                "pass_rate": 1.0,
                "threshold": 0.67,
                "met_threshold": True,
                "avg_generation_time": 0,
                "avg_validation_time": 0,
                "avg_total_time": 0,
            }
        }

        output = format_markdown(pass_rates)

        assert "PASSED" in output

    def test_failed_message(self):
        """Test overall fail message in markdown."""
        pass_rates = {
            "app-a": {
                "total_runs": 1,
                "passed_runs": 0,
                "pass_rate": 0.0,
                "threshold": 0.67,
                "met_threshold": False,
                "avg_generation_time": 0,
                "avg_validation_time": 0,
                "avg_total_time": 0,
            }
        }

        output = format_markdown(pass_rates)

        assert "FAILED" in output
        assert ":x:" in output


# ===========================================================================
# format_json
# ===========================================================================


class TestFormatJson:
    """Tests for JSON output formatting."""

    def test_json_structure(self):
        """Test JSON output has expected structure."""
        pass_rates = {
            "app-a": {
                "total_runs": 3,
                "passed_runs": 3,
                "pass_rate": 1.0,
                "threshold": 0.67,
                "met_threshold": True,
                "avg_generation_time": 10.0,
                "avg_validation_time": 5.0,
                "avg_total_time": 15.0,
            }
        }

        output = format_json(pass_rates)
        data = json.loads(output)

        assert "apps" in data
        assert "all_passed" in data
        assert "summary" in data
        assert data["all_passed"] is True
        assert data["summary"]["total_apps"] == 1
        assert data["summary"]["passed_apps"] == 1

    def test_all_passed_flag_false(self):
        """Test all_passed is False when any app fails."""
        pass_rates = {
            "app-a": {"met_threshold": True},
            "app-b": {"met_threshold": False},
        }

        output = format_json(pass_rates)
        data = json.loads(output)

        assert data["all_passed"] is False

    def test_valid_json(self):
        """Test output is valid JSON."""
        pass_rates = {
            "app-a": {"met_threshold": True},
        }

        output = format_json(pass_rates)
        data = json.loads(output)  # Should not raise

        assert isinstance(data, dict)


# ===========================================================================
# Integration: load_results -> compute_pass_rates -> format
# ===========================================================================


class TestIntegration:
    """End-to-end integration tests for the pipeline."""

    def test_full_pipeline(self, tmp_path: Path):
        """Test the full load -> compute -> format pipeline."""
        # Write 3 results: 2 pass, 1 fail
        _write_result(tmp_path, "calculator", 1, passed=True)
        _write_result(tmp_path, "calculator", 2, passed=True)
        _write_result(tmp_path, "calculator", 3, passed=False)

        # Load
        results = load_results(tmp_path)
        assert "calculator" in results
        assert len(results["calculator"]) == 3

        # Compute (2/3 = 0.666..., use threshold below that)
        rates = compute_pass_rates(results, threshold=0.66)
        assert rates["calculator"]["met_threshold"] is True

        # Format all three
        console = format_console(rates)
        assert "calculator" in console

        md = format_markdown(rates)
        assert "calculator" in md

        json_out = format_json(rates)
        data = json.loads(json_out)
        assert data["all_passed"] is True

    def test_multiple_apps_pipeline(self, tmp_path: Path):
        """Test pipeline with multiple apps."""
        _write_result(tmp_path, "app-pass", 1, passed=True)
        _write_result(tmp_path, "app-pass", 2, passed=True)
        _write_result(tmp_path, "app-fail", 1, passed=False)
        _write_result(tmp_path, "app-fail", 2, passed=False)

        results = load_results(tmp_path)
        rates = compute_pass_rates(results, threshold=0.67)

        assert rates["app-pass"]["met_threshold"] is True
        assert rates["app-fail"]["met_threshold"] is False

        json_out = format_json(rates)
        data = json.loads(json_out)
        assert data["all_passed"] is False
        assert data["summary"]["total_apps"] == 2
        assert data["summary"]["passed_apps"] == 1
