//! SDK Hook Factories - Create hooks for the Anthropic Agent SDK.
//!
//! These hooks integrate with the SDK's query() function to:
//! 1. Collect evidence (files, tests, commands) via PostToolUse
//! 2. Block dangerous operations via PreToolUse
//! 3. Track session lifecycle via Stop/SubagentStop
//!
//! # Example Usage
//! ```rust,no_run
//! use superclaude_runtime::hooks::{create_sdk_hooks, HookConfig};
//! use superclaude_runtime::evidence::EvidenceCollector;
//!
//! let evidence = EvidenceCollector::new();
//! let hooks = create_sdk_hooks(evidence);
//! // Pass hooks to ClaudeAgentOptions
//! ```
//!
//! Based on: SuperClaude/Orchestrator/hooks.py

use crate::evidence::EvidenceCollector;
use crate::safety::SafetyValidator;
use futures::future::BoxFuture;
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::path::Path;
use std::sync::{Arc, Mutex};
use tracing::{debug, info, warn};

/// Hook callback function type (async)
pub type HookCallback = Box<
    dyn Fn(HookInput, Option<String>, HashMap<String, Value>) -> BoxFuture<'static, HookOutput>
        + Send
        + Sync,
>;

/// Input data passed to hook callbacks
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HookInput {
    pub hook_event_name: String,
    pub tool_name: String,
    pub tool_input: HashMap<String, Value>,
    #[serde(default)]
    pub tool_response: Value,
    #[serde(default)]
    pub session_id: String,
    #[serde(default)]
    pub stop_hook_active: bool,
}

/// Output returned by hook callbacks
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HookOutput {
    #[serde(skip_serializing_if = "Option::is_none")]
    pub hook_specific_output: Option<HookSpecificOutput>,
}

impl HookOutput {
    /// Create an "allow" response (empty output)
    pub fn allow() -> Self {
        Self {
            hook_specific_output: None,
        }
    }

    /// Create a "deny" response for PreToolUse
    pub fn deny(reason: impl Into<String>) -> Self {
        Self {
            hook_specific_output: Some(HookSpecificOutput {
                hook_event_name: "PreToolUse".to_string(),
                permission_decision: Some("deny".to_string()),
                permission_decision_reason: Some(reason.into()),
            }),
        }
    }
}

/// Hook-specific output structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HookSpecificOutput {
    #[serde(rename = "hookEventName")]
    pub hook_event_name: String,
    #[serde(rename = "permissionDecision", skip_serializing_if = "Option::is_none")]
    pub permission_decision: Option<String>,
    #[serde(
        rename = "permissionDecisionReason",
        skip_serializing_if = "Option::is_none"
    )]
    pub permission_decision_reason: Option<String>,
}

/// Hook matcher and callback configuration
pub struct HookMatcher {
    /// Regex pattern to match tool names (e.g., "Bash", "Write|Edit")
    pub matcher: Option<String>,
    /// Hook callbacks to execute
    pub hooks: Vec<HookCallback>,
}

/// Complete hook configuration for all event types
#[derive(Default)]
pub struct HookConfig {
    pub pre_tool_use: Vec<HookMatcher>,
    pub post_tool_use: Vec<HookMatcher>,
    pub stop: Vec<HookCallback>,
    pub subagent_stop: Vec<HookCallback>,
}

impl HookConfig {
    /// Create empty hook configuration
    pub fn new() -> Self {
        Self::default()
    }

    /// Merge another hook configuration into this one
    pub fn merge(&mut self, other: HookConfig) {
        self.pre_tool_use.extend(other.pre_tool_use);
        self.post_tool_use.extend(other.post_tool_use);
        self.stop.extend(other.stop);
        self.subagent_stop.extend(other.subagent_stop);
    }
}

/// Create a complete set of SDK hooks for the agentic loop.
///
/// Combines safety hooks (PreToolUse) and evidence hooks (PostToolUse).
pub fn create_sdk_hooks(evidence: Arc<Mutex<EvidenceCollector>>) -> HookConfig {
    let safety_hooks = create_safety_hooks();
    let evidence_hooks = create_evidence_hooks(evidence);

    let mut combined = HookConfig::new();
    combined.merge(safety_hooks);
    combined.merge(evidence_hooks);

    combined
}

