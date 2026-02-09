//! Page header component.

use leptos::prelude::*;

#[component]
pub fn PageHeader(
    #[prop(into)] title: String,
    #[prop(into)] subtitle: String,
) -> impl IntoView {
    view! {
        <div class="page-header">
            <h2>{title}</h2>
            <p>{subtitle}</p>
        </div>
    }
}
