"""
Evidence Collector - Accumulates evidence from SDK hooks during execution.

Evidence is collected via PostToolUse hooks and used for quality assessment.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class FileChange:
    """Record of a file modification."""

    path: str
    action: str  # "write", "edit", "read"
    timestamp: datetime = field(default_factory=datetime.now)
    lines_changed: int = 0
    content_hash: str = ""


@dataclass
class CommandResult:
    """Record of a command execution."""

    command: str
    output: str
    exit_code: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: int = 0


@dataclass
class TestResult:
    """Parsed test execution results."""

    framework: str  # "pytest", "jest", "go", "cargo", etc.
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    coverage: float = 0.0
    duration_seconds: float = 0.0


@dataclass
class EvidenceCollector:
    """
    Collects evidence from SDK hooks during query() execution.

    This is passed to hook callbacks which populate it as tools execute.
    Evidence is then used for quality assessment after each iteration.

    Example:
        evidence = EvidenceCollector()
        hooks = create_sdk_hooks(evidence)

        async for msg in query(prompt, options=ClaudeAgentOptions(hooks=hooks)):
            pass

        # Evidence is now populated
        print(evidence.files_written)
        print(evidence.test_results)
    """

    # File tracking
    files_written: list[str] = field(default_factory=list)
    files_edited: list[str] = field(default_factory=list)
    files_read: list[str] = field(default_factory=list)
    file_changes: list[FileChange] = field(default_factory=list)

    # Command tracking
    commands_run: list[CommandResult] = field(default_factory=list)

    # Test tracking
    tests_run: bool = False
    test_results: list[TestResult] = field(default_factory=list)

    # Subagent tracking
    subagents_spawned: int = 0
    subagent_results: list[dict[str, Any]] = field(default_factory=list)

    # Session info
    session_id: str = ""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None

    # Raw tool invocations (for debugging)
    tool_invocations: list[dict[str, Any]] = field(default_factory=list)

    def reset(self) -> None:
        """Reset evidence for next iteration while preserving session info."""
        self.files_written.clear()
        self.files_edited.clear()
        self.files_read.clear()
        self.file_changes.clear()
        self.commands_run.clear()
        self.tests_run = False
        self.test_results.clear()
        self.subagents_spawned = 0
        self.subagent_results.clear()
        self.tool_invocations.clear()

    def record_file_write(self, path: str, lines_changed: int = 0) -> None:
        """Record a file write operation."""
        self.files_written.append(path)
        self.file_changes.append(
            FileChange(path=path, action="write", lines_changed=lines_changed)
        )

    def record_file_edit(self, path: str, lines_changed: int = 0) -> None:
        """Record a file edit operation."""
        self.files_edited.append(path)
        self.file_changes.append(
            FileChange(path=path, action="edit", lines_changed=lines_changed)
        )

    def record_file_read(self, path: str) -> None:
        """Record a file read operation."""
        self.files_read.append(path)
        self.file_changes.append(FileChange(path=path, action="read"))

    def record_command(
        self, command: str, output: str, exit_code: int = 0, duration_ms: int = 0
    ) -> None:
        """Record a command execution."""
        self.commands_run.append(
            CommandResult(
                command=command,
                output=output,
                exit_code=exit_code,
                duration_ms=duration_ms,
            )
        )

        # Check if this was a test command and parse results
        test_result = self._parse_test_output(command, output)
        if test_result:
            self.tests_run = True
            self.test_results.append(test_result)

    def record_tool_invocation(
        self, tool_name: str, tool_input: dict[str, Any], tool_output: Any
    ) -> None:
        """Record raw tool invocation for debugging."""
        self.tool_invocations.append(
            {
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_output": str(tool_output)[:1000],  # Truncate large outputs
                "timestamp": datetime.now().isoformat(),
            }
        )

    def _parse_test_output(self, command: str, output: str) -> TestResult | None:
        """Parse test framework output to extract pass/fail counts."""
        output_lower = output.lower()

        # Detect pytest
        if "pytest" in command or "pytest" in output_lower:
            return self._parse_pytest_output(output)

        # Detect Jest/npm test
        if "jest" in command or "npm test" in command or "tests passed" in output_lower:
            return self._parse_jest_output(output)

        # Detect Cargo tests (check BEFORE Go tests because "cargo test" contains "go test")
        if "cargo test" in command:
            return self._parse_cargo_test_output(output)

        # Detect Go tests
        if "go test" in command:
            return self._parse_go_test_output(output)

        return None

    def _parse_pytest_output(self, output: str) -> TestResult:
        """Parse pytest output format."""
        result = TestResult(framework="pytest")

        # Match patterns like "5 passed, 2 failed, 1 skipped"
        passed_match = re.search(r"(\d+)\s+passed", output)
        failed_match = re.search(r"(\d+)\s+failed", output)
        skipped_match = re.search(r"(\d+)\s+skipped", output)
        errors_match = re.search(r"(\d+)\s+error", output)

        if passed_match:
            result.passed = int(passed_match.group(1))
        if failed_match:
            result.failed = int(failed_match.group(1))
        if skipped_match:
            result.skipped = int(skipped_match.group(1))
        if errors_match:
            result.errors = int(errors_match.group(1))

        # Parse coverage if present
        coverage_match = re.search(r"(\d+(?:\.\d+)?)\s*%", output)
        if coverage_match:
            result.coverage = float(coverage_match.group(1))

        return result

    def _parse_jest_output(self, output: str) -> TestResult:
        """Parse Jest output format."""
        result = TestResult(framework="jest")

        # Match patterns like "Tests: 5 passed, 2 failed, 7 total"
        passed_match = re.search(r"(\d+)\s+passed", output)
        failed_match = re.search(r"(\d+)\s+failed", output)

        if passed_match:
            result.passed = int(passed_match.group(1))
        if failed_match:
            result.failed = int(failed_match.group(1))

        return result

    def _parse_go_test_output(self, output: str) -> TestResult:
        """Parse Go test output format."""
        result = TestResult(framework="go")

        # Go tests output "ok" for passed, "FAIL" for failed
        ok_count = len(re.findall(r"^ok\s+", output, re.MULTILINE))
        fail_count = len(re.findall(r"^FAIL\s+", output, re.MULTILINE))

        result.passed = ok_count
        result.failed = fail_count

        return result

    def _parse_cargo_test_output(self, output: str) -> TestResult:
        """Parse Cargo test output format."""
        result = TestResult(framework="cargo")

        # Match "test result: ok. X passed; Y failed"
        match = re.search(r"(\d+)\s+passed.*?(\d+)\s+failed", output)
        if match:
            result.passed = int(match.group(1))
            result.failed = int(match.group(2))

        return result

    @property
    def total_files_modified(self) -> int:
        """Total unique files written or edited."""
        return len(set(self.files_written + self.files_edited))

    @property
    def total_tests_passed(self) -> int:
        """Total tests passed across all test runs."""
        return sum(r.passed for r in self.test_results)

    @property
    def total_tests_failed(self) -> int:
        """Total tests failed across all test runs."""
        return sum(r.failed for r in self.test_results)

    @property
    def all_tests_passing(self) -> bool:
        """True if tests were run and all passed."""
        if not self.tests_run:
            return False
        return self.total_tests_failed == 0 and self.total_tests_passed > 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize evidence to dictionary for logging/metrics."""
        return {
            "files_written": self.files_written,
            "files_edited": self.files_edited,
            "files_read": self.files_read,
            "total_files_modified": self.total_files_modified,
            "commands_run": len(self.commands_run),
            "tests_run": self.tests_run,
            "tests_passed": self.total_tests_passed,
            "tests_failed": self.total_tests_failed,
            "all_tests_passing": self.all_tests_passing,
            "subagents_spawned": self.subagents_spawned,
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
        }
