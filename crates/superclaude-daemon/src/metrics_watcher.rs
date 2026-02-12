//! File watcher for .superclaude_metrics/ directory
//!
//! Watches for changes to events.jsonl and other metric files,
//! parsing them into AgentEvents for streaming.

use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;

use anyhow::{Context, Result};
use chrono::Utc;
use notify::RecursiveMode;
use notify_debouncer_mini::{new_debouncer, DebouncedEventKind};
use prost_types::Timestamp;
use tokio::fs::File;
use tokio::io::{AsyncBufReadExt, AsyncSeekExt, BufReader, SeekFrom};
use tokio::sync::broadcast;
use tracing::{debug, error, info, warn};

use superclaude_proto::*;

/// Watches .superclaude_metrics/ for file changes
pub struct MetricsWatcher {
    _watcher: notify_debouncer_mini::Debouncer<notify::RecommendedWatcher>,
}

impl MetricsWatcher {
    pub fn new(
        metrics_path: PathBuf,
        execution_id: String,
        event_tx: broadcast::Sender<AgentEvent>,
    ) -> Result<Self> {
        let events_file = metrics_path.join("events.jsonl");

        // Track file position to only read new lines
        let file_position = Arc::new(tokio::sync::RwLock::new(0u64));

        let execution_id_clone = execution_id.clone();
        let event_tx_clone = event_tx.clone();
        let file_position_clone = file_position.clone();
        let events_file_clone = events_file.clone();

        // Create debounced file watcher
        let (tx, rx) = std::sync::mpsc::channel();

        let mut debouncer = new_debouncer(Duration::from_millis(100), tx)
            .context("Failed to create file watcher")?;

        debouncer
            .watcher()
            .watch(&metrics_path, RecursiveMode::NonRecursive)
            .context("Failed to watch metrics directory")?;

        // Spawn handler for file events
        tokio::spawn(async move {
            // First, process any existing content
            if events_file_clone.exists() {
                if let Err(e) = process_events_file(
                    &events_file_clone,
                    &execution_id_clone,
                    &event_tx_clone,
                    &file_position_clone,
                )
                .await
                {
                    warn!(error = %e, "Failed to process existing events file");
                }
            }

            // Then watch for changes
            while let Ok(result) = rx.recv() {
                match result {
                    Ok(events) => {
                        for event in events {
                            if event.kind == DebouncedEventKind::Any {
                                if event.path.file_name().map(|n| n == "events.jsonl").unwrap_or(false) {
                                    if let Err(e) = process_events_file(
                                        &events_file_clone,
                                        &execution_id_clone,
                                        &event_tx_clone,
                                        &file_position_clone,
                                    )
                                    .await
                                    {
                                        error!(error = %e, "Failed to process events file");
                                    }
                                }
                            }
                        }
                    }
                    Err(e) => {
                        error!(error = %e, "File watcher error");
                    }
                }
            }
        });

        info!(
            path = %metrics_path.display(),
            "Started metrics watcher"
        );

        Ok(Self {
            _watcher: debouncer,
        })
    }
}

/// Read new lines from events.jsonl and emit as AgentEvents
async fn process_events_file(
    path: &PathBuf,
    execution_id: &str,
    event_tx: &broadcast::Sender<AgentEvent>,
    file_position: &tokio::sync::RwLock<u64>,
) -> Result<()> {
    let file = File::open(path).await?;
    let mut reader = BufReader::new(file);

    // Seek to last known position
    let pos = *file_position.read().await;
    reader.seek(SeekFrom::Start(pos)).await?;

    let mut line = String::new();
    while reader.read_line(&mut line).await? > 0 {
        let trimmed = line.trim();
        if !trimmed.is_empty() {
            if let Some(event) = parse_metrics_event(trimmed, execution_id) {
                debug!(execution_id = %execution_id, "Parsed metrics event");
                let _ = event_tx.send(event);
            }
        }
        line.clear();
    }

    // Update file position
    *file_position.write().await = reader.stream_position().await?;

    Ok(())
}

