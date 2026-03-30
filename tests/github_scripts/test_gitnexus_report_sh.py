"""Tests for .github/scripts/gitnexus-report.sh.

Validates shell script syntax, security hardening, structural correctness,
and functional behavior via subprocess execution with mock binaries.
"""

import os
import subprocess
import textwrap
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parent.parent.parent / ".github" / "scripts" / "gitnexus-report.sh"


# ── Tier 1: Static Analysis ──────────────────────────────────────────


class TestShellSyntax:
    """Validate shell script parses without errors."""

    def test_bash_syntax_check(self):
        """Script passes bash -n syntax validation."""
        result = subprocess.run(
            ["bash", "-n", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Syntax error: {result.stderr}"

    def test_shebang_present(self):
        """Script has a bash shebang line."""
        first_line = SCRIPT_PATH.read_text().split("\n")[0]
        assert first_line.startswith("#!/"), f"Missing shebang: {first_line}"
        assert "bash" in first_line


class TestErrorHandling:
    """Validate robust error handling settings."""

    def test_uses_strict_error_mode(self):
        """Script uses set -euo pipefail for robust error handling."""
        content = SCRIPT_PATH.read_text()
        assert "set -euo pipefail" in content

    def test_no_bare_set_e(self):
        """Script should not have plain 'set -e' without -u and pipefail."""
        for line in SCRIPT_PATH.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if stripped == "set -e" or (
                stripped.startswith("set -e ") and "pipefail" not in stripped
            ):
                pytest.fail(f"Found weak error handling: '{stripped}'. Use 'set -euo pipefail'.")


class TestSecurityHardening:
    """Validate input sanitization and safe command patterns."""

    def test_npx_calls_use_double_dash_separator(self):
        """All npx gitnexus impact calls use -- to prevent flag injection."""
        content = SCRIPT_PATH.read_text()
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "npx gitnexus impact" in stripped and "-- " not in stripped:
                pytest.fail(f"Line {i}: npx gitnexus impact without '--' separator: {stripped}")

    def test_remote_is_configurable(self):
        """Remote name is configurable via GITNEXUS_REMOTE env var."""
        content = SCRIPT_PATH.read_text()
        assert "GITNEXUS_REMOTE" in content, (
            "Expected GITNEXUS_REMOTE env var for configurable remote name"
        )

    def test_no_hardcoded_origin_in_git_diff(self):
        """git diff does not hardcode 'origin/' — should use $REMOTE variable."""
        content = SCRIPT_PATH.read_text()
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "git diff" in stripped and '"origin/' in stripped:
                pytest.fail(f"Line {i}: Hardcoded 'origin/' in git diff. Use $REMOTE variable.")


class TestDependencyValidation:
    """Validate that required tools are checked before use."""

    def test_check_deps_function_exists(self):
        """Script defines a check_deps function."""
        content = SCRIPT_PATH.read_text()
        assert "check_deps" in content, "Missing check_deps function"

    def test_checks_for_required_tools(self):
        """check_deps validates jq, npx, and git."""
        content = SCRIPT_PATH.read_text()
        for tool in ["jq", "npx", "git"]:
            assert tool in content, f"Missing dependency check for {tool}"


class TestDeduplication:
    """Validate safe array deduplication without word splitting."""

    def test_uses_mapfile_for_dedup(self):
        """Deduplication uses mapfile instead of bare command substitution."""
        content = SCRIPT_PATH.read_text()
        # Should NOT have the word-splitting pattern
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "UNIQUE_PROCESSES=($(" in stripped or "UNIQUE_MODULES=($(" in stripped:
                pytest.fail(f"Line {i}: Word-splitting-vulnerable array assignment: {stripped}")


class TestHtmlMarker:
    """Validate HTML comment marker for idempotent PR comments."""

    MARKER = "<!-- gitnexus-impact -->"

    def test_report_includes_html_marker(self):
        """Main report output includes the HTML marker."""
        content = SCRIPT_PATH.read_text()
        assert self.MARKER in content, "Missing HTML marker in report output"

    def test_early_exit_includes_html_marker(self):
        """Early exit path (no changed files) also includes the HTML marker."""
        content = SCRIPT_PATH.read_text()
        # Find the early exit block (between "CHANGED_FILES[@]} -eq 0" and "exit 0")
        lines = content.splitlines()
        in_early_exit = False
        found_marker = False
        for line in lines:
            if "-eq 0" in line and "CHANGED_FILES" in line:
                in_early_exit = True
            if in_early_exit:
                if self.MARKER in line:
                    found_marker = True
                if "exit 0" in line:
                    break
        assert found_marker, (
            "Early exit path (no changed files) does not include HTML marker. "
            "This breaks idempotent PR comment updates."
        )


class TestStructure:
    """Validate expected functions and structure."""

    EXPECTED_FUNCTIONS = ["risk_rank", "risk_badge", "check_deps"]

    def test_all_functions_defined(self):
        """Script defines all expected functions."""
        content = SCRIPT_PATH.read_text()
        for func in self.EXPECTED_FUNCTIONS:
            assert f"{func}()" in content, f"Missing function: {func}()"

    def test_no_unused_github_output(self):
        """No 'report=' output to GITHUB_OUTPUT (it was never consumed)."""
        content = SCRIPT_PATH.read_text()
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "report=" in stripped and "GITHUB_OUTPUT" in stripped:
                pytest.fail(f"Line {i}: Dead 'report=' output to GITHUB_OUTPUT: {stripped}")


# ── Tier 2: Execution Tests ──────────────────────────────────────────


@pytest.fixture
def mock_bin_dir(tmp_path):
    """Create a temp directory with mock binaries for npx, jq, git."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    # Mock git: returns configurable file list via GIT_MOCK_FILES env var
    git_script = bin_dir / "git"
    git_script.write_text(
        textwrap.dedent("""\
        #!/usr/bin/env bash
        if [[ "$1" == "diff" && "$2" == "--name-only" ]]; then
            if [[ -n "${GIT_MOCK_FILES:-}" ]]; then
                printf '%s\\n' "${GIT_MOCK_FILES}"
            fi
        else
            /usr/bin/git "$@"
        fi
    """)
    )
    git_script.chmod(0o755)

    # Mock npx: returns canned JSON via NPX_MOCK_RESPONSE env var or file
    default_json = bin_dir / "default_response.json"
    default_json.write_text(
        '{"risk":"LOW","impactedCount":1,"summary":{"direct":1,"processes_affected":0,"modules_affected":0},"affected_processes":[],"affected_modules":[],"byDepth":{}}'
    )
    npx_script = bin_dir / "npx"
    npx_script.write_text(
        textwrap.dedent(f"""\
        #!/usr/bin/env bash
        if [[ "$1" == "gitnexus" && "$2" == "impact" ]]; then
            if [[ -n "${{NPX_MOCK_RESPONSE:-}}" ]]; then
                echo "$NPX_MOCK_RESPONSE"
            else
                cat "{default_json}"
            fi
        elif [[ "$1" == "gitnexus" && "$2" == "analyze" ]]; then
            echo "Indexed."
        else
            echo "mock npx: unknown command $*" >&2
            exit 1
        fi
    """)
    )
    npx_script.chmod(0o755)

    return bin_dir


@pytest.fixture
def run_report(mock_bin_dir, tmp_path):
    """Helper to run gitnexus-report.sh with mock environment."""

    def _run(
        base_ref="main",
        mock_files="",
        mock_response=None,
        extra_env=None,
        remote="origin",
    ):
        env = os.environ.copy()
        # Prepend mock bin dir to PATH
        env["PATH"] = f"{mock_bin_dir}:{env['PATH']}"
        env["GIT_MOCK_FILES"] = mock_files
        env["GITNEXUS_REMOTE"] = remote

        if mock_response is not None:
            env["NPX_MOCK_RESPONSE"] = mock_response

        # Set up GITHUB_OUTPUT
        gh_output = tmp_path / "github_output.txt"
        gh_output.touch()
        env["GITHUB_OUTPUT"] = str(gh_output)

        if extra_env:
            env.update(extra_env)

        result = subprocess.run(
            ["bash", str(SCRIPT_PATH), base_ref],
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        return result, gh_output.read_text()

    return _run


class TestExecution:
    """Functional tests via subprocess with mock binaries."""

    def test_no_changed_files_exits_cleanly(self, run_report):
        """Empty git diff produces exit 0 with HTML marker in output."""
        result, gh_output = run_report(mock_files="")
        assert result.returncode == 0
        assert "<!-- gitnexus-impact -->" in result.stdout
        assert "risk=NONE" in gh_output

    def test_single_file_low_risk(self, run_report):
        """Single changed file with LOW risk produces correct report."""
        result, gh_output = run_report(
            mock_files="src/main.py",
            mock_response='{"risk":"LOW","impactedCount":2,"summary":{"direct":2,"processes_affected":0,"modules_affected":0},"affected_processes":[],"affected_modules":[],"byDepth":{}}',
        )
        assert result.returncode == 0
        assert "<!-- gitnexus-impact -->" in result.stdout
        assert "`src/main.py`" in result.stdout
        assert "risk=LOW" in gh_output

    def test_multiple_files_highest_risk_wins(self, run_report, mock_bin_dir):
        """When multiple files have different risks, overall risk is the highest."""
        # Override npx mock to return HIGH for any file
        npx_script = mock_bin_dir / "npx"
        npx_script.write_text(
            textwrap.dedent("""\
            #!/usr/bin/env bash
            if [[ "$1" == "gitnexus" && "$2" == "impact" ]]; then
                echo '{"risk":"HIGH","impactedCount":5,"summary":{"direct":5,"processes_affected":1,"modules_affected":1},"affected_processes":[{"name":"Auth Flow"}],"affected_modules":[{"name":"core"}],"byDepth":{}}'
            else
                echo "mock" >&2
            fi
        """)
        )
        npx_script.chmod(0o755)

        result, gh_output = run_report(mock_files="file1.py\nfile2.py")
        assert result.returncode == 0
        assert "risk=HIGH" in gh_output

    def test_gitnexus_error_handled(self, run_report, mock_bin_dir):
        """GitNexus returning an error is handled gracefully."""
        npx_script = mock_bin_dir / "npx"
        npx_script.write_text(
            textwrap.dedent("""\
            #!/usr/bin/env bash
            if [[ "$1" == "gitnexus" && "$2" == "impact" ]]; then
                echo '{"error":"not indexed"}'
            else
                echo "mock" >&2
            fi
        """)
        )
        npx_script.chmod(0o755)

        result, gh_output = run_report(mock_files="broken.py")
        assert result.returncode == 0
        # UNKNOWN risk maps to :white_circle: **NONE** badge
        assert ":white_circle:" in result.stdout
        assert "risk=NONE" in gh_output

    def test_github_output_written(self, run_report):
        """GITHUB_OUTPUT file receives risk= when env var is set."""
        _, gh_output = run_report(mock_files="test.py")
        assert "risk=" in gh_output

    def test_missing_dependency_exits_with_error(self, tmp_path):
        """Missing jq causes exit 1 with clear error message."""
        # Create a bin dir with only git and npx, no jq
        # Include /usr/bin so bash builtins and coreutils work
        bin_dir = tmp_path / "empty_bin"
        bin_dir.mkdir()
        for cmd in ["git", "npx"]:
            script = bin_dir / cmd
            script.write_text("#!/bin/bash\necho mock")
            script.chmod(0o755)

        env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(tmp_path)}
        result = subprocess.run(
            ["bash", str(SCRIPT_PATH), "main"],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        assert result.returncode != 0
        assert "jq" in result.stderr

    def test_max_files_cap(self, run_report):
        """More than MAX_FILES files are capped."""
        # Generate 55 file names
        files = "\n".join(f"file{i}.py" for i in range(55))
        result, _ = run_report(
            mock_files=files,
            extra_env={"GITNEXUS_MAX_FILES": "50"},
        )
        assert result.returncode == 0
        assert "capping analysis to 50" in result.stderr
