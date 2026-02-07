//! Execution management - spawns and monitors claude CLI processes

use std::path::PathBuf;
use std::process::Stdio;
use std::sync::Arc;

use anyhow::{Context, Result};
use chrono::Utc;
use parking_lot::RwLock;
use prost_types::Timestamp;
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::{Child, Command};
use tokio::sync::broadcast;
use tracing::{debug, error, info, warn};
use uuid::Uuid;

use crate::metrics_watcher::MetricsWatcher;
use crate::proto::*;

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

    // Process management
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

        // Build the command
        let mut cmd = Command::new(&claude_path);
        cmd.arg("--print")  // Non-interactive mode
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

        // Read stdout for progress
        if let Some(stdout) = child.stdout.take() {
            let inner = self.clone();
            tokio::spawn(async move {
                let reader = BufReader::new(stdout);
                let mut lines = reader.lines();

                while let Ok(Some(line)) = lines.next_line().await {
                    debug!(execution_id = %inner.id, line = %line, "claude stdout");
                    inner.parse_output_line(&line);
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

    fn parse_output_line(&self, line: &str) {
        // Parse claude CLI output for events
        if line.contains("Iteration") {
            if let Some(num) = line
                .split_whitespace()
                .find(|s| s.parse::<i32>().is_ok())
                .and_then(|s| s.parse().ok())
            {
                *self.current_iteration.write() = num;

                self.emit_event(AgentEvent {
                    execution_id: self.id.clone(),
                    timestamp: Self::now_timestamp(),
                    event: Some(agent_event::Event::IterationStarted(IterationStarted {
                        iteration: num,
                        depth: 0,
                        node_id: format!("iter-{}", num),
                    })),
                });
            }
        }

        if line.contains("Score:") || line.contains("score:") {
            if let Some(score_str) = line.split(':').last() {
                if let Ok(score) = score_str.trim().trim_end_matches('%').parse::<f32>() {
                    let old_score = *self.current_score.read();
                    *self.current_score.write() = score;

                    self.emit_event(AgentEvent {
                        execution_id: self.id.clone(),
                        timestamp: Self::now_timestamp(),
                        event: Some(agent_event::Event::ScoreUpdated(ScoreUpdated {
                            old_score,
                            new_score: score,
                            reason: "Score updated".to_string(),
                            dimensions: None,
                        })),
                    });
                }
            }
        }

        if line.contains("Tool:") || line.contains("Using") {
            let tool_name = line
                .split_whitespace()
                .nth(1)
                .unwrap_or("Unknown")
                .to_string();

            self.emit_event(AgentEvent {
                execution_id: self.id.clone(),
                timestamp: Self::now_timestamp(),
                event: Some(agent_event::Event::ToolInvoked(ToolInvoked {
                    tool_name,
                    summary: line.to_string(),
                    blocked: false,
                    block_reason: String::new(),
                    depth: 1,
                    node_id: Uuid::new_v4().to_string(),
                    parent_node_id: format!("iter-{}", *self.current_iteration.read()),
                })),
            });

            self.evidence.write().commands_run += 1;
        }

        if line.contains("Write:") || line.contains("Created") {
            if let Some(path) = line.split_whitespace().last() {
                self.evidence.write().files_written.push(path.to_string());
            }
        }

        if line.contains("Edit:") || line.contains("Modified") {
            if let Some(path) = line.split_whitespace().last() {
                self.evidence.write().files_edited.push(path.to_string());
            }
        }
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
