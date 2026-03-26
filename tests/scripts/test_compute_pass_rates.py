"""Tests for scripts/compute_pass_rates.py - Stochastic pass rate computation."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path for imports when running as script
_PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.compute_pass_rates import (  # noqa: E402
    compute_pass_rates,
    find_result_files,
    format_console_output,
    format_markdown_output,
    load_results,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_run(
    agent: str = "test-agent",
    run: int = 1,
    passed: bool = True,
    score: float | None = None,
) -> dict:
    """Create a mock stochastic run result dict."""
    result: dict = {
        "agent": agent,
        "run": run,
        "passed": passed,
    }
    if score is not None:
        result["score"] = score
    return result


def _write_json(path: Path, data: dict) -> Path:
    """Write a JSON file and return its path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return path


# ===========================================================================
# find_result_files
# ===========================================================================


class TestFindResultFiles:
    """Tests for find_result_files function."""

    def test_finds_direct_json_files(self, tmp_path: Path):
        """Direct JSON files in input_dir should be found."""
        # Arrange
        _write_json(tmp_path / "result1.json", _make_run())
        _write_json(tmp_path / "result2.json", _make_run())

        # Act
        files = find_result_files(tmp_path)

        # Assert
        assert len(files) == 2
        assert all(f.suffix == ".json" for f in files)

    def test_finds_nested_json_files(self, tmp_path: Path):
        """JSON files in artifact subdirectories should be found."""
        # Arrange
        _write_json(tmp_path / "artifact-run1" / "result.json", _make_run())
        _write_json(tmp_path / "artifact-run2" / "result.json", _make_run())

        # Act
        files = find_result_files(tmp_path)

        # Assert
        assert len(files) == 2

    def test_finds_both_direct_and_nested(self, tmp_path: Path):
        """Both direct and nested JSON files should be found."""
        # Arrange
        _write_json(tmp_path / "direct.json", _make_run())
        _write_json(tmp_path / "subdir" / "nested.json", _make_run())

        # Act
        files = find_result_files(tmp_path)

        # Assert
        assert len(files) == 2

    def test_returns_sorted_paths(self, tmp_path: Path):
        """Result files should be returned in sorted order."""
        # Arrange
        _write_json(tmp_path / "z_result.json", _make_run())
        _write_json(tmp_path / "a_result.json", _make_run())
        _write_json(tmp_path / "m_result.json", _make_run())

        # Act
        files = find_result_files(tmp_path)

        # Assert
        assert files == sorted(files)

    def test_empty_directory(self, tmp_path: Path):
        """Empty directory should return empty list."""
        # Act
        files = find_result_files(tmp_path)

        # Assert
        assert files == []

    def test_ignores_non_json_files(self, tmp_path: Path):
        """Non-JSON files should be ignored."""
        # Arrange
        (tmp_path / "readme.txt").write_text("not json")
        (tmp_path / "data.csv").write_text("a,b,c")
        _write_json(tmp_path / "result.json", _make_run())

        # Act
        files = find_result_files(tmp_path)

        # Assert
        assert len(files) == 1
        assert files[0].name == "result.json"

    def test_does_not_recurse_deeply(self, tmp_path: Path):
        """Only one level of subdirectory nesting should be searched."""
        # Arrange
        _write_json(
            tmp_path / "sub" / "deep" / "result.json",
            _make_run(),
        )

        # Act
        files = find_result_files(tmp_path)

        # Assert — the deeply nested file should NOT be found
        assert len(files) == 0

    def test_ignores_non_json_in_subdirectories(self, tmp_path: Path):
        """Non-JSON files in subdirectories should be ignored."""
        # Arrange
        subdir = tmp_path / "artifact-run1"
        subdir.mkdir()
        (subdir / "log.txt").write_text("some log")
        _write_json(subdir / "result.json", _make_run())

        # Act
        files = find_result_files(tmp_path)

        # Assert
        assert len(files) == 1
        assert files[0].name == "result.json"


