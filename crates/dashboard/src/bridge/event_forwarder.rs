//! Forwards gRPC event streams to Tauri event bus.
//!
//! This module handles the bridging between the daemon's gRPC streaming API
//! and Tauri's frontend event system, allowing real-time updates in the UI.

use tauri::{AppHandle, Emitter};
use tokio_stream::StreamExt;
use tonic::transport::Channel;
use tracing::{debug, error, info};

use superclaude_proto::super_claude_service_client::SuperClaudeServiceClient;
use superclaude_proto::*;

use crate::commands::execution::AgentEventDto;

/// Start forwarding events for a given execution to the Tauri event bus.
pub async fn start_forwarding(
    mut client: SuperClaudeServiceClient<Channel>,
    execution_id: String,
    app_handle: AppHandle,
) {
    info!(execution_id = %execution_id, "Starting event forwarding");

    let stream_result = client
        .stream_events(StreamEventsRequest {
            execution_id: execution_id.clone(),
            include_history: true,
        })
        .await;

    let mut stream = match stream_result {
        Ok(resp) => resp.into_inner(),
        Err(e) => {
            error!(error = %e, "Failed to open event stream");
            return;
        }
    };

    while let Some(Ok(event)) = stream.next().await {
        let (event_type, data) = format_event_data(&event);
        let dto = AgentEventDto {
            execution_id: event.execution_id.clone(),
            event_type,
            data,
        };
        debug!(execution_id = %event.execution_id, "Forwarding event");
        let _ = app_handle.emit("agent-event", &dto);
    }

    info!(execution_id = %execution_id, "Event stream ended");
}

fn format_event_data(event: &AgentEvent) -> (String, serde_json::Value) {
    match &event.event {
        Some(agent_event::Event::IterationStarted(e)) => (
            "iteration_started".to_string(),
            serde_json::json!({"iteration": e.iteration, "depth": e.depth}),
        ),
        Some(agent_event::Event::IterationCompleted(e)) => (
            "iteration_completed".to_string(),
            serde_json::json!({"iteration": e.iteration, "score": e.score}),
        ),
        Some(agent_event::Event::ScoreUpdated(e)) => (
            "score_updated".to_string(),
            serde_json::json!({"old": e.old_score, "new": e.new_score, "reason": e.reason}),
        ),
        Some(agent_event::Event::StateChanged(e)) => (
            "state_changed".to_string(),
            serde_json::json!({"old": e.old_state, "new": e.new_state, "reason": e.reason}),
        ),
        Some(agent_event::Event::ToolInvoked(e)) => (
            "tool_invoked".to_string(),
            serde_json::json!({"tool": e.tool_name, "summary": e.summary}),
        ),
        Some(agent_event::Event::LogMessage(e)) => (
            "log_message".to_string(),
            serde_json::json!({"level": e.level, "message": e.message}),
        ),
        Some(agent_event::Event::Error(e)) => (
            "error".to_string(),
            serde_json::json!({"type": e.error_type, "message": e.message}),
        ),
        _ => ("other".to_string(), serde_json::Value::Null),
    }
}
