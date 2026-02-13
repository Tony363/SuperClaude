//! Execution management - spawns and monitors claude CLI processes

use std::collections::{HashMap, VecDeque};
use std::path::PathBuf;
use std::process::Stdio;
use std::sync::{Arc, LazyLock};

use anyhow::{Context, Result};
use chrono::Utc;
use parking_lot::RwLock;
use prost_types::Timestamp;
use regex::Regex;
use serde::Deserialize;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::process::Command;
use tokio::sync::broadcast;
use tracing::{debug, error, info, warn};
use uuid::Uuid;

use crate::metrics_watcher::MetricsWatcher;
use superclaude_proto::*;

// Compiled regex patterns for test output parsing
static PYTEST_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"(\d+) passed(?:,\s*(\d+) failed)?(?:,\s*(\d+) (?:skipped|deselected))?")
        .unwrap()
});
static CARGO_TEST_RE: LazyLock<Regex> = LazyLock::new(|| {
    Regex::new(r"test result:\s*(?:ok|FAILED)\.\s+(\d+) passed;\s+(\d+) failed;\s+(\d+) ignored")
        .unwrap()
});

/// Maximum number of events retained in history to prevent unbounded memory growth.
const MAX_EVENT_HISTORY: usize = 5_000;

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

/// Tracks a pending tool use for correlation with its result.
struct PendingToolUse {
    tool_name: String,
    tool_input: String,
    node_id: String,
    parent_node_id: String,
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

    // Telemetry tracking
    total_cost_usd: RwLock<f64>,
    total_input_tokens: RwLock<u64>,
    total_output_tokens: RwLock<u64>,
    pending_tool_uses: RwLock<HashMap<String, PendingToolUse>>,
    run_instructions: RwLock<Option<RunInstructions>>,

    // JSONL persistence
    jsonl_writer: RwLock<Option<std::io::BufWriter<std::fs::File>>>,

    // Event streaming
    event_tx: broadcast::Sender<AgentEvent>,
    event_history: RwLock<VecDeque<AgentEvent>>,

    // Process management — stores the PID for lifecycle control (kill on stop).
    // The Child itself stays local to run_execution() for await-safe waiting.
    process_pid: RwLock<Option<u32>>,
    /// Piped stdin handle for interactive input via SendInput RPC.
    child_stdin: tokio::sync::RwLock<Option<tokio::process::ChildStdin>>,
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
            total_cost_usd: RwLock::new(0.0),
            total_input_tokens: RwLock::new(0),
            total_output_tokens: RwLock::new(0),
            pending_tool_uses: RwLock::new(HashMap::new()),
            run_instructions: RwLock::new(None),
            jsonl_writer: RwLock::new(None),
            event_tx: event_tx.clone(),
            event_history: RwLock::new(VecDeque::new()),
            process_pid: RwLock::new(None),
            child_stdin: tokio::sync::RwLock::new(None),
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
            .arg("--permission-mode").arg("bypassPermissions")
            .arg("--no-session-persistence")
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

        // Store the PID for lifecycle control (used by stop() to kill the process)
        if let Some(pid) = child.id() {
            *self.process_pid.write() = Some(pid);
        }

