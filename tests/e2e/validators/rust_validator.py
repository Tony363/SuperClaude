"""Rust application validator for E2E tests."""

from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from tests.e2e.validators import BaseValidator, ValidationResult


class RustValidator(BaseValidator):
    """Validator for Rust applications."""

    @property
    def language(self) -> str:
        return "rust"

    def setup(self, workdir: Path, config: dict[str, Any]) -> ValidationResult:
        """Verify Rust toolchain is available."""
        start_time = time.time()

        # Check for Cargo.toml
        cargo_toml = workdir / "Cargo.toml"
        if not cargo_toml.exists():
            return ValidationResult(
                passed=False,
                step="setup",
                message="No Cargo.toml found",
                duration_seconds=time.time() - start_time,
            )

        try:
            # Verify cargo is available
            result = subprocess.run(
                ["cargo", "--version"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                return ValidationResult(
                    passed=False,
                    step="setup",
                    message="cargo not available",
                    duration_seconds=time.time() - start_time,
                )

            cargo_version = result.stdout.strip()

            # Fetch dependencies (cargo build will do this, but we can pre-fetch)
            result = subprocess.run(
                ["cargo", "fetch"],
                capture_output=True,
                text=True,
                timeout=120,
                cwd=workdir,
            )

            if result.returncode != 0:
                # cargo fetch failing is not critical, build will retry
                pass

            return ValidationResult(
                passed=True,
                step="setup",
                message=f"Rust toolchain ready ({cargo_version})",
                duration_seconds=time.time() - start_time,
            )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                passed=False,
                step="setup",
                message="Setup timed out",
                duration_seconds=time.time() - start_time,
            )
        except FileNotFoundError:
            return ValidationResult(
                passed=False,
                step="setup",
                message="Rust toolchain not installed (cargo not found)",
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
        """Run cargo check to verify code compiles."""
        start_time = time.time()

        try:
            result = subprocess.run(
                ["cargo", "check"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=workdir,
            )

            if result.returncode != 0:
                # Extract the most relevant error message
                error_output = result.stderr or result.stdout
                return ValidationResult(
                    passed=False,
                    step="compile_check",
                    message="cargo check failed",
                    duration_seconds=time.time() - start_time,
                    details={"errors": error_output[-2000:]},
                )

            return ValidationResult(
                passed=True,
                step="compile_check",
                message="Rust code compiles successfully",
                duration_seconds=time.time() - start_time,
            )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                passed=False,
                step="compile_check",
                message="cargo check timed out",
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            return ValidationResult(
                passed=False,
                step="compile_check",
                message=f"Compile check error: {e}",
                duration_seconds=time.time() - start_time,
            )

    def run_tests(self, workdir: Path, config: dict[str, Any]) -> ValidationResult:
        """Run cargo test."""
        start_time = time.time()

        try:
            result = subprocess.run(
                ["cargo", "test"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=workdir,
            )

            output = result.stdout + result.stderr
            passed = result.returncode == 0

            # Parse test output
            test_info = self._parse_cargo_test_output(output)

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
                message="cargo test timed out",
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            return ValidationResult(
                passed=False,
                step="test_execution",
                message=f"Test execution error: {e}",
                duration_seconds=time.time() - start_time,
            )

    def _parse_cargo_test_output(self, output: str) -> str:
        """Extract test summary from cargo test output."""
        import re

        # cargo test format: "test result: ok. X passed; Y failed; Z ignored"
        match = re.search(
            r"test result: (ok|FAILED)\. (\d+) passed; (\d+) failed", output
        )
        if match:
            status, passed, failed = match.groups()
            return f"{passed} passed, {failed} failed"

        # Alternative: count individual test lines
        # "test test_name ... ok"
        passed_count = len(re.findall(r"test .+ \.\.\. ok", output))
        failed_count = len(re.findall(r"test .+ \.\.\. FAILED", output))

        if passed_count or failed_count:
            return f"{passed_count} passed, {failed_count} failed"

        return "test results unclear"

    def run_functional_test(
        self, workdir: Path, config: dict[str, Any]
    ) -> ValidationResult | None:
        """Run binary if it's an executable project."""
        start_time = time.time()
        functional_config = config.get("validation", {}).get("functional_test")
        if not functional_config:
            return None

        # For Rust, functional tests typically run the built binary
        test_type = functional_config.get("type")
        if test_type != "binary":
            return None

        try:
            # First build the release binary
            result = subprocess.run(
                ["cargo", "build", "--release"],
                capture_output=True,
                text=True,
                timeout=180,
                cwd=workdir,
            )

            if result.returncode != 0:
                return ValidationResult(
                    passed=False,
                    step="functional_test",
                    message="Failed to build release binary",
                    duration_seconds=time.time() - start_time,
                )

            # Run the binary with provided args
            args = functional_config.get("args", [])
            binary_name = functional_config.get("binary")
            if not binary_name:
                # Try to get from Cargo.toml
                cargo_toml = workdir / "Cargo.toml"
                if cargo_toml.exists():
                    import re

                    content = cargo_toml.read_text()
                    match = re.search(r'name\s*=\s*"([^"]+)"', content)
                    if match:
                        binary_name = match.group(1)

            if not binary_name:
                return ValidationResult(
                    passed=False,
                    step="functional_test",
                    message="Could not determine binary name",
                    duration_seconds=time.time() - start_time,
                )

            binary_path = workdir / "target" / "release" / binary_name

            if not binary_path.exists():
                return ValidationResult(
                    passed=False,
                    step="functional_test",
                    message=f"Binary not found: {binary_path}",
                    duration_seconds=time.time() - start_time,
                )

            result = subprocess.run(
                [str(binary_path)] + args,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=workdir,
            )

            expected_output = functional_config.get("expected_output", "")
            if expected_output and expected_output in result.stdout:
                return ValidationResult(
                    passed=True,
                    step="functional_test",
                    message="Binary execution test passed",
                    duration_seconds=time.time() - start_time,
                    details={"output": result.stdout},
                )
            elif not expected_output and result.returncode == 0:
                return ValidationResult(
                    passed=True,
                    step="functional_test",
                    message="Binary executed successfully",
                    duration_seconds=time.time() - start_time,
                )
            else:
                return ValidationResult(
                    passed=False,
                    step="functional_test",
                    message="Binary execution test failed",
                    duration_seconds=time.time() - start_time,
                    details={
                        "expected": expected_output,
                        "actual": result.stdout,
                        "stderr": result.stderr,
                    },
                )

        except subprocess.TimeoutExpired:
            return ValidationResult(
                passed=False,
                step="functional_test",
                message="Functional test timed out",
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            return ValidationResult(
                passed=False,
                step="functional_test",
                message=f"Functional test error: {e}",
                duration_seconds=time.time() - start_time,
            )

    def cleanup(self, workdir: Path) -> None:
        """Remove target directory."""
        target_dir = workdir / "target"
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)

        # Remove Cargo.lock (optional, keep if you want reproducible builds)
        cargo_lock = workdir / "Cargo.lock"
        if cargo_lock.exists():
            cargo_lock.unlink()
