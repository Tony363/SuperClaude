"""Tests for scripts/apply_autofix.py pure functions."""

from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.apply_autofix import (
    build_fix_command,
    load_fix_plan,
    pre_check_file,
)
from scripts.fix_type_registry import get_fix_type


class TestPreCheckFile:
    """Tests for pre_check_file."""

    def test_nonexistent_file(self, tmp_path: Path):
        success, msg = pre_check_file(tmp_path / "no_file.py")
        assert success is False
        assert "does not exist" in msg

    def test_directory_not_file(self, tmp_path: Path):
        d = tmp_path / "subdir"
        d.mkdir()
        success, msg = pre_check_file(d)
        assert success is False
        assert "Not a file" in msg

    def test_non_python_file(self, tmp_path: Path, monkeypatch):
        f = tmp_path / "test.txt"
        f.write_text("hello")
        monkeypatch.chdir(tmp_path)
        from unittest.mock import patch

        with patch("scripts.apply_autofix.is_file_allowed_for_autofix", return_value=True):
            success, msg = pre_check_file(f)
        assert success is False
        assert "Not a Python" in msg

    def test_file_exceeds_loc_limit(self, tmp_path: Path, monkeypatch):
        f = tmp_path / "big.py"
        f.write_text("x = 1\n" * 300)

        monkeypatch.chdir(tmp_path)

        # allowlist blocks this file anyway, so mock it
        with patch("scripts.apply_autofix.is_file_allowed_for_autofix", return_value=True):
            success, msg = pre_check_file(f)
        assert success is False
        assert "LOC limit" in msg

    def test_valid_small_python_file(self, tmp_path: Path, monkeypatch):
        f = tmp_path / "good.py"
        f.write_text("x = 1\n")
        monkeypatch.chdir(tmp_path)

        with patch("scripts.apply_autofix.is_file_allowed_for_autofix", return_value=True):
            success, msg = pre_check_file(f)
        assert success is True
        assert "passed" in msg.lower()


class TestBuildFixCommand:
    """Tests for build_fix_command."""

    def test_ruff_format_command(self):
        fix_type = get_fix_type("ruff_format")
        assert fix_type is not None
        cmd = build_fix_command(fix_type, Path("test.py"))
        assert "ruff" in cmd
        assert "test.py" in cmd


class TestLoadFixPlan:
    """Tests for load_fix_plan."""

    def test_loads_valid_json(self, tmp_path: Path):
        import json

        data = {"findings": [{"file": "test.py", "autofix_eligible": True}]}
        p = tmp_path / "quality.json"
        p.write_text(json.dumps(data))

        result = load_fix_plan(p)
        assert result is not None
        assert len(result["findings"]) == 1

    def test_missing_file(self, tmp_path: Path):
        result = load_fix_plan(tmp_path / "nope.json")
        assert result is None

    def test_invalid_json(self, tmp_path: Path):
        p = tmp_path / "bad.json"
        p.write_text("not json")
        result = load_fix_plan(p)
        assert result is None


# ---------------------------------------------------------------------------
# Additional coverage: run_command, apply_fix, check_idempotency,
# check_syntax, check_git_changes, apply_autofix_to_file,
# apply_autofix_to_category, main
# ---------------------------------------------------------------------------

import json  # noqa: E402
import subprocess  # noqa: E402

from scripts.apply_autofix import (  # noqa: E402
    apply_autofix_to_category,
    apply_autofix_to_file,
    apply_fix,
    check_git_changes,
    check_idempotency,
    check_syntax,
    main,
    run_command,
)


