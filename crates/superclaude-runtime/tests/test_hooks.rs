//! Integration tests for hooks module

use serde_json::{json, Value};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use superclaude_runtime::evidence::EvidenceCollector;
use superclaude_runtime::hooks::{
    create_evidence_hooks, create_logging_hooks, create_safety_hooks, create_sdk_hooks, merge_hooks,
    HookInput, HookOutput,
};

/// Helper to create a HookInput for testing
fn make_hook_input(
    event_name: &str,
    tool_name: &str,
    tool_input: HashMap<String, Value>,
) -> HookInput {
    HookInput {
        hook_event_name: event_name.to_string(),
        tool_name: tool_name.to_string(),
        tool_input,
        tool_response: Value::Null,
        session_id: "test-session".to_string(),
        stop_hook_active: false,
    }
}

#[tokio::test]
async fn test_safety_hooks_block_rm_rf_root() {
    let config = create_safety_hooks();

    // Find Bash matcher
    let bash_matcher = config
        .pre_tool_use
        .iter()
        .find(|m| m.matcher.as_deref() == Some("Bash"))
        .expect("Should have Bash matcher");

    let mut tool_input = HashMap::new();
    tool_input.insert("command".to_string(), json!("rm -rf /"));

    let input = make_hook_input("PreToolUse", "Bash", tool_input);
    let result = bash_matcher.hooks[0](input, None, HashMap::new()).await;

    assert!(result.hook_specific_output.is_some());
    let output = result.hook_specific_output.unwrap();
    assert_eq!(output.permission_decision, Some("deny".to_string()));
    assert!(output
        .permission_decision_reason
        .unwrap()
        .contains("Dangerous command"));
}

#[tokio::test]
async fn test_safety_hooks_block_git_reset_hard() {
    let config = create_safety_hooks();

    let bash_matcher = config
        .pre_tool_use
        .iter()
        .find(|m| m.matcher.as_deref() == Some("Bash"))
        .unwrap();

    let mut tool_input = HashMap::new();
    tool_input.insert("command".to_string(), json!("git reset --hard"));

    let input = make_hook_input("PreToolUse", "Bash", tool_input);
    let result = bash_matcher.hooks[0](input, None, HashMap::new()).await;

    assert!(result.hook_specific_output.is_some());
}

#[tokio::test]
async fn test_safety_hooks_allow_safe_commands() {
    let config = create_safety_hooks();

    let bash_matcher = config
        .pre_tool_use
        .iter()
        .find(|m| m.matcher.as_deref() == Some("Bash"))
        .unwrap();

    let safe_commands = vec!["ls -la", "git status", "npm install", "cargo build"];

    for command in safe_commands {
        let mut tool_input = HashMap::new();
        tool_input.insert("command".to_string(), json!(command));

        let input = make_hook_input("PreToolUse", "Bash", tool_input);
        let result = bash_matcher.hooks[0](input, None, HashMap::new()).await;

        assert!(
            result.hook_specific_output.is_none(),
            "Command '{}' should be allowed",
            command
        );
    }
}

#[tokio::test]
async fn test_safety_hooks_block_system_paths() {
    let config = create_safety_hooks();

    let write_matcher = config
        .pre_tool_use
        .iter()
        .find(|m| m.matcher.as_deref() == Some("Write|Edit"))
        .unwrap();

    let mut tool_input = HashMap::new();
    tool_input.insert("file_path".to_string(), json!("/etc/passwd"));

    let input = make_hook_input("PreToolUse", "Write", tool_input);
    let result = write_matcher.hooks[0](input, None, HashMap::new()).await;

    assert!(result.hook_specific_output.is_some());
    let output = result.hook_specific_output.unwrap();
    assert_eq!(output.permission_decision, Some("deny".to_string()));
}

#[tokio::test]
async fn test_safety_hooks_allow_user_paths() {
    let config = create_safety_hooks();

    let write_matcher = config
        .pre_tool_use
        .iter()
        .find(|m| m.matcher.as_deref() == Some("Write|Edit"))
        .unwrap();

    let mut tool_input = HashMap::new();
    tool_input.insert("file_path".to_string(), json!("/home/user/test.py"));

    let input = make_hook_input("PreToolUse", "Write", tool_input);
    let result = write_matcher.hooks[0](input, None, HashMap::new()).await;

    assert!(result.hook_specific_output.is_none());
}

