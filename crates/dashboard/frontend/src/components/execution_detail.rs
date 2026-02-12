//! Expandable execution detail panel component.

use leptos::prelude::*;
use crate::components::diff_view::DiffView;
use crate::components::execution_tree::ExecutionTree;
use crate::state::{AppState, ExecutionDetailDto, ScoreDimensionDto, RunInstructionsDto, AgentEventDto};

#[component]
pub fn ExecutionDetailPanel() -> impl IntoView {
    let state = expect_context::<AppState>();

    view! {
        {move || {
            if state.detail_loading.get() {
                return view! {
                    <div class="exec-detail-panel">
                        <div class="loading"><div class="spinner"></div></div>
                    </div>
                }.into_any();
            }

            match state.execution_detail.get() {
                None => view! { <div></div> }.into_any(),
                Some(detail) => {
                    view! { <DetailContent detail=detail /> }.into_any()
                }
            }
        }}
    }
}

#[component]
fn DetailContent(detail: ExecutionDetailDto) -> impl IntoView {
    let active_tab = RwSignal::new(0_usize);

    let is_failed = detail.state == "failed";
    let termination_reason = detail.termination_reason.clone();

    let detail_for_run = detail.clone();
    let detail_for_log = detail.clone();
    let detail_for_files = detail.clone();
    let detail_for_quality = detail.clone();

    view! {
        <div class="exec-detail-panel">
            {if is_failed && !termination_reason.is_empty() {
                let reason = termination_reason.clone();
                Some(view! {
                    <div class="error-banner">
                        <span class="error-icon">"!"</span>
                        <div class="error-content">
                            <strong>"Execution Failed"</strong>
                            <p>{reason}</p>
                        </div>
                    </div>
                })
            } else {
                None
            }}

            <div class="detail-tab-bar">
                <button
                    class=move || if active_tab.get() == 0 { "detail-tab active" } else { "detail-tab" }
                    on:click=move |_| active_tab.set(0)
                >
                    "Run Instructions"
                </button>
                <button
                    class=move || if active_tab.get() == 1 { "detail-tab active" } else { "detail-tab" }
                    on:click=move |_| active_tab.set(1)
                >
                    "Execution Log"
                </button>
                <button
                    class=move || if active_tab.get() == 2 { "detail-tab active" } else { "detail-tab" }
                    on:click=move |_| active_tab.set(2)
                >
                    "Files Changed"
                </button>
                <button
                    class=move || if active_tab.get() == 3 { "detail-tab active" } else { "detail-tab" }
                    on:click=move |_| active_tab.set(3)
                >
                    "Quality Breakdown"
                </button>
                <button
                    class=move || if active_tab.get() == 4 { "detail-tab active" } else { "detail-tab" }
                    on:click=move |_| active_tab.set(4)
                >
                    "Execution Tree"
                </button>
            </div>

            {move || {
                let tab = active_tab.get();
                match tab {
                    0 => {
                        let d = detail_for_run.clone();
                        view! { <RunInstructionsTab run_instructions=d.run_instructions /> }.into_any()
                    }
                    1 => {
                        let d = detail_for_log.clone();
                        view! { <ExecutionLogTab events=d.events.clone() /> }.into_any()
                    }
                    2 => {
                        let d = detail_for_files.clone();
                        view! { <FilesChangedTab files_written=d.files_written.clone() files_edited=d.files_edited.clone() events=d.events.clone() /> }.into_any()
                    }
                    3 => {
                        let d = detail_for_quality.clone();
                        view! { <QualityBreakdownTab breakdown=d.score_breakdown.clone() /> }.into_any()
                    }
                    4 => {
                        view! { <ExecutionTree /> }.into_any()
                    }
                    _ => view! { <div></div> }.into_any(),
                }
            }}
        </div>
    }
}

/// Copy text to clipboard via the Web Clipboard API.
fn copy_to_clipboard(text: &str) {
    if let Some(clipboard) = web_sys::window().map(|w| w.navigator().clipboard()) {
        let _ = clipboard.write_text(text);
    }
}

#[component]
fn CopyableCommand(#[prop(into)] label: String, #[prop(into)] command: String) -> impl IntoView {
    if command.is_empty() {
        return view! { <div></div> }.into_any();
    }

    let cmd_for_copy = command.clone();
    let cmd_for_display = command.clone();

    view! {
        <div style="margin-bottom: 8px;">
            <div class="log-label">{label}</div>
            <div class="copyable-cmd">
                <code>{cmd_for_display}</code>
                <button class="btn-copy" on:click=move |_| {
                    copy_to_clipboard(&cmd_for_copy);
                }>"Copy"</button>
            </div>
        </div>
    }.into_any()
}