class TestRunCommand:
    """Tests for run_command."""

    def test_success_returns_true_and_stdout(self):
        """Successful command returns (True, stdout)."""
        fake = subprocess.CompletedProcess(args=["echo"], returncode=0, stdout="hello\n")
        with patch("scripts.apply_autofix.subprocess.run", return_value=fake) as mock_run:
            success, output = run_command(["echo", "hello"])
        assert success is True
        assert output == "hello"
        mock_run.assert_called_once_with(
            ["echo", "hello"], capture_output=True, text=True, check=False
        )

    def test_nonzero_returncode_returns_false(self):
        """Non-zero return code returns (False, stdout)."""
        fake = subprocess.CompletedProcess(args=["false"], returncode=1, stdout="err msg")
        with patch("scripts.apply_autofix.subprocess.run", return_value=fake):
            success, output = run_command(["false"])
        assert success is False
        assert output == "err msg"

    def test_called_process_error_returns_false_with_stderr(self):
        """CalledProcessError is caught and returns (False, stderr)."""
        err = subprocess.CalledProcessError(1, "cmd", stderr="bad input")
        with patch("scripts.apply_autofix.subprocess.run", side_effect=err):
            success, output = run_command(["cmd"], check=True)
        assert success is False
        assert "bad input" in output

    def test_called_process_error_no_stderr_returns_str(self):
        """CalledProcessError with no stderr falls back to str(e)."""
        err = subprocess.CalledProcessError(2, "cmd", stderr="")
        with patch("scripts.apply_autofix.subprocess.run", side_effect=err):
            success, output = run_command(["cmd"], check=True)
        assert success is False
        # When stderr is empty string (falsy), str(e) is used
        assert "cmd" in output or "returned non-zero" in output

    def test_capture_output_false(self):
        """When capture_output=False, output is empty string."""
        fake = subprocess.CompletedProcess(args=["ls"], returncode=0, stdout=None)
        with patch("scripts.apply_autofix.subprocess.run", return_value=fake):
            success, output = run_command(["ls"], capture_output=False)
        assert success is True
        assert output == ""

    def test_check_flag_forwarded(self):
        """The check parameter is forwarded to subprocess.run."""
        fake = subprocess.CompletedProcess(args=["true"], returncode=0, stdout="")
        with patch("scripts.apply_autofix.subprocess.run", return_value=fake) as mock_run:
            run_command(["true"], check=True)
        mock_run.assert_called_once_with(["true"], capture_output=True, text=True, check=True)


class TestApplyFix:
    """Tests for apply_fix."""

    def test_unknown_fix_type_returns_false(self):
        """Unknown fix type name is rejected."""
        success, msg = apply_fix(Path("test.py"), "nonexistent_fix_type")
        assert success is False
        assert "Unknown fix type" in msg

    def test_successful_fix_returns_true(self, tmp_path: Path):
        """Successful command returns (True, 'Applied ...')."""
        f = tmp_path / "ok.py"
        f.write_text("x = 1\n")
        with patch("scripts.apply_autofix.run_command", return_value=(True, "")):
            success, msg = apply_fix(f, "ruff_format")
        assert success is True
        assert "Applied ruff_format" in msg

    def test_failed_command_returns_false(self, tmp_path: Path):
        """Failed command returns (False, '<fix_type> failed: ...')."""
        f = tmp_path / "bad.py"
        f.write_text("x = 1\n")
        with patch("scripts.apply_autofix.run_command", return_value=(False, "some error")):
            success, msg = apply_fix(f, "ruff_format")
        assert success is False
        assert "ruff_format failed" in msg
        assert "some error" in msg


