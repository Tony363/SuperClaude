//! Execution Control page — launch, pause, resume, stop executions.

use std::sync::Arc;

use leptos::prelude::*;

use crate::components::config_form::ConfigForm;
use crate::components::execution_detail::ExecutionDetailPanel;
use crate::components::header::PageHeader;
use crate::components::status_badge::StatusBadge;
use crate::ipc::commands::tauri_invoke;
use crate::state::{AppState, ExecutionDetailDto};

async fn refresh_executions(state: &AppState) {
    let list_args = serde_json::json!({"include_completed": true});
    if let Ok(execs) = tauri_invoke::<_, Vec<crate::state::ExecutionSummaryDto>>(
        "list_executions",
        &list_args,
    )
    .await
    {
        state.executions.set(execs);
    }
}

async fn fetch_execution_detail(state: &AppState, execution_id: &str) {
    state.detail_loading.set(true);
    let args = serde_json::json!({"execution_id": execution_id});
    match tauri_invoke::<_, ExecutionDetailDto>("get_execution_detail", &args).await {
        Ok(detail) => {
            state.execution_detail.set(Some(detail));
        }
        Err(e) => {
            web_sys::console::error_1(&format!("Failed to fetch detail: {e}").into());
            state.execution_detail.set(None);
        }
    }
    state.detail_loading.set(false);
}