# ===========================================================================
# load_results
# ===========================================================================


class TestLoadResults:
    """Tests for load_results function."""

    def test_groups_by_agent(self, tmp_path: Path):
        """Results should be grouped by agent name."""
        # Arrange
        _write_json(tmp_path / "r1.json", _make_run(agent="alpha", run=1))
        _write_json(tmp_path / "r2.json", _make_run(agent="alpha", run=2))
        _write_json(tmp_path / "r3.json", _make_run(agent="beta", run=1))

        # Act
        results = load_results(tmp_path)

        # Assert
        assert "alpha" in results
        assert "beta" in results
        assert len(results["alpha"]) == 2
        assert len(results["beta"]) == 1

    def test_missing_agent_key_defaults_to_unknown(self, tmp_path: Path):
        """Results without 'agent' key should be grouped under 'unknown'."""
        # Arrange
        _write_json(tmp_path / "r1.json", {"run": 1, "passed": True})

        # Act
        results = load_results(tmp_path)

        # Assert
        assert "unknown" in results
        assert len(results["unknown"]) == 1

    def test_empty_directory_returns_empty_dict(self, tmp_path: Path):
        """Empty input directory should return empty dict."""
        # Act
        results = load_results(tmp_path)

        # Assert
        assert results == {}

    def test_invalid_json_is_skipped(self, tmp_path: Path, capsys):
        """Malformed JSON files should be skipped with a warning."""
        # Arrange
        (tmp_path / "bad.json").write_text("{not valid json!!!")
        _write_json(tmp_path / "good.json", _make_run(agent="valid"))

        # Act
        results = load_results(tmp_path)

        # Assert — only the valid file should be loaded
        assert "valid" in results
        assert len(results) == 1

        # Warning should be printed to stderr
        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_preserves_all_fields(self, tmp_path: Path):
        """All fields from the JSON should be preserved in loaded results."""
        # Arrange
        data = _make_run(agent="myagent", run=3, passed=False, score=0.42)
        _write_json(tmp_path / "r.json", data)

        # Act
        results = load_results(tmp_path)

        # Assert
        loaded = results["myagent"][0]
        assert loaded["agent"] == "myagent"
        assert loaded["run"] == 3
        assert loaded["passed"] is False
        assert loaded["score"] == 0.42

    def test_loads_from_nested_subdirectories(self, tmp_path: Path):
        """Results in artifact subdirectories should also be loaded."""
        # Arrange
        _write_json(
            tmp_path / "artifact-agent1-run1" / "result.json",
            _make_run(agent="agent1", run=1),
        )

        # Act
        results = load_results(tmp_path)

        # Assert
        assert "agent1" in results

    def test_returns_plain_dict_not_defaultdict(self, tmp_path: Path):
        """Return value should be a plain dict, not a defaultdict."""
        # Arrange
        _write_json(tmp_path / "r.json", _make_run(agent="a"))

        # Act
        results = load_results(tmp_path)

        # Assert
        assert type(results) is dict


# ===========================================================================
# compute_pass_rates
# ===========================================================================