class TestCheckIdempotency:
    """Tests for check_idempotency."""

    def test_idempotent_on_first_pass(self, tmp_path: Path):
        """File unchanged after fix => idempotent on pass 1."""
        f = tmp_path / "stable.py"
        f.write_text("x = 1\n")

        # apply_fix is called but file content stays the same
        with patch("scripts.apply_autofix.apply_fix", return_value=(True, "ok")):
            success, msg = check_idempotency(f, "ruff_format")
        assert success is True
        assert "stabilized after 1 pass" in msg

    def test_not_idempotent_after_max_passes(self, tmp_path: Path):
        """File keeps changing => not idempotent."""
        f = tmp_path / "unstable.py"
        f.write_text("x = 0\n")
        call_count = 0

        def mutating_fix(path, name):
            nonlocal call_count
            call_count += 1
            # Each call changes the file content differently
            f.write_text(f"x = {call_count * 10}\n")
            return (True, "ok")

        # ruff_format has max_passes=1, so after 1 pass if still changing => fail
        with patch("scripts.apply_autofix.apply_fix", side_effect=mutating_fix):
            success, msg = check_idempotency(f, "ruff_format")
        assert success is False
        assert "NOT idempotent" in msg

    def test_fix_failure_during_pass(self, tmp_path: Path):
        """If apply_fix fails during a pass, return failure."""
        f = tmp_path / "err.py"
        f.write_text("x = 1\n")

        with patch("scripts.apply_autofix.apply_fix", return_value=(False, "tool crash")):
            success, msg = check_idempotency(f, "ruff_format")
        assert success is False
        assert "Pass 1 failed" in msg

    def test_multi_pass_fix_type_stabilizes(self, tmp_path: Path):
        """ruff_lint_fix has max_passes=3; stabilizes after 2 passes."""
        f = tmp_path / "lint.py"
        f.write_text("import os\n")

        call_count = 0

        def stabilize_on_second(path, name):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: changes the file
                f.write_text("# fixed\n")
            # Second and later: no changes (file content stays)
            return (True, "ok")

        with patch("scripts.apply_autofix.apply_fix", side_effect=stabilize_on_second):
            success, msg = check_idempotency(f, "ruff_lint_fix")
        assert success is True
        assert "stabilized after 2 pass" in msg

    def test_unreadable_file_before_pass(self, tmp_path: Path):
        """OSError reading file before pass returns failure."""
        f = tmp_path / "gone.py"
        # File doesn't exist so open() will fail
        success, msg = check_idempotency(f, "ruff_format")
        assert success is False
        assert "Cannot read file for idempotency check" in msg

    def test_unreadable_file_after_pass(self, tmp_path: Path):
        """OSError reading file after pass returns failure."""
        f = tmp_path / "disappear.py"
        f.write_text("x = 1\n")

        def delete_file(path, name):
            f.unlink()  # Remove file so second read fails
            return (True, "ok")

        with patch("scripts.apply_autofix.apply_fix", side_effect=delete_file):
            success, msg = check_idempotency(f, "ruff_format")
        assert success is False
        assert "Cannot read file after pass" in msg

    def test_unknown_fix_type_defaults_max_passes_1(self, tmp_path: Path):
        """Unknown fix type name falls back to max_passes=1."""
        f = tmp_path / "unknown.py"
        f.write_text("x = 1\n")

        # apply_fix will return failure for unknown type, but we mock it
        # to succeed so we can verify max_passes=1 behavior
        with patch("scripts.apply_autofix.apply_fix", return_value=(True, "ok")):
            success, msg = check_idempotency(f, "nonexistent_type")
        assert success is True
        assert "stabilized after 1 pass" in msg


class TestCheckSyntax:
    """Tests for check_syntax."""

    def test_valid_syntax_returns_true(self):
        """Valid Python file passes syntax check."""
        with patch("scripts.apply_autofix.run_command", return_value=(True, "")):
            success, msg = check_syntax(Path("good.py"))
        assert success is True
        assert "Syntax check passed" in msg

    def test_invalid_syntax_returns_false(self):
        """Syntax error returns failure with message."""
        with patch(
            "scripts.apply_autofix.run_command",
            return_value=(False, "SyntaxError: invalid syntax"),
        ):
            success, msg = check_syntax(Path("bad.py"))
        assert success is False
        assert "Syntax error after formatting" in msg

    def test_calls_py_compile(self):
        """Verifies the correct py_compile command is constructed."""
        with patch("scripts.apply_autofix.run_command", return_value=(True, "")) as mock_cmd:
            check_syntax(Path("/tmp/test.py"))
        mock_cmd.assert_called_once_with(["python", "-m", "py_compile", "/tmp/test.py"])


