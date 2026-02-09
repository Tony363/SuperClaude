//! Events tracking module for SuperClaude orchestrator.
//!
//! Writes real-time events to .superclaude_metrics/events.jsonl for consumption
//! by the Zed panel and other monitoring tools.
//!
//! This module is a direct port of SuperClaude/Orchestrator/events_hooks.py
//! and maintains compatibility with the daemon's metrics_watcher.rs parser.

use std::collections::HashMap;
use std::fs::OpenOptions;
use std::io::Write as IoWrite;
use std::path::PathBuf;
use std::sync::{Arc, Mutex};

use anyhow::{Context, Result};
use chrono::Utc;
use serde::{Deserialize, Serialize};
use serde_json::Value as JsonValue;

/// Event types matching daemon schema
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum EventType {
    IterationStart,
    IterationComplete,
    ToolUse,
    FileChange,
    TestResult,
    ScoreUpdate,
    StateChange,
    SubagentSpawn,
    SubagentComplete,
    Artifact,
    Log,
    Error,
}

/// File action types
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum FileAction {
    Read,
    Write,
    Edit,
    Delete,
}

/// Log levels
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum LogLevel {
    Debug,
    Info,
    Warn,
    Error,
}

/// Quality dimensions for iteration scoring
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct QualityDimensions {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub code_changes: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tests_run: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub tests_pass: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub coverage: Option<f32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub no_errors: Option<f32>,
}

/// Tracks and emits events for the Zed panel integration.
///
/// This class manages the JSONL writer and provides methods
/// for recording various event types in the format expected by
/// the superclaude-daemon.
pub struct EventsTracker {
    writer: Arc<Mutex<JsonlWriter>>,
    current_iteration: i32,
    current_depth: i32,
    node_counter: u32,
}

impl EventsTracker {
    /// Initialize the events tracker.
    ///
    /// # Arguments
    /// * `session_id` - Unique session identifier (auto-generated if None)
    /// * `metrics_dir` - Directory for events.jsonl (default: .superclaude_metrics/)
    pub fn new(session_id: Option<String>, metrics_dir: Option<PathBuf>) -> Result<Self> {
        let metrics_dir = metrics_dir.unwrap_or_else(|| PathBuf::from(".superclaude_metrics"));
        let session_id = session_id.unwrap_or_else(|| uuid::Uuid::new_v4().to_string());

        let writer = JsonlWriter::new(metrics_dir, session_id)?;

        Ok(Self {
            writer: Arc::new(Mutex::new(writer)),
            current_iteration: 0,
            current_depth: 0,
            node_counter: 0,
        })
    }

    /// Generate a unique node ID.
    fn next_node_id(&mut self, prefix: &str) -> String {
        self.node_counter += 1;
        format!("{}-{}", prefix, self.node_counter)
    }

    /// Record the start of an iteration.
    ///
    /// # Arguments
    /// * `iteration` - 0-indexed iteration number
    /// * `depth` - Nesting depth for visualization
    ///
    /// # Returns
    /// Node ID for this iteration
    pub fn record_iteration_start(&mut self, iteration: i32, depth: i32) -> Result<String> {
        self.current_iteration = iteration;
        self.current_depth = depth;
        let node_id = format!("iter-{}", iteration);

        let mut event = HashMap::new();
        event.insert("event_type".to_string(), json!("iteration_start"));
        event.insert("iteration".to_string(), json!(iteration));
        event.insert("depth".to_string(), json!(depth));
        event.insert("node_id".to_string(), json!(&node_id));

        self.writer.lock().unwrap().write_event(event)?;
        Ok(node_id)
    }