#[component]
fn RunInstructionsTab(run_instructions: Option<RunInstructionsDto>) -> impl IntoView {
    match run_instructions {
        None => view! {
            <div class="detail-section-empty">"No run instructions available."</div>
        }.into_any(),
        Some(ri) => {
            let build = ri.build_command.clone();
            let run = ri.run_command.clone();
            let notes = ri.notes.clone();
            let artifacts = ri.artifacts.clone();

            view! {
                <div>
                    <CopyableCommand label="Build Command".to_string() command=build />
                    <CopyableCommand label="Run Command".to_string() command=run />

                    {if !artifacts.is_empty() {
                        let arts = artifacts.clone();
                        Some(view! {
                            <div style="margin-bottom: 8px;">
                                <div class="log-label">"Artifacts"</div>
                                <div class="files-changed">
                                    {arts.into_iter().map(|a| {
                                        view! {
                                            <div class="file-entry">
                                                <span class="file-path">{a}</span>
                                            </div>
                                        }
                                    }).collect_view()}
                                </div>
                            </div>
                        })
                    } else {
                        None
                    }}

                    {if !notes.is_empty() {
                        let n = notes.clone();
                        Some(view! {
                            <div>
                                <div class="log-label">"Notes"</div>
                                <div class="log-pre">{n}</div>
                            </div>
                        })
                    } else {
                        None
                    }}
                </div>
            }.into_any()
        }
    }
}

#[component]
fn ExecutionLogTab(events: Vec<AgentEventDto>) -> impl IntoView {
    if events.is_empty() {
        return view! {
            <div class="detail-section-empty">"No events recorded."</div>
        }.into_any();
    }

    view! {
        <div class="execution-log">
            {events.into_iter().enumerate().map(|(i, evt)| {
                view! { <LogEntry index=i event=evt /> }
            }).collect_view()}
        </div>
    }.into_any()
}

#[component]
fn LogEntry(index: usize, event: AgentEventDto) -> impl IntoView {
    let expanded = RwSignal::new(false);

    let tool_name = event.data.get("tool_name")
        .and_then(|v| v.as_str())
        .unwrap_or(&event.event_type)
        .to_string();

    let summary = event.data.get("summary")
        .and_then(|v| v.as_str())
        .unwrap_or("")
        .to_string();

    let tool_input = event.data.get("tool_input")
        .map(|v| serde_json::to_string_pretty(v).unwrap_or_default())
        .unwrap_or_default();

    let tool_output = event.data.get("tool_output")
        .map(|v| serde_json::to_string_pretty(v).unwrap_or_default())
        .unwrap_or_default();

    let has_details = !tool_input.is_empty() || !tool_output.is_empty();
    let tool_input_display = tool_input.clone();
    let tool_output_display = tool_output.clone();

    view! {
        <div class="log-entry">
            <div class="log-entry-header" on:click=move |_| {
                if has_details {
                    expanded.set(!expanded.get());
                }
            }>
                <span class="log-entry-num">{index + 1}</span>
                <span class="log-entry-tool">{tool_name.clone()}</span>
                <span class="log-entry-summary">{summary.clone()}</span>
                {if has_details {
                    Some(view! {
                        <span style="font-size: 11px; color: var(--text-muted);">
                            {move || if expanded.get() { "v" } else { ">" }}
                        </span>
                    })
                } else {
                    None
                }}
            </div>
            {move || {
                if !expanded.get() {
                    return view! { <div></div> }.into_any();
                }
                let ti = tool_input_display.clone();
                let to = tool_output_display.clone();
                view! {
                    <div class="log-entry-detail">
                        {if !ti.is_empty() {
                            let ti2 = ti.clone();
                            Some(view! {
                                <div class="log-label">"Input"</div>
                                <pre class="log-pre">{ti2}</pre>
                            })
                        } else {
                            None
                        }}
                        {if !to.is_empty() {
                            let to2 = to.clone();
                            Some(view! {
                                <div class="log-label">"Output"</div>
                                <pre class="log-pre">{to2}</pre>
                            })
                        } else {
                            None
                        }}
                    </div>
                }.into_any()
            }}
        </div>
    }
}

/// A file diff entry extracted from tool events.
struct FileDiffEntry {
    file_path: String,
    action: String, // "edit" or "write"
    old_string: Option<String>,
    new_string: Option<String>,
    content: Option<String>,
}

fn extract_diff_entries(events: &[AgentEventDto]) -> Vec<FileDiffEntry> {
    let mut entries = Vec::new();
    for evt in events {
        if evt.event_type != "tool_invoked" {
            continue;
        }
        let tool_name = evt.data.get("tool_name").and_then(|v| v.as_str()).unwrap_or("");
        let summary = evt.data.get("summary").and_then(|v| v.as_str()).unwrap_or("");
        // Skip "(result)" pseudo-events
        if summary == "(result)" {
            continue;
        }
        if tool_name != "Edit" && tool_name != "Write" {
            continue;
        }
        let tool_input_str = evt.data.get("tool_input").and_then(|v| v.as_str()).unwrap_or("");
        if tool_input_str.is_empty() {
            continue;
        }
        if let Ok(input) = serde_json::from_str::<serde_json::Value>(tool_input_str) {
            let file_path = input.get("file_path")
                .and_then(|v| v.as_str())
                .unwrap_or("")
                .to_string();
            if file_path.is_empty() {
                continue;
            }
            if tool_name == "Edit" {
                entries.push(FileDiffEntry {
                    file_path,
                    action: "edit".to_string(),
                    old_string: input.get("old_string").and_then(|v| v.as_str()).map(String::from),
                    new_string: input.get("new_string").and_then(|v| v.as_str()).map(String::from),
                    content: None,
                });
            } else {
                entries.push(FileDiffEntry {
                    file_path,
                    action: "write".to_string(),
                    old_string: None,
                    new_string: None,
                    content: input.get("content").and_then(|v| v.as_str()).map(String::from),
                });
            }
        }
    }
    entries
}

