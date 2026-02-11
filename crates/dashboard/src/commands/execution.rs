//! Execution lifecycle Tauri commands.

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, State};
use tokio_stream::StreamExt;

use crate::state::AppState;
use superclaude_proto::*;

/// DTO for execution config coming from the frontend.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionConfigDto {
    pub max_iterations: Option<i32>,
    pub quality_threshold: Option<f32>,
    pub model: Option<String>,
    pub timeout_seconds: Option<f32>,
}

/// DTO for start execution response.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct StartExecutionResult {
    pub execution_id: String,
    pub state: String,
}

/// DTO for execution summary.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionSummaryDto {
    pub execution_id: String,
    pub task: String,
    pub state: String,
    pub current_iteration: i32,
    pub current_score: f32,
}

/// DTO for agent events emitted to the frontend.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentEventDto {
    pub execution_id: String,
    pub event_type: String,
    pub data: serde_json::Value,
}

fn state_name(state: i32) -> String {
    match state {
        1 => "pending".to_string(),
        2 => "running".to_string(),
        3 => "paused".to_string(),
        4 => "completed".to_string(),
        5 => "failed".to_string(),
        6 => "cancelled".to_string(),
        _ => "unknown".to_string(),
    }
}

#[tauri::command(rename_all = "snake_case")]
pub async fn start_execution(
    task: String,
    config: Option<ExecutionConfigDto>,
    state: State<'_, AppState>,
) -> Result<StartExecutionResult, String> {
    let mut client = state.get_client().await.map_err(|e| e.to_string())?;

    let proto_config = config.map(|c| ExecutionConfig {
        max_iterations: c.max_iterations.unwrap_or(3),
        quality_threshold: c.quality_threshold.unwrap_or(70.0),
        model: c.model.unwrap_or_else(|| "sonnet".to_string()),
        timeout_seconds: c.timeout_seconds.unwrap_or(300.0),
        pal_review_enabled: true,
        min_improvement: 5.0,
    });

    let resp = client
        .start_execution(StartExecutionRequest {
            task,
            project_root: state.project_root.to_string_lossy().to_string(),
            config: proto_config,
        })
        .await
        .map_err(|e| format!("gRPC error: {e}"))?;

    Ok(StartExecutionResult {
        execution_id: resp.execution_id,
        state: state_name(resp.state),
    })
}

#[tauri::command(rename_all = "snake_case")]
pub async fn stop_execution(
    execution_id: String,
    force: bool,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let mut client = state.get_client().await.map_err(|e| e.to_string())?;
    let resp = client
        .stop_execution(StopExecutionRequest {
            execution_id,
            force,
        })
        .await
        .map_err(|e| format!("gRPC error: {e}"))?;
    Ok(resp.message)
}

#[tauri::command(rename_all = "snake_case")]
pub async fn pause_execution(
    execution_id: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let mut client = state.get_client().await.map_err(|e| e.to_string())?;
    let resp = client
        .pause_execution(PauseExecutionRequest { execution_id })
        .await
        .map_err(|e| format!("gRPC error: {e}"))?;
    Ok(resp.message)
}

#[tauri::command(rename_all = "snake_case")]
pub async fn resume_execution(
    execution_id: String,
    state: State<'_, AppState>,
) -> Result<String, String> {
    let mut client = state.get_client().await.map_err(|e| e.to_string())?;
    let resp = client
        .resume_execution(ResumeExecutionRequest { execution_id })
        .await
        .map_err(|e| format!("gRPC error: {e}"))?;
    Ok(resp.message)
}

#[tauri::command(rename_all = "snake_case")]
pub async fn list_executions(
    include_completed: bool,
    state: State<'_, AppState>,
) -> Result<Vec<ExecutionSummaryDto>, String> {
    let mut client = state.get_client().await.map_err(|e| e.to_string())?;
    let resp = client
        .list_executions(ListExecutionsRequest {
            include_completed,
            limit: 100,
        })
        .await
        .map_err(|e| format!("gRPC error: {e}"))?;

    Ok(resp
        .executions
        .into_iter()
        .map(|e| ExecutionSummaryDto {
            execution_id: e.execution_id,
            task: e.task,
            state: state_name(e.state),
            current_iteration: e.current_iteration,
            current_score: e.current_score,
        })
        .collect())
}