    /// Record the completion of an iteration.
    ///
    /// # Arguments
    /// * `iteration` - 0-indexed iteration number
    /// * `score` - Quality score (0-100)
    /// * `improvements` - List of improvement suggestions
    /// * `dimensions` - Quality dimension scores
    /// * `duration_seconds` - Time taken for this iteration
    pub fn record_iteration_complete(
        &self,
        iteration: i32,
        score: f32,
        improvements: Option<Vec<String>>,
        dimensions: Option<QualityDimensions>,
        duration_seconds: f32,
    ) -> Result<()> {
        let node_id = format!("iter-{}", iteration);

        let mut event = HashMap::new();
        event.insert("event_type".to_string(), json!("iteration_complete"));
        event.insert("iteration".to_string(), json!(iteration));
        event.insert("score".to_string(), json!(score));
        event.insert("improvements".to_string(), json!(improvements.unwrap_or_default()));
        event.insert("duration_seconds".to_string(), json!(duration_seconds));
        event.insert("node_id".to_string(), json!(node_id));

        if let Some(dims) = dimensions {
            event.insert("dimensions".to_string(), serde_json::to_value(dims)?);
        }

        self.writer.lock().unwrap().write_event(event)?;
        Ok(())
    }

    /// Record a tool invocation.
    ///
    /// # Arguments
    /// * `tool_name` - Name of the tool (Write, Edit, Bash, etc.)
    /// * `tool_input` - Tool input parameters
    /// * `tool_output` - Tool output/response
    /// * `blocked` - Whether the tool was blocked by safety hooks
    /// * `block_reason` - Reason for blocking
    /// * `parent_node_id` - Parent node for tree visualization
    ///
    /// # Returns
    /// Node ID for this tool invocation
    pub fn record_tool_use(
        &mut self,
        tool_name: &str,
        tool_input: &HashMap<String, JsonValue>,
        tool_output: Option<&str>,
        blocked: bool,
        block_reason: &str,
        parent_node_id: Option<&str>,
    ) -> Result<String> {
        let node_id = self.next_node_id("tool");
        let summary = summarize_tool(tool_name, tool_input, tool_output);

        let mut event = HashMap::new();
        event.insert("event_type".to_string(), json!("tool_use"));
        event.insert("tool".to_string(), json!(tool_name));
        event.insert("summary".to_string(), json!(summary));
        event.insert("blocked".to_string(), json!(blocked));
        event.insert("block_reason".to_string(), json!(block_reason));
        event.insert("depth".to_string(), json!(self.current_depth + 1));
        event.insert("node_id".to_string(), json!(&node_id));
        event.insert(
            "parent_node_id".to_string(),
            json!(parent_node_id.unwrap_or(&format!("iter-{}", self.current_iteration))),
        );

        self.writer.lock().unwrap().write_event(event)?;
        Ok(node_id)
    }

    /// Record a file change.
    ///
    /// # Arguments
    /// * `path` - File path
    /// * `action` - Action type (write, edit, read, delete)
    /// * `lines_added` - Number of lines added
    /// * `lines_removed` - Number of lines removed
    ///
    /// # Returns
    /// Node ID for this file change
    pub fn record_file_change(
        &mut self,
        path: &str,
        action: FileAction,
        lines_added: i32,
        lines_removed: i32,
    ) -> Result<String> {
        let node_id = self.next_node_id("file");

        let mut event = HashMap::new();
        event.insert("event_type".to_string(), json!("file_change"));
        event.insert("path".to_string(), json!(path));
        event.insert("action".to_string(), serde_json::to_value(action)?);
        event.insert("lines_added".to_string(), json!(lines_added));
        event.insert("lines_removed".to_string(), json!(lines_removed));
        event.insert("node_id".to_string(), json!(&node_id));

        self.writer.lock().unwrap().write_event(event)?;
        Ok(node_id)
    }

    /// Record test execution results.
    ///
    /// # Arguments
    /// * `framework` - Test framework (pytest, jest, cargo, go)
    /// * `passed` - Number of passed tests
    /// * `failed` - Number of failed tests
    /// * `skipped` - Number of skipped tests
    /// * `coverage` - Code coverage percentage
    /// * `failed_tests` - List of failed test names
    ///
    /// # Returns
    /// Node ID for this test result
    pub fn record_test_result(
        &mut self,
        framework: &str,
        passed: i32,
        failed: i32,
        skipped: i32,
        coverage: f32,
        failed_tests: Option<Vec<String>>,
    ) -> Result<String> {
        let node_id = self.next_node_id("test");

        let mut event = HashMap::new();
        event.insert("event_type".to_string(), json!("test_result"));
        event.insert("framework".to_string(), json!(framework));
        event.insert("passed".to_string(), json!(passed));
        event.insert("failed".to_string(), json!(failed));
        event.insert("skipped".to_string(), json!(skipped));
        event.insert("coverage".to_string(), json!(coverage));
        event.insert("failed_tests".to_string(), json!(failed_tests.unwrap_or_default()));
        event.insert("node_id".to_string(), json!(&node_id));

        self.writer.lock().unwrap().write_event(event)?;
        Ok(node_id)
    }

