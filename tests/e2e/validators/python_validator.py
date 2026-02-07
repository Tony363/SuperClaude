"""Python application validator for E2E tests."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from tests.e2e.validators import BaseValidator, ValidationResult


class PythonValidator(BaseValidator):
    """Validator for Python applications."""

    @property
    def language(self) -> str:
        return "python"

    def setup(self, workdir: Path, config: dict[str, Any]) -> ValidationResult:
        """Set up Python virtual environment and install dependencies."""
        start_time = time.time()
        venv_path = workdir / ".venv"

        try:
            # Create virtual environment
            result = subprocess.run(
                ["python3", "-m", "venv", str(venv_path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=workdir,
            )
            if result.returncode != 0:
                return ValidationResult(
                    passed=False,
                    step="setup",
                    message=f"Failed to create venv: {result.stderr}",
                    duration_seconds=time.time() - start_time,
                )

            # Install dependencies if requirements.txt exists
            requirements_file = workdir / "requirements.txt"
            if requirements_file.exists():
                pip_path = venv_path / "bin" / "pip"
                result = subprocess.run(
                    [str(pip_path), "install", "-r", str(requirements_file)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=workdir,
                )
                if result.returncode != 0:
                    return ValidationResult(
                        passed=False,
                        step="setup",
                        message=f"Failed to install dependencies: {result.stderr}",
                        duration_seconds=time.time() - start_time,
                        details={"requirements": requirements_file.read_text()},
                    )

            return ValidationResult(
                passed=True,
                step="setup",
                message="Python environment set up successfully",
                duration_seconds=time.time() - start_time,
            )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                passed=False,
                step="setup",
                message="Setup timed out",
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            return ValidationResult(
                passed=False,
                step="setup",
                message=f"Setup error: {e}",
                duration_seconds=time.time() - start_time,
            )

    def check_files(self, workdir: Path, config: dict[str, Any]) -> ValidationResult:
        """Check that all required files exist."""
        start_time = time.time()
        validation_config = config.get("validation", {})
        required_files = validation_config.get("files_required", [])

        missing_files = []
        found_files = []

        for file_path in required_files:
            full_path = workdir / file_path
            if full_path.exists():
                found_files.append(file_path)
            else:
                missing_files.append(file_path)

        if missing_files:
            return ValidationResult(
                passed=False,
                step="files_check",
                message=f"Missing files: {', '.join(missing_files)}",
                duration_seconds=time.time() - start_time,
                details={"missing": missing_files, "found": found_files},
            )

        return ValidationResult(
            passed=True,
            step="files_check",
            message=f"All {len(required_files)} required files found",
            duration_seconds=time.time() - start_time,
            details={"found": found_files},
        )

    def compile_check(self, workdir: Path, config: dict[str, Any]) -> ValidationResult:
        """Run Python syntax check on all .py files."""
        start_time = time.time()
        python_files = list(workdir.glob("**/*.py"))

        # Exclude venv directory
        python_files = [f for f in python_files if ".venv" not in str(f)]

        if not python_files:
            return ValidationResult(
                passed=False,
                step="compile_check",
                message="No Python files found to check",
                duration_seconds=time.time() - start_time,
            )

        errors = []
        for py_file in python_files:
            try:
                result = subprocess.run(
                    ["python3", "-m", "py_compile", str(py_file)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=workdir,
                )
                if result.returncode != 0:
                    errors.append(f"{py_file.name}: {result.stderr}")
            except subprocess.TimeoutExpired:
                errors.append(f"{py_file.name}: Compilation timed out")
            except Exception as e:
                errors.append(f"{py_file.name}: {e}")

        if errors:
            return ValidationResult(
                passed=False,
                step="compile_check",
                message=f"Syntax errors in {len(errors)} file(s)",
                duration_seconds=time.time() - start_time,
                details={"errors": errors},
            )

        return ValidationResult(
            passed=True,
            step="compile_check",
            message=f"All {len(python_files)} Python files compile successfully",
            duration_seconds=time.time() - start_time,
            details={"files_checked": [f.name for f in python_files]},
        )

    def run_tests(self, workdir: Path, config: dict[str, Any]) -> ValidationResult:
        """Run pytest in the virtual environment."""
        start_time = time.time()
        venv_path = workdir / ".venv"
        pytest_path = venv_path / "bin" / "pytest"

        # Check if pytest is available
        if not pytest_path.exists():
            # Try to install pytest
            pip_path = venv_path / "bin" / "pip"
            subprocess.run(
                [str(pip_path), "install", "pytest"],
                capture_output=True,
                timeout=60,
                cwd=workdir,
            )

        if not pytest_path.exists():
            return ValidationResult(
                passed=False,
                step="test_execution",
                message="pytest not available in virtual environment",
                duration_seconds=time.time() - start_time,
            )

        try:
            result = subprocess.run(
                [str(pytest_path), "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=workdir,
                env={
                    **dict(__import__("os").environ),
                    "PYTHONPATH": str(workdir),
                },
            )

            # Parse pytest output for pass/fail counts
            output = result.stdout + result.stderr
            passed = result.returncode == 0

            # Extract test counts from pytest output
            test_info = self._parse_pytest_output(output)

            return ValidationResult(
                passed=passed,
                step="test_execution",
                message=f"Tests {'passed' if passed else 'failed'}: {test_info}",
                duration_seconds=time.time() - start_time,
                details={
                    "exit_code": result.returncode,
                    "stdout": result.stdout[-2000:] if result.stdout else "",
                    "stderr": result.stderr[-1000:] if result.stderr else "",
                },
            )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                passed=False,
                step="test_execution",
                message="Test execution timed out",
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            return ValidationResult(
                passed=False,
                step="test_execution",
                message=f"Test execution error: {e}",
                duration_seconds=time.time() - start_time,
            )

    def _parse_pytest_output(self, output: str) -> str:
        """Extract test count summary from pytest output."""
        import re

        # Look for pytest summary line like "5 passed in 0.12s"
        match = re.search(r"(\d+) passed", output)
        passed = int(match.group(1)) if match else 0

        match = re.search(r"(\d+) failed", output)
        failed = int(match.group(1)) if match else 0

        match = re.search(r"(\d+) error", output)
        errors = int(match.group(1)) if match else 0

        parts = []
        if passed:
            parts.append(f"{passed} passed")
        if failed:
            parts.append(f"{failed} failed")
        if errors:
            parts.append(f"{errors} errors")

        return ", ".join(parts) if parts else "no tests found"

    def run_functional_test(
        self, workdir: Path, config: dict[str, Any]
    ) -> ValidationResult | None:
        """Run HTTP functional test for Flask apps."""
        start_time = time.time()
        functional_config = config.get("validation", {}).get("functional_test")
        if not functional_config:
            return None

        test_type = functional_config.get("type")
        if test_type != "http":
            return None

        venv_path = workdir / ".venv"
        python_path = venv_path / "bin" / "python"

        # Start the Flask app in background
        try:
            import socket

            # Find available port
            sock = socket.socket()
            sock.bind(("", 0))
            port = sock.getsockname()[1]
            sock.close()

            # Start the app
            app_process = subprocess.Popen(
                [str(python_path), "-c", f"""
