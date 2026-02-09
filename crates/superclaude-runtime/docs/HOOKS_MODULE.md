# Hooks Module Documentation

## Overview

The `hooks` module provides a middleware pipeline for intercepting and processing tool invocations in the SuperClaude agentic loop. It integrates with the Anthropic Agent SDK to:

1. **Block dangerous operations** (PreToolUse) - Security validation before execution
2. **Collect evidence** (PostToolUse) - Track files, commands, and test results
3. **Track lifecycle** (Stop/SubagentStop) - Session finalization and subagent monitoring

## Architecture

Based on `SuperClaude/Orchestrator/hooks.py`, this module implements async hook execution with:

- Type-safe hook callbacks using `BoxFuture`
- Shared state via `Arc<Mutex<T>>` for thread-safe evidence collection
- Matcher-based routing (regex patterns like "Bash", "Write|Edit")
- Composable hook configurations via `merge_hooks()`

### Hook Execution Flow

```
1. Tool Invocation
   ↓
2. PreToolUse Hooks (safety validation)
   ↓ [blocked if denied]
3. Tool Execution
   ↓
4. PostToolUse Hooks (evidence collection)
   ↓
5. Stop/SubagentStop Hooks (finalization)
```

## Core Types

### HookInput

```rust
pub struct HookInput {
    pub hook_event_name: String,        // "PreToolUse", "PostToolUse", etc.
    pub tool_name: String,               // "Bash", "Write", "Edit", etc.
    pub tool_input: HashMap<String, Value>,  // Tool parameters
    pub tool_response: Value,            // Tool output (PostToolUse only)
    pub session_id: String,              // Session identifier
    pub stop_hook_active: bool,          // SubagentStop flag
}
```

### HookOutput

```rust
pub struct HookOutput {
    pub hook_specific_output: Option<HookSpecificOutput>,
}

impl HookOutput {
    // Allow operation (empty output)
    pub fn allow() -> Self;

    // Deny operation (PreToolUse)
    pub fn deny(reason: impl Into<String>) -> Self;
}
```

### HookConfig

```rust
pub struct HookConfig {
    pub pre_tool_use: Vec<HookMatcher>,
    pub post_tool_use: Vec<HookMatcher>,
    pub stop: Vec<HookCallback>,
    pub subagent_stop: Vec<HookCallback>,
}
```

### HookMatcher

```rust
pub struct HookMatcher {
    pub matcher: Option<String>,  // Regex pattern (None = all tools)
    pub hooks: Vec<HookCallback>,
}
```

## Hook Factories

### create_sdk_hooks()

Create complete hook configuration combining safety and evidence collection.

```rust
use superclaude_runtime::hooks::create_sdk_hooks;
use superclaude_runtime::evidence::EvidenceCollector;
use std::sync::{Arc, Mutex};

let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
let hooks = create_sdk_hooks(evidence);

// Use with SDK:
// let options = ClaudeAgentOptions { hooks: Some(hooks) };
```

**Includes:**
- Safety validation (blocks dangerous commands/paths)
- Evidence collection (files, commands, tests)
- Lifecycle tracking (session finalization)

### create_safety_hooks()

Create PreToolUse hooks for security validation.

```rust
use superclaude_runtime::hooks::create_safety_hooks;

let config = create_safety_hooks();

// Blocks:
// - Dangerous Bash commands (rm -rf /, git reset --hard, DROP DATABASE)
// - System path writes (/etc, /bin, C:\Windows)
// - Sensitive file access (.env, credentials, .ssh)
```

**Matchers:**
- `"Bash"` - Command validation via `SafetyValidator`
- `"Write|Edit"` - Path validation for file operations

### create_evidence_hooks()

Create PostToolUse hooks for evidence collection.

```rust
use superclaude_runtime::hooks::create_evidence_hooks;
use superclaude_runtime::evidence::EvidenceCollector;
use std::sync::{Arc, Mutex};

let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
let config = create_evidence_hooks(evidence);

// Tracks:
// - File writes/edits/reads with line counts
// - Command executions with outputs
// - Test results (parsed from output)
// - All tool invocations (debugging)
```

**Matchers:**
- `"Write|Edit|Read"` - File operation tracking
- `"Bash"` - Command execution tracking
- `None` - All tools (debugging)

**Stop Hooks:**
- `Stop` - Finalize evidence (set end_time, session_id)
- `SubagentStop` - Track subagent completions

### create_logging_hooks()

Create hooks that log all tool invocations.

```rust
use superclaude_runtime::hooks::create_logging_hooks;

let config = create_logging_hooks(|msg| {
    println!("{}", msg);
});

// Logs:
// [PRE] Bash: {"command": "ls -la"}...
// [POST] Bash: "file1\nfile2\nfile3"...
```