    /// Record a quality score update.
    ///
    /// # Arguments
    /// * `old_score` - Previous score
    /// * `new_score` - New score
    /// * `reason` - Reason for the change
    /// * `dimensions` - Quality dimension breakdown
    pub fn record_score_update(
        &self,
        old_score: f32,
        new_score: f32,
        reason: &str,
        dimensions: Option<QualityDimensions>,
    ) -> Result<()> {
        let mut event = HashMap::new();
        event.insert("event_type".to_string(), json!("score_update"));
        event.insert("old_score".to_string(), json!(old_score));
        event.insert("new_score".to_string(), json!(new_score));
        event.insert("reason".to_string(), json!(reason));

        if let Some(dims) = dimensions {
            event.insert("dimensions".to_string(), serde_json::to_value(dims)?);
        }

        self.writer.lock().unwrap().write_event(event)?;
        Ok(())
    }

    /// Record a subagent being spawned.
    ///
    /// # Arguments
    /// * `subagent_id` - Unique identifier for the subagent
    /// * `subagent_type` - Type of subagent (Explore, Plan, etc.)
    /// * `task` - Task assigned to the subagent
    /// * `parent_node_id` - Parent node for tree visualization
    ///
    /// # Returns
    /// Node ID for this subagent
    pub fn record_subagent_spawn(
        &mut self,
        subagent_id: &str,
        subagent_type: &str,
        task: &str,
        parent_node_id: Option<&str>,
    ) -> Result<String> {
        let node_id = self.next_node_id("subagent");

        let mut event = HashMap::new();
        event.insert("event_type".to_string(), json!("subagent_spawn"));
        event.insert("subagent_id".to_string(), json!(subagent_id));
        event.insert("subagent_type".to_string(), json!(subagent_type));
        event.insert("task".to_string(), json!(task));
        event.insert("depth".to_string(), json!(self.current_depth + 1));
        event.insert("node_id".to_string(), json!(&node_id));
        event.insert(
            "parent_node_id".to_string(),
            json!(parent_node_id.unwrap_or(&format!("iter-{}", self.current_iteration))),
        );

        self.writer.lock().unwrap().write_event(event)?;
        Ok(node_id)
    }

    /// Record a subagent completing.
    ///
    /// # Arguments
    /// * `subagent_id` - Unique identifier for the subagent
    /// * `node_id` - Node ID from spawn event
    /// * `success` - Whether the subagent succeeded
    /// * `result` - Result summary
    pub fn record_subagent_complete(
        &self,
        subagent_id: &str,
        node_id: &str,
        success: bool,
        result: &str,
    ) -> Result<()> {
        let mut event = HashMap::new();
        event.insert("event_type".to_string(), json!("subagent_complete"));
        event.insert("subagent_id".to_string(), json!(subagent_id));
        event.insert("node_id".to_string(), json!(node_id));
        event.insert("success".to_string(), json!(success));
        event.insert("result".to_string(), json!(result));

        self.writer.lock().unwrap().write_event(event)?;
        Ok(())
    }

    /// Record an artifact being written (e.g., Obsidian note).
    ///
    /// # Arguments
    /// * `path` - Path to the artifact
    /// * `artifact_type` - Type (decision, evidence, summary)
    /// * `title` - Human-readable title
    pub fn record_artifact(&self, path: &str, artifact_type: &str, title: &str) -> Result<()> {
        let mut event = HashMap::new();
        event.insert("event_type".to_string(), json!("artifact"));
        event.insert("path".to_string(), json!(path));
        event.insert("type".to_string(), json!(artifact_type));
        event.insert("title".to_string(), json!(title));

        self.writer.lock().unwrap().write_event(event)?;
        Ok(())
    }

