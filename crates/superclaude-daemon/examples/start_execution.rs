//! Quick helper to start an execution via the daemon's gRPC API.
//! Usage: cargo run -p superclaude-daemon --example start_execution -- "task description"

use superclaude_proto::super_claude_service_client::SuperClaudeServiceClient;
use superclaude_proto::{ExecutionConfig, StartExecutionRequest, StreamEventsRequest};
use tokio_stream::StreamExt;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let task = std::env::args()
        .nth(1)
        .unwrap_or_else(|| "Create a snake game in Rust using crossterm for terminal rendering. Include a Cargo.toml, src/main.rs, and make it fully playable.".to_string());

    println!("Connecting to daemon at 127.0.0.1:50051...");
    let mut client =
        SuperClaudeServiceClient::connect("http://127.0.0.1:50051").await?;

    println!("Starting execution: {task}");
    let resp = client
        .start_execution(StartExecutionRequest {
            task: task.clone(),
            project_root: "/home/tony/Desktop/SuperClaude".to_string(),
            config: Some(ExecutionConfig {
                max_iterations: 5,
                quality_threshold: 70.0,
                model: "sonnet".to_string(),
                timeout_seconds: 600.0,
                pal_review_enabled: false,
                min_improvement: 0.0,
            }),
        })
        .await?
        .into_inner();

    let eid = resp.execution_id;
    println!("Execution started: {eid}");
    println!("Subscribing to events...\n");

    let mut stream = client
        .stream_events(StreamEventsRequest {
            execution_id: eid.clone(),
            include_history: true,
        })
        .await?
        .into_inner();

    while let Some(event) = stream.next().await {
        match event {
            Ok(ev) => {
                let evt = ev.event.as_ref().map(|e| format!("{e:?}")).unwrap_or_default();
                // Truncate long events for readability
                let display = if evt.len() > 200 {
                    format!("{}...", &evt[..200])
                } else {
                    evt
                };
                println!("[{}] {display}", ev.execution_id);
            }
            Err(e) => {
                eprintln!("Stream error: {e}");
                break;
            }
        }
    }

    println!("\nEvent stream ended.");
    Ok(())
}