class TestComputePassRates:
    """Tests for compute_pass_rates function."""

    def test_all_passing(self):
        """All passing runs should yield pass_rate=1.0 and passed=True."""
        # Arrange
        agent_results = {
            "agent-a": [
                _make_run(passed=True, run=1),
                _make_run(passed=True, run=2),
                _make_run(passed=True, run=3),
            ],
        }

        # Act
        results, all_passed = compute_pass_rates(agent_results, threshold=0.8)

        # Assert
        assert results["agent-a"]["passes"] == 3
        assert results["agent-a"]["total"] == 3
        assert results["agent-a"]["pass_rate"] == 1.0
        assert results["agent-a"]["passed"] is True
        assert all_passed is True

    def test_all_failing(self):
        """All failing runs should yield pass_rate=0.0 and passed=False."""
        # Arrange
        agent_results = {
            "agent-a": [
                _make_run(passed=False, run=1),
                _make_run(passed=False, run=2),
            ],
        }

        # Act
        results, all_passed = compute_pass_rates(agent_results, threshold=0.8)

        # Assert
        assert results["agent-a"]["passes"] == 0
        assert results["agent-a"]["total"] == 2
        assert results["agent-a"]["pass_rate"] == 0.0
        assert results["agent-a"]["passed"] is False
        assert all_passed is False

    def test_mixed_results(self):
        """Mixed pass/fail should compute correct pass_rate."""
        # Arrange
        agent_results = {
            "agent-a": [
                _make_run(passed=True, run=1),
                _make_run(passed=True, run=2),
                _make_run(passed=False, run=3),
            ],
        }

        # Act
        results, all_passed = compute_pass_rates(agent_results, threshold=0.6)

        # Assert — 2/3 = 0.6667, threshold 0.6 => passed
        assert results["agent-a"]["passes"] == 2
        assert results["agent-a"]["total"] == 3
        assert abs(results["agent-a"]["pass_rate"] - 2 / 3) < 0.001
        assert results["agent-a"]["passed"] is True
        assert all_passed is True

    def test_threshold_boundary_exact_match(self):
        """Pass rate exactly at threshold should pass (>= comparison)."""
        # Arrange — 4/5 = 0.8, threshold = 0.8
        agent_results = {
            "agent-a": [_make_run(passed=True, run=i) for i in range(1, 5)]
            + [_make_run(passed=False, run=5)],
        }

        # Act
        results, all_passed = compute_pass_rates(agent_results, threshold=0.8)

        # Assert
        assert results["agent-a"]["pass_rate"] == 0.8
        assert results["agent-a"]["passed"] is True
        assert all_passed is True

    def test_threshold_boundary_just_below(self):
        """Pass rate just below threshold should fail."""
        # Arrange — 3/5 = 0.6, threshold = 0.8
        agent_results = {
            "agent-a": [
                _make_run(passed=True, run=1),
                _make_run(passed=True, run=2),
                _make_run(passed=True, run=3),
                _make_run(passed=False, run=4),
                _make_run(passed=False, run=5),
            ],
        }

        # Act
        results, all_passed = compute_pass_rates(agent_results, threshold=0.8)

        # Assert
        assert results["agent-a"]["pass_rate"] == 0.6
        assert results["agent-a"]["passed"] is False
        assert all_passed is False

    def test_threshold_zero_always_passes(self):
        """Threshold of 0.0 should always pass."""
        # Arrange
        agent_results = {
            "agent-a": [_make_run(passed=False, run=1)],
        }

        # Act
        results, all_passed = compute_pass_rates(agent_results, threshold=0.0)

        # Assert
        assert results["agent-a"]["passed"] is True
        assert all_passed is True

    def test_threshold_one_requires_all_passing(self):
        """Threshold of 1.0 requires 100% pass rate."""
        # Arrange
        agent_results = {
            "agent-a": [
                _make_run(passed=True, run=1),
                _make_run(passed=True, run=2),
                _make_run(passed=False, run=3),
            ],
        }

        # Act
        results, all_passed = compute_pass_rates(agent_results, threshold=1.0)

        # Assert
        assert results["agent-a"]["passed"] is False
        assert all_passed is False

    def test_multiple_agents(self):
        """Multiple agents should each get independent results."""
        # Arrange
        agent_results = {
            "agent-pass": [_make_run(passed=True, run=1)],
            "agent-fail": [_make_run(passed=False, run=1)],
        }

        # Act
        results, all_passed = compute_pass_rates(agent_results, threshold=0.5)

        # Assert
        assert results["agent-pass"]["passed"] is True
        assert results["agent-fail"]["passed"] is False
        assert all_passed is False

    def test_all_passed_true_when_all_agents_pass(self):
        """all_passed should be True only when every agent meets threshold."""
        # Arrange
        agent_results = {
            "a": [_make_run(passed=True, run=1)],
            "b": [_make_run(passed=True, run=1)],
        }

        # Act
        results, all_passed = compute_pass_rates(agent_results, threshold=0.5)

        # Assert
        assert all_passed is True

    def test_empty_agent_results(self):
        """Empty agent_results should return empty results and all_passed=True."""
        # Act
        results, all_passed = compute_pass_rates({}, threshold=0.8)

        # Assert
        assert results == {}
        assert all_passed is True

    def test_results_sorted_by_agent_name(self):
        """Results should be computed in sorted agent name order."""
        # Arrange
        agent_results = {
            "zebra": [_make_run(passed=True)],
            "alpha": [_make_run(passed=True)],
            "middle": [_make_run(passed=True)],
        }

        # Act
        results, _ = compute_pass_rates(agent_results)

        # Assert
        assert list(results.keys()) == ["alpha", "middle", "zebra"]

    def test_runs_sorted_by_run_number(self):
        """Runs should be sorted by run number in output."""
        # Arrange
        agent_results = {
            "agent-a": [
                _make_run(run=3, passed=False),
                _make_run(run=1, passed=True),
                _make_run(run=2, passed=True),
            ],
        }

        # Act
        results, _ = compute_pass_rates(agent_results)

        # Assert
        run_numbers = [r["run"] for r in results["agent-a"]["runs"]]
        assert run_numbers == [1, 2, 3]

    def test_threshold_stored_in_output(self):
        """Threshold value should be stored in each agent's results."""
        # Arrange
        agent_results = {"a": [_make_run(passed=True)]}

        # Act
        results, _ = compute_pass_rates(agent_results, threshold=0.75)

        # Assert
        assert results["a"]["threshold"] == 0.75

    def test_run_details_include_score(self):
        """Run details should include score when present."""
        # Arrange
        agent_results = {
            "a": [_make_run(run=1, passed=True, score=0.95)],
        }

        # Act
        results, _ = compute_pass_rates(agent_results)

        # Assert
        assert results["a"]["runs"][0]["score"] == 0.95

    def test_run_details_score_none_when_absent(self):
        """Run details should have score=None when not in source data."""
        # Arrange
        agent_results = {
            "a": [_make_run(run=1, passed=True)],  # No score
        }

        # Act
        results, _ = compute_pass_rates(agent_results)

        # Assert
        assert results["a"]["runs"][0]["score"] is None

    def test_missing_passed_field_defaults_to_false(self):
        """Runs missing 'passed' field should default to False."""
        # Arrange
        agent_results = {
            "a": [{"agent": "a", "run": 1}],  # No 'passed' key
        }

        # Act
        results, all_passed = compute_pass_rates(agent_results, threshold=0.5)

        # Assert
        assert results["a"]["passes"] == 0
        assert results["a"]["passed"] is False

    def test_missing_run_field_gets_index_based_default(self):
        """Runs missing 'run' field should get index-based run number in output."""
        # Arrange
        agent_results = {
            "a": [
                {"agent": "a", "passed": True},
                {"agent": "a", "passed": True},
            ],
        }

        # Act
        results, _ = compute_pass_rates(agent_results)

        # Assert — r.get("run", i + 1) where i is enumerate index after sorting
        # Sorting uses r.get("run", 0) = 0 for both, preserving original order.
        # Then output uses r.get("run", i + 1): since no "run" key, defaults to 1, 2.
        run_numbers = [r["run"] for r in results["a"]["runs"]]
        assert run_numbers == [1, 2]

    def test_default_threshold_is_0_8(self):
        """Default threshold should be 0.8 when not specified."""
        # Arrange
        agent_results = {"a": [_make_run(passed=True)]}

        # Act
        results, _ = compute_pass_rates(agent_results)

        # Assert
        assert results["a"]["threshold"] == 0.8

    def test_single_run_passing(self):
        """Single passing run should pass any threshold <= 1.0."""
        # Arrange
        agent_results = {"a": [_make_run(passed=True, run=1)]}

        # Act
        results, all_passed = compute_pass_rates(agent_results, threshold=1.0)

        # Assert
        assert results["a"]["pass_rate"] == 1.0
        assert results["a"]["passed"] is True
        assert all_passed is True

    def test_single_run_failing(self):
        """Single failing run should fail any threshold > 0."""
        # Arrange
        agent_results = {"a": [_make_run(passed=False, run=1)]}

        # Act
        results, all_passed = compute_pass_rates(agent_results, threshold=0.1)

        # Assert
        assert results["a"]["pass_rate"] == 0.0
        assert results["a"]["passed"] is False
        assert all_passed is False