class TestCheckGitChanges:
    """Tests for check_git_changes."""

    def test_no_changes_returns_true(self):
        """No git diff output means file is already formatted."""
        with patch("scripts.apply_autofix.run_command", return_value=(True, "")):
            success, msg = check_git_changes(Path("test.py"))
        assert success is True
        assert "already formatted" in msg

    def test_reasonable_diff_returns_true(self):
        """Small diff passes verification."""
        diff_output = "\n".join([f"+ line {i}" for i in range(10)])
        with patch("scripts.apply_autofix.run_command", return_value=(True, diff_output)):
            success, msg = check_git_changes(Path("test.py"))
        assert success is True
        assert "diff lines" in msg

    def test_large_diff_returns_false(self):
        """Suspiciously large diff fails verification."""
        diff_output = "\n".join([f"+ line {i}" for i in range(600)])
        with patch("scripts.apply_autofix.run_command", return_value=(True, diff_output)):
            success, msg = check_git_changes(Path("test.py"))
        assert success is False
        assert "Suspiciously large diff" in msg

    def test_git_diff_failure_returns_false(self):
        """git diff command failure returns (False, 'git diff failed')."""
        with patch("scripts.apply_autofix.run_command", return_value=(False, "error")):
            success, msg = check_git_changes(Path("test.py"))
        assert success is False
        assert "git diff failed" in msg

    def test_whitespace_only_diff_treated_as_no_changes(self):
        """Whitespace-only diff output is treated as no changes."""
        with patch("scripts.apply_autofix.run_command", return_value=(True, "   \n  \n ")):
            success, msg = check_git_changes(Path("test.py"))
        assert success is True
        assert "already formatted" in msg


class TestApplyAutofixToFile:
    """Tests for apply_autofix_to_file (full pipeline for one file)."""

    def test_pre_check_failure_short_circuits(self, tmp_path: Path):
        """If pre_check_file fails, pipeline stops immediately."""
        f = tmp_path / "missing.py"  # Does not exist
        success, msg, details = apply_autofix_to_file(f, "ruff_format")
        assert success is False
        assert "does not exist" in msg
        assert len(details["checks_failed"]) == 1
        assert details["checks_failed"][0][0] == "pre_check"

    def test_apply_fix_failure_short_circuits(self, tmp_path: Path, monkeypatch):
        """If apply_fix fails, pipeline stops after pre-check."""
        f = tmp_path / "ok.py"
        f.write_text("x = 1\n")
        monkeypatch.chdir(tmp_path)

        with (
            patch("scripts.apply_autofix.is_file_allowed_for_autofix", return_value=True),
            patch("scripts.apply_autofix.apply_fix", return_value=(False, "ruff crashed")),
        ):
            success, msg, details = apply_autofix_to_file(f, "ruff_format")
        assert success is False
        assert "ruff crashed" in msg
        assert "pre_check" in details["checks_passed"]
        assert details["checks_failed"][0][0] == "ruff_format"

    def test_idempotency_failure_triggers_rollback(self, tmp_path: Path, monkeypatch):
        """Idempotency failure triggers git restore rollback."""
        f = tmp_path / "unstable.py"
        f.write_text("x = 1\n")
        monkeypatch.chdir(tmp_path)

        with (
            patch("scripts.apply_autofix.is_file_allowed_for_autofix", return_value=True),
            patch("scripts.apply_autofix.apply_fix", return_value=(True, "ok")),
            patch(
                "scripts.apply_autofix.check_idempotency", return_value=(False, "not idempotent")
            ),
            patch("scripts.apply_autofix.run_command", return_value=(True, "")) as mock_cmd,
        ):
            success, msg, details = apply_autofix_to_file(f, "ruff_format")
        assert success is False
        assert "not idempotent" in msg
        # Verify git restore was called for rollback
        mock_cmd.assert_called_once()
        assert "git" in mock_cmd.call_args[0][0]
        assert "restore" in mock_cmd.call_args[0][0]

    def test_syntax_failure_triggers_rollback(self, tmp_path: Path, monkeypatch):
        """Syntax check failure triggers git restore rollback."""
        f = tmp_path / "broken.py"
        f.write_text("x = 1\n")
        monkeypatch.chdir(tmp_path)

        with (
            patch("scripts.apply_autofix.is_file_allowed_for_autofix", return_value=True),
            patch("scripts.apply_autofix.apply_fix", return_value=(True, "ok")),
            patch("scripts.apply_autofix.check_idempotency", return_value=(True, "ok")),
            patch("scripts.apply_autofix.check_syntax", return_value=(False, "SyntaxError")),
            patch("scripts.apply_autofix.run_command", return_value=(True, "")) as mock_cmd,
        ):
            success, msg, details = apply_autofix_to_file(f, "ruff_format")
        assert success is False
        assert "SyntaxError" in msg
        assert ("syntax", "SyntaxError") in details["checks_failed"]
        mock_cmd.assert_called_once()

    def test_git_changes_warning_does_not_fail(self, tmp_path: Path, monkeypatch):
        """Git changes warning is logged but doesn't cause failure."""
        f = tmp_path / "warned.py"
        f.write_text("x = 1\n")
        monkeypatch.chdir(tmp_path)

        with (
            patch("scripts.apply_autofix.is_file_allowed_for_autofix", return_value=True),
            patch("scripts.apply_autofix.apply_fix", return_value=(True, "ok")),
            patch("scripts.apply_autofix.check_idempotency", return_value=(True, "ok")),
            patch("scripts.apply_autofix.check_syntax", return_value=(True, "ok")),
            patch("scripts.apply_autofix.check_git_changes", return_value=(False, "large diff")),
        ):
            success, msg, details = apply_autofix_to_file(f, "ruff_format")
        assert success is True
        assert "git_changes" not in details["checks_passed"]
        assert ("git_changes", "large diff") in details["checks_failed"]

    def test_full_success_pipeline(self, tmp_path: Path, monkeypatch):
        """All checks pass => success with all checks recorded."""
        f = tmp_path / "perfect.py"
        f.write_text("x = 1\n")
        monkeypatch.chdir(tmp_path)

        with (
            patch("scripts.apply_autofix.is_file_allowed_for_autofix", return_value=True),
            patch("scripts.apply_autofix.apply_fix", return_value=(True, "ok")),
            patch("scripts.apply_autofix.check_idempotency", return_value=(True, "ok")),
            patch("scripts.apply_autofix.check_syntax", return_value=(True, "ok")),
            patch("scripts.apply_autofix.check_git_changes", return_value=(True, "3 diff lines")),
        ):
            success, msg, details = apply_autofix_to_file(f, "ruff_format")
        assert success is True
        assert "successfully" in msg
        assert "pre_check" in details["checks_passed"]
        assert "ruff_format" in details["checks_passed"]
        assert "idempotency" in details["checks_passed"]
        assert "syntax" in details["checks_passed"]
        assert "git_changes" in details["checks_passed"]
        assert len(details["checks_failed"]) == 0