/// Create safety hooks that block dangerous operations.
pub fn create_safety_hooks() -> HookConfig {
    let validator = Arc::new(SafetyValidator::new());

    // Hook 1: Block dangerous Bash commands
    let validator_clone = Arc::clone(&validator);
    let block_dangerous_commands: HookCallback = Box::new(move |input, _tool_use_id, _context| {
        let validator = Arc::clone(&validator_clone);
        Box::pin(async move {
            if input.hook_event_name != "PreToolUse" {
                return HookOutput::allow();
            }

            if input.tool_name == "Bash" {
                if let Some(command) = input.tool_input.get("command").and_then(|v| v.as_str()) {
                    if let Err(e) = validator.validate_command(command) {
                        warn!("Blocked dangerous command: {}", command);
                        return HookOutput::deny(format!("{}", e));
                    }
                }
            }

            HookOutput::allow()
        })
    });

    // Hook 2: Validate file paths for Write/Edit operations
    let validator_clone = Arc::clone(&validator);
    let validate_file_paths: HookCallback = Box::new(move |input, _tool_use_id, _context| {
        let validator = Arc::clone(&validator_clone);
        Box::pin(async move {
            if input.hook_event_name != "PreToolUse" {
                return HookOutput::allow();
            }

            if input.tool_name == "Write" || input.tool_name == "Edit" {
                if let Some(file_path) = input.tool_input.get("file_path").and_then(|v| v.as_str())
                {
                    if let Err(e) = validator.validate_path(Path::new(file_path)) {
                        warn!("Blocked file operation on: {}", file_path);
                        return HookOutput::deny(format!("{}", e));
                    }
                }
            }

            HookOutput::allow()
        })
    });

    let mut config = HookConfig::new();

    config.pre_tool_use.push(HookMatcher {
        matcher: Some("Bash".to_string()),
        hooks: vec![block_dangerous_commands],
    });

    config.pre_tool_use.push(HookMatcher {
        matcher: Some("Write|Edit".to_string()),
        hooks: vec![validate_file_paths],
    });

    config
}

