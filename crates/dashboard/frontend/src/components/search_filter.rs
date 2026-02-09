//! Search bar and filter buttons for inventory.

use leptos::prelude::*;

use crate::state::AppState;

#[component]
pub fn SearchFilter() -> impl IntoView {
    let state = expect_context::<AppState>();

    let on_input = move |ev: leptos::ev::Event| {
        let val = event_target_value(&ev);
        state.search_query.set(val);
    };

    let kinds = vec!["agent", "trait", "extension", "command", "skill", "mode"];

    let set_filter = move |kind: &'static str| {
        move |_| {
            let current = state.kind_filter.get();
            if current.as_deref() == Some(kind) {
                state.kind_filter.set(None);
            } else {
                state.kind_filter.set(Some(kind.to_string()));
            }
        }
    };

    let is_active = move |kind: &'static str| {
        move || {
            if state.kind_filter.get().as_deref() == Some(kind) {
                "filter-btn active"
            } else {
                "filter-btn"
            }
        }
    };

    view! {
        <div class="search-bar">
            <input
                class="search-input"
                type="text"
                placeholder="Search agents, commands, skills..."
                on:input=on_input
                prop:value={move || state.search_query.get()}
            />
            {kinds.into_iter().map(|k| view! {
                <button class={is_active(k)} on:click={set_filter(k)}>{k}</button>
            }).collect_view()}
        </div>
    }
}