class TestApplyAutofixToCategory:
    """Tests for apply_autofix_to_category."""

    def test_missing_fix_plan_file_returns_skipped(self, tmp_path: Path):
        """Missing fix plan file returns skipped status."""
        result = apply_autofix_to_category("quality", tmp_path)
        assert result["status"] == "skipped"
        assert "No fix plan found" in result["reason"]

    def test_invalid_fix_plan_returns_error(self, tmp_path: Path):
        """Invalid JSON fix plan returns error status."""
        p = tmp_path / "quality.json"
        p.write_text("not json")
        result = apply_autofix_to_category("quality", tmp_path)
        assert result["status"] == "error"
        assert "Failed to load fix plan" in result["reason"]

    def test_no_eligible_findings_returns_skipped(self, tmp_path: Path):
        """No autofix-eligible findings returns skipped status."""
        p = tmp_path / "quality.json"
        data = {"findings": [{"file": "test.py", "autofix_eligible": False}]}
        p.write_text(json.dumps(data))
        result = apply_autofix_to_category("quality", tmp_path)
        assert result["status"] == "skipped"
        assert "No autofix-eligible findings" in result["reason"]
        assert result["total_findings"] == 1

    def test_empty_findings_returns_skipped(self, tmp_path: Path):
        """Empty findings list returns skipped status."""
        p = tmp_path / "quality.json"
        p.write_text(json.dumps({"findings": []}))
        result = apply_autofix_to_category("quality", tmp_path)
        assert result["status"] == "skipped"
        assert "No autofix-eligible findings" in result["reason"]

    def test_processes_eligible_findings(self, tmp_path: Path):
        """Eligible findings are processed and results tallied."""
        p = tmp_path / "quality.json"
        data = {
            "findings": [
                {
                    "file": "/tmp/a.py",
                    "autofix_eligible": True,
                    "_resolved_fix_type": "ruff_format",
                },
                {
                    "file": "/tmp/b.py",
                    "autofix_eligible": True,
                    "_resolved_fix_type": "ruff_format",
                },
                {"file": "/tmp/c.py", "autofix_eligible": False},
            ]
        }
        p.write_text(json.dumps(data))

        mock_details = {
            "file": "",
            "checks_passed": ["pre_check"],
            "checks_failed": [],
        }
        with patch(
            "scripts.apply_autofix.apply_autofix_to_file",
            return_value=(True, "ok", dict(mock_details)),
        ):
            result = apply_autofix_to_category("quality", tmp_path)

        assert result["category"] == "quality"
        assert result["total_findings"] == 3
        assert result["autofix_eligible"] == 2
        assert result["files_attempted"] == 2
        assert result["files_succeeded"] == 2
        assert result["files_failed"] == 0

    def test_tallies_failures(self, tmp_path: Path):
        """Failed file fixes are counted."""
        p = tmp_path / "quality.json"
        data = {
            "findings": [
                {"file": "/tmp/fail.py", "autofix_eligible": True},
            ]
        }
        p.write_text(json.dumps(data))

        mock_details = {"file": "/tmp/fail.py", "checks_passed": [], "checks_failed": []}
        with patch(
            "scripts.apply_autofix.apply_autofix_to_file",
            return_value=(False, "error", dict(mock_details)),
        ):
            result = apply_autofix_to_category("quality", tmp_path)

        assert result["files_succeeded"] == 0
        assert result["files_failed"] == 1

    def test_file_limit_enforced(self, tmp_path: Path):
        """MAX_FILES_PER_RUN limits the number of files processed."""
        p = tmp_path / "quality.json"
        # Create more files than MAX_FILES_PER_RUN (5)
        findings = [{"file": f"/tmp/file{i}.py", "autofix_eligible": True} for i in range(10)]
        p.write_text(json.dumps({"findings": findings}))

        mock_details = {"file": "", "checks_passed": [], "checks_failed": []}
        with patch(
            "scripts.apply_autofix.apply_autofix_to_file",
            return_value=(True, "ok", dict(mock_details)),
        ) as mock_fix:
            result = apply_autofix_to_category("quality", tmp_path)

        # Only MAX_FILES_PER_RUN (5) files should be attempted
        assert result["files_attempted"] == 5
        assert mock_fix.call_count == 5

    def test_multiple_findings_per_file_grouped(self, tmp_path: Path):
        """Multiple findings for the same file are grouped (one fix call)."""
        p = tmp_path / "quality.json"
        data = {
            "findings": [
                {
                    "file": "/tmp/same.py",
                    "autofix_eligible": True,
                    "_resolved_fix_type": "ruff_format",
                },
                {
                    "file": "/tmp/same.py",
                    "autofix_eligible": True,
                    "_resolved_fix_type": "ruff_format",
                },
            ]
        }
        p.write_text(json.dumps(data))

        mock_details = {"file": "/tmp/same.py", "checks_passed": [], "checks_failed": []}
        with patch(
            "scripts.apply_autofix.apply_autofix_to_file",
            return_value=(True, "ok", dict(mock_details)),
        ) as mock_fix:
            result = apply_autofix_to_category("quality", tmp_path)

        # Only one file should be processed despite two findings
        assert result["files_attempted"] == 1
        assert mock_fix.call_count == 1
        # The details should record findings_count = 2
        assert result["details"][0]["findings_count"] == 2

    def test_defaults_fix_type_to_ruff_format(self, tmp_path: Path):
        """Missing _resolved_fix_type defaults to ruff_format."""
        p = tmp_path / "quality.json"
        data = {
            "findings": [
                {"file": "/tmp/default.py", "autofix_eligible": True},
            ]
        }
        p.write_text(json.dumps(data))

        mock_details = {"file": "/tmp/default.py", "checks_passed": [], "checks_failed": []}
        with patch(
            "scripts.apply_autofix.apply_autofix_to_file",
            return_value=(True, "ok", dict(mock_details)),
        ) as mock_fix:
            apply_autofix_to_category("quality", tmp_path)

        # Verify ruff_format was used as default
        mock_fix.assert_called_once_with(Path("/tmp/default.py"), "ruff_format")