# ===========================================================================
# format_console_output
# ===========================================================================


class TestFormatConsoleOutput:
    """Tests for format_console_output function."""

    def _make_results(
        self,
        agent: str = "test-agent",
        passes: int = 3,
        total: int = 5,
        passed: bool = True,
        runs: list[dict] | None = None,
    ) -> dict:
        """Build a results dict matching compute_pass_rates output."""
        if runs is None:
            runs = [{"run": i + 1, "passed": i < passes, "score": None} for i in range(total)]
        return {
            agent: {
                "passes": passes,
                "total": total,
                "pass_rate": passes / total if total > 0 else 0.0,
                "threshold": 0.8,
                "passed": passed,
                "runs": runs,
            }
        }

    def test_includes_threshold_in_header(self):
        """Console output should include threshold percentage in header."""
        # Arrange
        results = self._make_results()

        # Act
        output = format_console_output(results, threshold=0.8)

        # Assert
        assert "80% threshold" in output

    def test_includes_agent_name(self):
        """Console output should include agent name."""
        # Arrange
        results = self._make_results(agent="my-agent")

        # Act
        output = format_console_output(results, threshold=0.8)

        # Assert
        assert "my-agent:" in output

    def test_shows_meets_threshold_for_passing(self):
        """Passing agent should show MEETS THRESHOLD."""
        # Arrange
        results = self._make_results(passed=True)

        # Act
        output = format_console_output(results, threshold=0.8)

        # Assert
        assert "MEETS THRESHOLD" in output

    def test_shows_below_threshold_for_failing(self):
        """Failing agent should show BELOW THRESHOLD."""
        # Arrange
        results = self._make_results(passes=1, total=5, passed=False)

        # Act
        output = format_console_output(results, threshold=0.8)

        # Assert
        assert "BELOW THRESHOLD" in output

    def test_shows_pass_count(self):
        """Console output should show pass count fraction."""
        # Arrange
        results = self._make_results(passes=3, total=5)

        # Act
        output = format_console_output(results, threshold=0.8)

        # Assert
        assert "3/5" in output

    def test_shows_run_details(self):
        """Console output should show individual run details."""
        # Arrange
        runs = [
            {"run": 1, "passed": True, "score": None},
            {"run": 2, "passed": False, "score": None},
        ]
        results = self._make_results(passes=1, total=2, runs=runs)

        # Act
        output = format_console_output(results, threshold=0.5)

        # Assert
        assert "Run 1" in output
        assert "Run 2" in output

    def test_shows_score_when_present(self):
        """Console output should show score when available."""
        # Arrange
        runs = [{"run": 1, "passed": True, "score": 0.95}]
        results = self._make_results(passes=1, total=1, runs=runs)

        # Act
        output = format_console_output(results, threshold=0.8)

        # Assert
        assert "score: 0.95" in output

    def test_hides_score_when_none(self):
        """Console output should not show score field when None."""
        # Arrange
        runs = [{"run": 1, "passed": True, "score": None}]
        results = self._make_results(passes=1, total=1, runs=runs)

        # Act
        output = format_console_output(results, threshold=0.8)

        # Assert
        assert "score:" not in output

    def test_includes_separator_line(self):
        """Console output should include a separator line."""
        # Arrange
        results = self._make_results()

        # Act
        output = format_console_output(results, threshold=0.8)

        # Assert
        assert "=" * 55 in output

    def test_shows_percentage(self):
        """Console output should show pass rate as percentage."""
        # Arrange
        results = self._make_results(passes=4, total=5, passed=True)

        # Act
        output = format_console_output(results, threshold=0.8)

        # Assert
        assert "80%" in output

    def test_empty_results(self):
        """Empty results dict should produce header-only output."""
        # Act
        output = format_console_output({}, threshold=0.8)

        # Assert — header present, no agent names or run details
        assert "80% threshold" in output
        assert "Run " not in output
        assert "MEETS THRESHOLD" not in output
        assert "BELOW THRESHOLD" not in output

    def test_multiple_agents(self):
        """Console output should include sections for each agent."""
        # Arrange
        results = {
            "agent-a": {
                "passes": 5,
                "total": 5,
                "pass_rate": 1.0,
                "threshold": 0.8,
                "passed": True,
                "runs": [{"run": i, "passed": True, "score": None} for i in range(1, 6)],
            },
            "agent-b": {
                "passes": 2,
                "total": 5,
                "pass_rate": 0.4,
                "threshold": 0.8,
                "passed": False,
                "runs": [{"run": i, "passed": i <= 2, "score": None} for i in range(1, 6)],
            },
        }

        # Act
        output = format_console_output(results, threshold=0.8)

        # Assert
        assert "agent-a:" in output
        assert "agent-b:" in output

    def test_different_threshold_values(self):
        """Console output should reflect different threshold percentages."""
        # Arrange
        results = self._make_results()

        # Act
        output_60 = format_console_output(results, threshold=0.6)
        output_90 = format_console_output(results, threshold=0.9)

        # Assert
        assert "60% threshold" in output_60
        assert "90% threshold" in output_90


