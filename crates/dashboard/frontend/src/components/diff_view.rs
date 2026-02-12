//! Diff view component for showing file changes with old/new content.

use leptos::prelude::*;

#[component]
pub fn DiffView(
    #[prop(into)] file_path: String,
    #[prop(into)] action: String,
    #[prop(into, default = String::new())] old_string: String,
    #[prop(into, default = String::new())] new_string: String,
    #[prop(into, default = String::new())] content: String,
) -> impl IntoView {
    let path_display = file_path.clone();

    match action.as_str() {
        "edit" => {
            view! {
                <div class="diff-view">
                    <div class="diff-header">"Edit: " {path_display}</div>
                    {if !old_string.is_empty() {
                        let old_display = old_string.clone();
                        Some(view! {
                            <div class="diff-block diff-removed">
                                <div class="diff-block-header">"Removed"</div>
                                <pre class="diff-content">{old_display}</pre>
                            </div>
                        })
                    } else {
                        None
                    }}
                    {if !new_string.is_empty() {
                        let new_display = new_string.clone();
                        Some(view! {
                            <div class="diff-block diff-added">
                                <div class="diff-block-header">"Added"</div>
                                <pre class="diff-content">{new_display}</pre>
                            </div>
                        })
                    } else {
                        None
                    }}
                </div>
            }.into_any()
        }
        "write" => {
            view! {
                <div class="diff-view">
                    <div class="diff-header">"New File: " {path_display}</div>
                    <div class="diff-block diff-added">
                        <div class="diff-block-header">"New File"</div>
                        <pre class="diff-content">{content}</pre>
                    </div>
                </div>
            }.into_any()
        }
        _ => view! { <div></div> }.into_any(),
    }
}