/// Parse a JSON line from events.jsonl into an AgentEvent
fn parse_metrics_event(line: &str, execution_id: &str) -> Option<AgentEvent> {
    // Try to parse the JSON line
    let value: serde_json::Value = serde_json::from_str(line).ok()?;

    let event_type = value.get("event_type")?.as_str()?;
    let timestamp = now_timestamp();

    let event = match event_type {
        "iteration_start" => {
            let iteration = value.get("iteration")?.as_i64()? as i32;
            Some(agent_event::Event::IterationStarted(IterationStarted {
                iteration,
                depth: value.get("depth").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
                node_id: format!("iter-{}", iteration),
            }))
        }

        "iteration_complete" => {
            let iteration = value.get("iteration")?.as_i64()? as i32;
            let score = value.get("score")?.as_f64()? as f32;

            Some(agent_event::Event::IterationCompleted(IterationCompleted {
                iteration,
                score,
                improvements: value
                    .get("improvements")
                    .and_then(|v| v.as_array())
                    .map(|arr| {
                        arr.iter()
                            .filter_map(|v| v.as_str().map(|s| s.to_string()))
                            .collect()
                    })
                    .unwrap_or_default(),
                dimensions: parse_dimensions(&value),
                duration_seconds: value.get("duration").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32,
                node_id: format!("iter-{}", iteration),
                total_cost_usd: value.get("total_cost_usd").and_then(|v| v.as_f64()).unwrap_or(0.0),
                input_tokens: value.get("input_tokens").and_then(|v| v.as_i64()).unwrap_or(0),
                output_tokens: value.get("output_tokens").and_then(|v| v.as_i64()).unwrap_or(0),
                num_turns: value.get("num_turns").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
            }))
        }

        "tool_use" | "tool_invoked" => {
            let tool_name = value.get("tool")?.as_str()?.to_string();

            Some(agent_event::Event::ToolInvoked(ToolInvoked {
                tool_name,
                summary: value.get("summary").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                blocked: value.get("blocked").and_then(|v| v.as_bool()).unwrap_or(false),
                block_reason: value.get("block_reason").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                depth: value.get("depth").and_then(|v| v.as_i64()).unwrap_or(1) as i32,
                node_id: value.get("id").and_then(|v| v.as_str()).unwrap_or(&uuid::Uuid::new_v4().to_string()).to_string(),
                parent_node_id: value.get("parent_id").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                tool_input: value.get("tool_input").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                tool_output: value.get("tool_output").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                tool_use_id: value.get("tool_use_id").and_then(|v| v.as_str()).unwrap_or("").to_string(),
            }))
        }

        "file_change" | "file_changed" => {
            let path = value.get("path")?.as_str()?.to_string();
            let action_str = value.get("action").and_then(|v| v.as_str()).unwrap_or("read");

            let action = match action_str {
                "write" | "created" => FileAction::Write,
                "edit" | "modified" => FileAction::Edit,
                "delete" | "removed" => FileAction::Delete,
                _ => FileAction::Read,
            };

            Some(agent_event::Event::FileChanged(FileChanged {
                path,
                action: action as i32,
                lines_added: value.get("lines_added").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
                lines_removed: value.get("lines_removed").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
                node_id: value.get("id").and_then(|v| v.as_str()).unwrap_or(&uuid::Uuid::new_v4().to_string()).to_string(),
            }))
        }

        "test_result" | "tests" => {
            Some(agent_event::Event::TestResult(TestResult {
                framework: value.get("framework").and_then(|v| v.as_str()).unwrap_or("unknown").to_string(),
                passed: value.get("passed").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
                failed: value.get("failed").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
                skipped: value.get("skipped").and_then(|v| v.as_i64()).unwrap_or(0) as i32,
                coverage_percent: value.get("coverage").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32,
                failed_tests: value
                    .get("failed_tests")
                    .and_then(|v| v.as_array())
                    .map(|arr| {
                        arr.iter()
                            .filter_map(|v| v.as_str().map(|s| s.to_string()))
                            .collect()
                    })
                    .unwrap_or_default(),
                node_id: value.get("id").and_then(|v| v.as_str()).unwrap_or(&uuid::Uuid::new_v4().to_string()).to_string(),
            }))
        }

        "score_update" | "score" => {
            Some(agent_event::Event::ScoreUpdated(ScoreUpdated {
                old_score: value.get("old_score").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32,
                new_score: value.get("new_score").or(value.get("score")).and_then(|v| v.as_f64()).unwrap_or(0.0) as f32,
                reason: value.get("reason").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                dimensions: parse_dimensions(&value),
            }))
        }

        "subagent_spawn" | "subagent_spawned" => {
            Some(agent_event::Event::SubagentSpawned(SubagentSpawned {
                subagent_id: value.get("subagent_id").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                subagent_type: value.get("subagent_type").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                task_summary: value.get("task").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                depth: value.get("depth").and_then(|v| v.as_i64()).unwrap_or(1) as i32,
                node_id: value.get("id").and_then(|v| v.as_str()).unwrap_or(&uuid::Uuid::new_v4().to_string()).to_string(),
                parent_node_id: value.get("parent_id").and_then(|v| v.as_str()).unwrap_or("").to_string(),
            }))
        }

        "subagent_complete" | "subagent_completed" => {
            Some(agent_event::Event::SubagentCompleted(SubagentCompleted {
                subagent_id: value.get("subagent_id").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                success: value.get("success").and_then(|v| v.as_bool()).unwrap_or(true),
                result_summary: value.get("result").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                node_id: value.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string(),
            }))
        }

        "artifact" | "obsidian_artifact" => {
            Some(agent_event::Event::ArtifactWritten(ArtifactWritten {
                obsidian_path: value.get("path").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                artifact_type: value.get("type").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                title: value.get("title").and_then(|v| v.as_str()).unwrap_or("").to_string(),
            }))
        }

        "log" | "message" => {
            let level_str = value.get("level").and_then(|v| v.as_str()).unwrap_or("info");
            let level = match level_str {
                "debug" => LogLevel::Debug,
                "warn" | "warning" => LogLevel::Warn,
                "error" => LogLevel::Error,
                _ => LogLevel::Info,
            };

            Some(agent_event::Event::LogMessage(LogMessage {
                level: level as i32,
                message: value.get("message").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                source: value.get("source").and_then(|v| v.as_str()).unwrap_or("").to_string(),
            }))
        }

        "error" => {
            Some(agent_event::Event::Error(ErrorOccurred {
                error_type: value.get("error_type").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                message: value.get("message").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                traceback: value.get("traceback").and_then(|v| v.as_str()).unwrap_or("").to_string(),
                recoverable: value.get("recoverable").and_then(|v| v.as_bool()).unwrap_or(true),
            }))
        }

        _ => {
            debug!(event_type = %event_type, "Unknown event type");
            None
        }
    };

    event.map(|e| AgentEvent {
        execution_id: execution_id.to_string(),
        timestamp,
        event: Some(e),
    })
}

fn parse_dimensions(value: &serde_json::Value) -> Option<QualityDimensions> {
    let dims = value.get("dimensions")?;

    Some(QualityDimensions {
        code_changes: dims.get("code_changes").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32,
        tests_run: dims.get("tests_run").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32,
        tests_pass: dims.get("tests_pass").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32,
        coverage: dims.get("coverage").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32,
        no_errors: dims.get("no_errors").and_then(|v| v.as_f64()).unwrap_or(0.0) as f32,
        breakdown: vec![],
    })
}

fn now_timestamp() -> Option<Timestamp> {
    let now = Utc::now();
    Some(Timestamp {
        seconds: now.timestamp(),
        nanos: now.timestamp_subsec_nanos() as i32,
    })
}
