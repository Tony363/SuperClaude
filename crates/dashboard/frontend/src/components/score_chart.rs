//! SVG line chart for quality score progression.

use leptos::prelude::*;

use crate::state::{AgentEventDto, AppState};

#[component]
pub fn ScoreChart() -> impl IntoView {
    let state = expect_context::<AppState>();

    let scores = move || {
        state
            .events
            .get()
            .iter()
            .filter(|e| e.event_type == "score_updated" || e.event_type == "iteration_completed")
            .filter_map(|e| e.data.get("score").or(e.data.get("new_score")).and_then(|v| v.as_f64()))
            .collect::<Vec<f64>>()
    };

    let chart_path = move || {
        let pts = scores();
        if pts.is_empty() {
            return String::new();
        }
        let w = 560.0_f64;
        let h = 180.0_f64;
        let n = pts.len() as f64;
        let step = if n > 1.0 { w / (n - 1.0) } else { w };

        pts.iter()
            .enumerate()
            .map(|(i, &score)| {
                let x = i as f64 * step;
                let y = h - (score / 100.0 * h);
                if i == 0 {
                    format!("M {x:.1} {y:.1}")
                } else {
                    format!("L {x:.1} {y:.1}")
                }
            })
            .collect::<Vec<_>>()
            .join(" ")
    };

    let area_path = move || {
        let pts = scores();
        if pts.is_empty() {
            return String::new();
        }
        let w = 560.0_f64;
        let h = 180.0_f64;
        let n = pts.len() as f64;
        let step = if n > 1.0 { w / (n - 1.0) } else { w };

        let mut path = pts
            .iter()
            .enumerate()
            .map(|(i, &score)| {
                let x = i as f64 * step;
                let y = h - (score / 100.0 * h);
                if i == 0 {
                    format!("M {x:.1} {y:.1}")
                } else {
                    format!("L {x:.1} {y:.1}")
                }
            })
            .collect::<Vec<_>>()
            .join(" ");

        let last_x = (pts.len() - 1) as f64 * step;
        path.push_str(&format!(" L {last_x:.1} {h:.1} L 0 {h:.1} Z"));
        path
    };

    // Threshold line at 70%
    let threshold_y = move || 180.0 - (70.0 / 100.0 * 180.0);

    view! {
        <div class="score-chart">
            <svg viewBox="0 0 560 200" preserveAspectRatio="xMidYMid meet">
                // Threshold line
                <line
                    x1="0" y1={move || format!("{:.1}", threshold_y())}
                    x2="560" y2={move || format!("{:.1}", threshold_y())}
                    class="threshold-line"
                />
                <text x="565" y={move || format!("{:.1}", threshold_y() + 4.0)}
                      class="chart-label">"70%"</text>

                // Area fill
                <path d={area_path} class="chart-area" />

                // Line
                <path d={chart_path} class="chart-line" />

                // Score dots
                {move || {
                    let pts = scores();
                    let w = 560.0_f64;
                    let h = 180.0_f64;
                    let n = pts.len() as f64;
                    let step = if n > 1.0 { w / (n - 1.0) } else { w };
                    pts.iter().enumerate().map(|(i, &score)| {
                        let x = i as f64 * step;
                        let y = h - (score / 100.0 * h);
                        view! {
                            <circle cx={format!("{x:.1}")} cy={format!("{y:.1}")} r="4" class="chart-dot" />
                        }
                    }).collect_view()
                }}

                // Y-axis labels
                <text x="-5" y="10" class="chart-label" text-anchor="end">"100"</text>
                <text x="-5" y="100" class="chart-label" text-anchor="end">"50"</text>
                <text x="-5" y="185" class="chart-label" text-anchor="end">"0"</text>
            </svg>
        </div>
    }
}