#[component]
pub fn ControlPage() -> impl IntoView {
    let state = expect_context::<AppState>();

    let state_for_start = state.clone();
    let on_start: Arc<dyn Fn(String, i32, f32, String) + Send + Sync> =
        Arc::new(move |task: String, max_iter: i32, threshold: f32, model: String| {
            if task.trim().is_empty() {
                return;
            }
            let state = state_for_start.clone();
            wasm_bindgen_futures::spawn_local(async move {
                let args = serde_json::json!({
                    "task": task,
                    "config": {
                        "max_iterations": max_iter,
                        "quality_threshold": threshold,
                        "model": model,
                    }
                });
                let result: Result<serde_json::Value, _> =
                    tauri_invoke("start_execution", &args).await;
                match result {
                    Ok(resp) => {
                        if let Some(exec_id) = resp.get("execution_id").and_then(|v| v.as_str()) {
                            let sub_args = serde_json::json!({"execution_id": exec_id});
                            let _: Result<(), _> =
                                tauri_invoke("subscribe_events", &sub_args).await;
                        }
                        refresh_executions(&state).await;
                    }
                    Err(e) => {
                        web_sys::console::error_1(&format!("Start failed: {e}").into());
                    }
                }
            });
        });

    let state_for_stop = state.clone();
    let do_stop = Arc::new(move |exec_id: String| {
        let state = state_for_stop.clone();
        wasm_bindgen_futures::spawn_local(async move {
            let args = serde_json::json!({"execution_id": exec_id, "force": false});
            let _: Result<String, _> = tauri_invoke("stop_execution", &args).await;
            refresh_executions(&state).await;
        });
    });

    let state_for_pause = state.clone();
    let do_pause = Arc::new(move |exec_id: String| {
        let state = state_for_pause.clone();
        wasm_bindgen_futures::spawn_local(async move {
            let args = serde_json::json!({"execution_id": exec_id});
            let _: Result<String, _> = tauri_invoke("pause_execution", &args).await;
            refresh_executions(&state).await;
        });
    });

    let state_for_resume = state.clone();
    let do_resume = Arc::new(move |exec_id: String| {
        let state = state_for_resume.clone();
        wasm_bindgen_futures::spawn_local(async move {
            let args = serde_json::json!({"execution_id": exec_id});
            let _: Result<String, _> = tauri_invoke("resume_execution", &args).await;
            refresh_executions(&state).await;
        });
    });

    let state_for_view = state.clone();

    view! {
        <div>
            <PageHeader
                title="Execution Control"
                subtitle="Launch and manage executions"
            />

            <ConfigForm on_submit=on_start />

            <h3 style="margin-bottom: 12px; font-size: 14px;">"Executions"</h3>
            <div class="exec-list">
                {move || {
                    let execs = state_for_view.executions.get();
                    let do_stop = do_stop.clone();
                    let do_pause = do_pause.clone();
                    let do_resume = do_resume.clone();
                    let state_inner = state_for_view.clone();

                    if execs.is_empty() {
                        view! {
                            <div class="empty-state">
                                <h3>"No executions"</h3>
                                <p>"Launch one above to get started."</p>
                            </div>
                        }.into_any()
                    } else {
                        execs.into_iter().map(|exec| {
                            let eid_stop = exec.execution_id.clone();
                            let eid_pause = exec.execution_id.clone();
                            let eid_resume = exec.execution_id.clone();
                            let eid_expand = exec.execution_id.clone();
                            let eid_check = exec.execution_id.clone();
                            let eid_for_detail = exec.execution_id.clone();
                            let score_str = format!("{:.0}%", exec.current_score);
                            let is_running = exec.state == "running";
                            let is_paused = exec.state == "paused";
                            let cost = exec.total_cost_usd;

                            let stop_fn = do_stop.clone();
                            let pause_fn = do_pause.clone();
                            let resume_fn = do_resume.clone();

                            let state_click = state_inner.clone();

                            view! {
                                <div class="exec-item-wrapper">
                                    <div class="exec-item" style="flex-wrap: wrap;" on:click=move |_| {
                                        let current = state_click.expanded_execution.get();
                                        let eid = eid_expand.clone();
                                        if current.as_deref() == Some(&eid) {
                                            // Collapse
                                            state_click.expanded_execution.set(None);
                                            state_click.execution_detail.set(None);
                                        } else {
                                            // Expand
                                            state_click.expanded_execution.set(Some(eid.clone()));
                                            let s = state_click.clone();
                                            wasm_bindgen_futures::spawn_local(async move {
                                                fetch_execution_detail(&s, &eid).await;
                                            });
                                        }
                                    }>
                                        <span class="exec-chevron">
                                            {move || {
                                                let expanded = state_inner.expanded_execution.get();
                                                if expanded.as_deref() == Some(&*eid_check) { "v" } else { ">" }
                                            }}
                                        </span>
                                        <StatusBadge status=exec.state.clone() />
                                        <span class="exec-task">{exec.task.clone()}</span>
                                        <span style="font-size: 12px; color: var(--text-muted);">
                                            "Iter " {exec.current_iteration}
                                        </span>
                                        {if cost > 0.0 {
                                            Some(view! { <span class="exec-cost">{format!("${:.4}", cost)}</span> })
                                        } else { None }}
                                        <span class="exec-score">{score_str}</span>
                                        {if exec.state == "failed" {
                                            Some(view! { <span style="font-size: 11px; color: var(--error);">"(click for details)"</span> })
                                        } else { None }}
                                        <div style="display: flex; gap: 6px;">
                                            {if is_running {
                                                let pf = pause_fn.clone();
                                                let ep = eid_pause.clone();
                                                Some(view! {
                                                    <button class="btn btn-secondary" on:click=move |ev| {
                                                        ev.stop_propagation();
                                                        pf(ep.clone());
                                                    }>"Pause"</button>
                                                })
                                            } else { None }}
                                            {if is_paused {
                                                let rf = resume_fn.clone();
                                                let er = eid_resume.clone();
                                                Some(view! {
                                                    <button class="btn btn-primary" on:click=move |ev| {
                                                        ev.stop_propagation();
                                                        rf(er.clone());
                                                    }>"Resume"</button>
                                                })
                                            } else { None }}
                                            {if is_running || is_paused {
                                                let sf = stop_fn.clone();
                                                let es = eid_stop.clone();
                                                Some(view! {
                                                    <button class="btn btn-danger" on:click=move |ev| {
                                                        ev.stop_propagation();
                                                        sf(es.clone());
                                                    }>"Stop"</button>
                                                })
                                            } else { None }}
                                        </div>
                                    </div>
                                    {move || {
                                        let expanded = state_inner.expanded_execution.get();
                                        if expanded.as_deref() == Some(eid_for_detail.as_str()) {
                                            Some(view! { <ExecutionDetailPanel /> })
                                        } else {
                                            None
                                        }
                                    }}
                                </div>
                            }
                        }).collect_view().into_any()
                    }
                }}
            </div>
        </div>
    }
}
