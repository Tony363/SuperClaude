# Anthropic API Client for SuperClaude Runtime

This document describes the Rust implementation of the Anthropic Messages API client in SuperClaude Runtime.

## Overview

The API client (`crates/superclaude-runtime/src/api.rs`) provides a complete Rust implementation of the Anthropic Messages API with the following features:

- **Request/Response Mode**: Standard synchronous API calls
- **Streaming Mode**: Server-Sent Events (SSE) with real-time deltas
- **Tool Use State Machine**: Proper streaming assembly for tool calls
- **Automatic Retries**: Exponential backoff for rate limits and server errors
- **Error Handling**: Comprehensive error types and recovery
- **Subprocess Bridge**: Fallback to Python SDK when needed

## Architecture

### Core Components

1. **AnthropicClient**: Main client for API communication
2. **MessageStream**: Streaming response handler
3. **StreamStateMachine**: Assembles streamed content blocks
4. **SubprocessBridge**: Python SDK compatibility layer

### Type System

The client uses strongly-typed structs that match Anthropic's API specification:

```rust
pub struct CreateMessageRequest {
    pub model: String,
    pub max_tokens: u32,
    pub messages: Vec<Message>,
    pub system: Option<String>,
    pub temperature: Option<f32>,
    pub tools: Option<Vec<Tool>>,
    // ... more fields
}

pub enum ContentBlock {
    Text { text: String },
    Image { source: ImageSource },
    ToolUse { id: String, name: String, input: Value },
    ToolResult { tool_use_id: String, content: String, is_error: Option<bool> },
}

pub enum StreamEvent {
    MessageStart { message: MessageStartData },
    ContentBlockStart { index: usize, content_block: ContentBlockStartData },
    ContentBlockDelta { index: usize, delta: ContentDelta },
    ContentBlockStop { index: usize },
    MessageDelta { delta: MessageDeltaData, usage: Usage },
    MessageStop,
    Ping,
    Error { error: ApiError },
}
```

## Usage

### Basic Request

```rust
use superclaude_runtime::api::{AnthropicClient, CreateMessageRequest, Message, ContentBlock, Role};

let client = AnthropicClient::from_env()?;

let request = CreateMessageRequest {
    model: "claude-3-5-sonnet-20241022".to_string(),
    max_tokens: 1024,
    messages: vec![
        Message {
            role: Role::User,
            content: vec![ContentBlock::Text {
                text: "Hello, Claude!".to_string(),
            }],
        },
    ],
    ..Default::default()
};

let response = client.create_message(request).await?;
println!("{:?}", response.content);
```

### Streaming

```rust
let mut stream = client.create_message_stream(request).await?;

while let Some(event) = stream.next().await {
    match event? {
        StreamEvent::ContentBlockDelta { delta, .. } => {
            if let ContentDelta::TextDelta { text } = delta {
                print!("{}", text);
            }
        }
        StreamEvent::MessageStop => break,
        _ => {}
    }
}
```

### Collect Full Message from Stream

```rust
let stream = client.create_message_stream(request).await?;
let message = stream.collect_message().await?;
// message is a complete CreateMessageResponse
```

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY` (required): Your API key
- `ANTHROPIC_API_BASE` (optional): API base URL (defaults to https://api.anthropic.com)
- `ANTHROPIC_API_VERSION` (optional): API version (defaults to 2023-06-01)

### Retry Configuration

```rust
use superclaude_runtime::api::RetryConfig;

let client = AnthropicClient::from_env()?
    .with_retry_config(RetryConfig {
        max_retries: 5,
        initial_delay_ms: 200,
        max_delay_ms: 20000,
        backoff_multiplier: 2.5,
    });
```

## Streaming State Machine

The client implements a sophisticated state machine for streaming responses:

1. **MessageStart**: Initializes message metadata
2. **ContentBlockStart**: Begins a new content block (text or tool use)
3. **ContentBlockDelta**: Accumulates partial content
4. **ContentBlockStop**: Finalizes a content block
5. **MessageDelta**: Updates stop reason and final usage
6. **MessageStop**: Completes the stream

### Tool Use Streaming

Tool use streaming requires special handling:

```
ContentBlockStart { ToolUse { id, name } }
  → ContentBlockDelta { InputJsonDelta { "{\"arg\"" } }
  → ContentBlockDelta { InputJsonDelta { ": \"value\"}" } }
  → ContentBlockStop