#[tokio::test]
async fn test_evidence_hooks_record_file_write() {
    let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
    let config = create_evidence_hooks(Arc::clone(&evidence));

    let write_matcher = config
        .post_tool_use
        .iter()
        .find(|m| m.matcher.as_deref() == Some("Write|Edit|Read"))
        .unwrap();

    let mut tool_input = HashMap::new();
    tool_input.insert("file_path".to_string(), json!("test.py"));
    tool_input.insert("content".to_string(), json!("line1\nline2\nline3"));

    let input = make_hook_input("PostToolUse", "Write", tool_input);
    write_matcher.hooks[0](input, None, HashMap::new()).await;

    let ev = evidence.lock().unwrap();
    assert_eq!(ev.files_written.len(), 1);
    assert_eq!(ev.files_written[0], "test.py");
    assert_eq!(ev.file_changes.len(), 1);
    assert_eq!(ev.file_changes[0].action, "write");
    assert_eq!(ev.file_changes[0].lines_changed, 3);
}

#[tokio::test]
async fn test_evidence_hooks_record_file_edit() {
    let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
    let config = create_evidence_hooks(Arc::clone(&evidence));

    let edit_matcher = config
        .post_tool_use
        .iter()
        .find(|m| m.matcher.as_deref() == Some("Write|Edit|Read"))
        .unwrap();

    let mut tool_input = HashMap::new();
    tool_input.insert("file_path".to_string(), json!("test.py"));
    tool_input.insert("old_string".to_string(), json!("old\ncode"));
    tool_input.insert("new_string".to_string(), json!("new\ncode\nmore"));

    let input = make_hook_input("PostToolUse", "Edit", tool_input);
    edit_matcher.hooks[0](input, None, HashMap::new()).await;

    let ev = evidence.lock().unwrap();
    assert_eq!(ev.files_edited.len(), 1);
    assert_eq!(ev.files_edited[0], "test.py");
    assert_eq!(ev.file_changes[0].action, "edit");
    // abs(2 - 1) + 1 = 2 lines changed
    assert_eq!(ev.file_changes[0].lines_changed, 2);
}

#[tokio::test]
async fn test_evidence_hooks_record_file_read() {
    let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
    let config = create_evidence_hooks(Arc::clone(&evidence));

    let read_matcher = config
        .post_tool_use
        .iter()
        .find(|m| m.matcher.as_deref() == Some("Write|Edit|Read"))
        .unwrap();

    let mut tool_input = HashMap::new();
    tool_input.insert("file_path".to_string(), json!("test.py"));

    let input = make_hook_input("PostToolUse", "Read", tool_input);
    read_matcher.hooks[0](input, None, HashMap::new()).await;

    let ev = evidence.lock().unwrap();
    assert_eq!(ev.files_read.len(), 1);
    assert_eq!(ev.files_read[0], "test.py");
}

#[tokio::test]
async fn test_evidence_hooks_record_command() {
    let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
    let config = create_evidence_hooks(Arc::clone(&evidence));

    let bash_matcher = config
        .post_tool_use
        .iter()
        .find(|m| m.matcher.as_deref() == Some("Bash"))
        .unwrap();

    let mut tool_input = HashMap::new();
    tool_input.insert("command".to_string(), json!("ls -la"));

    let mut input = make_hook_input("PostToolUse", "Bash", tool_input);
    input.tool_response = json!("file1\nfile2\nfile3");

    bash_matcher.hooks[0](input, None, HashMap::new()).await;

    let ev = evidence.lock().unwrap();
    assert_eq!(ev.commands_run.len(), 1);
    assert_eq!(ev.commands_run[0].command, "ls -la");
}

#[tokio::test]
async fn test_evidence_hooks_track_all_tools() {
    let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
    let config = create_evidence_hooks(Arc::clone(&evidence));

    // Find the hook with no matcher (tracks all tools)
    let all_tools_matcher = config
        .post_tool_use
        .iter()
        .find(|m| m.matcher.is_none())
        .unwrap();

    let mut tool_input = HashMap::new();
    tool_input.insert("test_key".to_string(), json!("test_value"));

    let input = make_hook_input("PostToolUse", "SomeTool", tool_input);
    all_tools_matcher.hooks[0](input, None, HashMap::new()).await;

    let ev = evidence.lock().unwrap();
    assert_eq!(ev.tool_invocations.len(), 1);
    assert_eq!(ev.tool_invocations[0].tool_name, "SomeTool");
}

