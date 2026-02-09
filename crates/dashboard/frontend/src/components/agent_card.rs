//! Card component for displaying an inventory item.

use leptos::prelude::*;

use crate::state::InventoryItemDto;

#[component]
pub fn AgentCard(item: InventoryItemDto) -> impl IntoView {
    let kind_class = match item.kind.as_str() {
        "agent" => "badge badge-agent",
        "trait" => "badge badge-trait",
        "extension" => "badge badge-extension",
        "command" => "badge badge-command",
        "skill" => "badge badge-skill",
        "mode" => "badge badge-mode",
        _ => "badge",
    };

    let triggers = item.triggers.clone();
    let tools = item.tools.clone();

    view! {
        <div class="card">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
                <span class="card-title">{item.name.clone()}</span>
                <span class={kind_class}>{item.kind.clone()}</span>
            </div>
            <div class="card-description">{item.description.clone()}</div>
            <div class="card-meta">
                {triggers.into_iter().map(|t| view! {
                    <span class="badge badge-trigger">{t}</span>
                }).collect_view()}
                {tools.into_iter().map(|t| view! {
                    <span class="badge badge-tool">{t}</span>
                }).collect_view()}
            </div>
        </div>
    }
}
