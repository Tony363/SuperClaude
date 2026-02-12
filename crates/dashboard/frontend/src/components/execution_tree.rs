//! Execution tree visualization component — SVG node graph with pan/zoom.

use leptos::prelude::*;
use crate::state::{AppState, ExecutionTree as ExecutionTreeData, TreeNodeStatus, TreeNodeType};

// Layout constants
const NODE_WIDTH: f64 = 140.0;
const NODE_HEIGHT: f64 = 50.0;
const H_GAP: f64 = 20.0;
const V_GAP: f64 = 70.0;
const PADDING: f64 = 40.0;

/// Compute hierarchical tree layout positions in-place.
fn layout_tree(tree: &mut ExecutionTreeData) {
    if tree.nodes.is_empty() {
        return;
    }

    // Build parent -> children adjacency
    let node_ids: Vec<String> = tree.nodes.iter().map(|n| n.node_id.clone()).collect();
    let mut children_map: std::collections::HashMap<String, Vec<String>> = std::collections::HashMap::new();
    let mut has_parent: std::collections::HashSet<String> = std::collections::HashSet::new();

    for edge in &tree.edges {
        children_map
            .entry(edge.from_id.clone())
            .or_default()
            .push(edge.to_id.clone());
        has_parent.insert(edge.to_id.clone());
    }

    // Find root nodes (no parent)
    let roots: Vec<String> = node_ids
        .iter()
        .filter(|id| !has_parent.contains(*id))
        .cloned()
        .collect();

    // DFS layout: assign x positions bottom-up, y by depth
    let mut x_positions: std::collections::HashMap<String, f64> = std::collections::HashMap::new();
    let mut y_positions: std::collections::HashMap<String, f64> = std::collections::HashMap::new();
    let mut next_x = PADDING;

    fn dfs_layout(
        node_id: &str,
        depth: usize,
        children_map: &std::collections::HashMap<String, Vec<String>>,
        x_positions: &mut std::collections::HashMap<String, f64>,
        y_positions: &mut std::collections::HashMap<String, f64>,
        next_x: &mut f64,
    ) {
        let y = PADDING + depth as f64 * (NODE_HEIGHT + V_GAP);
        y_positions.insert(node_id.to_string(), y);

        if let Some(children) = children_map.get(node_id) {
            if !children.is_empty() {
                for child in children {
                    dfs_layout(child, depth + 1, children_map, x_positions, y_positions, next_x);
                }
                // Center parent over children
                let child_xs: Vec<f64> = children
                    .iter()
                    .filter_map(|c| x_positions.get(c).copied())
                    .collect();
                if !child_xs.is_empty() {
                    let min_x = child_xs.iter().cloned().fold(f64::INFINITY, f64::min);
                    let max_x = child_xs.iter().cloned().fold(f64::NEG_INFINITY, f64::max);
                    x_positions.insert(node_id.to_string(), (min_x + max_x) / 2.0);
                } else {
                    x_positions.insert(node_id.to_string(), *next_x);
                    *next_x += NODE_WIDTH + H_GAP;
                }
                return;
            }
        }

        // Leaf node
        x_positions.insert(node_id.to_string(), *next_x);
        *next_x += NODE_WIDTH + H_GAP;
    }

    for root in &roots {
        dfs_layout(root, 0, &children_map, &mut x_positions, &mut y_positions, &mut next_x);
    }

    // Apply computed positions
    for node in &mut tree.nodes {
        node.x = x_positions.get(&node.node_id).copied().unwrap_or(PADDING);
        node.y = y_positions.get(&node.node_id).copied().unwrap_or(PADDING);
    }
}

fn status_class(status: TreeNodeStatus) -> &'static str {
    match status {
        TreeNodeStatus::Success => "tree-node-success",
        TreeNodeStatus::Failed => "tree-node-failed",
        TreeNodeStatus::Running => "tree-node-running",
        TreeNodeStatus::Pending => "tree-node-pending",
    }
}

fn type_icon(node_type: TreeNodeType) -> &'static str {
    match node_type {
        TreeNodeType::Iteration => "I",
        TreeNodeType::ToolCall => "T",
        TreeNodeType::SubagentSpawn => "S",
    }
}

