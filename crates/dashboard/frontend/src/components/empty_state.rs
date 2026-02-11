//! Empty state component with optional icon and action button.

use leptos::prelude::*;

#[component]
pub fn EmptyState(
    title: String,
    message: String,
    #[prop(optional)] icon: Option<String>,
    #[prop(optional)] action: Option<(String, Callback<()>)>,
) -> impl IntoView {
    view! {
        <div class="empty-state">
            {icon.map(|i| view! { <div class="empty-icon">{i}</div> })}
            <h3>{title}</h3>
            <p>{message}</p>
            {action.map(|(label, cb)| view! {
                <button class="btn-primary" on:click=move |_| cb.run(())>
                    {label}
                </button>
            })}
        </div>
    }
}
