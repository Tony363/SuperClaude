"""Validators for E2E application generation tests.

Each validator implements language-specific setup, validation, and cleanup
for generated applications.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ValidationResult:
    """Result of a validation step."""

    passed: bool
    step: str
    message: str
    duration_seconds: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.step}: {self.message}"


@dataclass
class ValidationReport:
    """Complete validation report for an application."""

    app_name: str
    passed: bool
    steps: list[ValidationResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    error: str | None = None

    @property
    def failed_steps(self) -> list[ValidationResult]:
        """Return list of failed validation steps."""
        return [s for s in self.steps if not s.passed]

    @property
    def summary(self) -> str:
        """Return a summary string of the validation."""
        passed_count = sum(1 for s in self.steps if s.passed)
        total_count = len(self.steps)
        status = "PASSED" if self.passed else "FAILED"
        return f"{self.app_name}: {status} ({passed_count}/{total_count} steps)"


class BaseValidator(ABC):
    """Base class for language-specific validators."""

    @property
    @abstractmethod
    def language(self) -> str:
        """Return the language this validator handles."""
        ...

    @abstractmethod
    def setup(self, workdir: Path, config: dict[str, Any]) -> ValidationResult:
        """Set up the environment (install dependencies, etc.).

        Args:
            workdir: Working directory containing generated code
            config: App configuration from e2e_apps.yaml

        Returns:
            ValidationResult indicating setup success/failure
        """
        ...

    @abstractmethod
    def check_files(self, workdir: Path, config: dict[str, Any]) -> ValidationResult:
        """Check that required files exist.

        Args:
            workdir: Working directory containing generated code
            config: App configuration from e2e_apps.yaml

        Returns:
            ValidationResult indicating file check success/failure
        """
        ...

    @abstractmethod
    def compile_check(self, workdir: Path, config: dict[str, Any]) -> ValidationResult:
        """Run compile/syntax check.

        Args:
            workdir: Working directory containing generated code
            config: App configuration from e2e_apps.yaml

        Returns:
            ValidationResult indicating compile check success/failure
        """
        ...

    @abstractmethod
    def run_tests(self, workdir: Path, config: dict[str, Any]) -> ValidationResult:
        """Run the application's test suite.

        Args:
            workdir: Working directory containing generated code
            config: App configuration from e2e_apps.yaml

        Returns:
            ValidationResult indicating test execution success/failure
        """
        ...

    def run_functional_test(
        self, workdir: Path, config: dict[str, Any]
    ) -> ValidationResult | None:
        """Run optional functional tests (HTTP calls, CLI execution, etc.).

        Args:
            workdir: Working directory containing generated code
            config: App configuration from e2e_apps.yaml

        Returns:
            ValidationResult or None if no functional test configured
        """
        functional_config = config.get("validation", {}).get("functional_test")
        if not functional_config:
            return None
        # Subclasses can override for language-specific functional tests
        return ValidationResult(
            passed=True,
            step="functional_test",
            message="No functional test implemented for this validator",
        )

    @abstractmethod
    def cleanup(self, workdir: Path) -> None:
        """Clean up temporary files and directories.

        Args:
            workdir: Working directory to clean up
        """
        ...

    def validate(self, workdir: Path, config: dict[str, Any]) -> ValidationReport:
        """Run all validation steps and return a complete report.

        Args:
            workdir: Working directory containing generated code
            config: App configuration from e2e_apps.yaml

        Returns:
            ValidationReport with all step results
        """
        import time

        app_name = config.get("app_name", "unknown")
        report = ValidationReport(app_name=app_name, passed=True)
        start_time = time.time()
        validation_config = config.get("validation", {})

        try:
            # Step 1: Check required files
            result = self.check_files(workdir, config)
            report.steps.append(result)
            if not result.passed:
                report.passed = False
                return report

            # Step 2: Setup environment
            result = self.setup(workdir, config)
            report.steps.append(result)
            if not result.passed:
                report.passed = False
                return report

            # Step 3: Compile check (if enabled)
            if validation_config.get("compile_check", False):
                result = self.compile_check(workdir, config)
                report.steps.append(result)
                if not result.passed:
                    report.passed = False
                    return report

            # Step 4: Run tests (if enabled)
            if validation_config.get("test_execution", False):
                result = self.run_tests(workdir, config)
                report.steps.append(result)
                if not result.passed:
                    report.passed = False
                    return report

            # Step 5: Functional test (if configured)
            result = self.run_functional_test(workdir, config)
            if result is not None:
                report.steps.append(result)
                if not result.passed:
                    report.passed = False

        except Exception as e:
            report.passed = False
            report.error = str(e)
        finally:
            report.total_duration_seconds = time.time() - start_time

        return report


# Import validators for convenience
from tests.e2e.validators.python_validator import PythonValidator
from tests.e2e.validators.node_validator import NodeValidator
from tests.e2e.validators.rust_validator import RustValidator

__all__ = [
    "BaseValidator",
    "ValidationResult",
    "ValidationReport",
    "PythonValidator",
    "NodeValidator",
    "RustValidator",
]
