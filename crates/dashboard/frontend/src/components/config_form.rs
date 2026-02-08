//! Configuration form for execution settings.

use leptos::prelude::*;
use std::sync::Arc;

#[component]
pub fn ConfigForm(
    on_submit: Arc<dyn Fn(String, i32, f32, String) + Send + Sync>,
) -> impl IntoView {
    let task = RwSignal::new(String::new());
    let max_iter = RwSignal::new(3_i32);
    let threshold = RwSignal::new(70.0_f32);
    let model = RwSignal::new("sonnet".to_string());
    let task_error = RwSignal::new(Option::<String>::None);
    let submitting = RwSignal::new(false);

    let on_submit = on_submit.clone();
    let handle_submit = move |_| {
        let task_val = task.get();

        // Validation
        if task_val.trim().is_empty() {
            task_error.set(Some("Task description is required".to_string()));
            return;
        }
        if task_val.len() < 3 {
            task_error.set(Some("Task must be at least 3 characters".to_string()));
            return;
        }

        task_error.set(None);
        submitting.set(true);

        on_submit(
            task_val,
            max_iter.get(),
            threshold.get(),
            model.get(),
        );

        // Reset submitting state after a brief delay
        wasm_bindgen_futures::spawn_local(async move {
            gloo_timers::future::TimeoutFuture::new(1000).await;
            submitting.set(false);
        });
    };

    view! {
        <div class="card" style="margin-bottom: 16px;">
            <div class="form-group">
                <label class="form-label">"Task Description"</label>
                <textarea
                    class="form-textarea"
                    placeholder="Describe the task to execute..."
                    on:input=move |ev| {
                        task.set(event_target_value(&ev));
                        task_error.set(None);
                    }
                    prop:value=move || task.get()
                ></textarea>
                {move || {
                    task_error.get().map(|err| view! {
                        <div class="error-text">{err}</div>
                    })
                }}
            </div>

            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px;">
                <div class="form-group">
                    <label class="form-label">"Max Iterations"</label>
                    <input
                        class="form-input"
                        type="number"
                        min="1" max="10"
                        on:input=move |ev| {
                            if let Ok(v) = event_target_value(&ev).parse() {
                                max_iter.set(v);
                            }
                        }
                        prop:value=move || max_iter.get().to_string()
                    />
                </div>

                <div class="form-group">
                    <label class="form-label">"Quality Threshold"</label>
                    <input
                        class="form-input"
                        type="number"
                        min="0" max="100" step="5"
                        on:input=move |ev| {
                            if let Ok(v) = event_target_value(&ev).parse() {
                                threshold.set(v);
                            }
                        }
                        prop:value=move || format!("{:.0}", threshold.get())
                    />
                </div>

                <div class="form-group">
                    <label class="form-label">"Model"</label>
                    <select
                        class="form-select"
                        on:change=move |ev| model.set(event_target_value(&ev))
                    >
                        <option value="sonnet" selected=move || model.get() == "sonnet">"Sonnet"</option>
                        <option value="opus" selected=move || model.get() == "opus">"Opus"</option>
                        <option value="haiku" selected=move || model.get() == "haiku">"Haiku"</option>
                    </select>
                </div>
            </div>

            <button
                class="btn btn-primary"
                on:click=handle_submit
                disabled=move || submitting.get()
            >
                {move || if submitting.get() { "Starting..." } else { "Start Execution" }}
            </button>
        </div>
    }
}