/// Subscribe to execution events — streams events via Tauri emit().
#[tauri::command(rename_all = "snake_case")]
pub async fn subscribe_events(
    execution_id: String,
    app_handle: AppHandle,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let mut client = state.get_client().await.map_err(|e| e.to_string())?;

    let mut stream = client
        .stream_events(StreamEventsRequest {
            execution_id: execution_id.clone(),
            include_history: true,
        })
        .await
        .map_err(|e| format!("gRPC error: {e}"))?;

    // Spawn a task to forward events
    tokio::spawn(async move {
        while let Some(Ok(event)) = stream.next().await {
            let (event_type, data) = format_event(&event);
            let dto = AgentEventDto {
                execution_id: event.execution_id.clone(),
                event_type,
                data,
            };
            let _ = app_handle.emit("agent-event", &dto);
        }
    });

    Ok(())
}

fn format_event(event: &AgentEvent) -> (String, serde_json::Value) {
    match &event.event {
        Some(agent_event::Event::IterationStarted(e)) => (
            "iteration_started".to_string(),
            serde_json::json!({
                "iteration": e.iteration,
                "depth": e.depth,
                "node_id": e.node_id,
            }),
        ),
        Some(agent_event::Event::IterationCompleted(e)) => (
            "iteration_completed".to_string(),
            serde_json::json!({
                "iteration": e.iteration,
                "score": e.score,
                "improvements": e.improvements,
                "duration_seconds": e.duration_seconds,
            }),
        ),
        Some(agent_event::Event::ToolInvoked(e)) => (
            "tool_invoked".to_string(),
            serde_json::json!({
                "tool_name": e.tool_name,
                "summary": e.summary,
                "blocked": e.blocked,
            }),
        ),
        Some(agent_event::Event::FileChanged(e)) => (
            "file_changed".to_string(),
            serde_json::json!({
                "path": e.path,
                "action": e.action,
                "lines_added": e.lines_added,
                "lines_removed": e.lines_removed,
            }),
        ),
        Some(agent_event::Event::TestResult(e)) => (
            "test_result".to_string(),
            serde_json::json!({
                "framework": e.framework,
                "passed": e.passed,
                "failed": e.failed,
                "skipped": e.skipped,
                "coverage_percent": e.coverage_percent,
            }),
        ),
        Some(agent_event::Event::ScoreUpdated(e)) => (
            "score_updated".to_string(),
            serde_json::json!({
                "old_score": e.old_score,
                "new_score": e.new_score,
                "reason": e.reason,
            }),
        ),
        Some(agent_event::Event::StateChanged(e)) => (
            "state_changed".to_string(),
            serde_json::json!({
                "old_state": state_name(e.old_state),
                "new_state": state_name(e.new_state),
                "reason": e.reason,
            }),
        ),
        Some(agent_event::Event::SubagentSpawned(e)) => (
            "subagent_spawned".to_string(),
            serde_json::json!({
                "subagent_id": e.subagent_id,
                "subagent_type": e.subagent_type,
                "task_summary": e.task_summary,
            }),
        ),
        Some(agent_event::Event::SubagentCompleted(e)) => (
            "subagent_completed".to_string(),
            serde_json::json!({
                "subagent_id": e.subagent_id,
                "success": e.success,
                "result_summary": e.result_summary,
            }),
        ),
        Some(agent_event::Event::LogMessage(e)) => (
            "log_message".to_string(),
            serde_json::json!({
                "level": e.level,
                "message": e.message,
                "source": e.source,
            }),
        ),
        Some(agent_event::Event::Error(e)) => (
            "error".to_string(),
            serde_json::json!({
                "error_type": e.error_type,
                "message": e.message,
                "recoverable": e.recoverable,
            }),
        ),
        Some(agent_event::Event::ArtifactWritten(e)) => (
            "artifact_written".to_string(),
            serde_json::json!({
                "obsidian_path": e.obsidian_path,
                "artifact_type": e.artifact_type,
                "title": e.title,
            }),
        ),
        None => ("unknown".to_string(), serde_json::Value::Null),
    }
}