    /// Record an error.
    ///
    /// # Arguments
    /// * `error_type` - Type of error
    /// * `message` - Error message
    /// * `traceback` - Stack trace if available
    /// * `recoverable` - Whether execution can continue
    pub fn record_error(
        &self,
        error_type: &str,
        message: &str,
        traceback: &str,
        recoverable: bool,
    ) -> Result<()> {
        let mut event = HashMap::new();
        event.insert("event_type".to_string(), json!("error"));
        event.insert("error_type".to_string(), json!(error_type));
        event.insert("message".to_string(), json!(message));
        event.insert("traceback".to_string(), json!(traceback));
        event.insert("recoverable".to_string(), json!(recoverable));

        self.writer.lock().unwrap().write_event(event)?;
        Ok(())
    }

    /// Record a log message.
    ///
    /// # Arguments
    /// * `level` - Log level (debug, info, warn, error)
    /// * `message` - Log message
    /// * `source` - Source of the log
    pub fn record_log(&self, level: LogLevel, message: &str, source: &str) -> Result<()> {
        let mut event = HashMap::new();
        event.insert("event_type".to_string(), json!("log"));
        event.insert("level".to_string(), serde_json::to_value(level)?);
        event.insert("message".to_string(), json!(message));
        event.insert("source".to_string(), json!(source));

        self.writer.lock().unwrap().write_event(event)?;
        Ok(())
    }

    /// Record an execution state change.
    ///
    /// # Arguments
    /// * `old_state` - Previous state
    /// * `new_state` - New state
    /// * `reason` - Reason for the change
    pub fn record_state_change(
        &self,
        old_state: &str,
        new_state: &str,
        reason: &str,
    ) -> Result<()> {
        let mut event = HashMap::new();
        event.insert("event_type".to_string(), json!("state_change"));
        event.insert("old_state".to_string(), json!(old_state));
        event.insert("new_state".to_string(), json!(new_state));
        event.insert("reason".to_string(), json!(reason));

        self.writer.lock().unwrap().write_event(event)?;
        Ok(())
    }

    /// Flush any buffered events.
    pub fn flush(&self) -> Result<()> {
        self.writer.lock().unwrap().flush()
    }

    /// Close the tracker and flush remaining events.
    pub fn close(&self) -> Result<()> {
        self.flush()
    }
}

/// JSONL writer with file locking for thread/process safety
struct JsonlWriter {
    events_file: PathBuf,
    session_id: String,
}

impl JsonlWriter {
    fn new(metrics_dir: PathBuf, session_id: String) -> Result<Self> {
        // Ensure metrics directory exists
        std::fs::create_dir_all(&metrics_dir)
            .with_context(|| format!("Failed to create metrics directory: {:?}", metrics_dir))?;

        let events_file = metrics_dir.join("events.jsonl");

        Ok(Self {
            events_file,
            session_id,
        })
    }

    fn write_event(&mut self, mut event: HashMap<String, JsonValue>) -> Result<()> {
        // Add timestamp and session_id
        event.insert(
            "timestamp".to_string(),
            json!(Utc::now().to_rfc3339()),
        );
        event.insert("session_id".to_string(), json!(&self.session_id));

        // Open file in append mode with file locking
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.events_file)
            .with_context(|| format!("Failed to open events file: {:?}", self.events_file))?;

        // Lock the file (blocking)
        #[cfg(unix)]
        {
            use fs2::FileExt;
            file.lock_exclusive()
                .context("Failed to acquire file lock")?;
        }

        // Write JSONL entry
        let json_line = serde_json::to_string(&event)? + "\n";
        file.write_all(json_line.as_bytes())
            .context("Failed to write event")?;

        // Unlock happens automatically on drop

        Ok(())
    }

    fn flush(&mut self) -> Result<()> {
        // JSONL writes are already flushed immediately
        Ok(())
    }
}

