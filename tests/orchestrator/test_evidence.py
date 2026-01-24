"""Tests for EvidenceCollector in SuperClaude.Orchestrator.evidence."""

from datetime import datetime

from SuperClaude.Orchestrator.evidence import (
    CommandResult,
    FileChange,
    TestResult,
)


class TestEvidenceCollector:
    """Tests for EvidenceCollector dataclass."""

    def test_empty_evidence(self, empty_evidence):
        """Test empty evidence state."""
        assert empty_evidence.files_written == []
        assert empty_evidence.files_edited == []
        assert empty_evidence.files_read == []
        assert empty_evidence.tests_run is False
        assert empty_evidence.total_files_modified == 0

    def test_record_file_write(self, empty_evidence):
        """Test recording file writes."""
        empty_evidence.record_file_write("test.py", lines_changed=50)

        assert "test.py" in empty_evidence.files_written
        assert len(empty_evidence.file_changes) == 1
        assert empty_evidence.file_changes[0].action == "write"
        assert empty_evidence.file_changes[0].lines_changed == 50

    def test_record_file_edit(self, empty_evidence):
        """Test recording file edits."""
        empty_evidence.record_file_edit("config.py", lines_changed=10)

        assert "config.py" in empty_evidence.files_edited
        assert len(empty_evidence.file_changes) == 1
        assert empty_evidence.file_changes[0].action == "edit"

    def test_record_file_read(self, empty_evidence):
        """Test recording file reads."""
        empty_evidence.record_file_read("README.md")

        assert "README.md" in empty_evidence.files_read
        assert len(empty_evidence.file_changes) == 1
        assert empty_evidence.file_changes[0].action == "read"

    def test_total_files_modified(self, evidence_with_files):
        """Test total files modified count."""
        # Should count unique files written + edited, not reads
        assert evidence_with_files.total_files_modified == 2

    def test_record_command(self, empty_evidence):
        """Test recording commands."""
        empty_evidence.record_command(
            command="ls -la",
            output="file1.py\nfile2.py",
            exit_code=0,
        )

        assert len(empty_evidence.commands_run) == 1
        assert empty_evidence.commands_run[0].command == "ls -la"
        assert empty_evidence.commands_run[0].exit_code == 0

    def test_record_tool_invocation(self, empty_evidence):
        """Test recording raw tool invocations."""
        empty_evidence.record_tool_invocation(
            tool_name="Read",
            tool_input={"file_path": "test.py"},
            tool_output="file contents",
        )

        assert len(empty_evidence.tool_invocations) == 1
        assert empty_evidence.tool_invocations[0]["tool_name"] == "Read"

    def test_reset(self, evidence_with_files):
        """Test resetting evidence."""
        evidence_with_files.reset()

        assert evidence_with_files.files_written == []
        assert evidence_with_files.files_edited == []
        assert evidence_with_files.file_changes == []
        assert evidence_with_files.tests_run is False

    def test_to_dict(self, evidence_with_files):
        """Test conversion to dictionary."""
        result = evidence_with_files.to_dict()

        assert "files_written" in result
        assert "files_edited" in result
        assert "total_files_modified" in result
        assert result["total_files_modified"] == 2


class TestPytestParsing:
    """Tests for pytest output parsing."""

    def test_parse_pytest_passed(self, empty_evidence):
        """Test parsing pytest output with passed tests."""
        empty_evidence.record_command(
            command="pytest tests/",
            output="===== 10 passed in 2.5s =====",
        )

        assert empty_evidence.tests_run is True
        assert len(empty_evidence.test_results) == 1
        assert empty_evidence.test_results[0].framework == "pytest"
        assert empty_evidence.test_results[0].passed == 10
        assert empty_evidence.test_results[0].failed == 0

    def test_parse_pytest_mixed(self, empty_evidence):
        """Test parsing pytest output with mixed results."""
        empty_evidence.record_command(
            command="pytest tests/",
            output="===== 8 passed, 2 failed, 1 skipped in 3.0s =====",
        )

        result = empty_evidence.test_results[0]
        assert result.passed == 8
        assert result.failed == 2
        assert result.skipped == 1

    def test_parse_pytest_with_coverage(self, empty_evidence):
        """Test parsing pytest output with coverage."""
        empty_evidence.record_command(
            command="pytest --cov=src",
            output="===== 5 passed in 1.0s =====\nTotal coverage: 85.5%",
        )

        result = empty_evidence.test_results[0]
        assert result.coverage == 85.5

    def test_parse_pytest_errors(self, empty_evidence):
        """Test parsing pytest output with errors."""
        empty_evidence.record_command(
            command="pytest tests/",
            output="===== 3 passed, 1 error in 1.0s =====",
        )

        result = empty_evidence.test_results[0]
        assert result.passed == 3
        assert result.errors == 1


