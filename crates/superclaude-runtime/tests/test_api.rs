/*!
Integration tests for Anthropic API client
*/

use superclaude_runtime::api::{
    AnthropicClient, ContentBlock, CreateMessageRequest, Message, Role, StreamEvent,
};

#[tokio::test]
#[ignore] // Requires ANTHROPIC_API_KEY
async fn test_create_message_basic() {
    let client = AnthropicClient::from_env().expect("ANTHROPIC_API_KEY not set");

    let request = CreateMessageRequest {
        model: "claude-3-5-sonnet-20241022".to_string(),
        max_tokens: 100,
        messages: vec![Message {
            role: Role::User,
            content: vec![ContentBlock::Text {
                text: "Say 'Hello, World!' and nothing else.".to_string(),
            }],
        }],
        ..Default::default()
    };

    let response = client
        .create_message(request)
        .await
        .expect("API request failed");

    assert_eq!(response.role, Role::Assistant);
    assert!(!response.content.is_empty());
    println!("Response: {:?}", response.content);
}

#[tokio::test]
#[ignore] // Requires ANTHROPIC_API_KEY
async fn test_create_message_stream() {
    let client = AnthropicClient::from_env().expect("ANTHROPIC_API_KEY not set");

    let request = CreateMessageRequest {
        model: "claude-3-5-sonnet-20241022".to_string(),
        max_tokens: 100,
        messages: vec![Message {
            role: Role::User,
            content: vec![ContentBlock::Text {
                text: "Count from 1 to 5.".to_string(),
            }],
        }],
        ..Default::default()
    };

    let mut stream = client
        .create_message_stream(request)
        .await
        .expect("Stream request failed");

    let mut text_accumulated = String::new();
    let mut event_count = 0;

    while let Some(event) = stream.next().await {
        let event = event.expect("Stream event error");
        event_count += 1;

        match event {
            StreamEvent::ContentBlockDelta { delta, .. } => {
                if let superclaude_runtime::api::ContentDelta::TextDelta { text } = delta {
                    text_accumulated.push_str(&text);
                    print!("{}", text);
                }
            }
            StreamEvent::MessageStop => {
                println!("\n[Stream ended]");
            }
            _ => {}
        }
    }

    assert!(event_count > 0, "Should receive events");
    assert!(!text_accumulated.is_empty(), "Should accumulate text");
    println!("Total events: {}", event_count);
    println!("Accumulated text: {}", text_accumulated);
}

#[tokio::test]
#[ignore] // Requires ANTHROPIC_API_KEY
async fn test_stream_collect_message() {
    let client = AnthropicClient::from_env().expect("ANTHROPIC_API_KEY not set");

    let request = CreateMessageRequest {
        model: "claude-3-5-sonnet-20241022".to_string(),
        max_tokens: 50,
        messages: vec![Message {
            role: Role::User,
            content: vec![ContentBlock::Text {
                text: "Say hello.".to_string(),
            }],
        }],
        ..Default::default()
    };

    let stream = client
        .create_message_stream(request)
        .await
        .expect("Stream request failed");

    let message = stream.collect_message().await.expect("Collect failed");

    assert_eq!(message.role, Role::Assistant);
    assert!(!message.content.is_empty());
    assert!(message.usage.output_tokens > 0);
    println!("Collected message: {:?}", message);
}

#[test]
fn test_api_types_serialization() {
    let msg = Message {
        role: Role::User,
        content: vec![
            ContentBlock::Text {
                text: "Test message".to_string(),
            },
            ContentBlock::ToolResult {
                tool_use_id: "tool_123".to_string(),
                content: "Result".to_string(),
                is_error: Some(false),
            },
        ],
    };

    let json = serde_json::to_string(&msg).expect("Serialization failed");
    assert!(json.contains(r#""role":"user"#));
    assert!(json.contains("Test message"));

    let deserialized: Message = serde_json::from_str(&json).expect("Deserialization failed");
    assert_eq!(deserialized.role, Role::User);
    assert_eq!(deserialized.content.len(), 2);
}

#[test]
fn test_request_builder() {
    let request = CreateMessageRequest {
        model: "claude-sonnet-4-20250514".to_string(),
        max_tokens: 1024,
        messages: vec![Message {
            role: Role::User,
            content: vec![ContentBlock::Text {
                text: "Hello".to_string(),
            }],
        }],
        system: Some("You are a helpful assistant.".to_string()),
        temperature: Some(0.7),
        ..Default::default()
    };

    assert_eq!(request.model, "claude-sonnet-4-20250514");
    assert_eq!(request.max_tokens, 1024);
    assert_eq!(request.messages.len(), 1);
    assert_eq!(request.temperature, Some(0.7));
}

#[tokio::test]
#[ignore] // Requires mock server or live API
async fn test_retry_on_rate_limit() {
    // This test would require a mock server that returns 429
    // or controlled rate limit testing
    // For now, it's a placeholder demonstrating retry logic awareness
}

#[tokio::test]
#[ignore] // Requires mock server
async fn test_error_handling() {
    // Test with invalid API key
    let client = AnthropicClient::new(
        "invalid_key".to_string(),
        "https://api.anthropic.com".to_string(),
        "2023-06-01".to_string(),
    )
    .expect("Client creation failed");

    let request = CreateMessageRequest {
        model: "claude-3-5-sonnet-20241022".to_string(),
        max_tokens: 100,
        messages: vec![Message {
            role: Role::User,
            content: vec![ContentBlock::Text {
                text: "Test".to_string(),
            }],
        }],
        ..Default::default()
    };

    let result = client.create_message(request).await;
    assert!(result.is_err(), "Should fail with invalid API key");
}
