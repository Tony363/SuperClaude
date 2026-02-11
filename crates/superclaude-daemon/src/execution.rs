//! Execution management - spawns and monitors claude CLI processes

use std::path::PathBuf;
use std::process::Stdio;
use std::sync::Arc;

use anyhow::{Context, Result};
use chrono::Utc;
use parking_lot::RwLock;
use prost_types::Timestamp;
use serde::Deserialize;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};
use tokio::sync::broadcast;
use tracing::{debug, error, info, warn};
use uuid::Uuid;

use crate::metrics_watcher::MetricsWatcher;
use superclaude_proto::*;

// ---------------------------------------------------------------------------
// Claude CLI stream-json deserialization types
// ---------------------------------------------------------------------------

/// Top-level event from `claude --print --verbose --output-format stream-json`
#[derive(Debug, Deserialize)]
struct StreamJsonEvent {
    #[serde(rename = "type")]
    event_type: String,
    #[serde(default)]
    subtype: Option<String>,
    #[serde(default)]
    message: Option<StreamMessage>,
    /// Present on type="result"
    #[serde(default)]
    num_turns: Option<i32>,
    #[serde(default)]
    duration_ms: Option<f64>,
    #[serde(default)]
    total_cost_usd: Option<f64>,
    #[serde(default)]
    is_error: Option<bool>,
    #[serde(default)]
    result: Option<String>,
    /// Present on type="user" for tool results
    #[serde(default)]
    tool_use_result: Option<serde_json::Value>,
}

#[derive(Debug, Deserialize)]
struct StreamMessage {
    #[serde(default)]
    content: Vec<ContentBlock>,
    #[serde(default)]
    #[allow(dead_code)]
    usage: Option<UsageInfo>,
}

#[derive(Debug, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
enum ContentBlock {
    Text {
        text: String,
    },
    ToolUse {
        id: String,
        name: String,
        #[serde(default)]
        input: serde_json::Value,
    },
    ToolResult {
        #[serde(default)]
        #[allow(dead_code)]
        tool_use_id: Option<String>,
        #[serde(default)]
        content: Option<serde_json::Value>,
    },
    #[serde(other)]
    Unknown,
}

#[derive(Debug, Deserialize)]
#[allow(dead_code)]
struct UsageInfo {
    #[serde(default)]
    input_tokens: u64,
    #[serde(default)]
    output_tokens: u64,
}

/// Represents a running or completed execution
pub struct Execution {
    pub id: String,
    pub task: String,
    pub project_root: String,
    pub config: ExecutionConfig,
}

/// Handle to a running execution
#[derive(Clone)]
pub struct ExecutionHandle {
    inner: Arc<ExecutionInner>,
}

struct ExecutionInner {
    id: String,
    task: String,
    project_root: String,
    config: ExecutionConfig,

    // State
    state: RwLock<ExecutionState>,
    current_iteration: RwLock<i32>,
    current_score: RwLock<f32>,
    started_at: chrono::DateTime<Utc>,
    ended_at: RwLock<Option<chrono::DateTime<Utc>>>,
    termination_reason: RwLock<Option<String>>,

    // Evidence tracking
    evidence: RwLock<EvidenceSummary>,

    // Event streaming
    event_tx: broadcast::Sender<AgentEvent>,
    event_history: RwLock<Vec<AgentEvent>>,

    // Process management (kept for future process lifecycle management)
    #[allow(dead_code)]
    process: RwLock<Option<Child>>,
    _metrics_watcher: RwLock<Option<MetricsWatcher>>,
}

impl Execution {
    pub fn new(
        id: String,
        task: String,
        project_root: String,
        config: ExecutionConfig,
    ) -> Self {
        Self {
            id,
            task,
            project_root,
            config,
        }
    }

    pub async fn start(self) -> Result<ExecutionHandle> {
        let (event_tx, _) = broadcast::channel(1024);

        let inner = Arc::new(ExecutionInner {
            id: self.id.clone(),
            task: self.task.clone(),
            project_root: self.project_root.clone(),
            config: self.config.clone(),
            state: RwLock::new(ExecutionState::Pending),
            current_iteration: RwLock::new(0),
            current_score: RwLock::new(0.0),
            started_at: Utc::now(),
            ended_at: RwLock::new(None),
            termination_reason: RwLock::new(None),
            evidence: RwLock::new(EvidenceSummary::default()),
            event_tx: event_tx.clone(),
            event_history: RwLock::new(Vec::new()),
            process: RwLock::new(None),
            _metrics_watcher: RwLock::new(None),
        });

        let handle = ExecutionHandle {
            inner: inner.clone(),
        };

        // Spawn the execution in background
        let inner_clone = inner.clone();
        tokio::spawn(async move {
            let inner_for_error = inner_clone.clone();
            if let Err(e) = inner_clone.run_execution().await {
                error!(execution_id = %inner_for_error.id, error = %e, "Execution failed");
                *inner_for_error.state.write() = ExecutionState::Failed;
                *inner_for_error.termination_reason.write() = Some(e.to_string());
            }
        });

        Ok(handle)
    }
}

