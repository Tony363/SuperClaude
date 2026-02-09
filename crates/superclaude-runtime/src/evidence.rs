//! Evidence Collector - Accumulates evidence from SDK hooks during execution.
//!
//! Evidence is collected via PostToolUse hooks and used for quality assessment.

use chrono::{DateTime, Utc};
use regex::Regex;
use serde::{Deserialize, Serialize};
use std::collections::HashSet;

/// Record of a file modification.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct FileChange {
    pub path: String,
    pub action: String, // "write", "edit", "read"
    #[serde(with = "chrono::serde::ts_seconds")]
    pub timestamp: DateTime<Utc>,
    pub lines_changed: usize,
    #[serde(default)]
    pub content_hash: String,
}

impl FileChange {
    pub fn new(path: String, action: String) -> Self {
        Self {
            path,
            action,
            timestamp: Utc::now(),
            lines_changed: 0,
            content_hash: String::new(),
        }
    }

    pub fn with_lines(mut self, lines: usize) -> Self {
        self.lines_changed = lines;
        self
    }
}

/// Record of a command execution.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct CommandResult {
    pub command: String,
    pub output: String,
    pub exit_code: i32,
    #[serde(with = "chrono::serde::ts_seconds")]
    pub timestamp: DateTime<Utc>,
    pub duration_ms: u64,
}

impl CommandResult {
    pub fn new(command: String, output: String) -> Self {
        Self {
            command,
            output,
            exit_code: 0,
            timestamp: Utc::now(),
            duration_ms: 0,
        }
    }

    pub fn with_exit_code(mut self, code: i32) -> Self {
        self.exit_code = code;
        self
    }

    pub fn with_duration(mut self, duration_ms: u64) -> Self {
        self.duration_ms = duration_ms;
        self
    }
}

/// Parsed test execution results.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct TestResult {
    pub framework: String, // "pytest", "jest", "go", "cargo", etc.
    pub passed: u32,
    pub failed: u32,
    pub skipped: u32,
    pub errors: u32,
    pub coverage: f64,
    pub duration_seconds: f64,
}

impl TestResult {
    pub fn new(framework: String) -> Self {
        Self {
            framework,
            passed: 0,
            failed: 0,
            skipped: 0,
            errors: 0,
            coverage: 0.0,
            duration_seconds: 0.0,
        }
    }
}

/// Tool invocation record for debugging.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ToolInvocation {
    pub tool_name: String,
    pub tool_input: serde_json::Value,
    pub tool_output: String,
    pub timestamp: String,
}

/// Collects evidence from SDK hooks during query() execution.
///
/// This is passed to hook callbacks which populate it as tools execute.
/// Evidence is then used for quality assessment after each iteration.
///
/// # Example
/// ```rust,no_run
/// let mut evidence = EvidenceCollector::new();
/// evidence.record_file_write("test.py".to_string(), 50);
/// println!("Files written: {:?}", evidence.files_written);
/// ```
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EvidenceCollector {
    // File tracking
    pub files_written: Vec<String>,
    pub files_edited: Vec<String>,
    pub files_read: Vec<String>,
    pub file_changes: Vec<FileChange>,

    // Command tracking
    pub commands_run: Vec<CommandResult>,

    // Test tracking
    pub tests_run: bool,
    pub test_results: Vec<TestResult>,

    // Subagent tracking
    pub subagents_spawned: u32,
    pub subagent_results: Vec<serde_json::Value>,

    // Session info
    pub session_id: String,
    #[serde(with = "chrono::serde::ts_seconds")]
    pub start_time: DateTime<Utc>,
    #[serde(with = "chrono::serde::ts_seconds_option")]
    pub end_time: Option<DateTime<Utc>>,

    // Raw tool invocations (for debugging)
    pub tool_invocations: Vec<ToolInvocation>,
}

impl Default for EvidenceCollector {
    fn default() -> Self {
        Self::new()
    }
}

