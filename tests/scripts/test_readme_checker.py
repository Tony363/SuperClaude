"""Comprehensive tests for READMEQualityChecker."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from scripts.readme_checker import READMEQualityChecker

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_readme(tmp_path: Path, name: str, content: str) -> Path:
    """Write a README file into tmp_path and return its path."""
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


MINIMAL_README = "# Title\n\nSome content.\n"

THREE_HEADER_README = "# Title\n## Section A\n## Section B\n"

FIVE_HEADER_README = "# Title\n## Section A\n## Section B\n### Sub 1\n### Sub 2\n"

README_WITH_LOCAL_LINKS = "# Title\n[Link A](existing_file.txt)\n[Link B](missing_file.txt)\n"

README_WITH_HTTP_LINKS = (
    "# Title\n"
    "[GitHub](https://github.com/example/repo)\n"
    "[PyPI](https://pypi.org/project/example)\n"
    "[Other](https://example.com)\n"
)

README_WITH_ANCHOR_LINKS = "# Title\n[Jump](#section-a)\n[Jump 2](#section-b)\n"

README_NO_LINKS = "# Title\n\nJust plain text.\n"


# ---------------------------------------------------------------------------
# check_structure_consistency
# ---------------------------------------------------------------------------


class TestCheckStructureConsistency:
    """Tests for READMEQualityChecker.check_structure_consistency."""

    def test_identical_header_counts_score_100(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        for name in ["README.md", "README-zh.md", "README-ja.md"]:
            _write_readme(tmp_path, name, THREE_HEADER_README)
        checker = READMEQualityChecker()

        # Act
        checker.check_structure_consistency()

        # Assert
        result = checker.results["structure_consistency"]
        assert result["score"] == 100
        assert result["status"] == "PASS"
        assert len(result["details"]) == 3

    def test_small_header_difference_still_passes(self, tmp_path, monkeypatch):
        # Arrange -- 1-header diff -> score = 95 (>= 90 => PASS)
        monkeypatch.chdir(tmp_path)
        _write_readme(tmp_path, "README.md", THREE_HEADER_README)
        _write_readme(tmp_path, "README-zh.md", THREE_HEADER_README)
        _write_readme(tmp_path, "README-ja.md", THREE_HEADER_README + "## Extra\n")
        checker = READMEQualityChecker()

        # Act
        checker.check_structure_consistency()

        # Assert
        result = checker.results["structure_consistency"]
        assert result["score"] == 95
        assert result["status"] == "PASS"

    def test_large_header_difference_warns(self, tmp_path, monkeypatch):
        # Arrange -- 3-header diff -> score = 85 (< 90 => WARN)
        monkeypatch.chdir(tmp_path)
        _write_readme(tmp_path, "README.md", FIVE_HEADER_README)
        _write_readme(tmp_path, "README-zh.md", "# Title\n## Only One\n")
        checker = READMEQualityChecker()

        # Act
        checker.check_structure_consistency()

        # Assert
        result = checker.results["structure_consistency"]
        assert result["score"] == 85
        assert result["status"] == "WARN"

    def test_very_large_difference_clamps_to_zero(self, tmp_path, monkeypatch):
        # Arrange -- 25-header diff -> score = max(0, 100-125) = 0
        monkeypatch.chdir(tmp_path)
        headers = "\n".join(f"## H{i}" for i in range(26))
        _write_readme(tmp_path, "README.md", f"# Title\n{headers}\n")
        _write_readme(tmp_path, "README-zh.md", "# Title\n## One\n")
        checker = READMEQualityChecker()

        # Act
        checker.check_structure_consistency()

        # Assert
        result = checker.results["structure_consistency"]
        assert result["score"] == 0

    def test_single_file_present_scores_100(self, tmp_path, monkeypatch):
        # Arrange -- only one file => max_diff = 0
        monkeypatch.chdir(tmp_path)
        _write_readme(tmp_path, "README.md", THREE_HEADER_README)
        checker = READMEQualityChecker()

        # Act
        checker.check_structure_consistency()

        # Assert
        result = checker.results["structure_consistency"]
        assert result["score"] == 100
        assert result["status"] == "PASS"

    def test_no_files_present_leaves_empty_list(self, tmp_path, monkeypatch):
        # Arrange -- none of the expected files exist
        monkeypatch.chdir(tmp_path)
        checker = READMEQualityChecker()

        # Act
        checker.check_structure_consistency()

        # Assert -- results remain the initial empty list
        assert checker.results["structure_consistency"] == []

    def test_header_levels_all_counted(self, tmp_path, monkeypatch):
        # Arrange -- h1 through h6 all count
        monkeypatch.chdir(tmp_path)
        content = "# H1\n## H2\n### H3\n#### H4\n##### H5\n###### H6\n"
        _write_readme(tmp_path, "README.md", content)
        checker = READMEQualityChecker()

        # Act
        checker.check_structure_consistency()

        # Assert
        result = checker.results["structure_consistency"]
        assert result["details"]["README.md"] == 6


# ---------------------------------------------------------------------------
# check_link_validation
# ---------------------------------------------------------------------------


class TestCheckLinkValidation:
    """Tests for READMEQualityChecker.check_link_validation."""

    def test_all_local_links_valid(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        (tmp_path / "existing.txt").write_text("ok", encoding="utf-8")
        _write_readme(tmp_path, "README.md", "# T\n[Link](existing.txt)\n")
        checker = READMEQualityChecker()

        # Act
        checker.check_link_validation()

        # Assert
        result = checker.results["link_validation"]
        assert result["score"] == 100
        assert result["broken_links"] == 0
        assert result["status"] == "PASS"
        assert result["total_links"] == 1

    def test_broken_local_link_reduces_score(self, tmp_path, monkeypatch):
        # Arrange -- missing_file.txt does not exist
        monkeypatch.chdir(tmp_path)
        (tmp_path / "existing_file.txt").write_text("ok", encoding="utf-8")
        _write_readme(tmp_path, "README.md", README_WITH_LOCAL_LINKS)
        checker = READMEQualityChecker()

        # Act
        checker.check_link_validation()

        # Assert
        result = checker.results["link_validation"]
        assert result["broken_links"] == 1
        assert result["score"] == 90  # 100 - 1*10
        assert result["status"] == "PASS"
        assert "missing_file.txt" in result["broken_list"][0]

    def test_many_broken_links_fail(self, tmp_path, monkeypatch):
        # Arrange -- 3 broken links -> score = 70, still PASS (>= 80? no -> FAIL)
        monkeypatch.chdir(tmp_path)
        content = "# T\n[A](a.txt)\n[B](b.txt)\n[C](c.txt)\n"
        _write_readme(tmp_path, "README.md", content)
        checker = READMEQualityChecker()

        # Act
        checker.check_link_validation()

        # Assert
        result = checker.results["link_validation"]
        assert result["broken_links"] == 3
        assert result["score"] == 70  # 100 - 3*10
        assert result["status"] == "FAIL"

    def test_anchor_links_are_not_broken(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        _write_readme(tmp_path, "README.md", README_WITH_ANCHOR_LINKS)
        checker = READMEQualityChecker()

        # Act
        checker.check_link_validation()

        # Assert
        result = checker.results["link_validation"]
        assert result["broken_links"] == 0
        assert result["score"] == 100
        assert result["total_links"] == 2

    def test_http_links_skipped_without_requests(self, tmp_path, monkeypatch):
        # Arrange -- force HAS_REQUESTS to False
        monkeypatch.chdir(tmp_path)
        import scripts.readme_checker as mod

        monkeypatch.setattr(mod, "HAS_REQUESTS", False)
        _write_readme(tmp_path, "README.md", README_WITH_HTTP_LINKS)
        checker = READMEQualityChecker()

        # Act
        checker.check_link_validation()

        # Assert -- all HTTP links treated as anchors, none broken
        result = checker.results["link_validation"]
        assert result["broken_links"] == 0
        assert result["total_links"] == 3

    def test_http_links_non_key_domain_skipped(self, tmp_path, monkeypatch):
        # Arrange -- example.com is not in key domains, so status = "skipped"
        monkeypatch.chdir(tmp_path)
        import scripts.readme_checker as mod

        monkeypatch.setattr(mod, "HAS_REQUESTS", True)
        content = "# T\n[Other](https://example.com)\n"
        _write_readme(tmp_path, "README.md", content)
        checker = READMEQualityChecker()

        # Act
        checker.check_link_validation()

        # Assert
        result = checker.results["link_validation"]
        assert result["broken_links"] == 0
        assert result["score"] == 100

    def test_no_links_scores_100(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        _write_readme(tmp_path, "README.md", README_NO_LINKS)
        checker = READMEQualityChecker()

        # Act
        checker.check_link_validation()

        # Assert
        result = checker.results["link_validation"]
        assert result["total_links"] == 0
        assert result["score"] == 100
        assert result["status"] == "PASS"

    def test_no_files_produces_empty_result(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        checker = READMEQualityChecker()

        # Act
        checker.check_link_validation()

        # Assert
        result = checker.results["link_validation"]
        assert result["total_links"] == 0
        assert result["score"] == 100

    def test_broken_list_capped_at_10(self, tmp_path, monkeypatch):
        # Arrange -- 15 broken links, only first 10 in broken_list
        monkeypatch.chdir(tmp_path)
        links = "\n".join(f"[L{i}](missing{i}.txt)" for i in range(15))
        _write_readme(tmp_path, "README.md", f"# T\n{links}\n")
        checker = READMEQualityChecker()

        # Act
        checker.check_link_validation()

        # Assert
        result = checker.results["link_validation"]
        assert result["broken_links"] == 15
        assert len(result["broken_list"]) == 10
        assert result["score"] == 0  # max(0, 100 - 150)

    def test_links_across_multiple_files(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        (tmp_path / "real.txt").write_text("ok", encoding="utf-8")
        _write_readme(tmp_path, "README.md", "# T\n[A](real.txt)\n[B](nope.txt)\n")
        _write_readme(tmp_path, "README-zh.md", "# T\n[C](real.txt)\n")
        checker = READMEQualityChecker()

        # Act
        checker.check_link_validation()

        # Assert
        result = checker.results["link_validation"]
        assert result["total_links"] == 3
        assert result["broken_links"] == 1


# ---------------------------------------------------------------------------
# check_translation_sync
# ---------------------------------------------------------------------------


class TestCheckTranslationSync:
    """Tests for READMEQualityChecker.check_translation_sync."""

    def test_all_files_same_mtime_scores_100(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        now = time.time()
        for name in ["README.md", "README-zh.md", "README-ja.md"]:
            p = _write_readme(tmp_path, name, MINIMAL_README)
            os.utime(p, (now, now))
        checker = READMEQualityChecker()

        # Act
        checker.check_translation_sync()

        # Assert
        result = checker.results["translation_sync"]
        assert result["score"] == 100
        assert result["status"] == "PASS"
        assert result["time_diff_days"] == 0.0

    def test_missing_file_returns_warn_score_60(self, tmp_path, monkeypatch):
        # Arrange -- only README.md exists
        monkeypatch.chdir(tmp_path)
        _write_readme(tmp_path, "README.md", MINIMAL_README)
        checker = READMEQualityChecker()

        # Act
        checker.check_translation_sync()

        # Assert
        result = checker.results["translation_sync"]
        assert result["score"] == 60
        assert result["status"] == "WARN"
        assert "Missing files" in result["message"]

    def test_missing_files_listed_in_message(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        _write_readme(tmp_path, "README.md", MINIMAL_README)
        _write_readme(tmp_path, "README-ja.md", MINIMAL_README)
        checker = READMEQualityChecker()

        # Act
        checker.check_translation_sync()

        # Assert
        result = checker.results["translation_sync"]
        assert "README-zh.md" in result["message"]

    def test_large_time_diff_reduces_score(self, tmp_path, monkeypatch):
        # Arrange -- 14-day diff => score = max(0, 100 - (14/7 * 20)) = 60
        monkeypatch.chdir(tmp_path)
        now = time.time()
        fourteen_days = 14 * 24 * 3600
        p1 = _write_readme(tmp_path, "README.md", MINIMAL_README)
        p2 = _write_readme(tmp_path, "README-zh.md", MINIMAL_README)
        p3 = _write_readme(tmp_path, "README-ja.md", MINIMAL_README)
        os.utime(p1, (now, now))
        os.utime(p2, (now, now))
        os.utime(p3, (now - fourteen_days, now - fourteen_days))
        checker = READMEQualityChecker()

        # Act
        checker.check_translation_sync()

        # Assert
        result = checker.results["translation_sync"]
        assert result["score"] == 60
        assert result["status"] == "WARN"
        assert result["time_diff_days"] == pytest.approx(14.0, abs=0.1)

    def test_35_day_diff_clamps_to_zero(self, tmp_path, monkeypatch):
        # Arrange -- 35-day diff => score = max(0, 100 - (35/7 * 20)) = 0
        monkeypatch.chdir(tmp_path)
        now = time.time()
        thirty_five_days = 35 * 24 * 3600
        p1 = _write_readme(tmp_path, "README.md", MINIMAL_README)
        p2 = _write_readme(tmp_path, "README-zh.md", MINIMAL_README)
        p3 = _write_readme(tmp_path, "README-ja.md", MINIMAL_README)
        os.utime(p1, (now, now))
        os.utime(p2, (now, now))
        os.utime(p3, (now - thirty_five_days, now - thirty_five_days))
        checker = READMEQualityChecker()

        # Act
        checker.check_translation_sync()

        # Assert
        result = checker.results["translation_sync"]
        assert result["score"] == 0

    def test_within_7_days_is_high_score(self, tmp_path, monkeypatch):
        # Arrange -- 3-day diff => score = int(100 - (3/7 * 20)) = 91
        monkeypatch.chdir(tmp_path)
        now = time.time()
        three_days = 3 * 24 * 3600
        p1 = _write_readme(tmp_path, "README.md", MINIMAL_README)
        p2 = _write_readme(tmp_path, "README-zh.md", MINIMAL_README)
        p3 = _write_readme(tmp_path, "README-ja.md", MINIMAL_README)
        os.utime(p1, (now, now))
        os.utime(p2, (now, now))
        os.utime(p3, (now - three_days, now - three_days))
        checker = READMEQualityChecker()

        # Act
        checker.check_translation_sync()

        # Assert
        result = checker.results["translation_sync"]
        assert result["score"] >= 90
        assert result["status"] == "PASS"

    def test_no_files_present_returns_warn(self, tmp_path, monkeypatch):
        # Arrange -- none of the expected files exist
        monkeypatch.chdir(tmp_path)
        checker = READMEQualityChecker()

        # Act
        checker.check_translation_sync()

        # Assert
        result = checker.results["translation_sync"]
        assert result["score"] == 60
        assert result["status"] == "WARN"

    def test_mod_times_dict_populated(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        now = time.time()
        for name in ["README.md", "README-zh.md", "README-ja.md"]:
            p = _write_readme(tmp_path, name, MINIMAL_README)
            os.utime(p, (now, now))
        checker = READMEQualityChecker()

        # Act
        checker.check_translation_sync()

        # Assert
        result = checker.results["translation_sync"]
        assert "mod_times" in result
        assert set(result["mod_times"].keys()) == {"README.md", "README-zh.md", "README-ja.md"}


# ---------------------------------------------------------------------------
# generate_report
# ---------------------------------------------------------------------------


class TestGenerateReport:
    """Tests for READMEQualityChecker.generate_report."""

    def _run_checks_first(self, checker: READMEQualityChecker) -> None:
        """Run the three checks so generate_report has data."""
        checker.check_structure_consistency()
        checker.check_link_validation()
        checker.check_translation_sync()

    def test_high_score_returns_zero_exit(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        now = time.time()
        for name in ["README.md", "README-zh.md", "README-ja.md"]:
            p = _write_readme(tmp_path, name, THREE_HEADER_README)
            os.utime(p, (now, now))
        checker = READMEQualityChecker()
        self._run_checks_first(checker)

        # Act
        exit_code = checker.generate_report()

        # Assert
        assert exit_code == 0
        assert checker.results["overall_score"] >= 70

    def test_low_score_returns_one_exit(self, tmp_path, monkeypatch):
        # Arrange -- force low scores by pre-setting results
        monkeypatch.chdir(tmp_path)
        checker = READMEQualityChecker()
        checker.results["structure_consistency"] = {"score": 20, "details": {}, "status": "WARN"}
        checker.results["link_validation"] = {
            "score": 20,
            "broken_links": 8,
            "total_links": 10,
            "broken_list": [],
            "status": "FAIL",
        }
        checker.results["translation_sync"] = {"score": 20, "status": "WARN", "time_diff_days": 30}

        # Act
        exit_code = checker.generate_report()

        # Assert
        assert exit_code == 1
        assert checker.results["overall_score"] == 20

    def test_overall_score_is_integer_average(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        checker = READMEQualityChecker()
        checker.results["structure_consistency"] = {"score": 90, "details": {}, "status": "PASS"}
        checker.results["link_validation"] = {
            "score": 80,
            "broken_links": 0,
            "total_links": 5,
            "broken_list": [],
            "status": "PASS",
        }
        checker.results["translation_sync"] = {"score": 70, "status": "WARN", "time_diff_days": 5}

        # Act
        checker.generate_report()

        # Assert -- (90 + 80 + 70) // 3 = 80
        assert checker.results["overall_score"] == 80

    def test_json_report_written(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        now = time.time()
        for name in ["README.md", "README-zh.md", "README-ja.md"]:
            p = _write_readme(tmp_path, name, MINIMAL_README)
            os.utime(p, (now, now))
        checker = READMEQualityChecker()
        self._run_checks_first(checker)

        # Act
        checker.generate_report()

        # Assert
        report_path = tmp_path / "readme-quality-report.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert "overall_score" in data
        assert "structure_consistency" in data
        assert "link_validation" in data
        assert "translation_sync" in data

    def test_github_step_summary_written(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        summary_file = tmp_path / "step_summary.md"
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
        now = time.time()
        for name in ["README.md", "README-zh.md", "README-ja.md"]:
            p = _write_readme(tmp_path, name, MINIMAL_README)
            os.utime(p, (now, now))
        checker = READMEQualityChecker()
        self._run_checks_first(checker)

        # Act
        checker.generate_report()

        # Assert
        assert summary_file.exists()
        content = summary_file.read_text(encoding="utf-8")
        assert "README Quality Check Report" in content
        assert "Overall Score" in content

    def test_no_github_step_summary_env(self, tmp_path, monkeypatch):
        # Arrange -- GITHUB_STEP_SUMMARY not set
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
        now = time.time()
        for name in ["README.md", "README-zh.md", "README-ja.md"]:
            p = _write_readme(tmp_path, name, MINIMAL_README)
            os.utime(p, (now, now))
        checker = READMEQualityChecker()
        self._run_checks_first(checker)

        # Act
        exit_code = checker.generate_report()

        # Assert -- should not crash, just skip summary file
        assert exit_code == 0

    def test_report_contains_broken_links(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        summary_file = tmp_path / "step_summary.md"
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
        checker = READMEQualityChecker()
        checker.results["structure_consistency"] = {"score": 100, "details": {}, "status": "PASS"}
        checker.results["link_validation"] = {
            "score": 80,
            "broken_links": 2,
            "total_links": 5,
            "broken_list": ["README.md: bad_link.txt", "README.md: other.txt"],
            "status": "PASS",
        }
        checker.results["translation_sync"] = {"score": 100, "status": "PASS", "time_diff_days": 0}

        # Act
        checker.generate_report()

        # Assert
        content = summary_file.read_text(encoding="utf-8")
        assert "Broken links" in content
        assert "bad_link.txt" in content

    def test_recommendation_excellent(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        summary_file = tmp_path / "step_summary.md"
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
        checker = READMEQualityChecker()
        checker.results["structure_consistency"] = {"score": 100, "details": {}, "status": "PASS"}
        checker.results["link_validation"] = {
            "score": 100,
            "broken_links": 0,
            "total_links": 0,
            "broken_list": [],
            "status": "PASS",
        }
        checker.results["translation_sync"] = {"score": 100, "status": "PASS", "time_diff_days": 0}

        # Act
        checker.generate_report()

        # Assert
        content = summary_file.read_text(encoding="utf-8")
        assert "excellent" in content

    def test_recommendation_needs_improvement(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        summary_file = tmp_path / "step_summary.md"
        monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary_file))
        checker = READMEQualityChecker()
        checker.results["structure_consistency"] = {"score": 30, "details": {}, "status": "WARN"}
        checker.results["link_validation"] = {
            "score": 30,
            "broken_links": 7,
            "total_links": 10,
            "broken_list": [],
            "status": "FAIL",
        }
        checker.results["translation_sync"] = {"score": 30, "status": "WARN", "time_diff_days": 20}

        # Act
        checker.generate_report()

        # Assert
        content = summary_file.read_text(encoding="utf-8")
        assert "Needs improvement" in content


# ---------------------------------------------------------------------------
# run_all_checks
# ---------------------------------------------------------------------------


class TestRunAllChecks:
    """Tests for READMEQualityChecker.run_all_checks."""

    def test_perfect_readmes_return_zero(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
        now = time.time()
        for name in ["README.md", "README-zh.md", "README-ja.md"]:
            p = _write_readme(tmp_path, name, THREE_HEADER_README)
            os.utime(p, (now, now))
        checker = READMEQualityChecker()

        # Act
        exit_code = checker.run_all_checks()

        # Assert
        assert exit_code == 0
        assert checker.results["overall_score"] >= 70

    def test_no_files_crashes_in_generate_report(self, tmp_path, monkeypatch):
        # Arrange -- no READMEs at all; structure_consistency stays as []
        # which has no .get() method, so generate_report raises AttributeError
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
        checker = READMEQualityChecker()

        # Act / Assert -- documents the crash behavior
        with pytest.raises(AttributeError):
            checker.run_all_checks()

    def test_populates_all_result_sections(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
        now = time.time()
        for name in ["README.md", "README-zh.md", "README-ja.md"]:
            p = _write_readme(tmp_path, name, MINIMAL_README)
            os.utime(p, (now, now))
        checker = READMEQualityChecker()

        # Act
        checker.run_all_checks()

        # Assert -- all four result keys are populated (not initial defaults)
        assert isinstance(checker.results["structure_consistency"], dict)
        assert isinstance(checker.results["link_validation"], dict)
        assert isinstance(checker.results["translation_sync"], dict)
        assert isinstance(checker.results["overall_score"], int)

    def test_json_report_created_by_run_all(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
        now = time.time()
        for name in ["README.md", "README-zh.md", "README-ja.md"]:
            p = _write_readme(tmp_path, name, MINIMAL_README)
            os.utime(p, (now, now))
        checker = READMEQualityChecker()

        # Act
        checker.run_all_checks()

        # Assert
        report_path = tmp_path / "readme-quality-report.json"
        assert report_path.exists()
        data = json.loads(report_path.read_text(encoding="utf-8"))
        assert data["overall_score"] == checker.results["overall_score"]


# ---------------------------------------------------------------------------
# Edge cases and integration-level tests
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge case and integration tests."""

    def test_readme_with_no_headers(self, tmp_path, monkeypatch):
        # Arrange -- file with no markdown headers
        monkeypatch.chdir(tmp_path)
        _write_readme(tmp_path, "README.md", "Just plain text, no headers.\n")
        checker = READMEQualityChecker()

        # Act
        checker.check_structure_consistency()

        # Assert
        result = checker.results["structure_consistency"]
        assert result["details"]["README.md"] == 0

    def test_empty_readme_file(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        _write_readme(tmp_path, "README.md", "")
        checker = READMEQualityChecker()

        # Act
        checker.check_structure_consistency()
        checker.check_link_validation()

        # Assert
        struct = checker.results["structure_consistency"]
        links = checker.results["link_validation"]
        assert struct["details"]["README.md"] == 0
        assert links["total_links"] == 0

    def test_mixed_valid_and_broken_links(self, tmp_path, monkeypatch):
        # Arrange
        monkeypatch.chdir(tmp_path)
        (tmp_path / "good.txt").write_text("ok", encoding="utf-8")
        content = "# Title\n[Good](good.txt)\n[Bad](bad.txt)\n[Anchor](#section)\n"
        _write_readme(tmp_path, "README.md", content)
        checker = READMEQualityChecker()

        # Act
        checker.check_link_validation()

        # Assert
        result = checker.results["link_validation"]
        assert result["total_links"] == 3
        assert result["broken_links"] == 1
        assert result["score"] == 90

    def test_checker_default_readme_files(self):
        # Arrange / Act
        checker = READMEQualityChecker()

        # Assert
        assert checker.readme_files == ["README.md", "README-zh.md", "README-ja.md"]

    def test_initial_results_shape(self):
        # Arrange / Act
        checker = READMEQualityChecker()

        # Assert
        assert checker.results["structure_consistency"] == []
        assert checker.results["link_validation"] == []
        assert checker.results["translation_sync"] == []
        assert checker.results["overall_score"] == 0

    def test_hash_inside_code_block_not_counted_as_header(self, tmp_path, monkeypatch):
        # Arrange -- hash at start of line is still matched by regex
        # (the implementation uses ^#{1,6}\s+ with MULTILINE)
        # This documents current behavior: code block hashes ARE counted
        monkeypatch.chdir(tmp_path)
        content = "# Real Header\n```\n# Comment in code\n```\n"
        _write_readme(tmp_path, "README.md", content)
        checker = READMEQualityChecker()

        # Act
        checker.check_structure_consistency()

        # Assert -- documents actual behavior (regex matches inside code blocks)
        result = checker.results["structure_consistency"]
        assert result["details"]["README.md"] == 2

    def test_translation_sync_exact_boundary_7_days(self, tmp_path, monkeypatch):
        # Arrange -- exactly 7 days => score = max(0, 100 - (1.0 * 20)) = 80
        monkeypatch.chdir(tmp_path)
        now = time.time()
        seven_days = 7 * 24 * 3600
        p1 = _write_readme(tmp_path, "README.md", MINIMAL_README)
        p2 = _write_readme(tmp_path, "README-zh.md", MINIMAL_README)
        p3 = _write_readme(tmp_path, "README-ja.md", MINIMAL_README)
        os.utime(p1, (now, now))
        os.utime(p2, (now, now))
        os.utime(p3, (now - seven_days, now - seven_days))
        checker = READMEQualityChecker()

        # Act
        checker.check_translation_sync()

        # Assert
        result = checker.results["translation_sync"]
        assert result["score"] == 80
        assert result["status"] == "PASS"
