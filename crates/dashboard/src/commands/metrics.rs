//! Historical metrics Tauri commands.

use tauri::State;

use crate::state::AppState;
use superclaude_core::metrics_reader;
use superclaude_core::types::MetricEvent;

/// Get all historical events from `.superclaude_metrics/events.jsonl`.
#[tauri::command]
pub async fn get_historical_events(
    state: State<'_, AppState>,
) -> Result<Vec<MetricEvent>, String> {
    metrics_reader::read_events(&state.project_root)
        .map_err(|e| format!("Failed to read events: {e}"))
}

/// Get all historical metrics from `.superclaude_metrics/metrics.jsonl`.
#[tauri::command]
pub async fn get_historical_metrics(
    state: State<'_, AppState>,
) -> Result<Vec<MetricEvent>, String> {
    metrics_reader::read_metrics(&state.project_root)
        .map_err(|e| format!("Failed to read metrics: {e}"))
}

/// Get events for a specific execution.
#[tauri::command(rename_all = "snake_case")]
pub async fn get_execution_events(
    execution_id: String,
    state: State<'_, AppState>,
) -> Result<Vec<MetricEvent>, String> {
    metrics_reader::read_events_for_execution(&state.project_root, &execution_id)
        .map_err(|e| format!("Failed to read execution events: {e}"))
}
