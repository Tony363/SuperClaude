/*!
Anthropic Messages API client for SuperClaude Runtime.

This module provides a Rust implementation of the Anthropic Messages API client,
supporting both request/response and streaming modes with SSE.

# Features
- POST /v1/messages with reqwest
- SSE streaming with eventsource-stream
- Tool-use streaming state machine
- Automatic retries with exponential backoff
- Error handling and recovery
- Subprocess bridge pattern as fallback

# Architecture
The client follows Anthropic's official API specification:
- Message API: https://docs.anthropic.com/en/api/messages
- Streaming: Server-Sent Events (SSE) format
- Tool use: Multi-step streaming state machine

# Usage
```rust
use superclaude_runtime::api::{AnthropicClient, CreateMessageRequest};

let client = AnthropicClient::from_env()?;
let request = CreateMessageRequest {
    model: "claude-sonnet-4-20250514".to_string(),
    max_tokens: 4096,
    messages: vec![
        Message {
            role: "user".to_string(),
            content: vec![ContentBlock::Text {
                text: "Hello, Claude!".to_string(),
            }],
        },
    ],
    ..Default::default()
};

// Streaming mode
let mut stream = client.create_message_stream(request).await?;
while let Some(event) = stream.next().await {
    match event? {
        StreamEvent::ContentBlockDelta { delta, .. } => {
            // Process delta
        }
        _ => {}
    }
}
```
*/

use anyhow::{Context, Result};
use reqwest::{header, Client, StatusCode};
use serde::{Deserialize, Serialize};
use std::env;
use std::time::Duration;
use tokio::time::sleep;
use tracing::{debug, warn};

// ============================================================================
// API Types - Match Anthropic's Messages API
// ============================================================================

/// Message role (user or assistant)
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum Role {
    User,
    Assistant,
}

/// Content block in a message
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ContentBlock {
    Text {
        text: String,
    },
    Image {
        source: ImageSource,
    },
    ToolUse {
        id: String,
        name: String,
        input: serde_json::Value,
    },
    ToolResult {
        tool_use_id: String,
        content: String,
        #[serde(skip_serializing_if = "Option::is_none")]
        is_error: Option<bool>,
    },
}

/// Image source (base64 or URL)
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ImageSource {
    Base64 {
        media_type: String,
        data: String,
    },
}

/// Message in conversation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub role: Role,
    pub content: Vec<ContentBlock>,
}

/// Tool definition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Tool {
    pub name: String,
    pub description: String,
    pub input_schema: serde_json::Value,
}

/// Request to create a message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateMessageRequest {
    pub model: String,
    pub max_tokens: u32,
    pub messages: Vec<Message>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub system: Option<String>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub temperature: Option<f32>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub top_p: Option<f32>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub top_k: Option<u32>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub tools: Option<Vec<Tool>>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub stream: Option<bool>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<serde_json::Value>,

    #[serde(skip_serializing_if = "Option::is_none")]
    pub stop_sequences: Option<Vec<String>>,
}

impl Default for CreateMessageRequest {
    fn default() -> Self {
        Self {
            model: "claude-sonnet-4-20250514".to_string(),
            max_tokens: 4096,
            messages: Vec::new(),
            system: None,
            temperature: None,
            top_p: None,
            top_k: None,
            tools: None,
            stream: None,
            metadata: None,
            stop_sequences: None,
        }
    }
}

/// Usage statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Usage {
    pub input_tokens: u32,
    pub output_tokens: u32,
}

/// Stop reason
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum StopReason {
    EndTurn,
    MaxTokens,
    StopSequence,
    ToolUse,
}

/// Response from create message (non-streaming)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CreateMessageResponse {
    pub id: String,
    pub r#type: String, // "message"
    pub role: Role,
    pub content: Vec<ContentBlock>,
    pub model: String,
    pub stop_reason: Option<StopReason>,
    pub stop_sequence: Option<String>,
    pub usage: Usage,
}

// ============================================================================
// Streaming Types
// ============================================================================

