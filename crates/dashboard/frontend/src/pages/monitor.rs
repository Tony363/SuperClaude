//! Live Execution Monitor page.

use leptos::prelude::*;

use crate::components::error_banner::ErrorBanner;
use crate::components::event_log::EventLog;
use crate::components::header::PageHeader;
use crate::components::score_chart::ScoreChart;
use crate::components::status_badge::StatusBadge;
use crate::ipc::commands::tauri_invoke_no_args;
use crate::state::{AppState, DaemonStatusDto};

#[component]
pub fn MonitorPage() -> impl IntoView {
    let state = expect_context::<AppState>();

    let active_executions = move || {
        state
            .executions
            .get()
            .into_iter()
            .filter(|e| e.state == "running" || e.state == "paused")
            .collect::<Vec<_>>()
    };

    let latest_score = move || {
        state
            .events
            .get()
            .iter()
            .rev()
            .find(|e| e.event_type == "score_updated" || e.event_type == "iteration_completed")
            .and_then(|e| {
                e.data
                    .get("score")
                    .or(e.data.get("new_score"))
                    .and_then(|v| v.as_f64())
            })
            .unwrap_or(0.0)
    };

    let event_count = move || state.events.get().len();

    let daemon_online = move || state.daemon_status.get().online;

    let retry_callback = Callback::new(move |_: ()| {
        let state = state.clone();
        wasm_bindgen_futures::spawn_local(async move {
            match tauri_invoke_no_args::<DaemonStatusDto>("ping_daemon").await {
                Ok(status) => state.daemon_status.set(status),
                Err(_) => {
                    state.daemon_status.set(DaemonStatusDto {
                        online: false,
                        version: String::new(),
                        active_executions: 0,
                    });
                }
            }
        });
    });

    view! {
        <div>
            <PageHeader
                title="Execution Monitor"
                subtitle="Live event stream and score progression"
            />

            {move || {
                if !daemon_online() {
                    view! {
                        <ErrorBanner
                            message="Daemon is offline. Start the daemon to monitor executions.".to_string()
                            retry=Some(retry_callback)
                        />
                    }.into_any()
                } else {
                    view! { <div></div> }.into_any()
                }
            }}

            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-value">{move || active_executions().len()}</div>
                    <div class="stat-label">"Active"</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{move || format!("{:.0}", latest_score())}</div>
                    <div class="stat-label">"Latest Score"</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{event_count}</div>
                    <div class="stat-label">"Events"</div>
                </div>
            </div>

            // Active executions
            <div style="margin-bottom: 16px;">
                {move || {
                    let execs = active_executions();
                    if execs.is_empty() {
                        view! {
                            <div class="card" style="text-align: center; padding: 24px;">
                                <p style="color: var(--text-muted);">"No active executions. Start one from the Control page."</p>
                            </div>
                        }.into_any()
                    } else {
                        view! {
                            <div class="exec-list">
                                {execs.into_iter().map(|exec| {
                                    let score_str = format!("{:.0}%", exec.current_score);
                                    view! {
                                        <div class="exec-item">
                                            <StatusBadge status=exec.state.clone() />
                                            <span class="exec-task">{exec.task.clone()}</span>
                                            <span style="font-size: 12px; color: var(--text-muted);">
                                                "Iter " {exec.current_iteration}
                                            </span>
                                            <span class="exec-score">{score_str}</span>
                                        </div>
                                    }
                                }).collect_view()}
                            </div>
                        }.into_any()
                    }
                }}
            </div>

            <div class="two-col">
                <div>
                    <h3 style="margin-bottom: 12px; font-size: 14px;">"Score Progression"</h3>
                    <ScoreChart />
                </div>
                <div>
                    <h3 style="margin-bottom: 12px; font-size: 14px;">"Event Stream"</h3>
                    <EventLog />
                </div>
            </div>
        </div>
    }
}