impl EvidenceCollector {
    /// Create a new evidence collector.
    pub fn new() -> Self {
        Self {
            files_written: Vec::new(),
            files_edited: Vec::new(),
            files_read: Vec::new(),
            file_changes: Vec::new(),
            commands_run: Vec::new(),
            tests_run: false,
            test_results: Vec::new(),
            subagents_spawned: 0,
            subagent_results: Vec::new(),
            session_id: String::new(),
            start_time: Utc::now(),
            end_time: None,
            tool_invocations: Vec::new(),
        }
    }

    /// Reset evidence for next iteration while preserving session info.
    pub fn reset(&mut self) {
        self.files_written.clear();
        self.files_edited.clear();
        self.files_read.clear();
        self.file_changes.clear();
        self.commands_run.clear();
        self.tests_run = false;
        self.test_results.clear();
        self.subagents_spawned = 0;
        self.subagent_results.clear();
        self.tool_invocations.clear();
    }

    /// Record a file write operation.
    pub fn record_file_write(&mut self, path: String, lines_changed: usize) {
        self.files_written.push(path.clone());
        self.file_changes.push(
            FileChange::new(path, "write".to_string()).with_lines(lines_changed)
        );
    }

    /// Record a file edit operation.
    pub fn record_file_edit(&mut self, path: String, lines_changed: usize) {
        self.files_edited.push(path.clone());
        self.file_changes.push(
            FileChange::new(path, "edit".to_string()).with_lines(lines_changed)
        );
    }

    /// Record a file read operation.
    pub fn record_file_read(&mut self, path: String) {
        self.files_read.push(path.clone());
        self.file_changes.push(FileChange::new(path, "read".to_string()));
    }

    /// Record a command execution.
    pub fn record_command(&mut self, command: String, output: String, exit_code: i32, duration_ms: u64) {
        let cmd_result = CommandResult::new(command.clone(), output.clone())
            .with_exit_code(exit_code)
            .with_duration(duration_ms);

        self.commands_run.push(cmd_result);

        // Check if this was a test command and parse results
        if let Some(test_result) = self.parse_test_output(&command, &output) {
            self.tests_run = true;
            self.test_results.push(test_result);
        }
    }

    /// Record raw tool invocation for debugging.
    pub fn record_tool_invocation(
        &mut self,
        tool_name: String,
        tool_input: serde_json::Value,
        tool_output: String,
    ) {
        // Truncate large outputs
        let truncated_output = if tool_output.len() > 1000 {
            format!("{}...", &tool_output[..1000])
        } else {
            tool_output
        };

        self.tool_invocations.push(ToolInvocation {
            tool_name,
            tool_input,
            tool_output: truncated_output,
            timestamp: Utc::now().to_rfc3339(),
        });
    }

    /// Parse test framework output to extract pass/fail counts.
    fn parse_test_output(&self, command: &str, output: &str) -> Option<TestResult> {
        let output_lower = output.to_lowercase();

        // Detect pytest
        if command.contains("pytest") || output_lower.contains("pytest") {
            return Some(self.parse_pytest_output(output));
        }

        // Detect Jest/npm test
        if command.contains("jest")
            || command.contains("npm test")
            || output_lower.contains("tests passed")
        {
            return Some(self.parse_jest_output(output));
        }

        // Detect Cargo tests (check BEFORE Go tests because "cargo test" contains "go test")
        if command.contains("cargo test") {
            return Some(self.parse_cargo_test_output(output));
        }

        // Detect Go tests
        if command.contains("go test") {
            return Some(self.parse_go_test_output(output));
        }

        None
    }

