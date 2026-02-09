//! Status badge component for execution states.

use leptos::prelude::*;

#[component]
pub fn StatusBadge(#[prop(into)] status: String) -> impl IntoView {
    let class = match status.as_str() {
        "running" => "status-badge status-running",
        "completed" => "status-badge status-completed",
        "failed" => "status-badge status-failed",
        "paused" => "status-badge status-paused",
        "pending" => "status-badge status-pending",
        _ => "status-badge",
    };

    view! {
        <span class={class}>{status}</span>
    }
}
