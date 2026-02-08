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

    // Listen for agent events
    {
        let state = state.clone();
        tauri_listen("agent-event", move |event: AgentEventDto| {
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