    /// Parse pytest output format.
    fn parse_pytest_output(&self, output: &str) -> TestResult {
        let mut result = TestResult::new("pytest".to_string());

        // Match patterns like "5 passed, 2 failed, 1 skipped"
        if let Ok(re) = Regex::new(r"(\d+)\s+passed") {
            if let Some(caps) = re.captures(output) {
                if let Some(val) = caps.get(1) {
                    result.passed = val.as_str().parse().unwrap_or(0);
                }
            }
        }

        if let Ok(re) = Regex::new(r"(\d+)\s+failed") {
            if let Some(caps) = re.captures(output) {
                if let Some(val) = caps.get(1) {
                    result.failed = val.as_str().parse().unwrap_or(0);
                }
            }
        }

        if let Ok(re) = Regex::new(r"(\d+)\s+skipped") {
            if let Some(caps) = re.captures(output) {
                if let Some(val) = caps.get(1) {
                    result.skipped = val.as_str().parse().unwrap_or(0);
                }
            }
        }

        if let Ok(re) = Regex::new(r"(\d+)\s+error") {
            if let Some(caps) = re.captures(output) {
                if let Some(val) = caps.get(1) {
                    result.errors = val.as_str().parse().unwrap_or(0);
                }
            }
        }

        // Parse coverage if present
        if let Ok(re) = Regex::new(r"(\d+(?:\.\d+)?)\s*%") {
            if let Some(caps) = re.captures(output) {
                if let Some(val) = caps.get(1) {
                    result.coverage = val.as_str().parse().unwrap_or(0.0);
                }
            }
        }

        result
    }

    /// Parse Jest output format.
    fn parse_jest_output(&self, output: &str) -> TestResult {
        let mut result = TestResult::new("jest".to_string());

        // Match patterns like "Tests: 5 passed, 2 failed, 7 total"
        if let Ok(re) = Regex::new(r"(\d+)\s+passed") {
            if let Some(caps) = re.captures(output) {
                if let Some(val) = caps.get(1) {
                    result.passed = val.as_str().parse().unwrap_or(0);
                }
            }
        }

        if let Ok(re) = Regex::new(r"(\d+)\s+failed") {
            if let Some(caps) = re.captures(output) {
                if let Some(val) = caps.get(1) {
                    result.failed = val.as_str().parse().unwrap_or(0);
                }
            }
        }

        result
    }

    /// Parse Go test output format.
    fn parse_go_test_output(&self, output: &str) -> TestResult {
        let mut result = TestResult::new("go".to_string());

        // Go tests output "ok" for passed, "FAIL" for failed
        // Use (?m) for multiline mode so ^ matches start of each line
        if let Ok(re) = Regex::new(r"(?m)^ok\s+") {
            result.passed = re.find_iter(output).count() as u32;
        }

        if let Ok(re) = Regex::new(r"(?m)^FAIL\s+") {
            result.failed = re.find_iter(output).count() as u32;
        }

        result
    }

    /// Parse Cargo test output format.
    fn parse_cargo_test_output(&self, output: &str) -> TestResult {
        let mut result = TestResult::new("cargo".to_string());

        // Match "test result: ok. X passed; Y failed"
        if let Ok(re) = Regex::new(r"(\d+)\s+passed.*?(\d+)\s+failed") {
            if let Some(caps) = re.captures(output) {
                if let Some(passed) = caps.get(1) {
                    result.passed = passed.as_str().parse().unwrap_or(0);
                }
                if let Some(failed) = caps.get(2) {
                    result.failed = failed.as_str().parse().unwrap_or(0);
                }
            }
        }

        result
    }

    /// Total unique files written or edited.
    pub fn total_files_modified(&self) -> usize {
        let mut files = HashSet::new();
        files.extend(self.files_written.iter().cloned());
        files.extend(self.files_edited.iter().cloned());
        files.len()
    }

    /// Total tests passed across all test runs.
    pub fn total_tests_passed(&self) -> u32 {
        self.test_results.iter().map(|r| r.passed).sum()
    }

    /// Total tests failed across all test runs.
    pub fn total_tests_failed(&self) -> u32 {
        self.test_results.iter().map(|r| r.failed).sum()
    }

    /// True if tests were run and all passed.
    pub fn all_tests_passing(&self) -> bool {
        if !self.tests_run {
            return false;
        }
        self.total_tests_failed() == 0 && self.total_tests_passed() > 0
    }

