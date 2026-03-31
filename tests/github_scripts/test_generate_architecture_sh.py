"""Tests for .github/scripts/generate-architecture.sh.

Validates shell script syntax, security hardening, structural correctness,
and functional behavior via subprocess execution with mock binaries.
"""

import os
import subprocess
import textwrap
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).parent.parent.parent / ".github" / "scripts" / "generate-architecture.sh"
)


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


class TestDependencyValidation:
    """Validate that required tools are checked before use."""

    def test_check_deps_function_exists(self):
        """Script defines a check_deps function."""
        content = SCRIPT_PATH.read_text()
        assert "check_deps" in content

    def test_checks_for_required_tools(self):
        """check_deps validates jq and npx."""
        content = SCRIPT_PATH.read_text()
        for tool in ["jq", "npx"]:
            assert tool in content, f"Missing dependency check for {tool}"


class TestErrorReporting:
    """Validate that GitNexus errors are logged, not silently swallowed."""

    def test_no_bare_fallback_without_warning(self):
        """GitNexus query failures should log a warning before falling back."""
        content = SCRIPT_PATH.read_text()
        assert "::warning::" in content, (
            "Expected ::warning:: annotations for GitNexus query failures"
        )

    def test_query_errors_produce_valid_fallback(self):
        """Fallback JSON should be valid (empty processes array)."""
        content = SCRIPT_PATH.read_text()
        assert '{"processes":[]}' in content


class TestOutputValidation:
    """Validate that generated ARCHITECTURE.md is validated before output."""

    def test_validates_non_empty(self):
        """Script checks that output is non-empty."""
        content = SCRIPT_PATH.read_text()
        assert "-s ARCHITECTURE.md" in content or "! -s" in content

    def test_validates_heading(self):
        """Script checks that output starts with a heading."""
        content = SCRIPT_PATH.read_text()
        assert "'^# '" in content or "heading" in content.lower()

    def test_validates_expected_sections(self):
        """Script checks for expected sections like 'Codebase Overview'."""
        content = SCRIPT_PATH.read_text()
        assert "Codebase Overview" in content


class TestStructure:
    """Validate expected functions and structure."""

    EXPECTED_FUNCTIONS = ["check_deps", "query_gitnexus", "extract_summaries", "render_section"]

    def test_all_functions_defined(self):
        """Script defines all expected helper functions."""
        content = SCRIPT_PATH.read_text()
        for func in self.EXPECTED_FUNCTIONS:
            assert f"{func}()" in content or f"{func} ()" in content, f"Missing function: {func}()"


# ── Tier 2: Execution Tests ──────────────────────────────────────────


@pytest.fixture
def mock_bin_dir(tmp_path):
    """Create a temp directory with mock binaries for npx and jq."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    # Mock npx: returns canned JSON for gitnexus query
    npx_script = bin_dir / "npx"
    npx_script.write_text(
        textwrap.dedent("""\
        #!/usr/bin/env bash
        if [[ "$1" == "gitnexus" && "$2" == "query" ]]; then
            echo '{"processes":[{"id":"proc_1","summary":"Test Process","priority":0.9,"symbol_count":3,"process_type":"core","step_count":5}],"process_symbols":[],"definitions":[]}'
        elif [[ "$1" == "gitnexus" && "$2" == "analyze" ]]; then
            echo "Indexed."
        elif [[ "$1" == "gitnexus" && "$2" == "status" ]]; then
            echo "Indexed: 100 files, 500 symbols"
        else
            echo "mock npx: $*" >&2
        fi
    """)
    )
    npx_script.chmod(0o755)

    # Mock find: return fixed counts
    find_script = bin_dir / "find"
    find_script.write_text(
        textwrap.dedent("""\
        #!/usr/bin/env bash
        # Return a few lines so wc -l counts them
        echo "file1"
        echo "file2"
        echo "file3"
    """)
    )
    find_script.chmod(0o755)

    return bin_dir


@pytest.fixture
def run_generate(mock_bin_dir, tmp_path):
    """Helper to run generate-architecture.sh with mock environment."""

    def _run(extra_env=None):
        work_dir = tmp_path / "repo"
        work_dir.mkdir(exist_ok=True)

        env = os.environ.copy()
        env["PATH"] = f"{mock_bin_dir}:{env['PATH']}"
        env["HOME"] = str(tmp_path)

        if extra_env:
            env.update(extra_env)

        result = subprocess.run(
            ["bash", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(work_dir),
            timeout=30,
        )
        arch_file = work_dir / "ARCHITECTURE.md"
        arch_content = arch_file.read_text() if arch_file.exists() else ""
        return result, arch_content

    return _run


class TestExecution:
    """Functional tests via subprocess with mock binaries."""

    def test_generates_architecture_md(self, run_generate):
        """Script creates ARCHITECTURE.md with expected structure."""
        result, content = run_generate()
        assert result.returncode == 0, f"Script failed: {result.stderr}"
        assert content.startswith("# SuperClaude Architecture")
        assert "## Codebase Overview" in content
        assert "## Entry Points" in content
        assert "## Core Modules" in content

    def test_includes_file_counts(self, run_generate):
        """Generated file includes file count table."""
        result, content = run_generate()
        assert result.returncode == 0
        assert "Python files" in content
        assert "Rust files" in content

    def test_includes_process_summaries(self, run_generate):
        """Generated file includes process summaries from GitNexus."""
        result, content = run_generate()
        assert result.returncode == 0
        assert "Test Process" in content

    def test_includes_footer(self, run_generate):
        """Generated file includes GitNexus attribution footer."""
        result, content = run_generate()
        assert result.returncode == 0
        assert "GitNexus" in content
        assert "code intelligence" in content

    def test_missing_dependency_exits_with_error(self, tmp_path):
        """Missing jq causes exit 1 with error message."""
        # Create a restricted PATH with symlinks to real coreutils but NOT jq.
        bin_dir = tmp_path / "restricted_bin"
        bin_dir.mkdir()
        # Symlink real binaries we need (not jq)
        import shutil

        for cmd in [
            "cat",
            "wc",
            "sort",
            "date",
            "head",
            "grep",
            "find",
            "sed",
            "tr",
            "printf",
            "dirname",
            "basename",
            "mkdir",
            "chmod",
            "rm",
            "echo",
            "test",
            "command",
        ]:
            real = shutil.which(cmd)
            if real:
                os.symlink(real, bin_dir / cmd)
        # Mock npx (no real npx needed)
        npx_mock = bin_dir / "npx"
        npx_mock.write_text("#!/bin/bash\necho mock")
        npx_mock.chmod(0o755)

        env = {"PATH": str(bin_dir), "HOME": str(tmp_path)}
        result = subprocess.run(
            ["/usr/bin/bash", str(SCRIPT_PATH)],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(tmp_path),
            timeout=10,
        )
        assert result.returncode != 0
        assert "jq" in result.stderr