# ===========================================================================
# format_markdown_output
# ===========================================================================


class TestFormatMarkdownOutput:
    """Tests for format_markdown_output function."""

    def _make_results(
        self,
        agent: str = "test-agent",
        passes: int = 3,
        total: int = 5,
        passed: bool = True,
        runs: list[dict] | None = None,
    ) -> dict:
        """Build a results dict matching compute_pass_rates output."""
        if runs is None:
            runs = [{"run": i + 1, "passed": i < passes, "score": None} for i in range(total)]
        return {
            agent: {
                "passes": passes,
                "total": total,
                "pass_rate": passes / total if total > 0 else 0.0,
                "threshold": 0.8,
                "passed": passed,
                "runs": runs,
            }
        }

    def test_starts_with_h1_header(self):
        """Markdown output should start with a level-1 heading."""
        # Arrange
        results = self._make_results()

        # Act
        output = format_markdown_output(results, threshold=0.8)

        # Assert
        assert output.startswith("# Stochastic Evaluation Results")

    def test_includes_threshold_description(self):
        """Markdown output should describe threshold."""
        # Arrange
        results = self._make_results()

        # Act
        output = format_markdown_output(results, threshold=0.8)

        # Assert
        assert "**Threshold**: 80%" in output

    def test_includes_summary_table(self):
        """Markdown output should include a summary table."""
        # Arrange
        results = self._make_results(agent="my-agent", passes=4, total=5, passed=True)

        # Act
        output = format_markdown_output(results, threshold=0.8)

        # Assert
        assert "| Agent | Pass Rate | Status |" in output
        assert "| my-agent |" in output

    def test_summary_table_pass_rate_fraction(self):
        """Summary table should show pass/total fraction."""
        # Arrange
        results = self._make_results(passes=3, total=5)

        # Act
        output = format_markdown_output(results, threshold=0.8)

        # Assert
        assert "3/5" in output

    def test_includes_details_section(self):
        """Markdown output should include a Details section."""
        # Arrange
        results = self._make_results()

        # Act
        output = format_markdown_output(results, threshold=0.8)

        # Assert
        assert "## Details" in output

    def test_details_show_individual_runs(self):
        """Details section should show each run as a list item."""
        # Arrange
        runs = [
            {"run": 1, "passed": True, "score": None},
            {"run": 2, "passed": False, "score": None},
        ]
        results = self._make_results(passes=1, total=2, runs=runs)

        # Act
        output = format_markdown_output(results, threshold=0.5)

        # Assert
        assert "- Run 1:" in output
        assert "- Run 2:" in output

    def test_details_show_score_when_present(self):
        """Run details should include score when available."""
        # Arrange
        runs = [{"run": 1, "passed": True, "score": 0.88}]
        results = self._make_results(passes=1, total=1, runs=runs)

        # Act
        output = format_markdown_output(results, threshold=0.8)

        # Assert
        assert "(score: 0.88)" in output

    def test_details_hide_score_when_none(self):
        """Run details should not include score when None."""
        # Arrange
        runs = [{"run": 1, "passed": True, "score": None}]
        results = self._make_results(passes=1, total=1, runs=runs)

        # Act
        output = format_markdown_output(results, threshold=0.8)

        # Assert
        assert "score:" not in output

    def test_agent_header_in_details(self):
        """Details section should have h3 heading per agent."""
        # Arrange
        results = self._make_results(agent="cool-agent")

        # Act
        output = format_markdown_output(results, threshold=0.8)

        # Assert
        assert "### cool-agent" in output

    def test_multiple_agents_in_markdown(self):
        """Markdown output should include all agents."""
        # Arrange
        results = {
            "agent-x": {
                "passes": 5,
                "total": 5,
                "pass_rate": 1.0,
                "threshold": 0.8,
                "passed": True,
                "runs": [{"run": 1, "passed": True, "score": None}],
            },
            "agent-y": {
                "passes": 0,
                "total": 3,
                "pass_rate": 0.0,
                "threshold": 0.8,
                "passed": False,
                "runs": [{"run": 1, "passed": False, "score": None}],
            },
        }

        # Act
        output = format_markdown_output(results, threshold=0.8)

        # Assert
        assert "agent-x" in output
        assert "agent-y" in output

    def test_empty_results_produces_valid_markdown(self):
        """Empty results should still produce valid markdown structure."""
        # Act
        output = format_markdown_output({}, threshold=0.8)

        # Assert
        assert "# Stochastic Evaluation Results" in output
        assert "## Summary" in output
        assert "## Details" in output

    def test_threshold_computes_run_count(self):
        """Threshold description should compute runs from threshold (hardcoded /5)."""
        # Arrange
        results = self._make_results()

        # Act
        output = format_markdown_output(results, threshold=0.6)

        # Assert — 0.6 * 5 = 3
        assert "3/5 runs" in output

    def test_unicode_status_indicators(self):
        """Markdown output should use unicode checkmarks and crosses."""
        # Arrange
        results = {
            "pass-agent": {
                "passes": 1,
                "total": 1,
                "pass_rate": 1.0,
                "threshold": 0.8,
                "passed": True,
                "runs": [{"run": 1, "passed": True, "score": None}],
            },
            "fail-agent": {
                "passes": 0,
                "total": 1,
                "pass_rate": 0.0,
                "threshold": 0.8,
                "passed": False,
                "runs": [{"run": 1, "passed": False, "score": None}],
            },
        }

        # Act
        output = format_markdown_output(results, threshold=0.8)

        # Assert — should contain unicode check and cross marks
        assert "\u2705" in output  # checkmark
        assert "\u274c" in output  # cross


