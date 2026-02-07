"""Node.js/React application validator for E2E tests."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from tests.e2e.validators import BaseValidator, ValidationResult


class NodeValidator(BaseValidator):
    """Validator for Node.js and React applications."""

    @property
    def language(self) -> str:
        return "node"

    def setup(self, workdir: Path, config: dict[str, Any]) -> ValidationResult:
        """Install npm dependencies."""
        start_time = time.time()

        # Check for package.json
        package_json = workdir / "package.json"
        if not package_json.exists():
            return ValidationResult(
                passed=False,
                step="setup",
                message="No package.json found",
                duration_seconds=time.time() - start_time,
            )

        try:
            # Run npm install
            result = subprocess.run(
                ["npm", "install"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=workdir,
            )

            if result.returncode != 0:
                return ValidationResult(
                    passed=False,
                    step="setup",
                    message=f"npm install failed: {result.stderr[:500]}",
                    duration_seconds=time.time() - start_time,
                    details={"stderr": result.stderr},
                )

            return ValidationResult(
                passed=True,
                step="setup",
                message="npm dependencies installed successfully",
                duration_seconds=time.time() - start_time,
            )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                passed=False,
                step="setup",
                message="npm install timed out",
                duration_seconds=time.time() - start_time,
            )
        except FileNotFoundError:
            return ValidationResult(
                passed=False,
                step="setup",
                message="npm not found - Node.js may not be installed",
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
            # Also check for .ts variant of .js files
            ts_variant = str(file_path).replace(".js", ".ts")

            if full_path.exists():
                found_files.append(file_path)
            elif (workdir / ts_variant).exists():
                found_files.append(ts_variant)
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
        """Run TypeScript compilation or ESLint syntax check."""
        start_time = time.time()

        # Check if TypeScript project
        tsconfig = workdir / "tsconfig.json"
        is_typescript = tsconfig.exists()

        if is_typescript:
            return self._typescript_compile(workdir, start_time)
        else:
            return self._javascript_syntax_check(workdir, start_time)

    def _typescript_compile(
        self, workdir: Path, start_time: float
    ) -> ValidationResult:
        """Run TypeScript compiler to check for type errors."""
        try:
            # Check if tsc is available via npx
            # Use lenient flags to ignore unused variable warnings (common in generated code)
            result = subprocess.run(
                [
                    "npx", "tsc", "--noEmit",
                    "--noUnusedLocals", "false",
                    "--noUnusedParameters", "false",
                ],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=workdir,
            )

            if result.returncode != 0:
                # Extract meaningful error from tsc output
                errors = result.stdout or result.stderr
                return ValidationResult(
                    passed=False,
                    step="compile_check",
                    message="TypeScript compilation failed",
                    duration_seconds=time.time() - start_time,
                    details={"errors": errors[:2000]},
                )

            return ValidationResult(
                passed=True,
                step="compile_check",
                message="TypeScript compilation successful",
                duration_seconds=time.time() - start_time,
            )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                passed=False,
                step="compile_check",
                message="TypeScript compilation timed out",
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            return ValidationResult(
                passed=False,
                step="compile_check",
                message=f"Compile check error: {e}",
                duration_seconds=time.time() - start_time,
            )

    def _javascript_syntax_check(
        self, workdir: Path, start_time: float
    ) -> ValidationResult:
        """Run Node.js syntax check on JavaScript files."""
        js_files = list(workdir.glob("**/*.js"))
        # Exclude node_modules
        js_files = [f for f in js_files if "node_modules" not in str(f)]

        if not js_files:
            return ValidationResult(
                passed=True,
                step="compile_check",
                message="No JavaScript files to check",
                duration_seconds=time.time() - start_time,
            )

        errors = []
        for js_file in js_files:
            try:
                result = subprocess.run(
                    ["node", "--check", str(js_file)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=workdir,
                )
                if result.returncode != 0:
                    errors.append(f"{js_file.name}: {result.stderr}")
            except Exception as e:
                errors.append(f"{js_file.name}: {e}")

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
            message=f"All {len(js_files)} JavaScript files have valid syntax",
            duration_seconds=time.time() - start_time,
        )

    def run_tests(self, workdir: Path, config: dict[str, Any]) -> ValidationResult:
        """Run npm test."""
        start_time = time.time()

        try:
            result = subprocess.run(
                ["npm", "test"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=workdir,
                env={
                    **dict(__import__("os").environ),
                    "CI": "true",  # Disable interactive mode in Jest
                },
            )

            output = result.stdout + result.stderr
            passed = result.returncode == 0

            # Parse test output for summary
            test_info = self._parse_test_output(output)

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

    def _parse_test_output(self, output: str) -> str:
        """Extract test summary from Jest/Mocha output."""
        import re

        # Jest format: "Tests: X passed, Y total"
        match = re.search(r"Tests:\s*(\d+)\s*passed", output)
        if match:
            passed = match.group(1)
            match_failed = re.search(r"(\d+)\s*failed", output)
            failed = match_failed.group(1) if match_failed else "0"
            return f"{passed} passed, {failed} failed"

        # Mocha format: "X passing"
        match = re.search(r"(\d+)\s*passing", output)
        if match:
            passed = match.group(1)
            match_failed = re.search(r"(\d+)\s*failing", output)
            failed = match_failed.group(1) if match_failed else "0"
            return f"{passed} passed, {failed} failed"

        return "test results unclear"

    def run_functional_test(
        self, workdir: Path, config: dict[str, Any]
    ) -> ValidationResult | None:
        """Run CLI functional test."""
        start_time = time.time()
        functional_config = config.get("validation", {}).get("functional_test")
        if not functional_config:
            return None

        test_type = functional_config.get("type")
        if test_type != "cli":
            return None

        command = functional_config.get("command", "")
        expected_output = functional_config.get("expected_output", "")

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=workdir,
            )

            actual_output = result.stdout.strip()

            if expected_output in actual_output:
                return ValidationResult(
                    passed=True,
                    step="functional_test",
                    message=f"CLI test passed: got expected output",
                    duration_seconds=time.time() - start_time,
                    details={"output": actual_output},
                )
            else:
                return ValidationResult(
                    passed=False,
                    step="functional_test",
                    message=f"CLI test failed: expected '{expected_output}' not in output",
                    duration_seconds=time.time() - start_time,
                    details={
                        "expected": expected_output,
                        "actual": actual_output,
                        "stderr": result.stderr,
                    },
                )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                passed=False,
                step="functional_test",
                message="CLI test timed out",
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            return ValidationResult(
                passed=False,
                step="functional_test",
                message=f"CLI test error: {e}",
                duration_seconds=time.time() - start_time,
            )

    def cleanup(self, workdir: Path) -> None:
        """Remove node_modules and build directories."""
        dirs_to_remove = [
            workdir / "node_modules",
            workdir / "dist",
            workdir / "build",
            workdir / ".next",
            workdir / "coverage",
        ]

        for dir_path in dirs_to_remove:
            if dir_path.exists():
                shutil.rmtree(dir_path, ignore_errors=True)

        # Remove lock files
        for lock_file in ["package-lock.json", "yarn.lock", "pnpm-lock.yaml"]:
            lock_path = workdir / lock_file
            if lock_path.exists():
                lock_path.unlink()
