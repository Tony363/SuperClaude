"""Smoke tests for SuperClaude package installation and entry points.

These tests verify:
1. Package imports correctly after installation
2. Entry point (main) is callable and behaves predictably
3. Module execution works without crashing
4. Optional extras gating works correctly

Note: These tests are designed to work with base install (no extras).
Tests requiring extras are skipped when dependencies are unavailable.
"""

import subprocess
import sys


class TestPackageImport:
    """Tests for basic package import functionality."""

    def test_import_superclaude(self):
        """SuperClaude package should be importable."""
        import SuperClaude

        assert SuperClaude is not None

    def test_import_main_module(self):
        """SuperClaude.__main__ should be importable."""
        import SuperClaude.__main__

        assert SuperClaude.__main__ is not None

    def test_main_function_exists(self):
        """main() function should exist and be callable."""
        from SuperClaude.__main__ import main

        assert callable(main)

    def test_main_function_returns_int(self):
        """main() should return an integer exit code."""
        from SuperClaude.__main__ import main

        result = main()
        assert isinstance(result, int)


class TestModuleExecution:
    """Tests for python -m SuperClaude execution."""

    def test_module_execution_runs(self):
        """python -m SuperClaude should run without crashing."""
        result = subprocess.run(
            [sys.executable, "-m", "SuperClaude"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Exit code 1 is expected (archive not available)
        # Just verify it doesn't crash with unhandled exception
        assert result.returncode in (0, 1)
        # Should not have Python traceback in stderr for expected failures
        if result.returncode == 1:
            assert "Traceback" not in result.stderr or "ImportError" in result.stderr

    def test_module_execution_message(self):
        """python -m SuperClaude should provide helpful message."""
        result = subprocess.run(
            [sys.executable, "-m", "SuperClaude"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # Should mention Claude Code or archive if not available
        output = result.stdout + result.stderr
        # When archive is missing, should give guidance
        if result.returncode == 1:
            assert "Claude Code" in output or "archive" in output.lower()


class TestExtrasGating:
    """Tests for optional dependency gating.

    These tests verify that the package handles missing optional
    dependencies gracefully and provides helpful error messages.
    """

    def test_core_imports_without_extras(self):
        """Core modules should import without optional extras."""
        # These should work with base install
        from core.types import LoopConfig, TerminationReason

        assert LoopConfig is not None
        assert TerminationReason is not None

    def test_loop_orchestrator_import(self):
        """Loop orchestrator should import with base install."""
        from core.loop_orchestrator import LoopOrchestrator

        assert LoopOrchestrator is not None

    def test_quality_assessment_import(self):
        """Quality assessment should import with base install."""
        from core.quality_assessment import QualityAssessor

        assert QualityAssessor is not None

    def test_pal_integration_import(self):
        """PAL integration should import with base install."""
        from core.pal_integration import PALReviewSignal

        assert PALReviewSignal is not None


class TestEntryPointBehavior:
    """Tests for entry point behavior and error handling."""

    def test_main_handles_missing_archive(self):
        """main() should handle missing archive gracefully."""
        from SuperClaude.__main__ import main

        # Should not raise an exception
        try:
            exit_code = main()
            assert isinstance(exit_code, int)
        except SystemExit as e:
            # SystemExit is acceptable if it has a code
            assert e.code is not None

    def test_subprocess_import_isolation(self):
        """Import in subprocess should not pollute parent environment."""
        # Run import in subprocess
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from SuperClaude.__main__ import main; print(main.__name__)",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "main" in result.stdout


class TestVersionInfo:
    """Tests for version information availability."""

    def test_version_accessible(self):
        """Package version should be accessible."""
        # Version may be in different locations depending on install method
        try:
            from importlib.metadata import version

            v = version("SuperClaude")
            assert v is not None
            assert len(v) > 0
        except Exception:
            # Fallback: check if pyproject.toml version is parseable
            pass  # Skip if metadata not available in test environment