class TestJestParsing:
    """Tests for Jest output parsing."""

    def test_parse_jest_passed(self, empty_evidence):
        """Test parsing Jest output with passed tests."""
        empty_evidence.record_command(
            command="npm test",
            output="Tests: 15 passed, 15 total",
        )

        assert empty_evidence.tests_run is True
        result = empty_evidence.test_results[0]
        assert result.framework == "jest"
        assert result.passed == 15

    def test_parse_jest_mixed(self, empty_evidence):
        """Test parsing Jest output with mixed results."""
        empty_evidence.record_command(
            command="jest",
            output="Tests: 10 passed, 5 failed, 15 total",
        )

        result = empty_evidence.test_results[0]
        assert result.passed == 10
        assert result.failed == 5


class TestGoTestParsing:
    """Tests for Go test output parsing."""

    def test_parse_go_test_ok(self, empty_evidence):
        """Test parsing Go test output with passing tests."""
        empty_evidence.record_command(
            command="go test ./...",
            output="ok\tgithub.com/user/pkg\t0.5s\nok\tgithub.com/user/pkg2\t0.3s",
        )

        assert empty_evidence.tests_run is True
        result = empty_evidence.test_results[0]
        assert result.framework == "go"
        assert result.passed == 2
        assert result.failed == 0

    def test_parse_go_test_fail(self, empty_evidence):
        """Test parsing Go test output with failures."""
        empty_evidence.record_command(
            command="go test ./...",
            output="FAIL\tgithub.com/user/pkg\t0.5s\nok\tgithub.com/user/pkg2\t0.3s",
        )

        result = empty_evidence.test_results[0]
        assert result.passed == 1
        assert result.failed == 1


class TestCargoTestParsing:
    """Tests for Cargo test output parsing."""

    def test_parse_cargo_test(self, empty_evidence):
        """Test parsing Cargo test output."""
        empty_evidence.record_command(
            command="cargo test",
            output="running 12 tests\ntest result: ok. 12 passed; 0 failed; 0 ignored",
        )

        assert empty_evidence.tests_run is True
        result = empty_evidence.test_results[0]
        assert result.framework == "cargo"
        assert result.passed == 12
        assert result.failed == 0


class TestTestAggregation:
    """Tests for aggregating test results."""

    def test_total_tests_passed(self, empty_evidence):
        """Test total tests passed across multiple runs."""
        empty_evidence.record_command("pytest tests/unit", "5 passed")
        empty_evidence.record_command("pytest tests/integration", "10 passed")

        assert empty_evidence.total_tests_passed == 15

    def test_total_tests_failed(self, empty_evidence):
        """Test total tests failed across multiple runs."""
        empty_evidence.record_command("pytest tests/", "5 passed, 2 failed")
        empty_evidence.record_command("pytest tests/other", "3 passed, 1 failed")

        assert empty_evidence.total_tests_failed == 3

    def test_all_tests_passing_true(self, evidence_with_passing_tests):
        """Test all_tests_passing when all pass."""
        assert evidence_with_passing_tests.all_tests_passing is True

    def test_all_tests_passing_false(self, evidence_with_failing_tests):
        """Test all_tests_passing when some fail."""
        assert evidence_with_failing_tests.all_tests_passing is False

    def test_all_tests_passing_no_tests(self, empty_evidence):
        """Test all_tests_passing when no tests run."""
        assert empty_evidence.all_tests_passing is False


class TestFileChange:
    """Tests for FileChange dataclass."""

    def test_file_change_defaults(self):
        """Test FileChange default values."""
        change = FileChange(path="test.py", action="write")

        assert change.path == "test.py"
        assert change.action == "write"
        assert change.lines_changed == 0
        assert isinstance(change.timestamp, datetime)


class TestCommandResult:
    """Tests for CommandResult dataclass."""

    def test_command_result_defaults(self):
        """Test CommandResult default values."""
        result = CommandResult(command="ls", output="files")

        assert result.command == "ls"
        assert result.output == "files"
        assert result.exit_code == 0
        assert isinstance(result.timestamp, datetime)


class TestTestResult:
    """Tests for TestResult dataclass."""

    def test_test_result_defaults(self):
        """Test TestResult default values."""
        result = TestResult(framework="pytest")

        assert result.framework == "pytest"
        assert result.passed == 0
        assert result.failed == 0
        assert result.skipped == 0
        assert result.coverage == 0.0