/// Streaming event from SSE
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum StreamEvent {
    MessageStart {
        message: MessageStartData,
    },
    ContentBlockStart {
        index: usize,
        content_block: ContentBlockStartData,
    },
    ContentBlockDelta {
        index: usize,
        delta: ContentDelta,
    },
    ContentBlockStop {
        index: usize,
    },
    MessageDelta {
        delta: MessageDeltaData,
        usage: Usage,
    },
    MessageStop,
    Ping,
    Error {
        error: ApiError,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageStartData {
    pub id: String,
    pub r#type: String,
    pub role: Role,
    pub content: Vec<serde_json::Value>,
    pub model: String,
    pub usage: Usage,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ContentBlockStartData {
    Text {
        text: String,
    },
    ToolUse {
        id: String,
        name: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ContentDelta {
    TextDelta {
        text: String,
    },
    InputJsonDelta {
        partial_json: String,
    },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MessageDeltaData {
    pub stop_reason: Option<StopReason>,
    pub stop_sequence: Option<String>,
}

// ============================================================================
// Error Types
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ApiError {
    pub r#type: String,
    pub message: String,
}

impl std::fmt::Display for ApiError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "API Error [{}]: {}", self.r#type, self.message)
    }
}

impl std::error::Error for ApiError {}

// ============================================================================
// Anthropic Client
// ============================================================================

/// Configuration for retry behavior
#[derive(Debug, Clone)]
pub struct RetryConfig {
    pub max_retries: u32,
    pub initial_delay_ms: u64,
    pub max_delay_ms: u64,
    pub backoff_multiplier: f64,
}

impl Default for RetryConfig {
    fn default() -> Self {
        Self {
            max_retries: 3,
            initial_delay_ms: 100,
            max_delay_ms: 10000,
            backoff_multiplier: 2.0,
        }
    }
}

/// Anthropic API client
pub struct AnthropicClient {
    api_key: String,
    api_base: String,
    api_version: String,
    http_client: Client,
    retry_config: RetryConfig,
}

impl AnthropicClient {
    /// Create a new client from environment variables
    ///
    /// Reads:
    /// - ANTHROPIC_API_KEY (required)
    /// - ANTHROPIC_API_BASE (optional, defaults to https://api.anthropic.com)
    /// - ANTHROPIC_API_VERSION (optional, defaults to 2023-06-01)
    pub fn from_env() -> Result<Self> {
        let api_key = env::var("ANTHROPIC_API_KEY")
            .context("ANTHROPIC_API_KEY environment variable not set")?;

        let api_base = env::var("ANTHROPIC_API_BASE")
            .unwrap_or_else(|_| "https://api.anthropic.com".to_string());

        let api_version =
            env::var("ANTHROPIC_API_VERSION").unwrap_or_else(|_| "2023-06-01".to_string());

        Self::new(api_key, api_base, api_version)
    }

    /// Create a new client with explicit configuration
    pub fn new(api_key: String, api_base: String, api_version: String) -> Result<Self> {
        let http_client = Client::builder()
            .timeout(Duration::from_secs(300)) // 5 minutes
            .build()
            .context("Failed to create HTTP client")?;

        Ok(Self {
            api_key,
            api_base,
            api_version,
            http_client,
            retry_config: RetryConfig::default(),
        })
    }

    /// Set custom retry configuration
    pub fn with_retry_config(mut self, config: RetryConfig) -> Self {
        self.retry_config = config;
        self
    }

    /// Create a message (non-streaming)
    pub async fn create_message(
        &self,
        mut request: CreateMessageRequest,
    ) -> Result<CreateMessageResponse> {
        request.stream = Some(false);

        self.retry_request(|| async {
            let url = format!("{}/v1/messages", self.api_base);
            let response = self
                .http_client
                .post(&url)
                .header(header::CONTENT_TYPE, "application/json")
                .header("x-api-key", &self.api_key)
                .header("anthropic-version", &self.api_version)
                .json(&request)
                .send()
                .await
                .context("Failed to send request")?;

            self.handle_response(response).await
        })
        .await
    }

    /// Create a message with streaming
    pub async fn create_message_stream(
        &self,
        mut request: CreateMessageRequest,
    ) -> Result<MessageStream> {
        request.stream = Some(true);

        let url = format!("{}/v1/messages", self.api_base);
        let response = self
            .http_client
            .post(&url)
            .header(header::CONTENT_TYPE, "application/json")
            .header(header::ACCEPT, "text/event-stream")
            .header("x-api-key", &self.api_key)
            .header("anthropic-version", &self.api_version)
            .json(&request)
            .send()
            .await
            .context("Failed to send streaming request")?;

        if !response.status().is_success() {
            let status = response.status();
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("API request failed [{}]: {}", status, error_text);
        }

        Ok(MessageStream::new(response))
    }

    /// Handle non-streaming response
    async fn handle_response<T: serde::de::DeserializeOwned>(
        &self,
        response: reqwest::Response,
    ) -> Result<T> {
        let status = response.status();

        if status.is_success() {
            let body = response.text().await.context("Failed to read response body")?;
            serde_json::from_str(&body).context("Failed to parse response JSON")
        } else {
            let error_text = response.text().await.unwrap_or_default();
            anyhow::bail!("API request failed [{}]: {}", status, error_text)
        }
    }

    /// Retry a request with exponential backoff
    async fn retry_request<F, Fut, T>(&self, f: F) -> Result<T>
    where
        F: Fn() -> Fut,
        Fut: std::future::Future<Output = Result<T>>,
    {
        let mut attempt = 0;
        let mut delay_ms = self.retry_config.initial_delay_ms;

        loop {
            match f().await {
                Ok(result) => return Ok(result),
                Err(err) => {
                    attempt += 1;

                    if attempt > self.retry_config.max_retries {
                        return Err(err);
                    }

                    // Check if error is retryable
                    let should_retry = err
                        .downcast_ref::<reqwest::Error>()
                        .map(|e| {
                            e.is_timeout()
                                || e.status()
                                    .map(|s| {
                                        s == StatusCode::TOO_MANY_REQUESTS
                                            || s.is_server_error()
                                    })
                                    .unwrap_or(false)
                        })
                        .unwrap_or(false);

                    if !should_retry {
                        return Err(err);
                    }

                    warn!(
                        "Request failed (attempt {}/{}), retrying in {}ms: {}",
                        attempt, self.retry_config.max_retries, delay_ms, err
                    );

                    sleep(Duration::from_millis(delay_ms)).await;

                    // Exponential backoff
                    delay_ms = ((delay_ms as f64) * self.retry_config.backoff_multiplier) as u64;
                    delay_ms = delay_ms.min(self.retry_config.max_delay_ms);
                }
            }
        }
    }
}

// ============================================================================
// Message Stream
// ============================================================================

use eventsource_stream::Eventsource;
use futures::stream::{Stream, StreamExt};

/// Streaming message response
pub struct MessageStream {
    stream: std::pin::Pin<Box<dyn Stream<Item = Result<eventsource_stream::Event, eventsource_stream::EventStreamError<reqwest::Error>>> + Send>>,
    state_machine: StreamStateMachine,
}

impl MessageStream {
    fn new(response: reqwest::Response) -> Self {
        let stream = Box::pin(response.bytes_stream().eventsource());
        Self {
            stream,
            state_machine: StreamStateMachine::default(),
        }
    }

    /// Get the next event from the stream
    pub async fn next(&mut self) -> Option<Result<StreamEvent>> {
        loop {
            match self.stream.next().await {
                Some(Ok(event)) => {
                    // Parse SSE event
                    match event.event.as_str() {
                        "message_start" | "content_block_start" | "content_block_delta"
                        | "content_block_stop" | "message_delta" | "message_stop" | "error" => {
                            match serde_json::from_str::<StreamEvent>(&event.data) {
                                Ok(stream_event) => {
                                    // Update state machine
                                    if let Err(e) = self.state_machine.process(&stream_event) {
                                        warn!("State machine error: {}", e);
                                    }
                                    return Some(Ok(stream_event));
                                }
                                Err(e) => {
                                    warn!("Failed to parse stream event: {}", e);
                                    continue;
                                }
                            }
                        }
                        "ping" => {
                            return Some(Ok(StreamEvent::Ping));
                        }
                        _ => {
                            debug!("Unknown event type: {}", event.event);
                            continue;
                        }
                    }
                }
                Some(Err(e)) => {
                    return Some(Err(anyhow::anyhow!("Stream error: {}", e)));
                }
                None => {
                    return None;
                }
            }
        }
    }

    /// Collect the full message from the stream
    pub async fn collect_message(mut self) -> Result<CreateMessageResponse> {
        while let Some(event) = self.next().await {
            event?; // Propagate errors
        }

        self.state_machine.into_message()
    }
}

// ============================================================================
// Stream State Machine for Tool Use
// ============================================================================

/// State machine for assembling streamed messages
#[derive(Debug, Default)]
struct StreamStateMachine {
    message_id: Option<String>,
    model: Option<String>,
    role: Option<Role>,
    content_blocks: Vec<StreamContentBlock>,
    current_index: Option<usize>,
    usage: Option<Usage>,
    stop_reason: Option<StopReason>,
    stop_sequence: Option<String>,
}

#[derive(Debug, Clone)]
enum StreamContentBlock {
    Text { text: String },
    ToolUse { id: String, name: String, input: String },
}

impl StreamStateMachine {
    fn process(&mut self, event: &StreamEvent) -> Result<()> {
        match event {
            StreamEvent::MessageStart { message } => {
                self.message_id = Some(message.id.clone());
                self.model = Some(message.model.clone());
                self.role = Some(message.role.clone());
                self.usage = Some(message.usage.clone());
            }
            StreamEvent::ContentBlockStart { index, content_block } => {
                self.current_index = Some(*index);
                match content_block {
                    ContentBlockStartData::Text { text } => {
                        self.content_blocks.push(StreamContentBlock::Text {
                            text: text.clone(),
                        });
                    }
                    ContentBlockStartData::ToolUse { id, name } => {
                        self.content_blocks.push(StreamContentBlock::ToolUse {
                            id: id.clone(),
                            name: name.clone(),
                            input: String::new(),
                        });
                    }
                }
            }
            StreamEvent::ContentBlockDelta { index, delta } => {
                if let Some(block) = self.content_blocks.get_mut(*index) {
                    match (block, delta) {
                        (StreamContentBlock::Text { text }, ContentDelta::TextDelta { text: delta_text }) => {
                            text.push_str(delta_text);
                        }
                        (StreamContentBlock::ToolUse { input, .. }, ContentDelta::InputJsonDelta { partial_json }) => {
                            input.push_str(partial_json);
                        }
                        _ => {
                            warn!("Mismatched delta type for content block");
                        }
                    }
                }
            }
            StreamEvent::ContentBlockStop { index: _ } => {
                self.current_index = None;
            }
            StreamEvent::MessageDelta { delta, usage } => {
                self.stop_reason = delta.stop_reason.clone();
                self.stop_sequence = delta.stop_sequence.clone();
                // Update usage with output tokens
                if let Some(existing_usage) = &mut self.usage {
                    existing_usage.output_tokens = usage.output_tokens;
                }
            }
            StreamEvent::MessageStop => {
                // Finalize
            }
            StreamEvent::Ping => {}
            StreamEvent::Error { error } => {
                anyhow::bail!("Stream error: {}", error);
            }
        }

        Ok(())
    }

    fn into_message(self) -> Result<CreateMessageResponse> {
        let message_id = self.message_id.context("Missing message ID")?;
        let model = self.model.context("Missing model")?;
        let role = self.role.context("Missing role")?;
        let usage = self.usage.context("Missing usage")?;

        let content: Vec<ContentBlock> = self
            .content_blocks
            .into_iter()
            .map(|block| match block {
                StreamContentBlock::Text { text } => ContentBlock::Text { text },
                StreamContentBlock::ToolUse { id, name, input } => {
                    let parsed_input: serde_json::Value =
                        serde_json::from_str(&input).unwrap_or_else(|_| {
                            serde_json::json!({ "error": "failed to parse tool input" })
                        });
                    ContentBlock::ToolUse {
                        id,
                        name,
                        input: parsed_input,
                    }
                }
            })
            .collect();

        Ok(CreateMessageResponse {
            id: message_id,
            r#type: "message".to_string(),
            role,
            content,
            model,
            stop_reason: self.stop_reason,
            stop_sequence: self.stop_sequence,
            usage,
        })
    }
}

// ============================================================================
// Subprocess Bridge Pattern (Fallback)
// ============================================================================

/// Subprocess bridge for calling Python SDK as fallback
///
/// This provides a compatibility layer when running Rust runtime alongside
/// existing Python infrastructure. It spawns a Python subprocess that uses
/// the official Anthropic SDK and communicates via JSON over stdin/stdout.
///
/// Usage:
/// ```rust
/// let bridge = SubprocessBridge::new("python3", vec!["-m", "superclaude_bridge"])?;
/// let response = bridge.create_message(request).await?;
/// ```
pub struct SubprocessBridge {
    python_path: String,
    args: Vec<String>,
}

impl SubprocessBridge {
    /// Create a new subprocess bridge
    pub fn new(python_path: impl Into<String>, args: Vec<impl Into<String>>) -> Self {
        Self {
            python_path: python_path.into(),
            args: args.into_iter().map(|s| s.into()).collect(),
        }
    }

    /// Create a message via subprocess
    pub async fn create_message(
        &self,
        request: CreateMessageRequest,
    ) -> Result<CreateMessageResponse> {
        use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
        use tokio::process::Command;

        let mut child = Command::new(&self.python_path)
            .args(&self.args)
            .stdin(std::process::Stdio::piped())
            .stdout(std::process::Stdio::piped())
            .stderr(std::process::Stdio::piped())
            .spawn()
            .context("Failed to spawn Python subprocess")?;

        let mut stdin = child.stdin.take().context("Failed to open stdin")?;
        let stdout = child.stdout.take().context("Failed to open stdout")?;

        // Send request as JSON
        let request_json = serde_json::to_string(&request)?;
        stdin
            .write_all(request_json.as_bytes())
            .await
            .context("Failed to write to stdin")?;
        stdin
            .write_all(b"\n")
            .await
            .context("Failed to write newline")?;
        drop(stdin);

        // Read response
        let mut reader = BufReader::new(stdout);
        let mut response_line = String::new();
        reader
            .read_line(&mut response_line)
            .await
            .context("Failed to read response")?;

        // Wait for process to exit
        let status = child.wait().await.context("Failed to wait for child")?;
        if !status.success() {
            anyhow::bail!("Subprocess exited with error: {}", status);
        }

        serde_json::from_str(&response_line).context("Failed to parse subprocess response")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_content_block_serialization() {
        let block = ContentBlock::Text {
            text: "Hello".to_string(),
        };
        let json = serde_json::to_string(&block).unwrap();
        assert!(json.contains(r#""type":"text"#));
        assert!(json.contains(r#""text":"Hello"#));
    }

    #[test]
    fn test_message_serialization() {
        let msg = Message {
            role: Role::User,
            content: vec![ContentBlock::Text {
                text: "Test".to_string(),
            }],
        };
        let json = serde_json::to_string(&msg).unwrap();
        assert!(json.contains(r#""role":"user"#));
    }

    #[test]
    fn test_create_message_request_default() {
        let req = CreateMessageRequest::default();
        assert_eq!(req.model, "claude-sonnet-4-20250514");
        assert_eq!(req.max_tokens, 4096);
    }

    #[tokio::test]
    async fn test_stream_state_machine() {
        let mut sm = StreamStateMachine::default();

        // Simulate message_start
        sm.process(&StreamEvent::MessageStart {
            message: MessageStartData {
                id: "msg_123".to_string(),
                r#type: "message".to_string(),
                role: Role::Assistant,
                content: vec![],
                model: "claude-3-5-sonnet-20241022".to_string(),
                usage: Usage {
                    input_tokens: 10,
                    output_tokens: 0,
                },
            },
        })
        .unwrap();

        // Simulate content_block_start
        sm.process(&StreamEvent::ContentBlockStart {
            index: 0,
            content_block: ContentBlockStartData::Text {
                text: String::new(),
            },
        })
        .unwrap();

        // Simulate content_block_delta
        sm.process(&StreamEvent::ContentBlockDelta {
            index: 0,
            delta: ContentDelta::TextDelta {
                text: "Hello".to_string(),
            },
        })
        .unwrap();

        sm.process(&StreamEvent::ContentBlockDelta {
            index: 0,
            delta: ContentDelta::TextDelta {
                text: " world".to_string(),
            },
        })
        .unwrap();

        // Simulate content_block_stop
        sm.process(&StreamEvent::ContentBlockStop { index: 0 })
            .unwrap();

        // Simulate message_delta
        sm.process(&StreamEvent::MessageDelta {
            delta: MessageDeltaData {
                stop_reason: Some(StopReason::EndTurn),
                stop_sequence: None,
            },
            usage: Usage {
                input_tokens: 10,
                output_tokens: 5,
            },
        })
        .unwrap();

        // Convert to message
        let msg = sm.into_message().unwrap();
        assert_eq!(msg.id, "msg_123");
        assert_eq!(msg.content.len(), 1);
        if let ContentBlock::Text { text } = &msg.content[0] {
            assert_eq!(text, "Hello world");
        } else {
            panic!("Expected text block");
        }
    }
}
