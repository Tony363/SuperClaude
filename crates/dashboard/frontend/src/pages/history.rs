//! Historical Metrics page — browse past sessions and events.

use leptos::prelude::*;

use crate::components::header::PageHeader;
use crate::ipc::commands::tauri_invoke_no_args;
use crate::state::AppState;

/// Metric event DTO matching the backend.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct MetricEventDto {
    pub event_type: String,
    #[serde(default)]
    pub timestamp: Option<String>,
    #[serde(default)]
    pub execution_id: String,
    #[serde(default)]
    pub session_id: String,
    #[serde(flatten)]
    pub data: serde_json::Value,
}

#[component]
pub fn HistoryPage() -> impl IntoView {
    let historical_events = RwSignal::new(Vec::<MetricEventDto>::new());
    let loading = RwSignal::new(false);

    // Fetch on mount
    {
        let historical_events = historical_events.clone();
        wasm_bindgen_futures::spawn_local(async move {
            loading.set(true);
            match tauri_invoke_no_args::<Vec<MetricEventDto>>("get_historical_events").await {
                Ok(events) => historical_events.set(events),
                Err(e) => {
                    web_sys::console::error_1(&format!("Failed to load history: {e}").into());
                }
            }
            loading.set(false);
        });
    }

    view! {
        <div>
            <PageHeader
                title="Historical Metrics"
                subtitle="Browse past executions and event history"
            />

            {move || {
                if loading.get() {
                    view! {
                        <div class="loading">
                            <div class="spinner"></div>
                            <span>"Loading history..."</span>
                        </div>
                    }.into_any()
                } else {
                    let events = historical_events.get();
                    if events.is_empty() {
                        view! {
                            <div class="empty-state">
                                <h3>"No historical data"</h3>
                                <p>"Events will appear here after executions complete."</p>
                                <p style="margin-top: 8px; font-size: 12px; color: var(--text-muted);">
                                    "Data is read from .superclaude_metrics/events.jsonl"
                                </p>
                            </div>
                        }.into_any()
                    } else {
                        let total = events.len();
                        let unique_sessions: std::collections::HashSet<_> =
                            events.iter().map(|e| e.session_id.clone()).collect();
                        let unique_executions: std::collections::HashSet<_> =
                            events.iter().map(|e| e.execution_id.clone()).collect();

                        view! {
                            <div>
                                <div class="stat-grid" style="margin-bottom: 16px;">
                                    <div class="stat-card">
                                        <div class="stat-value">{total}</div>
                                        <div class="stat-label">"Total Events"</div>
                                    </div>
                                    <div class="stat-card">
                                        <div class="stat-value">{unique_sessions.len()}</div>
                                        <div class="stat-label">"Sessions"</div>
                                    </div>
                                    <div class="stat-card">
                                        <div class="stat-value">{unique_executions.len()}</div>
                                        <div class="stat-label">"Executions"</div>
                                    </div>
                                </div>

                                <div class="event-log">
                                    {events.into_iter().rev().take(200).map(|evt| {
                                        let data_str = evt.data.to_string();
                                        let data_str = if data_str.len() > 100 {
                                            format!("{}...", &data_str[..100])
                                        } else {
                                            data_str
                                        };
                                        view! {
                                            <div class="event-log-entry">
                                                <span class="event-time">
                                                    {evt.timestamp.unwrap_or_default()}
                                                </span>
                                                <span class="event-type">{evt.event_type}</span>
                                                <span class="event-data">{data_str}</span>
                                            </div>
                                        }
                                    }).collect_view()}
                                </div>
                            </div>
                        }.into_any()
                    }
                }
            }}
        </div>
    }
}