    /// Serialize evidence to dictionary for logging/metrics.
    pub fn to_dict(&self) -> serde_json::Value {
        serde_json::json!({
            "files_written": self.files_written,
            "files_edited": self.files_edited,
            "files_read": self.files_read,
            "total_files_modified": self.total_files_modified(),
            "commands_run": self.commands_run.len(),
            "tests_run": self.tests_run,
            "tests_passed": self.total_tests_passed(),
            "tests_failed": self.total_tests_failed(),
            "all_tests_passing": self.all_tests_passing(),
            "subagents_spawned": self.subagents_spawned,
            "session_id": self.session_id,
            "start_time": self.start_time.to_rfc3339(),
            "end_time": self.end_time.map(|t| t.to_rfc3339()),
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_empty_evidence() {
        let evidence = EvidenceCollector::new();
        assert!(evidence.files_written.is_empty());
        assert!(evidence.files_edited.is_empty());
        assert!(evidence.files_read.is_empty());
        assert!(!evidence.tests_run);
        assert_eq!(evidence.total_files_modified(), 0);
    }

    #[test]
    fn test_record_file_write() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_file_write("test.py".to_string(), 50);

        assert!(evidence.files_written.contains(&"test.py".to_string()));
        assert_eq!(evidence.file_changes.len(), 1);
        assert_eq!(evidence.file_changes[0].action, "write");
        assert_eq!(evidence.file_changes[0].lines_changed, 50);
    }

    #[test]
    fn test_record_file_edit() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_file_edit("config.py".to_string(), 10);

        assert!(evidence.files_edited.contains(&"config.py".to_string()));
        assert_eq!(evidence.file_changes.len(), 1);
        assert_eq!(evidence.file_changes[0].action, "edit");
    }

    #[test]
    fn test_record_file_read() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_file_read("README.md".to_string());

        assert!(evidence.files_read.contains(&"README.md".to_string()));
        assert_eq!(evidence.file_changes.len(), 1);
        assert_eq!(evidence.file_changes[0].action, "read");
    }

    #[test]
    fn test_total_files_modified() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_file_write("src/auth.py".to_string(), 50);
        evidence.record_file_edit("src/config.py".to_string(), 10);
        evidence.record_file_read("README.md".to_string());