        // Set up metrics watcher and JSONL writer for .superclaude_metrics/
        let metrics_path = PathBuf::from(&self.project_root).join(".superclaude_metrics");
        if metrics_path.exists() || std::fs::create_dir_all(&metrics_path).is_ok() {
            // Initialize JSONL writer
            let jsonl_path = metrics_path.join("events.jsonl");
            match std::fs::OpenOptions::new()
                .create(true)
                .append(true)
                .open(&jsonl_path)
            {
                Ok(file) => {
                    *self.jsonl_writer.write() = Some(std::io::BufWriter::new(file));
                }
                Err(e) => {
                    warn!(error = %e, "Failed to open JSONL writer");
                }
            }

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
                    info!(execution_id = %inner.id, len = line.len(), "claude stdout line");
                    inner.parse_stream_json_line(&line);
                }
            });
        }

        // Read stderr for errors — accumulate into buffer for failure reporting
        // and emit ErrorOccurred events for the frontend.
        let stderr_buffer: Arc<RwLock<Vec<String>>> = Arc::new(RwLock::new(Vec::new()));
        if let Some(stderr) = child.stderr.take() {
            let inner = self.clone();
            let stderr_buf = stderr_buffer.clone();
            tokio::spawn(async move {
                let reader = BufReader::new(stderr);
                let mut lines = reader.lines();
                let mut batch: Vec<String> = Vec::new();
                let mut last_emit = tokio::time::Instant::now();

                loop {
                    let line_result = tokio::time::timeout(
                        std::time::Duration::from_millis(500),
                        lines.next_line(),
                    ).await;

                    match line_result {
                        Ok(Ok(Some(line))) => {
                            debug!(execution_id = %inner.id, line = %line, "claude stderr");
                            // Always buffer for failure reporting on process exit
                            stderr_buf.write().push(line.clone());
                            // Only batch lines that look like real errors for ErrorOccurred events
                            let lower = line.to_lowercase();
                            if lower.contains("error") || lower.contains("panic") || lower.contains("fatal") {
                                warn!(execution_id = %inner.id, line = %line, "claude stderr error");
                                batch.push(line);
                            }
                        }
                        Ok(Ok(None)) => {
                            // EOF — flush remaining batch
                            if !batch.is_empty() {
                                let msg = truncate_str(&batch.join("\n"), 1000);
                                inner.emit_event(AgentEvent {
                                    execution_id: inner.id.clone(),
                                    timestamp: Self::now_timestamp(),
                                    event: Some(agent_event::Event::Error(ErrorOccurred {
                                        error_type: "stderr".to_string(),
                                        message: msg,
                                        traceback: String::new(),
                                        recoverable: true,
                                    })),
                                });
                            }
                            break;
                        }
                        Ok(Err(_)) => break,
                        Err(_) => {
                            // Timeout — flush batch if non-empty
                        }
                    }

                    // Flush batch when >=5 lines accumulated or 500ms elapsed
                    if batch.len() >= 5 || (!batch.is_empty() && last_emit.elapsed() >= std::time::Duration::from_millis(500)) {
                        let msg = truncate_str(&batch.join("\n"), 1000);
                        inner.emit_event(AgentEvent {
                            execution_id: inner.id.clone(),
                            timestamp: Self::now_timestamp(),
                            event: Some(agent_event::Event::Error(ErrorOccurred {
                                error_type: "stderr".to_string(),
                                message: msg,
                                traceback: String::new(),
                                recoverable: true,
                            })),
                        });
                        batch.clear();
                        last_emit = tokio::time::Instant::now();
                    }
                }
            });
        }

        // Heartbeat task — emits periodic "Processing..." events so the UI
        // knows the execution is alive between tool calls.
        let heartbeat_handle = {
            let inner = self.clone();
            tokio::spawn(async move {
                let mut interval = tokio::time::interval(std::time::Duration::from_secs(5));
                loop {
                    interval.tick().await;
                    if *inner.state.read() != ExecutionState::Running {
                        break;
                    }
                    inner.emit_event(AgentEvent {
                        execution_id: inner.id.clone(),
                        timestamp: Self::now_timestamp(),
                        event: Some(agent_event::Event::LogMessage(LogMessage {
                            level: LogLevel::Debug as i32,
                            message: "Processing...".to_string(),
                            source: "heartbeat".to_string(),
                        })),
                    });
                }
            })
        };

        // Wait for completion
        let exit_status = child.wait().await?;

        // Stop the heartbeat
        heartbeat_handle.abort();

        // Clear stored PID
        *self.process_pid.write() = None;

        // Update final state
        *self.ended_at.write() = Some(Utc::now());

        if exit_status.success() {
            *self.state.write() = ExecutionState::Completed;
            *self.termination_reason.write() = Some("Execution completed successfully".to_string());
        } else {
            *self.state.write() = ExecutionState::Failed;
            // Only set termination_reason if handle_result_event() didn't already
            // populate it with the actual error text from stream-json output.
            if self.termination_reason.read().is_none() {
                let stderr_lines = stderr_buffer.read().join("\n");
                let reason = if stderr_lines.is_empty() {
                    format!("Process exited with code: {:?}", exit_status.code())
                } else {
                    format!(
                        "Process exited with code: {:?}. stderr: {}",
                        exit_status.code(),
                        truncate_str(&stderr_lines, 500)
                    )
                };
                *self.termination_reason.write() = Some(reason);
            }
        }

        // Flush JSONL writer
        if let Some(ref mut writer) = *self.jsonl_writer.write() {
            use std::io::Write;
            let _ = writer.flush();
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
                warn!(error = %e, "Skipping non-JSON or unrecognised line");
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

        // Accumulate token usage
        if let Some(usage) = &message.usage {
            *self.total_input_tokens.write() += usage.input_tokens;
            *self.total_output_tokens.write() += usage.output_tokens;
        }

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
                ContentBlock::ToolResult { tool_use_id, content } => {
                    // Correlate tool result with its invocation
                    if let Some(use_id) = tool_use_id {
                        self.correlate_tool_result(use_id, content);
                    }
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

        // Compute progressive score from accumulated evidence
        let score = self.compute_heuristic_score();
        let old_score = *self.current_score.read();

        if (score - old_score).abs() > f32::EPSILON {
            *self.current_score.write() = score;

            let quality_dims = self.compute_quality_breakdown();

            self.emit_event(AgentEvent {
                execution_id: self.id.clone(),
                timestamp: Self::now_timestamp(),
                event: Some(agent_event::Event::ScoreUpdated(ScoreUpdated {
                    old_score,
                    new_score: score,
                    reason: "Progressive evidence update".to_string(),
                    dimensions: Some(quality_dims),
                })),
            });
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

        // Enhanced summary for Bash commands
        let summary = if name == "Bash" {
            if let Some(cmd) = input.get("command").and_then(|v| v.as_str()) {
                format!("Bash: {}", truncate_str(cmd, 100))
            } else {
                "Bash".to_string()
            }
        } else if file_path.is_empty() {
            format!("{name}")
        } else {
            format!("{name}: {file_path}")
        };

        // Serialize full input for telemetry
        let tool_input = serde_json::to_string(input).unwrap_or_default();

        // Store pending tool use for correlation
        self.pending_tool_uses.write().insert(id.to_string(), PendingToolUse {
            tool_name: name.to_string(),
            tool_input: tool_input.clone(),
            node_id: node_id.clone(),
            parent_node_id: parent_node_id.to_string(),
        });

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
                tool_input,
                tool_output: String::new(),
                tool_use_id: id.to_string(),
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

                    // Detect Obsidian/markdown artifacts
                    if file_path.ends_with(".md") {
                        let fp = std::path::Path::new(&file_path);
                        let in_obsidian = fp.components().any(|c| {
                            let s = c.as_os_str().to_string_lossy();
                            s.contains("obsidian") || s.contains("vault") || s.contains(".superclaude_metrics")
                        });
                        if in_obsidian {
                            let title = fp.file_stem()
                                .map(|s| s.to_string_lossy().to_string())
                                .unwrap_or_default();
                            self.emit_event(AgentEvent {
                                execution_id: self.id.clone(),
                                timestamp: Self::now_timestamp(),
                                event: Some(agent_event::Event::ArtifactWritten(ArtifactWritten {
                                    obsidian_path: file_path.clone(),
                                    artifact_type: "document".to_string(),
                                    title,
                                })),
                            });
                        }
                    }

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
            "Task" => {
                let subagent_type = input
                    .get("subagent_type")
                    .and_then(|v| v.as_str())
                    .unwrap_or("unknown")
                    .to_string();
                let description = input
                    .get("description")
                    .and_then(|v| v.as_str())
                    .unwrap_or("")
                    .to_string();
                self.evidence.write().subagents_spawned += 1;
                self.emit_event(AgentEvent {
                    execution_id: self.id.clone(),
                    timestamp: Self::now_timestamp(),
                    event: Some(agent_event::Event::SubagentSpawned(SubagentSpawned {
                        subagent_id: id.to_string(),
                        subagent_type,
                        task_summary: description,
                        depth: 1,
                        node_id: format!("subagent-{}", id),
                        parent_node_id: parent_node_id.to_string(),
                    })),
                });
            }
            _ => {
                // Other tools (WebFetch, etc.) — already covered by ToolInvoked
            }
        }
    }

    /// Correlate a tool result with its pending invocation.
    fn correlate_tool_result(
        &self,
        tool_use_id: &str,
        content: &Option<serde_json::Value>,
    ) {
        let pending = self.pending_tool_uses.write().remove(tool_use_id);
        if let Some(pending) = pending {
            let tool_output = match content {
                Some(serde_json::Value::String(s)) => truncate_str(s, 2000),
                Some(serde_json::Value::Array(arr)) => {
                    let texts: Vec<String> = arr.iter()
                        .filter_map(|item| item.get("text").and_then(|t| t.as_str()).map(String::from))
                        .collect();
                    truncate_str(&texts.join("\n"), 2000)
                }
                _ => String::new(),
            };

            let is_task_tool = pending.tool_name == "Task";

            if !tool_output.is_empty() {
                self.emit_event(AgentEvent {
                    execution_id: self.id.clone(),
                    timestamp: Self::now_timestamp(),
                    event: Some(agent_event::Event::ToolInvoked(ToolInvoked {
                        tool_name: pending.tool_name,
                        summary: "(result)".to_string(),
                        blocked: false,
                        block_reason: String::new(),
                        depth: 1,
                        node_id: format!("{}-result", pending.node_id),
                        parent_node_id: pending.parent_node_id.clone(),
                        tool_input: pending.tool_input,
                        tool_output: tool_output.clone(),
                        tool_use_id: tool_use_id.to_string(),
                    })),
                });
            }

            // Emit SubagentCompleted when a Task tool result arrives
            if is_task_tool {
                self.emit_event(AgentEvent {
                    execution_id: self.id.clone(),
                    timestamp: Self::now_timestamp(),
                    event: Some(agent_event::Event::SubagentCompleted(SubagentCompleted {
                        subagent_id: pending.node_id.clone(),
                        success: true,
                        result_summary: truncate_str(&tool_output, 200),
                        node_id: format!("subagent-{}", pending.node_id),
                    })),
                });
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
        let caps = PYTEST_RE.captures(output)?;
        let passed: i32 = caps.get(1)?.as_str().parse().ok()?;
        let failed: i32 = caps.get(2).and_then(|m| m.as_str().parse().ok()).unwrap_or(0);
        let skipped: i32 = caps.get(3).and_then(|m| m.as_str().parse().ok()).unwrap_or(0);
        Some(("pytest".to_string(), passed, failed, skipped))
    }

    /// Parse cargo test summary: "test result: ok. X passed; Y failed; Z ignored"
    fn parse_cargo_test_summary(output: &str) -> Option<(String, i32, i32, i32)> {
        let caps = CARGO_TEST_RE.captures(output)?;
        let passed: i32 = caps.get(1)?.as_str().parse().ok()?;
        let failed: i32 = caps.get(2)?.as_str().parse().ok()?;
        let ignored: i32 = caps.get(3)?.as_str().parse().ok()?;
        Some(("cargo".to_string(), passed, failed, ignored))
    }

    fn handle_result_event(&self, event: &StreamJsonEvent) {
        let num_turns = event.num_turns.unwrap_or(0);
        let is_error = event.is_error.unwrap_or(false);
        let cost = event.total_cost_usd.unwrap_or(0.0);
        let duration_ms = event.duration_ms.unwrap_or(0.0);

        // Store cost
        *self.total_cost_usd.write() = cost;

        // Try to extract run instructions from result text
        let result_text = event.result.as_deref().unwrap_or("");
        self.try_extract_run_instructions(result_text);

        // If the result is an error, propagate the actual error text into
        // termination_reason so the dashboard shows the real message instead of
        // a generic "Process exited with code: Some(1)".
        if is_error && !result_text.is_empty() {
            *self.termination_reason.write() = Some(truncate_str(result_text, 500));
        }

        // Log the result summary (raised limit to 2000 chars)
        let truncated = truncate_str(result_text, 2000);

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

        // Build quality breakdown
        let quality_dims = self.compute_quality_breakdown();

        // Emit final iteration completed with telemetry
        let iteration = *self.current_iteration.read();
        let input_toks = *self.total_input_tokens.read();
        let output_toks = *self.total_output_tokens.read();
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
                dimensions: Some(quality_dims.clone()),
                duration_seconds: (duration_ms / 1000.0) as f32,
                node_id: format!("iter-{}", iteration),
                total_cost_usd: cost,
                input_tokens: input_toks as i64,
                output_tokens: output_toks as i64,
                num_turns,
            })),
        });

        // Emit score update with structured breakdown
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
                dimensions: Some(quality_dims),
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

    /// Try to extract run instructions from result text.
    fn try_extract_run_instructions(&self, text: &str) {
        if let Some(start) = text.find("{\"run_instructions\"") {
            let json_candidate = &text[start..];
            // Try parsing progressively larger chunks
            for end in (1..json_candidate.len()).rev() {
                if json_candidate.as_bytes().get(end) == Some(&b'}') {
                    if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(&json_candidate[..=end]) {
                        if let Some(ri) = parsed.get("run_instructions") {
                            let instructions = RunInstructions {
                                build_command: ri.get("build_command").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                                run_command: ri.get("run_command").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                                artifacts: ri.get("artifacts")
                                    .and_then(|v| v.as_array())
                                    .map(|arr| arr.iter().filter_map(|v| v.as_str().map(String::from)).collect())
                                    .unwrap_or_default(),
                                notes: ri.get("notes").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                            };
                            *self.run_instructions.write() = Some(instructions);
                            return;
                        }
                    }
                }
            }
        }
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

    /// Structured quality breakdown with per-dimension scores.
    fn compute_quality_breakdown(&self) -> QualityDimensions {
        let ev = self.evidence.read();
        let file_count = (ev.files_written.len() + ev.files_edited.len()) as f32;

        let files_score = if file_count > 0.0 {
            (30.0 + (file_count * 5.0).min(20.0)).min(50.0)
        } else {
            0.0
        };
        let tests_score = if ev.tests_run {
            if ev.tests_failed == 0 && ev.tests_passed > 0 { 20.0 } else { 10.0 }
        } else {
            0.0
        };
        let cmds_score = (ev.commands_run as f32 * 2.0).min(10.0);
        let completion_score = if file_count > 0.0 && ev.tests_run && ev.tests_failed == 0 && ev.tests_passed > 0 {
            20.0
        } else {
            0.0
        };

        QualityDimensions {
            code_changes: files_score / 50.0,
            tests_run: if ev.tests_run { 1.0 } else { 0.0 },
            tests_pass: if ev.tests_run && ev.tests_failed == 0 { 1.0 } else { 0.0 },
            coverage: 0.0,
            no_errors: if !ev.tests_run || ev.tests_failed == 0 { 1.0 } else { 0.0 },
            breakdown: vec![
                ScoreDimension {
                    name: "files_produced".to_string(),
                    score: files_score,
                    max_score: 50.0,
                    description: format!("{} files written/edited", file_count as i32),
                },
                ScoreDimension {
                    name: "tests".to_string(),
                    score: tests_score,
                    max_score: 20.0,
                    description: if ev.tests_run {
                        format!("{} passed, {} failed", ev.tests_passed, ev.tests_failed)
                    } else {
                        "No tests run".to_string()
                    },
                },
                ScoreDimension {
                    name: "commands".to_string(),
                    score: cmds_score,
                    max_score: 10.0,
                    description: format!("{} commands executed", ev.commands_run),
                },
                ScoreDimension {
                    name: "completion".to_string(),
                    score: completion_score,
                    max_score: 20.0,
                    description: if completion_score > 0.0 {
                        "Files produced + tests passing".to_string()
                    } else {
                        "Requires files + passing tests".to_string()
                    },
                },
            ],
        }
    }

    fn emit_event(&self, event: AgentEvent) {
        // Write to JSONL
        if let Some(ref mut writer) = *self.jsonl_writer.write() {
            use std::io::Write;
            if let Some(ref evt) = event.event {
                let json_line = match evt {
                    agent_event::Event::ToolInvoked(e) => serde_json::json!({
                        "execution_id": event.execution_id,
                        "event_type": "tool_invoked",
                        "tool_name": e.tool_name,
                        "summary": e.summary,
                        "tool_input": e.tool_input,
                        "tool_output": e.tool_output,
                        "tool_use_id": e.tool_use_id,
                    }),
                    agent_event::Event::IterationCompleted(e) => serde_json::json!({
                        "execution_id": event.execution_id,
                        "event_type": "iteration_completed",
                        "iteration": e.iteration,
                        "score": e.score,
                        "total_cost_usd": e.total_cost_usd,
                        "input_tokens": e.input_tokens,
                        "output_tokens": e.output_tokens,
                    }),
                    _ => serde_json::json!({
                        "execution_id": event.execution_id,
                        "event_type": "other",
                    }),
                };
                let _ = writeln!(writer, "{}", json_line);
            }
        }

        // Store in history with bounded size
        {
            let mut history = self.event_history.write();
            if history.len() >= MAX_EVENT_HISTORY {
                history.pop_front();
            }
            history.push_back(event.clone());
        }

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
        // Kill the child process via stored PID
        #[cfg(unix)]
        if let Some(pid) = *self.inner.process_pid.read() {
            let signal = if force { libc::SIGKILL } else { libc::SIGTERM };
            // Safety: sending a signal to a known PID is safe
            let ret = unsafe { libc::kill(pid as i32, signal) };
            if ret != 0 {
                let err = std::io::Error::last_os_error();
                warn!(execution_id = %self.inner.id, pid = pid, error = %err, "Failed to kill child process");
            }
        }
    }

    pub async fn pause(&self) {
        *self.inner.state.write() = ExecutionState::Paused;
    }

    pub async fn resume(&self) {
        *self.inner.state.write() = ExecutionState::Running;
    }

    /// Write input to the child process's stdin pipe.
    pub async fn send_input(&self, input: &str) -> Result<()> {
        let mut guard = self.inner.child_stdin.write().await;
        if let Some(ref mut stdin) = *guard {
            stdin.write_all(input.as_bytes()).await?;
            stdin.write_all(b"\n").await?;
            stdin.flush().await?;
            Ok(())
        } else {
            anyhow::bail!("stdin pipe not available (process may have exited)")
        }
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
            total_cost_usd: *self.inner.total_cost_usd.read(),
            total_input_tokens: *self.inner.total_input_tokens.read() as i64,
            total_output_tokens: *self.inner.total_output_tokens.read() as i64,
        }
    }

    pub fn to_summary(&self) -> ExecutionSummary {
        let duration = {
            let ended = self.inner.ended_at.read();
            match *ended {
                Some(end) => (end - self.inner.started_at).num_milliseconds() as f32 / 1000.0,
                None => (Utc::now() - self.inner.started_at).num_milliseconds() as f32 / 1000.0,
            }
        };

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
            total_cost_usd: *self.inner.total_cost_usd.read(),
            duration_seconds: duration,
            evidence: Some(self.inner.evidence.read().clone()),
        }
    }

    pub fn get_detail(&self) -> GetExecutionDetailResponse {
        let status = self.get_status_sync();
        let events = self.inner.event_history.read().iter().cloned().collect();
        let run_instructions = self.inner.run_instructions.read().clone();

        GetExecutionDetailResponse {
            status: Some(status),
            events,
            run_instructions,
        }
    }

    fn get_status_sync(&self) -> ExecutionStatus {
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
            total_cost_usd: *self.inner.total_cost_usd.read(),
            total_input_tokens: *self.inner.total_input_tokens.read() as i64,
            total_output_tokens: *self.inner.total_output_tokens.read() as i64,
        }
    }

    pub fn subscribe_events(&self) -> broadcast::Receiver<AgentEvent> {
        self.inner.event_tx.subscribe()
    }

    pub fn get_event_history(&self) -> Vec<AgentEvent> {
        self.inner.event_history.read().iter().cloned().collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // -- truncate_str tests --

    #[test]
    fn test_truncate_str_short() {
        assert_eq!(truncate_str("hello", 10), "hello");
    }

    #[test]
    fn test_truncate_str_exact() {
        assert_eq!(truncate_str("hello", 5), "hello");
    }

    #[test]
    fn test_truncate_str_long() {
        let result = truncate_str("hello world", 5);
        assert_eq!(result, "hello…");
    }

    #[test]
    fn test_truncate_str_unicode() {
        // "café" is 4 chars; truncating at 3 should give "caf…"
        let result = truncate_str("caf\u{00e9}", 3);
        assert_eq!(result, "caf…");
        // Emoji: "hi🎉bye" — 7 chars, truncate at 4 should give "hi🎉b…"
        let result = truncate_str("hi\u{1f389}bye", 4);
        assert_eq!(result, "hi\u{1f389}b…");
    }

    // -- pytest parsing tests --

    #[test]
    fn test_parse_pytest_basic() {
        let output = "====== 5 passed in 1.23s ======";
        let result = ExecutionInner::parse_pytest_summary(output);
        assert_eq!(result, Some(("pytest".to_string(), 5, 0, 0)));
    }

    #[test]
    fn test_parse_pytest_with_failures() {
        let output = "====== 3 passed, 2 failed in 4.56s ======";
        let result = ExecutionInner::parse_pytest_summary(output);
        assert_eq!(result, Some(("pytest".to_string(), 3, 2, 0)));
    }

    #[test]
    fn test_parse_pytest_with_skipped() {
        let output = "====== 10 passed, 1 failed, 3 skipped in 2.00s ======";
        let result = ExecutionInner::parse_pytest_summary(output);
        assert_eq!(result, Some(("pytest".to_string(), 10, 1, 3)));
    }

    #[test]
    fn test_parse_pytest_deselected() {
        let output = "====== 8 passed, 2 deselected in 0.50s ======";
        let result = ExecutionInner::parse_pytest_summary(output);
        assert_eq!(result, Some(("pytest".to_string(), 8, 0, 2)));
    }

    #[test]
    fn test_parse_pytest_no_match() {
        let output = "some random output with no test results";
        assert_eq!(ExecutionInner::parse_pytest_summary(output), None);
    }

    #[test]
    fn test_parse_pytest_does_not_match_test_names() {
        // A test named "test_something_passed" should not trigger a false positive
        let output = "FAILED test_something_passed - AssertionError";
        assert_eq!(ExecutionInner::parse_pytest_summary(output), None);
    }

    // -- cargo test parsing tests --

    #[test]
    fn test_parse_cargo_basic() {
        let output = "test result: ok. 10 passed; 0 failed; 0 ignored; 0 measured; 0 filtered out";
        let result = ExecutionInner::parse_cargo_test_summary(output);
        assert_eq!(result, Some(("cargo".to_string(), 10, 0, 0)));
    }

    #[test]
    fn test_parse_cargo_with_failures() {
        let output = "test result: FAILED. 8 passed; 2 failed; 1 ignored; 0 measured";
        let result = ExecutionInner::parse_cargo_test_summary(output);
        assert_eq!(result, Some(("cargo".to_string(), 8, 2, 1)));
    }

    #[test]
    fn test_parse_cargo_no_match() {
        let output = "running 5 tests";
        assert_eq!(ExecutionInner::parse_cargo_test_summary(output), None);
    }

    // -- heuristic score tests --

    fn make_inner_with_evidence(evidence: EvidenceSummary) -> Arc<ExecutionInner> {
        let (tx, _) = broadcast::channel(16);
        Arc::new(ExecutionInner {
            id: "test-id".to_string(),
            task: "test task".to_string(),
            project_root: "/tmp".to_string(),
            config: ExecutionConfig {
                max_iterations: 3,
                quality_threshold: 70.0,
                model: "sonnet".to_string(),
                timeout_seconds: 300.0,
                pal_review_enabled: false,
                min_improvement: 5.0,
            },
            state: RwLock::new(ExecutionState::Pending),
            current_iteration: RwLock::new(0),
            current_score: RwLock::new(0.0),
            started_at: Utc::now(),
            ended_at: RwLock::new(None),
            termination_reason: RwLock::new(None),
            evidence: RwLock::new(evidence),
            total_cost_usd: RwLock::new(0.0),
            total_input_tokens: RwLock::new(0),
            total_output_tokens: RwLock::new(0),
            pending_tool_uses: RwLock::new(HashMap::new()),
            run_instructions: RwLock::new(None),
            jsonl_writer: RwLock::new(None),
            event_tx: tx,
            event_history: RwLock::new(VecDeque::new()),
            process_pid: RwLock::new(None),
            child_stdin: tokio::sync::RwLock::new(None),
            _metrics_watcher: RwLock::new(None),
        })
    }

    #[test]
    fn test_heuristic_score_no_evidence() {
        let inner = make_inner_with_evidence(EvidenceSummary::default());
        assert_eq!(inner.compute_heuristic_score(), 0.0);
    }

    #[test]
    fn test_heuristic_score_files_only() {
        let inner = make_inner_with_evidence(EvidenceSummary {
            files_written: vec!["a.rs".to_string(), "b.rs".to_string()],
            ..Default::default()
        });
        // 30 base + 2*5 = 40
        assert_eq!(inner.compute_heuristic_score(), 40.0);
    }

    #[test]
    fn test_heuristic_score_full() {
        let inner = make_inner_with_evidence(EvidenceSummary {
            files_written: vec!["a.rs".to_string()],
            files_edited: vec!["b.rs".to_string()],
            commands_run: 3,
            tests_run: true,
            tests_passed: 5,
            tests_failed: 0,
            ..Default::default()
        });
        // files: 30 + 2*5 = 40, tests: 10+10=20, commands: 3*2=6, completion: 20
        assert_eq!(inner.compute_heuristic_score(), 86.0);
    }

    #[test]
    fn test_heuristic_score_capped_at_100() {
        let inner = make_inner_with_evidence(EvidenceSummary {
            files_written: vec![
                "a".into(), "b".into(), "c".into(), "d".into(), "e".into(),
            ],
            files_edited: vec![
                "f".into(), "g".into(), "h".into(), "i".into(), "j".into(),
            ],
            commands_run: 20,
            tests_run: true,
            tests_passed: 50,
            tests_failed: 0,
            ..Default::default()
        });
        // files: 30 + min(10*5,20)=50, tests: 20, cmds: min(40,10)=10, completion: 20 → 100 capped
        assert_eq!(inner.compute_heuristic_score(), 100.0);
    }
}
