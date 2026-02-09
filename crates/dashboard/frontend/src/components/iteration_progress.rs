//! Iteration progress bar component.

use leptos::prelude::*;

#[component]
pub fn IterationProgress(
    #[prop(into)] current: Signal<i32>,
    #[prop(into)] max: Signal<i32>,
    #[prop(into)] score: Signal<f32>,
) -> impl IntoView {
    let progress_pct = move || {
        let m = max.get();
        if m > 0 {
            (current.get() as f32 / m as f32 * 100.0).min(100.0)
        } else {
            0.0
        }
    };

    let fill_class = move || {
        let s = score.get();
        if s >= 70.0 {
            "progress-fill success"
        } else if s >= 40.0 {
            "progress-fill warning"
        } else {
            "progress-fill"
        }
    };

    view! {
        <div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                <span style="font-size: 12px; color: var(--text-secondary);">
                    "Iteration " {move || current.get()} " / " {move || max.get()}
                </span>
                <span style="font-size: 12px; font-family: var(--font-mono); font-weight: 600;">
                    {move || format!("{:.0}%", score.get())}
                </span>
            </div>
            <div class="progress-bar">
                <div class={fill_class} style={move || format!("width: {}%", progress_pct())}></div>
            </div>
        </div>
    }
}