/// Create evidence collection hooks.
pub fn create_evidence_hooks(evidence: Arc<Mutex<EvidenceCollector>>) -> HookConfig {
    let mut config = HookConfig::new();

    // Hook 1: Collect file changes
    let evidence_clone = Arc::clone(&evidence);
    let collect_file_changes: HookCallback = Box::new(move |input, _tool_use_id, _context| {
        let evidence = Arc::clone(&evidence_clone);
        Box::pin(async move {
            if input.hook_event_name != "PostToolUse" {
                return HookOutput::allow();
            }

            let file_path = input
                .tool_input
                .get("file_path")
                .and_then(|v| v.as_str())
                .unwrap_or("");

            if file_path.is_empty() {
                return HookOutput::allow();
            }

            let mut ev = evidence.lock().unwrap();

            match input.tool_name.as_str() {
                "Write" => {
                    let content = input
                        .tool_input
                        .get("content")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    let lines = content.matches('\n').count() + 1;
                    ev.record_file_write(file_path.to_string(), lines);
                    debug!("Recorded file write: {} ({} lines)", file_path, lines);
                }
                "Edit" => {
                    let old_str = input
                        .tool_input
                        .get("old_string")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    let new_str = input
                        .tool_input
                        .get("new_string")
                        .and_then(|v| v.as_str())
                        .unwrap_or("");
                    let lines =
                        (new_str.matches('\n').count() as i32 - old_str.matches('\n').count() as i32)
                            .unsigned_abs() as usize
                            + 1;
                    ev.record_file_edit(file_path.to_string(), lines);
                    debug!("Recorded file edit: {} ({} lines)", file_path, lines);
                }
                "Read" => {
                    ev.record_file_read(file_path.to_string());
                    debug!("Recorded file read: {}", file_path);
                }
                _ => {}
            }

            HookOutput::allow()
        })
    });

    // Hook 2: Collect command results
    let evidence_clone = Arc::clone(&evidence);
    let collect_command_results: HookCallback = Box::new(move |input, _tool_use_id, _context| {
        let evidence = Arc::clone(&evidence_clone);
        Box::pin(async move {
            if input.hook_event_name != "PostToolUse" {
                return HookOutput::allow();
            }

            if input.tool_name == "Bash" {
                let command = input
                    .tool_input
                    .get("command")
                    .and_then(|v| v.as_str())
                    .unwrap_or("");
                let output = input.tool_response.as_str().unwrap_or("");

                let mut ev = evidence.lock().unwrap();
                ev.record_command(command.to_string(), output.to_string(), 0, 0);
                debug!("Recorded command execution: {}", command);
            }

            HookOutput::allow()
        })
    });

    // Hook 3: Track all tool invocations (for debugging)
    let evidence_clone = Arc::clone(&evidence);
    let track_all_tools: HookCallback = Box::new(move |input, _tool_use_id, _context| {
        let evidence = Arc::clone(&evidence_clone);
        Box::pin(async move {
            if input.hook_event_name != "PostToolUse" {
                return HookOutput::allow();
            }

            let mut ev = evidence.lock().unwrap();
            ev.record_tool_invocation(
                input.tool_name.clone(),
                json!(input.tool_input),
                input.tool_response.as_str().unwrap_or("").to_string(),
            );

            HookOutput::allow()
        })
    });

    // Hook 4: Stop hook - finalize evidence collection
    let evidence_clone = Arc::clone(&evidence);
    let on_stop: HookCallback = Box::new(move |input, _tool_use_id, _context| {
        let evidence = Arc::clone(&evidence_clone);
        Box::pin(async move {
            if input.hook_event_name != "Stop" {
                return HookOutput::allow();
            }

            let mut ev = evidence.lock().unwrap();
            ev.end_time = Some(chrono::Utc::now());
            ev.session_id = input.session_id.clone();
            info!("Evidence collection finalized for session: {}", ev.session_id);

            HookOutput::allow()
        })
    });

    // Hook 5: SubagentStop hook - track subagent completions
    let evidence_clone = Arc::clone(&evidence);
    let on_subagent_stop: HookCallback = Box::new(move |input, tool_use_id, _context| {
        let evidence = Arc::clone(&evidence_clone);
        Box::pin(async move {
            if input.hook_event_name != "SubagentStop" {
                return HookOutput::allow();
            }

            let mut ev = evidence.lock().unwrap();
            ev.subagents_spawned += 1;
            ev.subagent_results.push(json!({
                "tool_use_id": tool_use_id,
                "stop_hook_active": input.stop_hook_active,
            }));

            HookOutput::allow()
        })
    });

    // Register PostToolUse hooks
    config.post_tool_use.push(HookMatcher {
        matcher: Some("Write|Edit|Read".to_string()),
        hooks: vec![collect_file_changes],
    });

    config.post_tool_use.push(HookMatcher {
        matcher: Some("Bash".to_string()),
        hooks: vec![collect_command_results],
    });

    config.post_tool_use.push(HookMatcher {
        matcher: None, // No matcher = all tools
        hooks: vec![track_all_tools],
    });

    // Register Stop/SubagentStop hooks
    config.stop.push(on_stop);
    config.subagent_stop.push(on_subagent_stop);

    config
}

/// Create hooks that log all tool invocations.
pub fn create_logging_hooks<F>(log_fn: F) -> HookConfig
where
    F: Fn(String) + Send + Sync + 'static,
{
    let log_fn = Arc::new(log_fn);
    let mut config = HookConfig::new();

    // PreToolUse logging
    let log_fn_clone = Arc::clone(&log_fn);
    let log_pre_tool: HookCallback = Box::new(move |input, _tool_use_id, _context| {
        let log_fn = Arc::clone(&log_fn_clone);
        Box::pin(async move {
            if input.hook_event_name != "PreToolUse" {
                return HookOutput::allow();
            }

            let tool_input_str = format!("{:?}", input.tool_input);
            let truncated = if tool_input_str.len() > 100 {
                format!("{}...", &tool_input_str[..100])
            } else {
                tool_input_str
            };

            log_fn(format!("[PRE] {}: {}", input.tool_name, truncated));

            HookOutput::allow()
        })
    });

    // PostToolUse logging
    let log_fn_clone = Arc::clone(&log_fn);
    let log_post_tool: HookCallback = Box::new(move |input, _tool_use_id, _context| {
        let log_fn = Arc::clone(&log_fn_clone);
        Box::pin(async move {
            if input.hook_event_name != "PostToolUse" {
                return HookOutput::allow();
            }

            let response_str = format!("{:?}", input.tool_response);
            let truncated = if response_str.len() > 100 {
                format!("{}...", &response_str[..100])
            } else {
                response_str
            };

            log_fn(format!("[POST] {}: {}", input.tool_name, truncated));

            HookOutput::allow()
        })
    });

    config.pre_tool_use.push(HookMatcher {
        matcher: None,
        hooks: vec![log_pre_tool],
    });

    config.post_tool_use.push(HookMatcher {
        matcher: None,
        hooks: vec![log_post_tool],
    });

    config
}