/// Generate a human-readable summary for a tool invocation
fn summarize_tool(
    tool_name: &str,
    tool_input: &HashMap<String, JsonValue>,
    _tool_output: Option<&str>,
) -> String {
    match tool_name {
        "Write" => {
            let path = tool_input
                .get("file_path")
                .and_then(|v| v.as_str())
                .unwrap_or("file");
            format!("Created {}", path)
        }
        "Edit" => {
            let path = tool_input
                .get("file_path")
                .and_then(|v| v.as_str())
                .unwrap_or("file");
            format!("Modified {}", path)
        }
        "Read" => {
            let path = tool_input
                .get("file_path")
                .and_then(|v| v.as_str())
                .unwrap_or("file");
            format!("Read {}", path)
        }
        "Bash" => {
            let cmd = tool_input
                .get("command")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            // Truncate long commands
            if cmd.len() > 60 {
                format!("Ran: {}...", &cmd[..57])
            } else {
                format!("Ran: {}", cmd)
            }
        }
        "Grep" => {
            let pattern = tool_input
                .get("pattern")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            format!("Searched for: {}", pattern)
        }
        "Glob" => {
            let pattern = tool_input
                .get("pattern")
                .and_then(|v| v.as_str())
                .unwrap_or("");
            format!("Found files: {}", pattern)
        }
        "Task" => {
            let desc = tool_input
                .get("description")
                .and_then(|v| v.as_str())
                .unwrap_or("task");
            format!("Spawned: {}", desc)
        }
        _ => format!("Used {}", tool_name),
    }
}

// Helper macro for JSON construction
macro_rules! json {
    ($val:expr) => {
        serde_json::to_value($val).unwrap()
    };
}

use json;

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;
    use std::io::{self, BufRead};
    use std::fs::File;

    #[test]
    fn test_events_tracker_creation() {
        let temp_dir = TempDir::new().unwrap();
        let tracker = EventsTracker::new(
            Some("test-session".to_string()),
            Some(temp_dir.path().to_path_buf()),
        );
        assert!(tracker.is_ok());
    }

    #[test]
    fn test_iteration_events() {
        let temp_dir = TempDir::new().unwrap();
        let mut tracker = EventsTracker::new(
            Some("test-session".to_string()),
            Some(temp_dir.path().to_path_buf()),
        )
        .unwrap();

        let node_id = tracker.record_iteration_start(0, 0).unwrap();
        assert_eq!(node_id, "iter-0");

        tracker
            .record_iteration_complete(0, 75.0, None, None, 1.5)
            .unwrap();

        // Verify JSONL was written
        let events_file = temp_dir.path().join("events.jsonl");
        assert!(events_file.exists());
    }

    #[test]
    fn test_tool_use_summary() {
        let mut input = HashMap::new();
        input.insert("file_path".to_string(), json!("src/main.rs"));

        let summary = summarize_tool("Write", &input, None);
        assert_eq!(summary, "Created src/main.rs");

        let summary = summarize_tool("Edit", &input, None);
        assert_eq!(summary, "Modified src/main.rs");
    }

    #[test]
    fn test_jsonl_format() {
        use std::fs::File;
        use std::io::BufRead;

        let temp_dir = TempDir::new().unwrap();
        let mut tracker = EventsTracker::new(
            Some("test-session".to_string()),
            Some(temp_dir.path().to_path_buf()),
        )
        .unwrap();

        tracker.record_iteration_start(0, 0).unwrap();
        tracker.flush().unwrap();

        // Read and parse JSONL
        let events_file = temp_dir.path().join("events.jsonl");
        let file = File::open(events_file).unwrap();
        let reader = io::BufReader::new(file);

        for line in reader.lines() {
            let line = line.unwrap();
            let parsed: serde_json::Value = serde_json::from_str(&line).unwrap();

            assert_eq!(parsed["event_type"], "iteration_start");
            assert_eq!(parsed["session_id"], "test-session");
            assert!(parsed["timestamp"].is_string());
            assert_eq!(parsed["iteration"], 0);
        }
    }
}
