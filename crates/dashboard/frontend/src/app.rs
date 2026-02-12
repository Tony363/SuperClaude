//! Root application component with layout and routing.

use leptos::prelude::*;

use crate::components::sidebar::Sidebar;
use crate::ipc::commands::tauri_invoke_no_args;
use crate::ipc::events::tauri_listen;
use crate::pages::control::ControlPage;
use crate::pages::history::HistoryPage;
use crate::pages::inventory::InventoryPage;
use crate::pages::monitor::MonitorPage;
use crate::state::{AgentEventDto, AppState, DaemonStatusDto, InventoryDto, Page};

#[component]
pub fn App() -> impl IntoView {
    let state = AppState::new();
    provide_context(state.clone());

    // Load inventory on mount
    {
        let state = state.clone();
        wasm_bindgen_futures::spawn_local(async move {
            match tauri_invoke_no_args::<InventoryDto>("get_inventory").await {
                Ok(inv) => {
                    state.inventory.set(inv);
                    state.inventory_loading.set(false);
                }
                Err(e) => {
                    web_sys::console::error_1(&format!("Inventory load failed: {e}").into());
                    state.inventory_loading.set(false);
                }
            }
        });
    }

    // Ping daemon on mount
    {
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
    }

    // Listen for agent events and update execution state
    {
        let state = state.clone();
        tauri_listen("agent-event", move |event: AgentEventDto| {
            let eid = event.execution_id.clone();

            match event.event_type.as_str() {
                "iteration_started" | "iteration_completed" => {
                    if let Some(iter) = event.data.get("iteration").and_then(|v| v.as_i64()) {
                        state.executions.update(|execs| {
                            if let Some(exec) = execs.iter_mut().find(|e| e.execution_id == eid) {
                                exec.current_iteration = iter as i32;
                            }
                        });
                    }
                    if let Some(score) = event.data.get("score").and_then(|v| v.as_f64()) {
                        state.executions.update(|execs| {
                            if let Some(exec) = execs.iter_mut().find(|e| e.execution_id == eid) {
                                exec.current_score = score as f32;
                            }
                        });
                    }
                }
                "score_updated" => {
                    if let Some(score) = event.data.get("new_score").and_then(|v| v.as_f64()) {
                        state.executions.update(|execs| {
                            if let Some(exec) = execs.iter_mut().find(|e| e.execution_id == eid) {
                                exec.current_score = score as f32;
                            }
                        });
                    }
                }
                "state_changed" => {
                    if let Some(new_state) = event.data.get("new_state").and_then(|v| v.as_str()) {
                        state.executions.update(|execs| {
                            if let Some(exec) = execs.iter_mut().find(|e| e.execution_id == eid) {
                                exec.state = new_state.to_string();
                            }
                        });
                    }
                }
                _ => {}
            }

            // Incrementally update the detail panel if this event is for the expanded execution
            if let Some(expanded_eid) = state.expanded_execution.get_untracked() {
                if expanded_eid == eid {
                    state.execution_detail.update(|opt_detail| {
                        if let Some(detail) = opt_detail {
                            // Append event to log
                            detail.events.push(event.clone());

                            // Update score
                            if event.event_type == "score_updated" {
                                if let Some(score) = event.data.get("new_score").and_then(|v| v.as_f64()) {
                                    detail.current_score = score as f32;
                                }
                                if let Some(dims) = event.data.get("dimensions").and_then(|v| v.as_array()) {
                                    detail.score_breakdown = dims.iter().filter_map(|d| {
                                        Some(crate::state::ScoreDimensionDto {
                                            name: d.get("name")?.as_str()?.to_string(),
                                            score: d.get("score")?.as_f64()? as f32,
                                            max_score: d.get("max_score")?.as_f64()? as f32,
                                            description: d.get("description")?.as_str()?.to_string(),
                                        })
                                    }).collect();
                                }
                            }

                            // Update files from file_changed events
                            if event.event_type == "file_changed" {
                                if let Some(path) = event.data.get("path").and_then(|v| v.as_str()) {
                                    let action = event.data.get("action").and_then(|v| v.as_i64()).unwrap_or(0);
                                    match action {
                                        2 => { // FILE_ACTION_WRITE
                                            if !detail.files_written.contains(&path.to_string()) {
                                                detail.files_written.push(path.to_string());
                                            }
                                        }
                                        3 => { // FILE_ACTION_EDIT
                                            if !detail.files_edited.contains(&path.to_string()) {
                                                detail.files_edited.push(path.to_string());
                                            }
                                        }
                                        _ => {}
                                    }
                                }
                            }

                            // Update iteration
                            if event.event_type == "iteration_started" || event.event_type == "iteration_completed" {
                                if let Some(iter) = event.data.get("iteration").and_then(|v| v.as_i64()) {
                                    detail.current_iteration = iter as i32;
                                }
                            }
                        }
                    });
                }
            }

            // Always append to the event log
            state.events.update(|evts| evts.push(event));
        });
    }

    let current_page = state.current_page;

    view! {
        <Sidebar />
        <main class="main-content">
            {move || match current_page.get() {
                Page::Inventory => view! { <InventoryPage /> }.into_any(),
                Page::Monitor => view! { <MonitorPage /> }.into_any(),
                Page::Control => view! { <ControlPage /> }.into_any(),
                Page::History => view! { <HistoryPage /> }.into_any(),
            }}
        </main>
    }
}
