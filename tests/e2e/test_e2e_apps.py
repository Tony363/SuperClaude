"""Pytest integration for E2E application generation tests.

These tests verify that SuperClaude can generate complete, working applications
from prompts. They are marked as 'e2e' and can be run with:

    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/e2e/ -m e2e -v

Note: These tests require ANTHROPIC_API_KEY to be set and may take several
minutes per test as they invoke Claude to generate full applications.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.e2e.runner import get_validator, run_single_test


class TestValidators:
    """Test validator functionality with pre-existing code."""

    def test_python_validator_check_files(self, python_validator, e2e_workdir: Path):
        """Test Python validator file checking."""
        # Create test files
        (e2e_workdir / "calculator.py").write_text("# calculator")
        (e2e_workdir / "test_calculator.py").write_text("# tests")

        config = {
            "validation": {
                "files_required": ["calculator.py", "test_calculator.py"],
            }
        }

        result = python_validator.check_files(e2e_workdir, config)
        assert result.passed
        assert "2 required files found" in result.message

    def test_python_validator_missing_files(self, python_validator, e2e_workdir: Path):
        """Test Python validator detects missing files."""
        (e2e_workdir / "calculator.py").write_text("# calculator")

        config = {
            "validation": {
                "files_required": ["calculator.py", "missing.py"],
            }
        }

        result = python_validator.check_files(e2e_workdir, config)
        assert not result.passed
        assert "missing.py" in result.message

    def test_python_validator_compile_check_valid(self, python_validator, e2e_workdir: Path):
        """Test Python validator compile check with valid code."""
        (e2e_workdir / "valid.py").write_text("""
def add(a: int, b: int) -> int:
    return a + b
""")

        config = {"validation": {}}
        result = python_validator.compile_check(e2e_workdir, config)
        assert result.passed

    def test_python_validator_compile_check_invalid(self, python_validator, e2e_workdir: Path):
        """Test Python validator compile check with invalid code."""
        (e2e_workdir / "invalid.py").write_text("""
