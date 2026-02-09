// Prevents additional console window on Windows
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod bridge;
mod commands;
mod state;

use state::AppState;
use std::path::PathBuf;
use tauri::Manager;

fn main() {
    tracing_subscriber::fmt::init();

    let project_root = PathBuf::from("/home/tony/Desktop/SuperClaude");

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let state = AppState::new(project_root);
            app.manage(state);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::config::ping_daemon,
            commands::config::get_daemon_config,
            commands::inventory::get_inventory,
            commands::inventory::get_agent_config,
            commands::execution::start_execution,
            commands::execution::stop_execution,
            commands::execution::pause_execution,
            commands::execution::resume_execution,
            commands::execution::list_executions,
            commands::execution::subscribe_events,
            commands::metrics::get_historical_events,
            commands::metrics::get_historical_metrics,
            commands::metrics::get_execution_events,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