/// Truncate a string to at most `max_chars` Unicode characters, appending '…'
/// if truncated. Safe for multi-byte UTF-8 (never slices mid-character).
fn truncate_str(s: &str, max_chars: usize) -> String {
    match s.char_indices().nth(max_chars) {
        Some((idx, _)) => format!("{}…", &s[..idx]),
        None => s.to_string(),
    }
}

impl ExecutionInner {
    async fn run_execution(self: Arc<Self>) -> Result<()> {
        info!(execution_id = %self.id, task = %self.task, "Starting execution");

        *self.state.write() = ExecutionState::Running;

        // Emit state change event
        self.emit_event(AgentEvent {
            execution_id: self.id.clone(),
            timestamp: Self::now_timestamp(),
            event: Some(agent_event::Event::StateChanged(StateChanged {
                old_state: ExecutionState::Pending as i32,
                new_state: ExecutionState::Running as i32,
                reason: "Execution started".to_string(),
            })),
        });

        // Find claude CLI
        let claude_path = which::which("claude")
            .context("claude CLI not found in PATH")?;

        // Build the command — use stream-json for structured output parsing
        let mut cmd = Command::new(&claude_path);
        cmd.arg("--print")
            .arg("--verbose")
            .arg("--output-format").arg("stream-json")
            .arg("--dangerously-skip-permissions")
            .arg("--model").arg(&self.config.model)
            .arg(&self.task)
            .current_dir(&self.project_root)
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::piped());

        // Set environment for SuperClaude configuration
        cmd.env("SUPERCLAUDE_EXECUTION_ID", &self.id);
        cmd.env("SUPERCLAUDE_MAX_ITERATIONS", self.config.max_iterations.to_string());
        cmd.env("SUPERCLAUDE_QUALITY_THRESHOLD", self.config.quality_threshold.to_string());
        cmd.env("SUPERCLAUDE_MODEL", &self.config.model);

        info!(
            execution_id = %self.id,
            claude_path = %claude_path.display(),
            project_root = %self.project_root,
            "Spawning claude CLI"
        );

        // Spawn the process
        let mut child = cmd.spawn().context("Failed to spawn claude CLI")?;

        // Set up metrics watcher for .superclaude_metrics/
        let metrics_path = PathBuf::from(&self.project_root).join(".superclaude_metrics");
        if metrics_path.exists() || std::fs::create_dir_all(&metrics_path).is_ok() {
            match MetricsWatcher::new(
                metrics_path,
                self.id.clone(),
                self.event_tx.clone(),
            ) {
                Ok(watcher) => {
                    *self._metrics_watcher.write() = Some(watcher);
                }
                Err(e) => {
                    warn!(error = %e, "Failed to start metrics watcher");
                }
            }
        }

        // Read stdout for structured JSON progress events
        if let Some(stdout) = child.stdout.take() {
            let inner = self.clone();
            tokio::spawn(async move {
                let reader = BufReader::new(stdout);
                let mut lines = reader.lines();

                while let Ok(Some(line)) = lines.next_line().await {
                    debug!(execution_id = %inner.id, len = line.len(), "claude stdout line");
                    inner.parse_stream_json_line(&line);
                }
            });
        }

        // Read stderr for errors
        if let Some(stderr) = child.stderr.take() {
            let inner = self.clone();
            tokio::spawn(async move {
                let reader = BufReader::new(stderr);
                let mut lines = reader.lines();

                while let Ok(Some(line)) = lines.next_line().await {
                    warn!(execution_id = %inner.id, line = %line, "claude stderr");
                }
            });
        }

        // Wait for completion
        let exit_status = child.wait().await?;

        // Update final state
        *self.ended_at.write() = Some(Utc::now());

        if exit_status.success() {
            *self.state.write() = ExecutionState::Completed;
            *self.termination_reason.write() = Some("Execution completed successfully".to_string());
        } else {
            *self.state.write() = ExecutionState::Failed;
            *self.termination_reason.write() = Some(format!(
                "Process exited with code: {:?}",
                exit_status.code()
            ));
        }