/// Merge multiple hook configurations.
pub fn merge_hooks(configs: Vec<HookConfig>) -> HookConfig {
    let mut merged = HookConfig::new();

    for config in configs {
        merged.merge(config);
    }

    merged
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_safety_hooks_block_dangerous_commands() {
        let config = create_safety_hooks();

        // Find the Bash matcher
        let bash_matcher = config
            .pre_tool_use
            .iter()
            .find(|m| m.matcher.as_deref() == Some("Bash"))
            .expect("Bash matcher should exist");

        // Test dangerous command
        let input = HookInput {
            hook_event_name: "PreToolUse".to_string(),
            tool_name: "Bash".to_string(),
            tool_input: {
                let mut map = HashMap::new();
                map.insert("command".to_string(), json!("rm -rf /"));
                map
            },
            tool_response: Value::Null,
            session_id: String::new(),
            stop_hook_active: false,
        };

        let result = bash_matcher.hooks[0](input, None, HashMap::new()).await;
        assert!(result.hook_specific_output.is_some());
        let output = result.hook_specific_output.unwrap();
        assert_eq!(output.permission_decision, Some("deny".to_string()));
    }

    #[tokio::test]
    async fn test_safety_hooks_allow_safe_commands() {
        let config = create_safety_hooks();

        let bash_matcher = config
            .pre_tool_use
            .iter()
            .find(|m| m.matcher.as_deref() == Some("Bash"))
            .unwrap();

        // Test safe command
        let input = HookInput {
            hook_event_name: "PreToolUse".to_string(),
            tool_name: "Bash".to_string(),
            tool_input: {
                let mut map = HashMap::new();
                map.insert("command".to_string(), json!("ls -la"));
                map
            },
            tool_response: Value::Null,
            session_id: String::new(),
            stop_hook_active: false,
        };

        let result = bash_matcher.hooks[0](input, None, HashMap::new()).await;
        assert!(result.hook_specific_output.is_none());
    }

    #[tokio::test]
    async fn test_evidence_hooks_record_file_write() {
        let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
        let config = create_evidence_hooks(Arc::clone(&evidence));

        // Find Write matcher
        let write_matcher = config
            .post_tool_use
            .iter()
            .find(|m| m.matcher.as_deref() == Some("Write|Edit|Read"))
            .unwrap();

        let input = HookInput {
            hook_event_name: "PostToolUse".to_string(),
            tool_name: "Write".to_string(),
            tool_input: {
                let mut map = HashMap::new();
                map.insert("file_path".to_string(), json!("test.py"));
                map.insert("content".to_string(), json!("line1\nline2\nline3"));
                map
            },
            tool_response: Value::Null,
            session_id: String::new(),
            stop_hook_active: false,
        };

        write_matcher.hooks[0](input, None, HashMap::new()).await;

        let ev = evidence.lock().unwrap();
        assert_eq!(ev.files_written.len(), 1);
        assert_eq!(ev.files_written[0], "test.py");
        assert_eq!(ev.file_changes[0].lines_changed, 3);
    }

    #[tokio::test]
    async fn test_merge_hooks() {
        let config1 = create_safety_hooks();
        let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
        let config2 = create_evidence_hooks(evidence);

        let merged = merge_hooks(vec![config1, config2]);

        assert!(merged.pre_tool_use.len() >= 2); // At least safety hooks
        assert!(merged.post_tool_use.len() >= 3); // At least evidence hooks
        assert!(merged.stop.len() >= 1);
        assert!(merged.subagent_stop.len() >= 1);
    }
}
