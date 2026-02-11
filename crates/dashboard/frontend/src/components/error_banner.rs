//! Error banner component with optional retry action.

use leptos::prelude::*;

#[component]
pub fn ErrorBanner(
    message: String,
    #[prop(optional)] retry: Option<Callback<()>>,
) -> impl IntoView {
    view! {
        <div class="error-banner">
            <div class="error-icon">"⚠️"</div>
            <div class="error-content">
                <strong>"Error"</strong>
                <p>{message}</p>
            </div>
            {retry.map(|cb| view! {
                <button class="btn-secondary" on:click=move |_| cb.run(())>
                    "Retry"
                </button>
            })}
        </div>
    }
}