#[tokio::test]
async fn test_evidence_hooks_stop() {
    let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
    let config = create_evidence_hooks(Arc::clone(&evidence));

    assert_eq!(config.stop.len(), 1);

    let input = make_hook_input("Stop", "", HashMap::new());
    config.stop[0](input, None, HashMap::new()).await;

    let ev = evidence.lock().unwrap();
    assert!(ev.end_time.is_some());
    assert_eq!(ev.session_id, "test-session");
}

#[tokio::test]
async fn test_evidence_hooks_subagent_stop() {
    let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
    let config = create_evidence_hooks(Arc::clone(&evidence));

    assert_eq!(config.subagent_stop.len(), 1);

    let input = make_hook_input("SubagentStop", "", HashMap::new());
    config.subagent_stop[0](input, Some("tool-123".to_string()), HashMap::new()).await;

    let ev = evidence.lock().unwrap();
    assert_eq!(ev.subagents_spawned, 1);
    assert_eq!(ev.subagent_results.len(), 1);
}

#[tokio::test]
async fn test_create_sdk_hooks() {
    let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
    let config = create_sdk_hooks(evidence);

    // Should have safety + evidence hooks combined
    assert!(config.pre_tool_use.len() >= 2); // Safety hooks
    assert!(config.post_tool_use.len() >= 3); // Evidence hooks
    assert_eq!(config.stop.len(), 1);
    assert_eq!(config.subagent_stop.len(), 1);
}

#[tokio::test]
async fn test_merge_hooks() {
    let safety = create_safety_hooks();
    let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
    let evidence_hooks = create_evidence_hooks(evidence);

    let merged = merge_hooks(vec![safety, evidence_hooks]);

    assert!(merged.pre_tool_use.len() >= 2);
    assert!(merged.post_tool_use.len() >= 3);
    assert_eq!(merged.stop.len(), 1);
    assert_eq!(merged.subagent_stop.len(), 1);
}

#[tokio::test]
async fn test_logging_hooks() {
    let logs = Arc::new(Mutex::new(Vec::new()));
    let logs_clone = Arc::clone(&logs);

    let log_fn = move |msg: String| {
        logs_clone.lock().unwrap().push(msg);
    };

    let config = create_logging_hooks(log_fn);

    // Test PreToolUse logging
    let pre_matcher = config.pre_tool_use.iter().find(|m| m.matcher.is_none()).unwrap();

    let mut tool_input = HashMap::new();
    tool_input.insert("command".to_string(), json!("test command"));

    let input = make_hook_input("PreToolUse", "Bash", tool_input);
    pre_matcher.hooks[0](input, None, HashMap::new()).await;

    let logged = logs.lock().unwrap();
    assert_eq!(logged.len(), 1);
    assert!(logged[0].contains("[PRE]"));
    assert!(logged[0].contains("Bash"));
}

#[tokio::test]
async fn test_hook_ordering() {
    let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
    let config = create_sdk_hooks(Arc::clone(&evidence));

    // Safety hooks should be first in PreToolUse (block before evidence)
    assert!(config.pre_tool_use.len() >= 2);

    // Test that dangerous command is blocked BEFORE evidence collection
    let bash_matcher = config
        .pre_tool_use
        .iter()
        .find(|m| m.matcher.as_deref() == Some("Bash"))
        .unwrap();

    let mut tool_input = HashMap::new();
    tool_input.insert("command".to_string(), json!("rm -rf /"));

    let input = make_hook_input("PreToolUse", "Bash", tool_input);
    let result = bash_matcher.hooks[0](input, None, HashMap::new()).await;

    // Should be blocked
    assert!(result.hook_specific_output.is_some());

    // Evidence should not have recorded it (PreToolUse doesn't record)
    let ev = evidence.lock().unwrap();
    assert_eq!(ev.commands_run.len(), 0);
}

#[tokio::test]
async fn test_multiple_hooks_same_tool() {
    let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));
    let config = create_sdk_hooks(evidence);

    // PostToolUse should have multiple hooks for file operations
    let file_matchers: Vec<_> = config
        .post_tool_use
        .iter()
        .filter(|m| {
            m.matcher
                .as_ref()
                .map(|s| s.contains("Write"))
                .unwrap_or(false)
        })
        .collect();

    assert!(file_matchers.len() >= 1);
}