# ===========================================================================
# Integration: load_results -> compute_pass_rates -> format
# ===========================================================================


class TestIntegration:
    """End-to-end integration tests for the full pipeline."""

    def test_full_pipeline_passing(self, tmp_path: Path):
        """Full pipeline: load -> compute -> format for passing results."""
        # Arrange — 4/5 pass, threshold 0.8
        for i in range(1, 6):
            _write_json(
                tmp_path / f"run{i}.json",
                _make_run(agent="architect", run=i, passed=(i <= 4)),
            )

        # Act
        agent_results = load_results(tmp_path)
        results, all_passed = compute_pass_rates(agent_results, threshold=0.8)
        console = format_console_output(results, threshold=0.8)
        markdown = format_markdown_output(results, threshold=0.8)

        # Assert
        assert "architect" in agent_results
        assert len(agent_results["architect"]) == 5
        assert results["architect"]["passes"] == 4
        assert results["architect"]["pass_rate"] == 0.8
        assert results["architect"]["passed"] is True
        assert all_passed is True
        assert "architect" in console
        assert "MEETS THRESHOLD" in console
        assert "architect" in markdown

    def test_full_pipeline_failing(self, tmp_path: Path):
        """Full pipeline for failing results."""
        # Arrange — 2/5 pass, threshold 0.8
        for i in range(1, 6):
            _write_json(
                tmp_path / f"run{i}.json",
                _make_run(agent="guardian", run=i, passed=(i <= 2)),
            )

        # Act
        agent_results = load_results(tmp_path)
        results, all_passed = compute_pass_rates(agent_results, threshold=0.8)
        console = format_console_output(results, threshold=0.8)

        # Assert
        assert results["guardian"]["passes"] == 2
        assert results["guardian"]["passed"] is False
        assert all_passed is False
        assert "BELOW THRESHOLD" in console

    def test_multi_agent_pipeline(self, tmp_path: Path):
        """Full pipeline with multiple agents, some passing some failing."""
        # Arrange
        for i in range(1, 4):
            _write_json(
                tmp_path / f"alpha-{i}.json",
                _make_run(agent="alpha", run=i, passed=True),
            )
        for i in range(1, 4):
            _write_json(
                tmp_path / f"beta-{i}.json",
                _make_run(agent="beta", run=i, passed=False),
            )

        # Act
        agent_results = load_results(tmp_path)
        results, all_passed = compute_pass_rates(agent_results, threshold=0.8)

        # Assert
        assert results["alpha"]["passed"] is True
        assert results["beta"]["passed"] is False
        assert all_passed is False

    def test_pipeline_with_nested_artifacts(self, tmp_path: Path):
        """Pipeline works with GitHub Actions nested artifact structure."""
        # Arrange
        _write_json(
            tmp_path / "stochastic-developer-run1" / "result.json",
            _make_run(agent="developer", run=1, passed=True),
        )
        _write_json(
            tmp_path / "stochastic-developer-run2" / "result.json",
            _make_run(agent="developer", run=2, passed=True),
        )

        # Act
        agent_results = load_results(tmp_path)
        results, all_passed = compute_pass_rates(agent_results, threshold=0.8)

        # Assert
        assert "developer" in results
        assert results["developer"]["passes"] == 2
        assert all_passed is True

    def test_pipeline_with_scores(self, tmp_path: Path):
        """Pipeline preserves score data through all stages."""
        # Arrange
        _write_json(
            tmp_path / "r1.json",
            _make_run(agent="optimizer", run=1, passed=True, score=0.92),
        )
        _write_json(
            tmp_path / "r2.json",
            _make_run(agent="optimizer", run=2, passed=False, score=0.35),
        )

        # Act
        agent_results = load_results(tmp_path)
        results, _ = compute_pass_rates(agent_results, threshold=0.5)
        console = format_console_output(results, threshold=0.5)
        markdown = format_markdown_output(results, threshold=0.5)

        # Assert
        assert results["optimizer"]["runs"][0]["score"] == 0.92
        assert results["optimizer"]["runs"][1]["score"] == 0.35
        assert "score: 0.92" in console
        assert "(score: 0.92)" in markdown