```

The state machine assembles these deltas into complete JSON:

```rust
ContentBlock::ToolUse {
    id: "tool_abc123",
    name: "read_file",
    input: json!({ "arg": "value" }),
}
```

## Error Handling

### Retryable Errors

The client automatically retries:
- HTTP 429 (Too Many Requests)
- HTTP 5xx (Server Errors)
- Network timeouts

### Non-Retryable Errors

These fail immediately:
- HTTP 401 (Invalid API Key)
- HTTP 400 (Bad Request)
- HTTP 413 (Request Too Large)

### Error Types

```rust
pub enum ApiError {
    NetworkError(reqwest::Error),
    ApiError { type: String, message: String },
    StreamError(String),
}
```

## Subprocess Bridge Pattern

For compatibility with existing Python infrastructure:

```rust
use superclaude_runtime::api::SubprocessBridge;

let bridge = SubprocessBridge::new("python3", vec!["-m", "superclaude_bridge"]);
let response = bridge.create_message(request).await?;
```

This spawns a Python subprocess that:
1. Reads JSON request from stdin
2. Calls the official Anthropic Python SDK
3. Writes JSON response to stdout

### Python Bridge Script

Create `superclaude_bridge.py`:

```python
import sys
import json
from anthropic import Anthropic

client = Anthropic()

# Read request from stdin
request = json.loads(sys.stdin.readline())

# Call API
response = client.messages.create(**request)

# Write response to stdout
print(json.dumps(response.model_dump()))
```

## Testing

### Unit Tests

```bash
cargo test -p superclaude-runtime api::tests
```

### Integration Tests (requires API key)

```bash
export ANTHROPIC_API_KEY=your_key_here
cargo test -p superclaude-runtime --test test_api -- --ignored
```

### Examples

```bash
export ANTHROPIC_API_KEY=your_key_here
cargo run --example api_basic
```

## Performance Considerations

### Connection Pooling

The client uses `reqwest::Client` which maintains a connection pool:
- Reuses TCP connections
- HTTP/2 multiplexing
- Automatic keep-alive

### Memory Usage

- Non-streaming: Buffers entire response in memory
- Streaming: Processes events incrementally
- State machine: Accumulates only current message content

### Timeouts

- Default HTTP timeout: 300 seconds (5 minutes)
- Configurable per request via `reqwest::Client`

## Comparison with Python SDK

| Feature | Rust Client | Python SDK |
|---------|------------|------------|
| Type Safety | Compile-time | Runtime |
| Memory Safety | Guaranteed | GC-dependent |
| Streaming | Native async | Generator-based |
| Error Handling | Result<T, E> | try/except |
| Performance | Zero-cost abstractions | Interpreter overhead |
| Tool Use State | Explicit state machine | Library-managed |

## Migration from Python

### Request Mapping

Python:
```python
response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}]
)
```

Rust:
```rust
let response = client.create_message(CreateMessageRequest {
    model: "claude-3-5-sonnet-20241022".to_string(),
    max_tokens: 1024,
    messages: vec![Message {
        role: Role::User,
        content: vec![ContentBlock::Text {
            text: "Hello".to_string()
        }]
    }],
    ..Default::default()
}).await?;
```

### Streaming Mapping

Python:
```python
with client.messages.stream(**params) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

Rust:
```rust
let mut stream = client.create_message_stream(request).await?;
while let Some(event) = stream.next().await {
    if let StreamEvent::ContentBlockDelta { delta, .. } = event? {
        if let ContentDelta::TextDelta { text } = delta {
            print!("{}", text);
        }
    }
}
```

## Future Enhancements

1. **Prompt Caching**: Support for Anthropic's prompt caching API
2. **Vision**: Image input handling
3. **Batch API**: Support for batch message processing
4. **Request Cancellation**: Graceful stream termination
5. **Metrics**: Built-in performance tracking
6. **Mock Server**: Testing utilities for CI/CD

## References

- [Anthropic API Documentation](https://docs.anthropic.com/en/api/messages)
- [Streaming Messages](https://docs.anthropic.com/en/api/messages-streaming)
- [Tool Use](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)
- [Error Handling](https://docs.anthropic.com/en/api/errors)