        // Emit completion event
        self.emit_event(AgentEvent {
            execution_id: self.id.clone(),
            timestamp: Self::now_timestamp(),
            event: Some(agent_event::Event::StateChanged(StateChanged {
                old_state: ExecutionState::Running as i32,
                new_state: *self.state.read() as i32,
                reason: self.termination_reason.read().clone().unwrap_or_default(),
            })),
        });

        info!(
            execution_id = %self.id,
            final_state = ?*self.state.read(),
            "Execution finished"
        );

        Ok(())
    }

    // -----------------------------------------------------------------------
    // Stream-JSON parsing
    // -----------------------------------------------------------------------

    fn parse_stream_json_line(&self, line: &str) {
        let trimmed = line.trim();
        if trimmed.is_empty() || !trimmed.starts_with('{') {
            return;
        }

        let event: StreamJsonEvent = match serde_json::from_str(trimmed) {
            Ok(e) => e,
            Err(e) => {
                debug!(error = %e, "Skipping non-JSON or unrecognised line");
                return;
            }
        };

        match event.event_type.as_str() {
            "system" => self.handle_system_event(&event),
            "assistant" => self.handle_assistant_event(&event),
            "user" => self.handle_user_event(&event),
            "result" => self.handle_result_event(&event),
            other => {
                debug!(event_type = other, "Ignoring unknown stream-json event type");
            }
        }
    }

    fn handle_system_event(&self, event: &StreamJsonEvent) {
        if event.subtype.as_deref() == Some("init") {
            self.emit_event(AgentEvent {
                execution_id: self.id.clone(),
                timestamp: Self::now_timestamp(),
                event: Some(agent_event::Event::LogMessage(LogMessage {
                    level: LogLevel::Info as i32,
                    message: "Claude session initialised".to_string(),
                    source: "claude-cli".to_string(),
                })),
            });
        }
    }

    fn handle_assistant_event(&self, event: &StreamJsonEvent) {
        let message = match &event.message {
            Some(m) => m,
            None => return,
        };

        // Each assistant message counts as one turn
        let iteration = {
            let mut iter = self.current_iteration.write();
            *iter += 1;
            *iter
        };

        let node_id = format!("iter-{}", iteration);

        self.emit_event(AgentEvent {
            execution_id: self.id.clone(),
            timestamp: Self::now_timestamp(),
            event: Some(agent_event::Event::IterationStarted(IterationStarted {
                iteration,
                depth: 0,
                node_id: node_id.clone(),
            })),
        });

        for block in &message.content {
            match block {
                ContentBlock::ToolUse { id, name, input } => {
                    self.handle_tool_use(id, name, input, &node_id);
                }
                ContentBlock::Text { text } => {
                    let truncated = truncate_str(text, 200);
                    self.emit_event(AgentEvent {
                        execution_id: self.id.clone(),
                        timestamp: Self::now_timestamp(),
                        event: Some(agent_event::Event::LogMessage(LogMessage {
                            level: LogLevel::Info as i32,
                            message: truncated,
                            source: "assistant".to_string(),
                        })),
                    });
                }
                ContentBlock::ToolResult { content, .. } => {
                    // Extract text from inline tool results for test detection
                    if let Some(serde_json::Value::String(text)) = content {
                        self.try_detect_test_results(text);
                    } else if let Some(serde_json::Value::Array(arr)) = content {
                        for item in arr {
                            if let Some(text) = item.get("text").and_then(|t| t.as_str()) {
                                self.try_detect_test_results(text);
                            }
                        }
                    }
                }
                ContentBlock::Unknown => {}
            }
        }
    }

    fn handle_tool_use(
        &self,
        id: &str,
        name: &str,
        input: &serde_json::Value,
        parent_node_id: &str,
    ) {
        let node_id = id.to_string();
        let file_path = input
            .get("file_path")
            .or_else(|| input.get("path"))
            .or_else(|| input.get("pattern"))
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string();

        let summary = if file_path.is_empty() {
            format!("{name}")
        } else {
            format!("{name}: {file_path}")
        };

        // Emit ToolInvoked for every tool
        self.emit_event(AgentEvent {
            execution_id: self.id.clone(),
            timestamp: Self::now_timestamp(),
            event: Some(agent_event::Event::ToolInvoked(ToolInvoked {
                tool_name: name.to_string(),
                summary: summary.clone(),
                blocked: false,
                block_reason: String::new(),
                depth: 1,
                node_id: node_id.clone(),
                parent_node_id: parent_node_id.to_string(),
            })),
        });

        // Emit file-change / evidence updates per tool type
        match name {
            "Write" => {
                if !file_path.is_empty() {
                    self.emit_event(AgentEvent {
                        execution_id: self.id.clone(),
                        timestamp: Self::now_timestamp(),
                        event: Some(agent_event::Event::FileChanged(FileChanged {
                            path: file_path.clone(),
                            action: FileAction::Write as i32,
                            lines_added: 0,
                            lines_removed: 0,
                            node_id: node_id.clone(),
                        })),
                    });
                    let mut ev = self.evidence.write();
                    if !ev.files_written.contains(&file_path) {
                        ev.files_written.push(file_path);
                    }
                }
            }
            "Edit" => {
                if !file_path.is_empty() {
                    self.emit_event(AgentEvent {
                        execution_id: self.id.clone(),
                        timestamp: Self::now_timestamp(),
                        event: Some(agent_event::Event::FileChanged(FileChanged {
                            path: file_path.clone(),
                            action: FileAction::Edit as i32,
                            lines_added: 0,
                            lines_removed: 0,
                            node_id: node_id.clone(),
                        })),
                    });
                    let mut ev = self.evidence.write();
                    if !ev.files_edited.contains(&file_path) {
                        ev.files_edited.push(file_path);
                    }
                }
            }
            "Read" | "Glob" | "Grep" => {
                if !file_path.is_empty() {
                    self.emit_event(AgentEvent {
                        execution_id: self.id.clone(),
                        timestamp: Self::now_timestamp(),
                        event: Some(agent_event::Event::FileChanged(FileChanged {
                            path: file_path,
                            action: FileAction::Read as i32,
                            lines_added: 0,
                            lines_removed: 0,
                            node_id: node_id.clone(),
                        })),
                    });
                }
            }
            "Bash" => {
                self.evidence.write().commands_run += 1;
            }
            _ => {
                // Other tools (Task, WebFetch, etc.) — already covered by ToolInvoked
            }
        }
    }

    fn handle_user_event(&self, event: &StreamJsonEvent) {
        // User events carry tool_use_result payloads
        if let Some(result) = &event.tool_use_result {
            // Check for file mutations in the result
            if let Some(result_type) = result.get("type").and_then(|t| t.as_str()) {
                if let Some(path) = result.get("path").and_then(|p| p.as_str()) {
                    let path_string = path.to_string();
                    let mut ev = self.evidence.write();
                    match result_type {
                        "create" => {
                            if !ev.files_written.contains(&path_string) {
                                ev.files_written.push(path_string);
                            }
                        }
                        "update" => {
                            if !ev.files_edited.contains(&path_string) {
                                ev.files_edited.push(path_string);
                            }
                        }
                        _ => {}
                    }
                }
            }

            // Extract text content for test-result detection
            if let Some(text) = result.get("content").and_then(|c| c.as_str()) {
                self.try_detect_test_results(text);
            } else if let Some(arr) = result.get("content").and_then(|c| c.as_array()) {
                for item in arr {
                    if let Some(text) = item.get("text").and_then(|t| t.as_str()) {
                        self.try_detect_test_results(text);
                    }
                }
            }
        }

        // Also inspect the message content blocks if present
        if let Some(message) = &event.message {
            for block in &message.content {
                if let ContentBlock::ToolResult { content, .. } = block {
                    if let Some(serde_json::Value::String(text)) = content {
                        self.try_detect_test_results(text);
                    } else if let Some(serde_json::Value::Array(arr)) = content {
                        for item in arr {
                            if let Some(text) = item.get("text").and_then(|t| t.as_str()) {
                                self.try_detect_test_results(text);
                            }
                        }
                    }
                }
            }
        }
    }

    fn try_detect_test_results(&self, output: &str) {
        // pytest: "X passed, Y failed, Z skipped" or "X passed"
        if let Some((framework, passed, failed, skipped)) = Self::parse_pytest_summary(output)
            .or_else(|| Self::parse_cargo_test_summary(output))
        {
            let mut ev = self.evidence.write();
            ev.tests_run = true;
            ev.tests_passed = passed;
            ev.tests_failed = failed;
            drop(ev); // release lock before emit

            self.emit_event(AgentEvent {
                execution_id: self.id.clone(),
                timestamp: Self::now_timestamp(),
                event: Some(agent_event::Event::TestResult(TestResult {
                    framework,
                    passed,
                    failed,
                    skipped,
                    coverage_percent: 0.0,
                    failed_tests: vec![],
                    node_id: format!("test-{}", Uuid::new_v4()),
                })),
            });
        }
    }

    /// Parse pytest summary: "X passed", "X passed, Y failed", "X passed, Y failed, Z skipped"
    fn parse_pytest_summary(output: &str) -> Option<(String, i32, i32, i32)> {
        // Look for "N passed" anywhere in the output
        let passed_idx = output.find(" passed")?;
        // Extract the number immediately before " passed" by splitting on non-digit chars
        let before = &output[..passed_idx];
        let num_str = before.rsplit(|c: char| !c.is_ascii_digit()).next().unwrap_or("");
        let passed: i32 = num_str.parse().ok()?;

        let rest = &output[passed_idx..];
        let mut failed: i32 = 0;
        let mut skipped: i32 = 0;

        if let Some(fi) = rest.find(" failed") {
            let seg = &rest[..fi];
            if let Some(comma_pos) = seg.rfind(", ") {
                let num_str = seg[comma_pos + 2..].trim();
                failed = num_str.parse().unwrap_or(0);
            }
        }
        if let Some(si) = rest.find(" skipped") {
            let seg = &rest[..si];
            if let Some(comma_pos) = seg.rfind(", ") {
                let num_str = seg[comma_pos + 2..].trim();
                skipped = num_str.parse().unwrap_or(0);
            }
        }

        Some(("pytest".to_string(), passed, failed, skipped))
    }

    /// Parse cargo test summary: "test result: ok. X passed; Y failed; Z ignored"
    fn parse_cargo_test_summary(output: &str) -> Option<(String, i32, i32, i32)> {
        let marker = "test result:";
        let idx = output.find(marker)?;
        let rest = &output[idx + marker.len()..];

        // Skip "ok." or "FAILED."
        let dot_idx = rest.find('.')?;
        let stats = &rest[dot_idx + 1..];

        let mut passed: i32 = 0;
        let mut failed: i32 = 0;
        let mut ignored: i32 = 0;

        for part in stats.split(';') {
            let part = part.trim();
            if part.ends_with("passed") {
                passed = part.split_whitespace().next()?.parse().ok()?;
            } else if part.ends_with("failed") {
                failed = part.split_whitespace().next()?.parse().ok()?;
            } else if part.ends_with("ignored") {
                ignored = part.split_whitespace().next()?.parse().ok()?;
            }
        }

        // Only return if we actually parsed something
        if passed > 0 || failed > 0 || ignored > 0 {
            Some(("cargo".to_string(), passed, failed, ignored))
        } else {
            None
        }
    }

    fn handle_result_event(&self, event: &StreamJsonEvent) {
        let num_turns = event.num_turns.unwrap_or(0);
        let is_error = event.is_error.unwrap_or(false);
        let cost = event.total_cost_usd.unwrap_or(0.0);
        let duration_ms = event.duration_ms.unwrap_or(0.0);

        // Log the result summary
        let result_text = event.result.as_deref().unwrap_or("");
        let truncated = truncate_str(result_text, 300);

        if !truncated.is_empty() {
            self.emit_event(AgentEvent {
                execution_id: self.id.clone(),
                timestamp: Self::now_timestamp(),
                event: Some(agent_event::Event::LogMessage(LogMessage {
                    level: if is_error { LogLevel::Error as i32 } else { LogLevel::Info as i32 },
                    message: truncated,
                    source: "result".to_string(),
                })),
            });
        }

        // Compute a heuristic score from evidence
        let score = self.compute_heuristic_score();
        let old_score = *self.current_score.read();
        *self.current_score.write() = score;

        // Emit final iteration completed
        let iteration = *self.current_iteration.read();
        self.emit_event(AgentEvent {
            execution_id: self.id.clone(),
            timestamp: Self::now_timestamp(),
            event: Some(agent_event::Event::IterationCompleted(IterationCompleted {
                iteration,
                score,
                improvements: vec![
                    format!("turns={num_turns}"),
                    format!("cost=${cost:.4}"),
                    format!("duration={duration_ms:.0}ms"),
                ],
                dimensions: None,
                duration_seconds: (duration_ms / 1000.0) as f32,
                node_id: format!("iter-{}", iteration),
            })),
        });

        // Emit score update (single read lock for atomicity)
        let score_reason = {
            let ev = self.evidence.read();
            format!(
                "Heuristic: {} files, {} cmds, tests_run={}",
                ev.files_written.len() + ev.files_edited.len(),
                ev.commands_run,
                ev.tests_run,
            )
        };
        self.emit_event(AgentEvent {
            execution_id: self.id.clone(),
            timestamp: Self::now_timestamp(),
            event: Some(agent_event::Event::ScoreUpdated(ScoreUpdated {
                old_score,
                new_score: score,
                reason: score_reason,
                dimensions: None,
            })),
        });

        info!(
            execution_id = %self.id,
            turns = num_turns,
            cost_usd = cost,
            score = score,
            is_error = is_error,
            "Execution result received"
        );
    }

    /// Evidence-based heuristic score (0–100).
    fn compute_heuristic_score(&self) -> f32 {
        let ev = self.evidence.read();
        let mut score: f32 = 0.0;

        // Files produced: +30 base if any, +5 per file (max +20 extra) → up to 50
        let file_count = (ev.files_written.len() + ev.files_edited.len()) as f32;
        if file_count > 0.0 {
            score += 30.0;
            score += (file_count * 5.0).min(20.0);
        }

        // Tests run: +10, all pass: +10 more → up to 20
        if ev.tests_run {
            score += 10.0;
            if ev.tests_failed == 0 && ev.tests_passed > 0 {
                score += 10.0;
            }
        }

        // Commands run: +2 per command (max +10) → up to 10
        score += (ev.commands_run as f32 * 2.0).min(10.0);

        // Completion bonus: +20 when files were produced and tests passed
        if file_count > 0.0 && ev.tests_run && ev.tests_failed == 0 && ev.tests_passed > 0 {
            score += 20.0;
        }

        score.min(100.0)
    }

    fn emit_event(&self, event: AgentEvent) {
        // Store in history
        self.event_history.write().push(event.clone());

        // Broadcast to subscribers (ignore errors if no receivers)
        let _ = self.event_tx.send(event);
    }

    fn now_timestamp() -> Option<Timestamp> {
        let now = Utc::now();
        Some(Timestamp {
            seconds: now.timestamp(),
            nanos: now.timestamp_subsec_nanos() as i32,
        })
    }
}

