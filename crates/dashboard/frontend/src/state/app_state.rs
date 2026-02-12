//! Global application state using Leptos signals.

use leptos::prelude::*;
use serde::{Deserialize, Serialize};

/// Which page is currently active.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum Page {
    Inventory,
    Monitor,
    Control,
    History,
}

impl Default for Page {
    fn default() -> Self {
        Page::Inventory
    }
}

/// Inventory item DTO (matches backend).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InventoryItemDto {
    pub name: String,
    pub kind: String,
    pub description: String,
    #[serde(default)]
    pub category: String,
    #[serde(default)]
    pub triggers: Vec<String>,
    #[serde(default)]
    pub tools: Vec<String>,
    #[serde(default)]
    pub aliases: Vec<String>,
    #[serde(default)]
    pub flags: Vec<String>,
    #[serde(default)]
    pub source_file: String,
}

/// Inventory DTO (matches backend).
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct InventoryDto {
    pub items: Vec<InventoryItemDto>,
}

/// Agent event DTO (matches backend emit).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentEventDto {
    pub execution_id: String,
    pub event_type: String,
    pub data: serde_json::Value,
}

/// Execution summary DTO.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionSummaryDto {
    pub execution_id: String,
    pub task: String,
    pub state: String,
    pub current_iteration: i32,
    pub current_score: f32,
    #[serde(default)]
    pub total_cost_usd: f64,
    #[serde(default)]
    pub duration_seconds: f32,
    #[serde(default)]
    pub files_written: i32,
    #[serde(default)]
    pub files_edited: i32,
    #[serde(default)]
    pub commands_run: i32,
    #[serde(default)]
    pub tests_passed: i32,
    #[serde(default)]
    pub tests_failed: i32,
}

/// Score dimension DTO for quality breakdown.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScoreDimensionDto {
    pub name: String,
    pub score: f32,
    pub max_score: f32,
    #[serde(default)]
    pub description: String,
}

/// Run instructions DTO.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RunInstructionsDto {
    #[serde(default)]
    pub build_command: String,
    #[serde(default)]
    pub run_command: String,
    #[serde(default)]
    pub artifacts: Vec<String>,
    #[serde(default)]
    pub notes: String,
}

/// Detailed execution DTO (returned by get_execution_detail).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExecutionDetailDto {
    pub execution_id: String,
    pub task: String,
    pub state: String,
    pub current_iteration: i32,
    #[serde(default)]
    pub max_iterations: i32,
    pub current_score: f32,
    #[serde(default)]
    pub quality_threshold: f32,
    #[serde(default)]
    pub termination_reason: String,
    #[serde(default)]
    pub total_cost_usd: f64,
    #[serde(default)]
    pub total_input_tokens: i64,
    #[serde(default)]
    pub total_output_tokens: i64,
    #[serde(default)]
    pub files_written: Vec<String>,
    #[serde(default)]
    pub files_edited: Vec<String>,
    #[serde(default)]
    pub commands_run: i32,
    #[serde(default)]
    pub tests_passed: i32,
    #[serde(default)]
    pub tests_failed: i32,
    #[serde(default)]
    pub events: Vec<AgentEventDto>,
    pub run_instructions: Option<RunInstructionsDto>,
    #[serde(default)]
    pub score_breakdown: Vec<ScoreDimensionDto>,
}

/// Daemon status DTO.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct DaemonStatusDto {
    pub online: bool,
    pub version: String,
    pub active_executions: i32,
}

/// Global app state — provided at the root via `provide_context`.
#[derive(Clone)]
pub struct AppState {
    pub current_page: RwSignal<Page>,
    pub inventory: RwSignal<InventoryDto>,
    pub inventory_loading: RwSignal<bool>,
    pub events: RwSignal<Vec<AgentEventDto>>,
    pub executions: RwSignal<Vec<ExecutionSummaryDto>>,
    pub daemon_status: RwSignal<DaemonStatusDto>,
    pub search_query: RwSignal<String>,
    pub kind_filter: RwSignal<Option<String>>,
    /// Which execution row is currently expanded (by execution_id).
    pub expanded_execution: RwSignal<Option<String>>,
    /// Cached detail for the currently expanded execution.
    pub execution_detail: RwSignal<Option<ExecutionDetailDto>>,
    /// Whether the detail panel is loading.
    pub detail_loading: RwSignal<bool>,
}

impl AppState {
    pub fn new() -> Self {
        Self {
            current_page: RwSignal::new(Page::default()),
            inventory: RwSignal::new(InventoryDto::default()),
            inventory_loading: RwSignal::new(true),
            events: RwSignal::new(Vec::new()),
            executions: RwSignal::new(Vec::new()),
            daemon_status: RwSignal::new(DaemonStatusDto::default()),
            search_query: RwSignal::new(String::new()),
            kind_filter: RwSignal::new(None),
            expanded_execution: RwSignal::new(None),
            execution_detail: RwSignal::new(None),
            detail_loading: RwSignal::new(false),
        }
    }
}