### merge_hooks()

Combine multiple hook configurations.

```rust
use superclaude_runtime::hooks::{merge_hooks, create_safety_hooks, create_evidence_hooks};
use std::sync::{Arc, Mutex};

let safety = create_safety_hooks();
let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
let evidence_hooks = create_evidence_hooks(evidence);
let logging = create_logging_hooks(|msg| println!("{}", msg));

let merged = merge_hooks(vec![safety, evidence_hooks, logging]);
```

## Hook Execution Examples

### Safety Hook (Block Dangerous Command)

```rust
// Input
HookInput {
    hook_event_name: "PreToolUse",
    tool_name: "Bash",
    tool_input: {
        "command": "rm -rf /"
    },
    ...
}

// Output
HookOutput {
    hook_specific_output: Some(HookSpecificOutput {
        hook_event_name: "PreToolUse",
        permission_decision: Some("deny"),
        permission_decision_reason: Some(
            "Dangerous command blocked: rm -rf /\nReason: Recursive deletion of root directory\nSeverity: 5/5"
        ),
    })
}
```

### Evidence Hook (Track File Write)

```rust
// Input
HookInput {
    hook_event_name: "PostToolUse",
    tool_name: "Write",
    tool_input: {
        "file_path": "test.py",
        "content": "line1\nline2\nline3"
    },
    ...
}

// Side Effect: Updates evidence collector
evidence.files_written.push("test.py");
evidence.file_changes.push(FileChange {
    path: "test.py",
    action: "write",
    lines_changed: 3,
    ...
});

// Output
HookOutput::allow()  // Empty output
```

## Pattern Matching

Hooks use regex patterns to match tool names:

| Pattern | Matches | Example Tools |
|---------|---------|---------------|
| `"Bash"` | Exact match | Bash |
| `"Write\|Edit"` | Multiple tools | Write, Edit |
| `"Write\|Edit\|Read"` | Multiple tools | Write, Edit, Read |
| `None` | All tools | Any tool invocation |

**Implementation:**

```rust
pub struct HookMatcher {
    pub matcher: Option<String>,  // Regex pattern
    pub hooks: Vec<HookCallback>,
}

// Execution logic (conceptual):
for matcher in &config.pre_tool_use {
    if matcher.matcher.is_none() || regex::Regex::new(&matcher.matcher).unwrap().is_match(&tool_name) {
        for hook in &matcher.hooks {
            let output = hook(input, tool_use_id, context).await;
            if output.hook_specific_output.is_some() {
                return output; // Blocked
            }
        }
    }
}
```

## Async Execution

All hooks are async and return `BoxFuture`:

```rust
pub type HookCallback = Box<
    dyn Fn(HookInput, Option<String>, HashMap<String, Value>) -> BoxFuture<'static, HookOutput>
        + Send
        + Sync,
>;

// Example hook implementation:
let my_hook: HookCallback = Box::new(move |input, _tool_use_id, _context| {
    Box::pin(async move {
        // Async logic here
        if input.tool_name == "Bash" {
            // Validate command
            return HookOutput::deny("Custom reason");
        }
        HookOutput::allow()
    })
});
```

## Thread Safety

Evidence collector uses `Arc<Mutex<T>>` for thread-safe access:

```rust
use std::sync::{Arc, Mutex};

let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
let evidence_clone = Arc::clone(&evidence);

let hook: HookCallback = Box::new(move |input, _, _| {
    let evidence = Arc::clone(&evidence_clone);
    Box::pin(async move {
        let mut ev = evidence.lock().unwrap();
        ev.record_file_write(path, lines);
        HookOutput::allow()
    })
});
```

## Integration with SDK

Hook configuration is passed to the Anthropic Agent SDK:

```rust
use claude_agent_sdk::{query, ClaudeAgentOptions};
use superclaude_runtime::hooks::create_sdk_hooks;
use superclaude_runtime::evidence::EvidenceCollector;
use std::sync::{Arc, Mutex};

#[tokio::main]
async fn main() {
    let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
    let hooks = create_sdk_hooks(Arc::clone(&evidence));

    let options = ClaudeAgentOptions {
        hooks: Some(hooks),
        ..Default::default()
    };

    let messages = query("Write a Python script", options).await?;

    // Evidence is populated during execution
    let ev = evidence.lock().unwrap();
    println!("Files written: {:?}", ev.files_written);
    println!("Commands run: {:?}", ev.commands_run);
}
```

## Hook Execution Order

### PreToolUse (Sequential, First Deny Wins)

