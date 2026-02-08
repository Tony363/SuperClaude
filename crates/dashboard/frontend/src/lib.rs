//! SuperClaude Dashboard — Leptos WASM frontend.

pub mod app;
pub mod components;
pub mod ipc;
pub mod pages;
pub mod state;

use leptos::*;
use wasm_bindgen::prelude::*;

/// WASM entry point — mount the Leptos app.
#[wasm_bindgen]
pub fn hydrate() {
    console_error_panic_hook::set_once();
    console_log::init_with_level(log::Level::Debug).expect("error initializing logger");

    leptos::mount::mount_to_body(app::App);
}