#[component]
pub fn ExecutionTree() -> impl IntoView {
    let state = expect_context::<AppState>();

    let pan_x = RwSignal::new(0.0_f64);
    let pan_y = RwSignal::new(0.0_f64);
    let zoom = RwSignal::new(1.0_f64);
    let dragging = RwSignal::new(false);
    let drag_start_x = RwSignal::new(0.0_f64);
    let drag_start_y = RwSignal::new(0.0_f64);
    let pan_start_x = RwSignal::new(0.0_f64);
    let pan_start_y = RwSignal::new(0.0_f64);

    // Compute the laid-out tree
    let laid_out_tree = move || {
        let mut tree = state.execution_tree.get();
        layout_tree(&mut tree);
        tree
    };

    // Compute SVG viewBox from node positions
    let viewbox = move || {
        let tree = laid_out_tree();
        if tree.nodes.is_empty() {
            return "0 0 600 400".to_string();
        }
        let max_x = tree.nodes.iter().map(|n| n.x + NODE_WIDTH).fold(0.0_f64, f64::max);
        let max_y = tree.nodes.iter().map(|n| n.y + NODE_HEIGHT).fold(0.0_f64, f64::max);
        format!("0 0 {} {}", max_x + PADDING, max_y + PADDING)
    };

    let selected_node = state.selected_tree_node;

    view! {
        <div
            class="execution-tree-container"
            on:mousedown=move |ev| {
                dragging.set(true);
                drag_start_x.set(ev.client_x() as f64);
                drag_start_y.set(ev.client_y() as f64);
                pan_start_x.set(pan_x.get());
                pan_start_y.set(pan_y.get());
            }
            on:mousemove=move |ev| {
                if dragging.get() {
                    let dx = ev.client_x() as f64 - drag_start_x.get();
                    let dy = ev.client_y() as f64 - drag_start_y.get();
                    pan_x.set(pan_start_x.get() + dx);
                    pan_y.set(pan_start_y.get() + dy);
                }
            }
            on:mouseup=move |_| dragging.set(false)
            on:mouseleave=move |_| dragging.set(false)
            on:wheel=move |ev| {
                ev.prevent_default();
                let delta = if ev.delta_y() > 0.0 { 0.9 } else { 1.1 };
                let new_zoom = (zoom.get() * delta).clamp(0.2, 5.0);
                zoom.set(new_zoom);
            }
        >
            {move || {
                let tree = laid_out_tree();
                if tree.nodes.is_empty() {
                    return view! {
                        <div class="detail-section-empty">"No tree data yet. Events will populate the tree as the execution progresses."</div>
                    }.into_any();
                }

                let px = pan_x.get();
                let py = pan_y.get();
                let z = zoom.get();
                let transform = format!("translate({}px, {}px) scale({})", px, py, z);
                let vb = viewbox();

                view! {
                    <svg
                        class="execution-tree-svg"
                        viewBox=vb
                        style=format!("transform: {}; transform-origin: 0 0;", transform)
                    >
                        // Render edges
                        {tree.edges.iter().map(|edge| {
                            let from = tree.nodes.iter().find(|n| n.node_id == edge.from_id);
                            let to = tree.nodes.iter().find(|n| n.node_id == edge.to_id);
                            if let (Some(from), Some(to)) = (from, to) {
                                let x1 = from.x + NODE_WIDTH / 2.0;
                                let y1 = from.y + NODE_HEIGHT;
                                let x2 = to.x + NODE_WIDTH / 2.0;
                                let y2 = to.y;
                                let mid_y = (y1 + y2) / 2.0;
                                let d = format!(
                                    "M {x1} {y1} C {x1} {mid_y}, {x2} {mid_y}, {x2} {y2}"
                                );
                                view! {
                                    <path class="tree-edge" d=d />
                                }.into_any()
                            } else {
                                view! { <g></g> }.into_any()
                            }
                        }).collect_view()}

                        // Render nodes
                        {tree.nodes.iter().map(|node| {
                            let cls = status_class(node.status);
                            let icon = type_icon(node.node_type);
                            let node_id = node.node_id.clone();
                            let label = node.label.clone();
                            let summary = if node.summary.len() > 20 {
                                format!("{}...", &node.summary[..20])
                            } else {
                                node.summary.clone()
                            };
                            let x = node.x;
                            let y = node.y;

                            view! {
                                <g
                                    class=format!("tree-node {}", cls)
                                    transform=format!("translate({}, {})", x, y)
                                    on:click=move |ev| {
                                        ev.stop_propagation();
                                        selected_node.set(Some(node_id.clone()));
                                    }
                                >
                                    <rect
                                        width=NODE_WIDTH
                                        height=NODE_HEIGHT
                                        rx="6"
                                        ry="6"
                                    />
                                    <text class="tree-node-icon" x="10" y="20" font-size="11">{icon}</text>
                                    <text class="tree-node-label" x="26" y="20" font-size="11">{label}</text>
                                    <text class="tree-node-summary" x="10" y="38" font-size="10">{summary}</text>
                                </g>
                            }
                        }).collect_view()}
                    </svg>

                    // Detail overlay for selected node
                    {move || {
                        let sel = selected_node.get();
                        if let Some(sel_id) = sel {
                            let tree = laid_out_tree();
                            if let Some(node) = tree.nodes.iter().find(|n| n.node_id == sel_id) {
                                let label = node.label.clone();
                                let summary = node.summary.clone();
                                let data_str = node.event_data
                                    .as_ref()
                                    .map(|d| serde_json::to_string_pretty(d).unwrap_or_default())
                                    .unwrap_or_default();
                                let status_str = format!("{:?}", node.status);
                                return view! {
                                    <div class="tree-node-detail-overlay">
                                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                            <strong>{label}</strong>
                                            <button
                                                class="btn-copy"
                                                on:click=move |_| selected_node.set(None)
                                            >"X"</button>
                                        </div>
                                        <div class="log-label">"Status: " {status_str}</div>
                                        {if !summary.is_empty() {
                                            Some(view! {
                                                <div class="log-label">"Summary"</div>
                                                <div style="font-size: 12px; color: var(--text-secondary); margin-bottom: 6px;">{summary}</div>
                                            })
                                        } else {
                                            None
                                        }}
                                        {if !data_str.is_empty() {
                                            Some(view! {
                                                <div class="log-label">"Event Data"</div>
                                                <pre class="log-pre" style="max-height: 200px;">{data_str}</pre>
                                            })
                                        } else {
                                            None
                                        }}
                                    </div>
                                }.into_any();
                            }
                        }
                        view! { <div></div> }.into_any()
                    }}
                }.into_any()
            }}
        </div>
    }
}
