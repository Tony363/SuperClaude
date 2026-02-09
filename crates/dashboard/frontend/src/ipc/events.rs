//! Tauri listen() bindings for receiving backend events in WASM.

use serde::de::DeserializeOwned;
use wasm_bindgen::prelude::*;

#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = ["window", "__TAURI__", "event"])]
    async fn listen(event: &str, handler: &Closure<dyn FnMut(JsValue)>) -> JsValue;
}

/// Listen for a Tauri event and call the handler with the deserialized payload.
///
/// Returns a closure that, when dropped, will unlisten.
pub fn tauri_listen<T, F>(event_name: &str, mut callback: F)
where
    T: DeserializeOwned + 'static,
    F: FnMut(T) + 'static,
{
    let event_name = event_name.to_string();
    let closure = Closure::new(move |val: JsValue| {
        // Tauri events have { event, payload } structure
        if let Ok(event_obj) = js_sys::Reflect::get(&val, &"payload".into()) {
            if let Ok(payload) = serde_wasm_bindgen::from_value::<T>(event_obj) {
                callback(payload);
            }
        }
    });

    wasm_bindgen_futures::spawn_local(async move {
        let _unlisten = listen(&event_name, &closure).await;
        // Keep closure alive — it won't be called after drop
        closure.forget();
    });
}