impl ExecutionHandle {
    pub fn state(&self) -> ExecutionState {
        *self.inner.state.read()
    }

    pub async fn stop(&self, force: bool) {
        info!(execution_id = %self.inner.id, force = force, "Stopping execution");
        *self.inner.state.write() = ExecutionState::Cancelled;
        *self.inner.termination_reason.write() = Some("Stopped by user".to_string());
    }

    pub async fn pause(&self) {
        *self.inner.state.write() = ExecutionState::Paused;
    }

    pub async fn resume(&self) {
        *self.inner.state.write() = ExecutionState::Running;
    }

    pub async fn get_status(&self) -> ExecutionStatus {
        ExecutionStatus {
            execution_id: self.inner.id.clone(),
            task: self.inner.task.clone(),
            state: *self.inner.state.read() as i32,
            current_iteration: *self.inner.current_iteration.read(),
            max_iterations: self.inner.config.max_iterations,
            current_score: *self.inner.current_score.read(),
            quality_threshold: self.inner.config.quality_threshold,
            termination_reason: self.inner.termination_reason.read().clone().unwrap_or_default(),
            evidence: Some(self.inner.evidence.read().clone()),
            started_at: Some(Timestamp {
                seconds: self.inner.started_at.timestamp(),
                nanos: self.inner.started_at.timestamp_subsec_nanos() as i32,
            }),
            ended_at: self.inner.ended_at.read().map(|dt| Timestamp {
                seconds: dt.timestamp(),
                nanos: dt.timestamp_subsec_nanos() as i32,
            }),
        }
    }

    pub fn to_summary(&self) -> ExecutionSummary {
        ExecutionSummary {
            execution_id: self.inner.id.clone(),
            task: self.inner.task.clone(),
            state: *self.inner.state.read() as i32,
            current_iteration: *self.inner.current_iteration.read(),
            current_score: *self.inner.current_score.read(),
            started_at: Some(Timestamp {
                seconds: self.inner.started_at.timestamp(),
                nanos: self.inner.started_at.timestamp_subsec_nanos() as i32,
            }),
        }
    }

    pub fn subscribe_events(&self) -> broadcast::Receiver<AgentEvent> {
        self.inner.event_tx.subscribe()
    }

    pub fn get_event_history(&self) -> Vec<AgentEvent> {
        self.inner.event_history.read().clone()
    }
}
