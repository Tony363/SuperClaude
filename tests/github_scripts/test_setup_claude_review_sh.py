"""Tests for .github/workflows/setup-claude-review.sh.

Validates shell script syntax, hardening patterns (set -euo pipefail,
read -r flags), and structural correctness without executing the
interactive script.
"""

import subprocess
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).parent.parent.parent / ".github" / "workflows" / "setup-claude-review.sh"
)


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

    def test_script_is_executable_or_has_shebang(self):
        """Script has a bash shebang line."""
        first_line = SCRIPT_PATH.read_text().split("\n")[0]
        assert first_line.startswith("#!/"), f"Missing shebang: {first_line}"
        assert "bash" in first_line


class TestErrorHandling:
    """Validate robust error handling settings."""

    def test_uses_strict_error_mode(self):
        """Script uses set -euo pipefail for robust error handling."""
        content = SCRIPT_PATH.read_text()
        assert "set -euo pipefail" in content, (
            "Expected 'set -euo pipefail' but not found. "
            "The script should catch undefined vars (-u) and pipe failures (-o pipefail)."
        )

    def test_no_bare_set_e(self):
        """Script should not have plain 'set -e' without -u and pipefail."""
        for line in SCRIPT_PATH.read_text().splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Catch exactly "set -e" without the full flags
            if (
                stripped == "set -e"
                or stripped.startswith("set -e ")
                and "pipefail" not in stripped
            ):
                pytest.fail(f"Found weak error handling: '{stripped}'. Use 'set -euo pipefail'.")


class TestReadCommands:
    """All read commands must use -r to prevent backslash interpretation."""

    def test_all_read_commands_have_r_flag(self):
        """Every 'read' command in the script uses the -r flag."""
        content = SCRIPT_PATH.read_text()
        violations = []
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            # Match lines that invoke read as a command (not in comments or strings)
            if "read " in stripped or "read\t" in stripped:
                # Check if it's actually a read command (not part of another word like 'readonly')
                tokens = stripped.split()
                for j, token in enumerate(tokens):
                    if token == "read" and j < len(tokens) - 1:
                        # This is a bare 'read' command - must have -r somewhere after
                        rest = " ".join(tokens[j:])
                        if "-r" not in rest:
                            violations.append(f"Line {i}: {stripped}")
        assert not violations, (
            "Found 'read' without -r flag (backslash interpretation risk):\n"
            + "\n".join(violations)
        )


class TestSecretCaching:
    """Secret list should be cached to avoid redundant API calls."""

    def test_secret_list_cached_in_variable(self):
        """gh secret list output is stored in a variable for reuse."""
        content = SCRIPT_PATH.read_text()
        assert "SECRET_LIST=" in content, "Expected SECRET_LIST variable for caching gh secret list"

    def test_no_direct_gh_secret_list_in_grep(self):
        """No direct 'gh secret list | grep' calls (should use cached variable)."""
        content = SCRIPT_PATH.read_text()
        violations = []
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if "gh secret list" in stripped and "grep" in stripped:
                violations.append(f"Line {i}: {stripped}")
        assert not violations, "Found uncached 'gh secret list | grep' calls:\n" + "\n".join(
            violations
        )


class TestFunctionDefinitions:
    """All expected functions are defined in the script."""

    EXPECTED_FUNCTIONS = [
        "check_prerequisites",
        "select_phase",
        "configure_secrets",
        "install_workflows",
        "install_github_app",
        "create_claude_md",
        "test_setup",
        "print_summary",
        "main",
    ]

    def test_all_functions_defined(self):
        """Script defines all expected functions."""
        content = SCRIPT_PATH.read_text()
        for func in self.EXPECTED_FUNCTIONS:
            assert f"{func}()" in content, f"Missing function: {func}()"

    def test_helper_output_functions(self):
        """Script defines colored output helper functions."""
        content = SCRIPT_PATH.read_text()
        for helper in ["info", "success", "warning", "error", "prompt"]:
            assert f"{helper}()" in content, f"Missing helper: {helper}()"


class TestPromptConsistency:
    """Interactive prompts should use a consistent pattern."""

    def test_no_prompt_then_bare_read(self):
        """No instances of prompt() followed by bare 'read' on the next line."""
        lines = SCRIPT_PATH.read_text().splitlines()
        violations = []
        for i in range(len(lines) - 1):
            current = lines[i].strip()
            next_line = lines[i + 1].strip()
            if current.startswith("prompt ") and next_line.startswith("read "):
                violations.append(f"Lines {i + 1}-{i + 2}: prompt then bare read")
        assert not violations, (
            "Found inconsistent prompt pattern (should use 'read -rp'):\n" + "\n".join(violations)
        )