import sys
sys.path.insert(0, '.')
from app import app
app.run(host='127.0.0.1', port={port}, debug=False)
"""],
                cwd=workdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            # Wait for app to start
            import time as time_module

            time_module.sleep(2)

            # Make request
            import urllib.request
            import json

            endpoint = functional_config.get("endpoint", "/health")
            url = f"http://127.0.0.1:{port}{endpoint}"

            try:
                with urllib.request.urlopen(url, timeout=10) as response:
                    status_code = response.getcode()
                    body = json.loads(response.read().decode())

                    expected_status = functional_config.get("expected_status", 200)
                    expected_json = functional_config.get("expected_json", {})

                    if status_code != expected_status:
                        return ValidationResult(
                            passed=False,
                            step="functional_test",
                            message=f"Expected status {expected_status}, got {status_code}",
                            duration_seconds=time.time() - start_time,
                        )

                    for key, value in expected_json.items():
                        if body.get(key) != value:
                            return ValidationResult(
                                passed=False,
                                step="functional_test",
                                message=f"Expected {key}={value}, got {body.get(key)}",
                                duration_seconds=time.time() - start_time,
                            )

                    return ValidationResult(
                        passed=True,
                        step="functional_test",
                        message=f"HTTP test passed: {endpoint} returned {status_code}",
                        duration_seconds=time.time() - start_time,
                        details={"response": body},
                    )

            except Exception as e:
                return ValidationResult(
                    passed=False,
                    step="functional_test",
                    message=f"HTTP request failed: {e}",
                    duration_seconds=time.time() - start_time,
                )
            finally:
                app_process.terminate()
                app_process.wait(timeout=5)

        except Exception as e:
            return ValidationResult(
                passed=False,
                step="functional_test",
                message=f"Functional test error: {e}",
                duration_seconds=time.time() - start_time,
            )

    def cleanup(self, workdir: Path) -> None:
        """Remove virtual environment and cache directories."""
        dirs_to_remove = [
            workdir / ".venv",
            workdir / "__pycache__",
            workdir / ".pytest_cache",
        ]

        for dir_path in dirs_to_remove:
            if dir_path.exists():
                shutil.rmtree(dir_path, ignore_errors=True)

        # Remove __pycache__ in subdirectories
        for pycache in workdir.rglob("__pycache__"):
            shutil.rmtree(pycache, ignore_errors=True)
