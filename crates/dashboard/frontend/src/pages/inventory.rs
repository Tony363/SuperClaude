//! Feature Inventory page — grid of all agents, commands, skills, modes.

use leptos::prelude::*;

use crate::components::agent_card::AgentCard;
use crate::components::empty_state::EmptyState;
use crate::components::header::PageHeader;
use crate::components::loading_spinner::LoadingSpinner;
use crate::components::search_filter::SearchFilter;
use crate::state::AppState;

#[component]
pub fn InventoryPage() -> impl IntoView {
    let state = expect_context::<AppState>();

    let filtered_items = move || {
        let inv = state.inventory.get();
        let query = state.search_query.get().to_lowercase();
        let kind_filter = state.kind_filter.get();

        inv.items
            .into_iter()
            .filter(|item| {
                if let Some(ref kind) = kind_filter {
                    if item.kind != *kind {
                        return false;
                    }
                }
                if query.is_empty() {
                    return true;
                }
                item.name.to_lowercase().contains(&query)
                    || item.description.to_lowercase().contains(&query)
                    || item.triggers.iter().any(|t| t.to_lowercase().contains(&query))
                    || item.category.to_lowercase().contains(&query)
            })
            .collect::<Vec<_>>()
    };

    let counts = move || {
        let inv = state.inventory.get();
        let agents = inv.items.iter().filter(|i| i.kind == "agent").count();
        let traits = inv.items.iter().filter(|i| i.kind == "trait").count();
        let extensions = inv.items.iter().filter(|i| i.kind == "extension").count();
        let commands = inv.items.iter().filter(|i| i.kind == "command").count();
        let skills = inv.items.iter().filter(|i| i.kind == "skill").count();
        let modes = inv.items.iter().filter(|i| i.kind == "mode").count();
        (agents, traits, extensions, commands, skills, modes)
    };

    view! {
        <div>
            <PageHeader
                title="Feature Inventory"
                subtitle="Browse all agents, commands, skills, and modes"
            />

            <div class="stat-grid">
                <div class="stat-card">
                    <div class="stat-value">{move || counts().0}</div>
                    <div class="stat-label">"Core Agents"</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{move || counts().1}</div>
                    <div class="stat-label">"Traits"</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{move || counts().2}</div>
                    <div class="stat-label">"Extensions"</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{move || counts().3}</div>
                    <div class="stat-label">"Commands"</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{move || counts().4}</div>
                    <div class="stat-label">"Skills"</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{move || counts().5}</div>
                    <div class="stat-label">"Modes"</div>
                </div>
            </div>

            <SearchFilter />

            {move || {
                if state.inventory_loading.get() {
                    view! {
                        <LoadingSpinner text=Some("Loading inventory...".to_string()) />
                    }.into_any()
                } else {
                    view! {
                        <div class="card-grid">
                            {move || {
                                let items = filtered_items();
                                if items.is_empty() {
                                    view! {
                                        <EmptyState
                                            title="No items found".to_string()
                                            message="Try adjusting your search or filters".to_string()
                                            icon=Some("🔍".to_string())
                                        />
                                    }.into_any()
                                } else {
                                    items.into_iter().map(|item| {
                                        view! { <AgentCard item=item /> }
                                    }).collect_view().into_any()
                                }
                            }}
                        </div>
                    }.into_any()
                }
            }}
        </div>
    }
}