#[component]
fn FilesChangedTab(files_written: Vec<String>, files_edited: Vec<String>, events: Vec<AgentEventDto>) -> impl IntoView {
    let diff_entries = extract_diff_entries(&events);
    let has_diffs = !diff_entries.is_empty();

    if files_written.is_empty() && files_edited.is_empty() && !has_diffs {
        return view! {
            <div class="detail-section-empty">"No file changes recorded."</div>
        }.into_any();
    }

    // Build a set of files that have diff entries
    let diff_paths: std::collections::HashSet<String> = diff_entries.iter().map(|d| d.file_path.clone()).collect();

    view! {
        <div class="files-changed">
            // Show diff entries with expand/collapse
            {diff_entries.into_iter().enumerate().map(|(_i, entry)| {
                let expanded = RwSignal::new(false);
                let path = entry.file_path.clone();
                let action_badge = if entry.action == "edit" { "M" } else { "A" };
                let badge_class = if entry.action == "edit" { "file-action file-modified" } else { "file-action file-added" };

                let diff_action = entry.action.clone();
                let diff_old = entry.old_string.clone().unwrap_or_default();
                let diff_new = entry.new_string.clone().unwrap_or_default();
                let diff_content = entry.content.clone().unwrap_or_default();
                let diff_path = entry.file_path.clone();

                view! {
                    <div>
                        <div class="file-entry" style="cursor: pointer;" on:click=move |_| expanded.set(!expanded.get())>
                            <span class={badge_class}>{action_badge}</span>
                            <span class="file-path">{path.clone()}</span>
                            <span style="font-size: 11px; color: var(--text-muted);">
                                {move || if expanded.get() { "v" } else { ">" }}
                            </span>
                        </div>
                        {move || {
                            if !expanded.get() {
                                return view! { <div></div> }.into_any();
                            }
                            view! {
                                <div style="padding-left: 30px; padding-top: 4px; padding-bottom: 8px;">
                                    <DiffView
                                        file_path=diff_path.clone()
                                        action=diff_action.clone()
                                        old_string=diff_old.clone()
                                        new_string=diff_new.clone()
                                        content=diff_content.clone()
                                    />
                                </div>
                            }.into_any()
                        }}
                    </div>
                }
            }).collect_view()}

            // Show remaining files that don't have diff entries
            {files_written.into_iter().filter(|f| !diff_paths.contains(f)).map(|f| {
                view! {
                    <div class="file-entry">
                        <span class="file-action file-added">"A"</span>
                        <span class="file-path">{f}</span>
                    </div>
                }
            }).collect_view()}
            {files_edited.into_iter().filter(|f| !diff_paths.contains(f)).map(|f| {
                view! {
                    <div class="file-entry">
                        <span class="file-action file-modified">"M"</span>
                        <span class="file-path">{f}</span>
                    </div>
                }
            }).collect_view()}
        </div>
    }.into_any()
}

#[component]
fn QualityBreakdownTab(breakdown: Vec<ScoreDimensionDto>) -> impl IntoView {
    if breakdown.is_empty() {
        return view! {
            <div class="detail-section-empty">"No quality breakdown available."</div>
        }.into_any();
    }

    view! {
        <div class="quality-breakdown">
            {breakdown.into_iter().map(|dim| {
                let pct = if dim.max_score > 0.0 {
                    (dim.score / dim.max_score * 100.0).min(100.0)
                } else {
                    0.0
                };
                let score_label = format!("{:.1} / {:.1}", dim.score, dim.max_score);
                let bar_width = format!("{}%", pct as i32);
                let bar_class = if pct >= 80.0 {
                    "progress-fill success"
                } else if pct >= 50.0 {
                    "progress-fill warning"
                } else {
                    "progress-fill error"
                };

                view! {
                    <div class="quality-dim">
                        <div class="quality-dim-header">
                            <span class="quality-dim-name">{dim.name.clone()}</span>
                            <span class="quality-dim-score">{score_label}</span>
                        </div>
                        <div class="progress-bar">
                            <div class={bar_class} style=format!("width: {bar_width}") />
                        </div>
                        {if !dim.description.is_empty() {
                            Some(view! {
                                <div class="quality-dim-desc">{dim.description.clone()}</div>
                            })
                        } else {
                            None
                        }}
                    </div>
                }
            }).collect_view()}
        </div>
    }.into_any()
}
