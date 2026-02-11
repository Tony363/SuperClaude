//! Basic example of using the Anthropic API client
//!
//! Run with:
//! ```bash
//! export ANTHROPIC_API_KEY=your_key_here
//! cargo run --example api_basic
//! ```

use superclaude_runtime::api::{
    AnthropicClient, ContentBlock, CreateMessageRequest, Message, Role, StreamEvent,
};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Initialize logging
    tracing_subscriber::fmt()
        .with_max_level(tracing::Level::INFO)
        .init();

    // Create client from environment
    let client = AnthropicClient::from_env()?;
    println!("✓ API client initialized");

    // Example 1: Simple non-streaming request
    println!("\n--- Example 1: Non-streaming request ---");
    let request = CreateMessageRequest {
        model: "claude-3-5-sonnet-20241022".to_string(),
        max_tokens: 100,
        messages: vec![Message {
            role: Role::User,
            content: vec![ContentBlock::Text {
                text: "Explain what Rust is in one sentence.".to_string(),
            }],
        }],
        ..Default::default()
    };

    let response = client.create_message(request).await?;
    println!("Model: {}", response.model);
    println!("Stop reason: {:?}", response.stop_reason);
    println!("Usage: {} input, {} output tokens",
        response.usage.input_tokens,
        response.usage.output_tokens
    );

    if let ContentBlock::Text { text } = &response.content[0] {
        println!("\nResponse:\n{}", text);
    }

    // Example 2: Streaming request
    println!("\n--- Example 2: Streaming request ---");
    let request = CreateMessageRequest {
        model: "claude-3-5-sonnet-20241022".to_string(),
        max_tokens: 200,
        messages: vec![Message {
            role: Role::User,
            content: vec![ContentBlock::Text {
                text: "Count from 1 to 10, one number per line.".to_string(),
            }],
        }],
        ..Default::default()
    };

    let mut stream = client.create_message_stream(request).await?;
    println!("Streaming response:");

    let mut event_count = 0;
    while let Some(event) = stream.next().await {
        let event = event?;
        event_count += 1;

        match event {
            StreamEvent::MessageStart { message } => {
                println!("\n[Message started: {}]", message.id);
            }
            StreamEvent::ContentBlockDelta { delta, .. } => {
                if let superclaude_runtime::api::ContentDelta::TextDelta { text } = delta {
                    print!("{}", text);
                    std::io::Write::flush(&mut std::io::stdout()).ok();
                }
            }
            StreamEvent::MessageDelta { usage, .. } => {
                println!("\n[Output tokens: {}]", usage.output_tokens);
            }
            StreamEvent::MessageStop => {
                println!("\n[Stream complete]");
            }
            _ => {}
        }
    }

    println!("Total events received: {}", event_count);

    // Example 3: Using system prompt and temperature
    println!("\n--- Example 3: With system prompt ---");
    let request = CreateMessageRequest {
        model: "claude-3-5-sonnet-20241022".to_string(),
        max_tokens: 150,
        messages: vec![Message {
            role: Role::User,
            content: vec![ContentBlock::Text {
                text: "What should I build?".to_string(),
            }],
        }],
        system: Some("You are a creative software architect who suggests innovative project ideas.".to_string()),
        temperature: Some(0.9),
        ..Default::default()
    };

    let response = client.create_message(request).await?;
    if let ContentBlock::Text { text } = &response.content[0] {
        println!("Creative suggestion:\n{}", text);
    }

    println!("\n✓ All examples completed successfully");
    Ok(())
}
