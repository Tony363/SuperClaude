//! Loading spinner component with optional text.

use leptos::prelude::*;

#[component]
pub fn LoadingSpinner(
    #[prop(optional)] text: Option<String>,
) -> impl IntoView {
    view! {
        <div class="loading-container">
            <div class="spinner"></div>
            {text.map(|t| view! { <p>{t}</p> })}
        </div>
    }
}
