//! Scrolling event log component.

use leptos::prelude::*;

use crate::state::{AgentEventDto, AppState};

#[component]
pub fn EventLog() -> impl IntoView {
    let state = expect_context::<AppState>();

    let events = move || {
        let evts = state.events.get();
        // Show most recent first, limit to 100
        evts.into_iter().rev().take(100).collect::<Vec<_>>()
    };

    view! {
        <div class="event-log">
            {move || {
                let evts = events();
                if evts.is_empty() {
                    view! {
                        <div class="empty-state">
                            <h3>"No events yet"</h3>
                            <p>"Events will appear here when an execution is running."</p>
                        </div>
                    }.into_any()
                } else {
                    evts.into_iter().map(|evt| {
                        let data_str = evt.data.to_string();
                        let data_str = if data_str.len() > 120 {
                            format!("{}...", &data_str[..120])
                        } else {
                            data_str
                        };
                        view! {
                            <div class="event-log-entry">
                                <span class="event-type">{evt.event_type.clone()}</span>
                                <span class="event-data">{data_str}</span>
                            </div>
                        }
                    }).collect_view().into_any()
                }
            }}
        </div>
    }
}
