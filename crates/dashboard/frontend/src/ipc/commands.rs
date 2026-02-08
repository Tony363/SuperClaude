//! Tauri invoke() wrappers for calling backend commands from WASM.

use serde::{de::DeserializeOwned, Serialize};
use wasm_bindgen::prelude::*;
use wasm_bindgen_futures::JsFuture;

#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(js_namespace = ["window", "__TAURI__", "core"])]
    async fn invoke(cmd: &str, args: JsValue) -> JsValue;
}

/// Call a Tauri backend command with typed arguments and response.
pub async fn tauri_invoke<A: Serialize, R: DeserializeOwned>(
    cmd: &str,
    args: &A,
) -> Result<R, String> {
    let args_js = serde_wasm_bindgen::to_value(args).map_err(|e| e.to_string())?;
    let result = invoke(cmd, args_js).await;

    // Check for error
    if result.is_undefined() || result.is_null() {
        return Err("Null response from backend".to_string());
    }

    serde_wasm_bindgen::from_value(result).map_err(|e| e.to_string())
}

/// Call a command with no arguments.
pub async fn tauri_invoke_no_args<R: DeserializeOwned>(cmd: &str) -> Result<R, String> {
    let empty = serde_json::json!({});
    tauri_invoke(cmd, &empty).await
}
