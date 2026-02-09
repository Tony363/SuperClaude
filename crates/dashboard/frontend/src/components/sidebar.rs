//! Sidebar navigation component.

use leptos::prelude::*;

use crate::state::{AppState, DaemonStatusDto, Page};

#[component]
pub fn Sidebar() -> impl IntoView {
    let state = expect_context::<AppState>();

    let set_page = move |page: Page| {
        move |_| state.current_page.set(page)
    };

    let is_active = move |page: Page| {
        move || {
            if state.current_page.get() == page {
                "nav-item active"
            } else {
                "nav-item"
            }
        }
    };

    let daemon_online = move || state.daemon_status.get().online;
    let daemon_dot_class = move || {
        if daemon_online() {
            "status-dot online"
        } else {
            "status-dot"
        }
    };
    let daemon_label = move || {
        let status = state.daemon_status.get();
        if status.online {
            format!("Daemon v{}", status.version)
        } else {
            "Daemon offline".to_string()
        }
    };

    view! {
        <aside class="sidebar">
            <div class="sidebar-header">
                <h1>"SuperClaude"</h1>
                <div class="version">"Dashboard v0.1.0"</div>
            </div>

            <nav class="sidebar-nav">
                <div class={is_active(Page::Inventory)} on:click={set_page(Page::Inventory)}>
                    <span class="nav-icon">"#"</span>
                    <span>"Inventory"</span>
                </div>
                <div class={is_active(Page::Monitor)} on:click={set_page(Page::Monitor)}>
                    <span class="nav-icon">"~"</span>
                    <span>"Monitor"</span>
                </div>
                <div class={is_active(Page::Control)} on:click={set_page(Page::Control)}>
                    <span class="nav-icon">">"</span>
                    <span>"Control"</span>
                </div>
                <div class={is_active(Page::History)} on:click={set_page(Page::History)}>
                    <span class="nav-icon">"@"</span>
                    <span>"History"</span>
                </div>
            </nav>

            <div class="sidebar-footer">
                <div class="daemon-status">
                    <span class={daemon_dot_class}></span>
                    <span>{daemon_label}</span>
                </div>
            </div>
        </aside>
    }
}