def broken(
    # Missing closing paren and body
""")

        config = {"validation": {}}
        result = python_validator.compile_check(e2e_workdir, config)
        assert not result.passed
        assert "Syntax errors" in result.message

    def test_node_validator_check_files(self, node_validator, e2e_workdir: Path):
        """Test Node validator file checking."""
        (e2e_workdir / "package.json").write_text('{"name": "test"}')
        (e2e_workdir / "src").mkdir()
        (e2e_workdir / "src" / "index.js").write_text("// index")

        config = {
            "validation": {
                "files_required": ["package.json", "src/index.js"],
            }
        }

        result = node_validator.check_files(e2e_workdir, config)
        assert result.passed

    def test_node_validator_ts_variant(self, node_validator, e2e_workdir: Path):
        """Test Node validator accepts .ts variant of .js files."""
        (e2e_workdir / "package.json").write_text('{"name": "test"}')
        (e2e_workdir / "src").mkdir()
        (e2e_workdir / "src" / "index.ts").write_text("// typescript")

        config = {
            "validation": {
                # Asking for .js but .ts should also be accepted
                "files_required": ["package.json", "src/index.js"],
            }
        }

        result = node_validator.check_files(e2e_workdir, config)
        assert result.passed

    def test_rust_validator_check_files(self, rust_validator, e2e_workdir: Path):
        """Test Rust validator file checking."""
        (e2e_workdir / "Cargo.toml").write_text('[package]\nname = "test"')
        (e2e_workdir / "src").mkdir()
        (e2e_workdir / "src" / "lib.rs").write_text("// lib")

        config = {
            "validation": {
                "files_required": ["Cargo.toml", "src/lib.rs"],
            }
        }

        result = rust_validator.check_files(e2e_workdir, config)
        assert result.passed


class TestGetValidator:
    """Test validator factory function."""

    def test_get_python_validator(self):
        """Test getting Python validator."""
        validator = get_validator("python")
        assert validator.language == "python"

    def test_get_node_validator(self):
        """Test getting Node validator."""
        validator = get_validator("node")
        assert validator.language == "node"

    def test_get_rust_validator(self):
        """Test getting Rust validator."""
        validator = get_validator("rust")
        assert validator.language == "rust"

    def test_invalid_language(self):
        """Test invalid language raises error."""
        with pytest.raises(ValueError, match="No validator for language"):
            get_validator("cobol")


@pytest.mark.e2e
@pytest.mark.e2e_python
@pytest.mark.slow
class TestE2EPythonApps:
    """E2E tests for Python application generation.

    These tests actually invoke Claude to generate applications and validate
    that they compile and pass tests. They are slow and require API access.
    """

    def test_python_cli_calculator(
        self,
        e2e_workdir: Path,
        python_calculator_config: dict[str, Any],
        e2e_settings: dict[str, Any],
    ):
        """Test generation of Python CLI calculator app."""
        if not python_calculator_config:
            pytest.skip("python-cli-calculator not configured")

        merged_config = {**e2e_settings, **python_calculator_config}
        base_dir = Path(__file__).parent.parent.parent

        result = run_single_test(
            app_name="python-cli-calculator",
            app_config=merged_config,
            run_number=1,
            base_dir=base_dir,
            output_dir=e2e_workdir / "output",
            dry_run=False,
            keep_workdir=True,  # Keep for debugging
        )

        assert result.passed, f"Test failed: {result.reason}"

    def test_python_rest_api(
        self,
        e2e_workdir: Path,
        python_rest_api_config: dict[str, Any],
        e2e_settings: dict[str, Any],
    ):
        """Test generation of Python REST API app."""
        if not python_rest_api_config:
            pytest.skip("python-rest-api not configured")

        merged_config = {**e2e_settings, **python_rest_api_config}
        base_dir = Path(__file__).parent.parent.parent

        result = run_single_test(
            app_name="python-rest-api",
            app_config=merged_config,
            run_number=1,
            base_dir=base_dir,
            output_dir=e2e_workdir / "output",
            dry_run=False,
            keep_workdir=True,
        )

        assert result.passed, f"Test failed: {result.reason}"


@pytest.mark.e2e
@pytest.mark.e2e_node
@pytest.mark.slow
class TestE2ENodeApps:
    """E2E tests for Node.js application generation."""

    def test_react_todo_component(
        self,
        e2e_workdir: Path,
        react_todo_config: dict[str, Any],
        e2e_settings: dict[str, Any],
    ):
        """Test generation of React todo component."""
        if not react_todo_config:
            pytest.skip("react-todo-component not configured")

        merged_config = {**e2e_settings, **react_todo_config}
        base_dir = Path(__file__).parent.parent.parent

        result = run_single_test(
            app_name="react-todo-component",
            app_config=merged_config,
            run_number=1,
            base_dir=base_dir,
            output_dir=e2e_workdir / "output",
            dry_run=False,
            keep_workdir=True,
        )

        assert result.passed, f"Test failed: {result.reason}"

    def test_node_cli_tool(
        self,
        e2e_workdir: Path,
        node_cli_config: dict[str, Any],
        e2e_settings: dict[str, Any],
    ):
        """Test generation of Node CLI tool."""
        if not node_cli_config:
            pytest.skip("node-cli-tool not configured")

        merged_config = {**e2e_settings, **node_cli_config}
        base_dir = Path(__file__).parent.parent.parent

        result = run_single_test(
            app_name="node-cli-tool",
            app_config=merged_config,
            run_number=1,
            base_dir=base_dir,
            output_dir=e2e_workdir / "output",
            dry_run=False,
            keep_workdir=True,
        )

        assert result.passed, f"Test failed: {result.reason}"


@pytest.mark.e2e
@pytest.mark.e2e_rust
@pytest.mark.slow
class TestE2ERustApps:
    """E2E tests for Rust application generation."""

    def test_rust_fibonacci(
        self,
        e2e_workdir: Path,
        rust_fibonacci_config: dict[str, Any],
        e2e_settings: dict[str, Any],
    ):
        """Test generation of Rust fibonacci library."""
        if not rust_fibonacci_config:
            pytest.skip("rust-fibonacci not configured")

        merged_config = {**e2e_settings, **rust_fibonacci_config}
        base_dir = Path(__file__).parent.parent.parent

        result = run_single_test(
            app_name="rust-fibonacci",
            app_config=merged_config,
            run_number=1,
            base_dir=base_dir,
            output_dir=e2e_workdir / "output",
            dry_run=False,
            keep_workdir=True,
        )

        assert result.passed, f"Test failed: {result.reason}"


class TestDryRun:
    """Test dry-run functionality."""

    def test_dry_run_returns_pass(
        self,
        e2e_workdir: Path,
        python_calculator_config: dict[str, Any],
        e2e_settings: dict[str, Any],
    ):
        """Test that dry-run returns pass without executing."""
        if not python_calculator_config:
            pytest.skip("python-cli-calculator not configured")

        merged_config = {**e2e_settings, **python_calculator_config}
        base_dir = Path(__file__).parent.parent.parent

        result = run_single_test(
            app_name="python-cli-calculator",
            app_config=merged_config,
            run_number=1,
            base_dir=base_dir,
            output_dir=e2e_workdir / "output",
            dry_run=True,  # Dry run
        )

        assert result.passed
        assert result.reason == "DRY RUN"
        assert result.total_time_seconds == 0