        // Should count unique files written + edited, not reads
        assert_eq!(evidence.total_files_modified(), 2);
    }

    #[test]
    fn test_record_command() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_command(
            "ls -la".to_string(),
            "file1.py\nfile2.py".to_string(),
            0,
            0,
        );

        assert_eq!(evidence.commands_run.len(), 1);
        assert_eq!(evidence.commands_run[0].command, "ls -la");
        assert_eq!(evidence.commands_run[0].exit_code, 0);
    }

    #[test]
    fn test_reset() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_file_write("test.py".to_string(), 50);
        evidence.record_file_edit("config.py".to_string(), 10);
        evidence.tests_run = true;

        evidence.reset();

        assert!(evidence.files_written.is_empty());
        assert!(evidence.files_edited.is_empty());
        assert!(evidence.file_changes.is_empty());
        assert!(!evidence.tests_run);
    }

    #[test]
    fn test_parse_pytest_passed() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_command(
            "pytest tests/".to_string(),
            "===== 10 passed in 2.5s =====".to_string(),
            0,
            0,
        );

        assert!(evidence.tests_run);
        assert_eq!(evidence.test_results.len(), 1);
        assert_eq!(evidence.test_results[0].framework, "pytest");
        assert_eq!(evidence.test_results[0].passed, 10);
        assert_eq!(evidence.test_results[0].failed, 0);
    }

    #[test]
    fn test_parse_pytest_mixed() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_command(
            "pytest tests/".to_string(),
            "===== 8 passed, 2 failed, 1 skipped in 3.0s =====".to_string(),
            1,
            0,
        );

        let result = &evidence.test_results[0];
        assert_eq!(result.passed, 8);
        assert_eq!(result.failed, 2);
        assert_eq!(result.skipped, 1);
    }

    #[test]
    fn test_parse_pytest_with_coverage() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_command(
            "pytest --cov=src".to_string(),
            "===== 5 passed in 1.0s =====\nTotal coverage: 85.5%".to_string(),
            0,
            0,
        );

        let result = &evidence.test_results[0];
        assert_eq!(result.coverage, 85.5);
    }

    #[test]
    fn test_parse_pytest_errors() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_command(
            "pytest tests/".to_string(),
            "===== 3 passed, 1 error in 1.0s =====".to_string(),
            1,
            0,
        );

        let result = &evidence.test_results[0];
        assert_eq!(result.passed, 3);
        assert_eq!(result.errors, 1);
    }

    #[test]
    fn test_parse_jest_passed() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_command(
            "npm test".to_string(),
            "Tests: 15 passed, 15 total".to_string(),
            0,
            0,
        );

        assert!(evidence.tests_run);
        let result = &evidence.test_results[0];
        assert_eq!(result.framework, "jest");
        assert_eq!(result.passed, 15);
    }

    #[test]
    fn test_parse_jest_mixed() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_command(
            "jest".to_string(),
            "Tests: 10 passed, 5 failed, 15 total".to_string(),
            1,
            0,
        );

        let result = &evidence.test_results[0];
        assert_eq!(result.passed, 10);
        assert_eq!(result.failed, 5);
    }

    #[test]
    fn test_parse_go_test_ok() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_command(
            "go test ./...".to_string(),
            "ok\tgithub.com/user/pkg\t0.5s\nok\tgithub.com/user/pkg2\t0.3s".to_string(),
            0,
            0,
        );

        assert!(evidence.tests_run);
        let result = &evidence.test_results[0];
        assert_eq!(result.framework, "go");
        assert_eq!(result.passed, 2);
        assert_eq!(result.failed, 0);
    }

    #[test]
    fn test_parse_go_test_fail() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_command(
            "go test ./...".to_string(),
            "FAIL\tgithub.com/user/pkg\t0.5s\nok\tgithub.com/user/pkg2\t0.3s".to_string(),
            1,
            0,
        );

        let result = &evidence.test_results[0];
        assert_eq!(result.passed, 1);
        assert_eq!(result.failed, 1);
    }

    #[test]
    fn test_parse_cargo_test() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_command(
            "cargo test".to_string(),
            "running 12 tests\ntest result: ok. 12 passed; 0 failed; 0 ignored".to_string(),
            0,
            0,
        );

        assert!(evidence.tests_run);
        let result = &evidence.test_results[0];
        assert_eq!(result.framework, "cargo");
        assert_eq!(result.passed, 12);
        assert_eq!(result.failed, 0);
    }

    #[test]
    fn test_total_tests_passed() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_command("pytest tests/unit".to_string(), "5 passed".to_string(), 0, 0);
        evidence.record_command("pytest tests/integration".to_string(), "10 passed".to_string(), 0, 0);

        assert_eq!(evidence.total_tests_passed(), 15);
    }

    #[test]
    fn test_total_tests_failed() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_command("pytest tests/".to_string(), "5 passed, 2 failed".to_string(), 1, 0);
        evidence.record_command("pytest tests/other".to_string(), "3 passed, 1 failed".to_string(), 1, 0);

        assert_eq!(evidence.total_tests_failed(), 3);
    }

    #[test]
    fn test_all_tests_passing_true() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_command("pytest tests/".to_string(), "10 passed".to_string(), 0, 0);

        assert!(evidence.all_tests_passing());
    }

    #[test]
    fn test_all_tests_passing_false() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_command("pytest tests/".to_string(), "5 passed, 3 failed".to_string(), 1, 0);

        assert!(!evidence.all_tests_passing());
    }

    #[test]
    fn test_all_tests_passing_no_tests() {
        let evidence = EvidenceCollector::new();
        assert!(!evidence.all_tests_passing());
    }

    #[test]
    fn test_to_dict() {
        let mut evidence = EvidenceCollector::new();
        evidence.record_file_write("src/auth.py".to_string(), 50);
        evidence.record_file_edit("src/config.py".to_string(), 10);

        let result = evidence.to_dict();
        assert!(result.get("files_written").is_some());
        assert!(result.get("files_edited").is_some());
        assert_eq!(result["total_files_modified"], 2);
    }
}