1. Safety validation hooks (block dangerous operations)
2. Custom validation hooks
3. Logging hooks

**Order matters:** If any hook returns `deny`, execution stops and tool is blocked.

### PostToolUse (All Execute)

1. Evidence collection (file tracking)
2. Evidence collection (command tracking)
3. Evidence collection (all tools)
4. Custom hooks
5. Logging hooks

**All execute:** PostToolUse hooks always run (no early exit).

### Stop/SubagentStop (Sequential)

1. Evidence finalization
2. Custom cleanup hooks

## Testing

Comprehensive test suite at `/crates/superclaude-runtime/tests/test_hooks.rs`:

```bash
cargo test -p superclaude-runtime --test test_hooks
```

**Tests cover:**
- Safety hook blocking (dangerous commands, system paths)
- Safety hook allowance (safe commands, user paths)
- Evidence collection (files, commands, tools)
- Stop/SubagentStop lifecycle
- Hook merging and ordering
- Logging hooks
- Multiple hooks same tool

## Performance Considerations

1. **Compiled Patterns:** Regex compiled once in `SafetyValidator::new()`
2. **Arc<Mutex>:** Minimal lock contention (short critical sections)
3. **Async:** Non-blocking I/O for hook execution
4. **Truncation:** Large outputs truncated (1000 chars) in tool invocations

## Security Best Practices

1. **Always use safety hooks** - Never bypass security validation
2. **Safety hooks first** - Place safety hooks before evidence hooks in merged configs
3. **Validate all inputs** - Use SafetyValidator for commands and paths
4. **Log denials** - Use `tracing::warn!` for audit trail
5. **Test dangerous patterns** - Maintain comprehensive test coverage

## Error Handling

Hooks should handle errors gracefully and log them:

```rust
let my_hook: HookCallback = Box::new(move |input, _, _| {
    Box::pin(async move {
        match validate_something(&input) {
            Ok(_) => HookOutput::allow(),
            Err(e) => {
                tracing::warn!("Validation failed: {}", e);
                HookOutput::deny(format!("Validation error: {}", e))
            }
        }
    })
});
```

## Custom Hooks

Create custom hooks for application-specific logic:

```rust
use superclaude_runtime::hooks::{HookCallback, HookConfig, HookMatcher, HookInput, HookOutput};
use futures::future::BoxFuture;

// Custom PreToolUse hook
fn create_custom_hooks() -> HookConfig {
    let custom_validator: HookCallback = Box::new(|input, _, _| {
        Box::pin(async move {
            if input.hook_event_name != "PreToolUse" {
                return HookOutput::allow();
            }

            // Custom validation logic
            if input.tool_name == "Write" {
                if let Some(path) = input.tool_input.get("file_path") {
                    if path.as_str().unwrap().ends_with(".lock") {
                        return HookOutput::deny("Cannot write .lock files");
                    }
                }
            }

            HookOutput::allow()
        })
    });

    let mut config = HookConfig::new();
    config.pre_tool_use.push(HookMatcher {
        matcher: Some("Write".to_string()),
        hooks: vec![custom_validator],
    });

    config
}
```

## Migration from Python

Key differences from Python implementation:

| Aspect | Python | Rust |
|--------|--------|------|
| Callbacks | `async def` | `BoxFuture<'static, HookOutput>` |
| State | Global `evidence` | `Arc<Mutex<EvidenceCollector>>` |
| Pattern Matching | Dict with "matcher" key | `HookMatcher` struct |
| Hook Config | `dict[str, list[dict]]` | `HookConfig` struct |
| Error Handling | Return `{}` or dict | `HookOutput::allow()` / `deny()` |
| Merging | List concatenation | `merge_hooks()` function |

## Future Enhancements

Potential improvements:

- [ ] Async pattern compilation (lazy evaluation)
- [ ] Hook execution metrics (timing, success rate)
- [ ] Conditional hook activation (feature flags)
- [ ] Hook priority ordering
- [ ] Dynamic hook registration (hot reload)
- [ ] Structured logging (JSON format)
- [ ] Hook circuit breaker (fail-fast)
- [ ] Parallel hook execution (where safe)

## Related Modules

- **safety** - Pattern validation and security checks
- **evidence** - Evidence collector and data structures
- **quality** - Quality assessment using evidence
- **loop_runner** - Main agentic loop integration

## References

- Python implementation: `SuperClaude/Orchestrator/hooks.py`
- Safety module: `crates/superclaude-runtime/src/safety.rs`
- Evidence module: `crates/superclaude-runtime/src/evidence.rs`
- Test suite: `crates/superclaude-runtime/tests/test_hooks.rs`