class TestMain:
    """Tests for main() CLI entry point."""

    def test_missing_fix_plans_dir_exits_1(self, tmp_path: Path, monkeypatch):
        """Non-existent fix-plans-dir causes sys.exit(1)."""
        monkeypatch.setattr(
            "sys.argv",
            ["apply_autofix", "--fix-plans-dir", str(tmp_path / "nonexistent")],
        )
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    def test_default_category_is_quality(self, tmp_path: Path, monkeypatch):
        """Without --category, defaults to ['quality']."""
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        output_file = tmp_path / "results.json"

        monkeypatch.setattr(
            "sys.argv",
            [
                "apply_autofix",
                "--fix-plans-dir",
                str(plans_dir),
                "--output",
                str(output_file),
            ],
        )

        with patch(
            "scripts.apply_autofix.apply_autofix_to_category",
            return_value={"files_succeeded": 0, "files_failed": 0},
        ) as mock_cat:
            main()

        mock_cat.assert_called_once_with("quality", plans_dir)

    def test_specific_category(self, tmp_path: Path, monkeypatch):
        """--category flag processes only that category."""
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        output_file = tmp_path / "results.json"

        monkeypatch.setattr(
            "sys.argv",
            [
                "apply_autofix",
                "--fix-plans-dir",
                str(plans_dir),
                "--output",
                str(output_file),
                "--category",
                "security",
            ],
        )

        with patch(
            "scripts.apply_autofix.apply_autofix_to_category",
            return_value={"files_succeeded": 0, "files_failed": 0},
        ) as mock_cat:
            main()

        mock_cat.assert_called_once_with("security", plans_dir)

    def test_writes_results_json(self, tmp_path: Path, monkeypatch):
        """Results JSON is written with expected structure."""
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        output_file = tmp_path / "results.json"

        monkeypatch.setattr(
            "sys.argv",
            [
                "apply_autofix",
                "--fix-plans-dir",
                str(plans_dir),
                "--output",
                str(output_file),
            ],
        )

        with patch(
            "scripts.apply_autofix.apply_autofix_to_category",
            return_value={"files_succeeded": 2, "files_failed": 0},
        ):
            main()

        assert output_file.exists()
        data = json.loads(output_file.read_text())
        assert "timestamp" in data
        assert data["categories_processed"] == ["quality"]
        assert data["total_files_succeeded"] == 2
        assert data["total_files_failed"] == 0
        assert len(data["results"]) == 1

    def test_exits_1_on_failures(self, tmp_path: Path, monkeypatch):
        """sys.exit(1) when total_failed > 0."""
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        output_file = tmp_path / "results.json"

        monkeypatch.setattr(
            "sys.argv",
            [
                "apply_autofix",
                "--fix-plans-dir",
                str(plans_dir),
                "--output",
                str(output_file),
            ],
        )

        with patch(
            "scripts.apply_autofix.apply_autofix_to_category",
            return_value={"files_succeeded": 1, "files_failed": 2},
        ):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_exits_0_on_success(self, tmp_path: Path, monkeypatch):
        """No sys.exit on full success (implicit exit 0)."""
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        output_file = tmp_path / "results.json"

        monkeypatch.setattr(
            "sys.argv",
            [
                "apply_autofix",
                "--fix-plans-dir",
                str(plans_dir),
                "--output",
                str(output_file),
            ],
        )

        with patch(
            "scripts.apply_autofix.apply_autofix_to_category",
            return_value={"files_succeeded": 3, "files_failed": 0},
        ):
            # Should not raise SystemExit
            main()

    def test_default_output_path(self, tmp_path: Path, monkeypatch):
        """Default output is autofix-results.json in cwd."""
        plans_dir = tmp_path / "plans"
        plans_dir.mkdir()
        monkeypatch.chdir(tmp_path)

        monkeypatch.setattr(
            "sys.argv",
            ["apply_autofix", "--fix-plans-dir", str(plans_dir)],
        )

        with patch(
            "scripts.apply_autofix.apply_autofix_to_category",
            return_value={"files_succeeded": 0, "files_failed": 0},
        ):
            main()

        default_output = tmp_path / "autofix-results.json"
        assert default_output.exists()
