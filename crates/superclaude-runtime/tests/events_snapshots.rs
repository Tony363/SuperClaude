//! Snapshot tests for events JSONL output
//!
//! These tests verify that the Rust EventsTracker produces JSONL output
//! that matches the format expected by the daemon's metrics_watcher.rs parser.

use std::collections::HashMap;
use std::fs;
use std::path::PathBuf;

use insta::assert_yaml_snapshot;
use serde_json::Value as JsonValue;
use tempfile::TempDir;

use superclaude_runtime::events::{EventsTracker, FileAction, LogLevel, QualityDimensions};

/// Helper to read and parse JSONL events from a file
fn read_events(events_file: PathBuf) -> Vec<JsonValue> {
    let content = fs::read_to_string(events_file).unwrap();
    content
        .lines()
        .filter(|line| !line.trim().is_empty())
        .map(|line| serde_json::from_str(line).unwrap())
        .collect()
}

/// Helper to strip timestamp and session_id for snapshot testing
fn normalize_event(mut event: JsonValue) -> JsonValue {
    if let Some(obj) = event.as_object_mut() {
        obj.remove("timestamp");
        obj.remove("session_id");
    }
    event
}

#[test]
fn test_iteration_start_event() {
    let temp_dir = TempDir::new().unwrap();
    let mut tracker = EventsTracker::new(
        Some("test-session".to_string()),
        Some(temp_dir.path().to_path_buf()),
    )
    .unwrap();

    tracker.record_iteration_start(0, 0).unwrap();
    tracker.flush().unwrap();

    let events = read_events(temp_dir.path().join("events.jsonl"));
    assert_eq!(events.len(), 1);

    let normalized = normalize_event(events[0].clone());
    assert_yaml_snapshot!(normalized, @r###"
    ---
    depth: 0
    event_type: iteration_start
    iteration: 0
    node_id: iter-0
    "###);
}

#[test]
fn test_iteration_complete_event() {
    let temp_dir = TempDir::new().unwrap();
    let tracker = EventsTracker::new(
        Some("test-session".to_string()),
        Some(temp_dir.path().to_path_buf()),
    )
    .unwrap();

    let dims = QualityDimensions {
        code_changes: Some(80.0),
        tests_run: Some(100.0),
        tests_pass: Some(90.0),
        coverage: Some(75.0),
        no_errors: Some(100.0),
    };

    tracker
        .record_iteration_complete(
            0,
            85.0,
            Some(vec!["Add error handling".to_string()]),
            Some(dims),
            1.5,
        )
        .unwrap();
    tracker.flush().unwrap();

    let events = read_events(temp_dir.path().join("events.jsonl"));
    assert_eq!(events.len(), 1);

    let normalized = normalize_event(events[0].clone());
    assert_yaml_snapshot!(normalized, @r###"
    ---
    dimensions:
      code_changes: 80
      coverage: 75
      no_errors: 100
      tests_pass: 90
      tests_run: 100
    duration_seconds: 1.5
    event_type: iteration_complete
    improvements:
      - Add error handling
    iteration: 0
    node_id: iter-0
    score: 85
    "###);
}

#[test]
fn test_tool_use_event() {
    let temp_dir = TempDir::new().unwrap();
    let mut tracker = EventsTracker::new(
        Some("test-session".to_string()),
        Some(temp_dir.path().to_path_buf()),
    )
    .unwrap();

    let mut input = HashMap::new();
    input.insert("file_path".to_string(), serde_json::json!("src/main.rs"));

    tracker
        .record_tool_use("Write", &input, None, false, "", None)
        .unwrap();
    tracker.flush().unwrap();

    let events = read_events(temp_dir.path().join("events.jsonl"));
    assert_eq!(events.len(), 1);

    let mut normalized = normalize_event(events[0].clone());
    // Remove dynamic node_id for snapshot
    if let Some(obj) = normalized.as_object_mut() {
        obj.remove("node_id");
        obj.remove("parent_node_id");
    }

    assert_yaml_snapshot!(normalized, @r###"
    ---
    block_reason: ""
    blocked: false
    depth: 1
    event_type: tool_use
    summary: Created src/main.rs
    tool: Write
    "###);
}

#[test]
fn test_file_change_event() {
    let temp_dir = TempDir::new().unwrap();
    let mut tracker = EventsTracker::new(
        Some("test-session".to_string()),
        Some(temp_dir.path().to_path_buf()),
    )
    .unwrap();

    tracker
        .record_file_change("src/lib.rs", FileAction::Edit, 5, 3)
        .unwrap();
    tracker.flush().unwrap();

    let events = read_events(temp_dir.path().join("events.jsonl"));
    assert_eq!(events.len(), 1);

    let mut normalized = normalize_event(events[0].clone());
    if let Some(obj) = normalized.as_object_mut() {
        obj.remove("node_id");
    }

    assert_yaml_snapshot!(normalized, @r###"
    ---
    action: edit
    event_type: file_change
    lines_added: 5
    lines_removed: 3
    path: src/lib.rs
    "###);
}

#[test]
fn test_test_result_event() {
    let temp_dir = TempDir::new().unwrap();
    let mut tracker = EventsTracker::new(
        Some("test-session".to_string()),
        Some(temp_dir.path().to_path_buf()),
    )
    .unwrap();

    tracker
        .record_test_result(
            "pytest",
            15,
            2,
            1,
            85.5,
            Some(vec!["test_foo".to_string(), "test_bar".to_string()]),
        )
        .unwrap();
    tracker.flush().unwrap();

    let events = read_events(temp_dir.path().join("events.jsonl"));
    assert_eq!(events.len(), 1);

    let mut normalized = normalize_event(events[0].clone());
    if let Some(obj) = normalized.as_object_mut() {
        obj.remove("node_id");
    }

    assert_yaml_snapshot!(normalized, @r###"
    ---
    coverage: 85.5
    event_type: test_result
    failed: 2
    failed_tests:
      - test_foo
      - test_bar
    framework: pytest
    passed: 15
    skipped: 1
    "###);
}

#[test]
fn test_score_update_event() {
    let temp_dir = TempDir::new().unwrap();
    let tracker = EventsTracker::new(
        Some("test-session".to_string()),
        Some(temp_dir.path().to_path_buf()),
    )
    .unwrap();

    tracker
        .record_score_update(70.0, 85.0, "Tests passed", None)
        .unwrap();
    tracker.flush().unwrap();

    let events = read_events(temp_dir.path().join("events.jsonl"));
    assert_eq!(events.len(), 1);

    let normalized = normalize_event(events[0].clone());
    assert_yaml_snapshot!(normalized, @r###"
    ---
    event_type: score_update
    new_score: 85
    old_score: 70
    reason: Tests passed
    "###);
}

#[test]
fn test_subagent_spawn_event() {
    let temp_dir = TempDir::new().unwrap();
    let mut tracker = EventsTracker::new(
        Some("test-session".to_string()),
        Some(temp_dir.path().to_path_buf()),
    )
    .unwrap();

    tracker
        .record_subagent_spawn("agent-123", "Explore", "Find all test files", None)
        .unwrap();
    tracker.flush().unwrap();

    let events = read_events(temp_dir.path().join("events.jsonl"));
    assert_eq!(events.len(), 1);

    let mut normalized = normalize_event(events[0].clone());
    if let Some(obj) = normalized.as_object_mut() {
        obj.remove("node_id");
        obj.remove("parent_node_id");
    }

    assert_yaml_snapshot!(normalized, @r###"
    ---
    depth: 1
    event_type: subagent_spawn
    subagent_id: agent-123
    subagent_type: Explore
    task: Find all test files
    "###);
}

#[test]
fn test_subagent_complete_event() {
    let temp_dir = TempDir::new().unwrap();
    let tracker = EventsTracker::new(
        Some("test-session".to_string()),
        Some(temp_dir.path().to_path_buf()),
    )
    .unwrap();

    tracker
        .record_subagent_complete("agent-123", "subagent-1", true, "Found 15 test files")
        .unwrap();
    tracker.flush().unwrap();

    let events = read_events(temp_dir.path().join("events.jsonl"));
    assert_eq!(events.len(), 1);

    let normalized = normalize_event(events[0].clone());
    assert_yaml_snapshot!(normalized, @r###"
    ---
    event_type: subagent_complete
    node_id: subagent-1
    result: Found 15 test files
    subagent_id: agent-123
    success: true
    "###);
}

#[test]
fn test_artifact_event() {
    let temp_dir = TempDir::new().unwrap();
    let tracker = EventsTracker::new(
        Some("test-session".to_string()),
        Some(temp_dir.path().to_path_buf()),
    )
    .unwrap();

    tracker
        .record_artifact(
            "decisions/2025-02-07-use-rust.md",
            "decision",
            "Decision: Use Rust for Runtime",
        )
        .unwrap();
    tracker.flush().unwrap();

    let events = read_events(temp_dir.path().join("events.jsonl"));
    assert_eq!(events.len(), 1);

    let normalized = normalize_event(events[0].clone());
    assert_yaml_snapshot!(normalized, @r###"
    ---
    event_type: artifact
    path: decisions/2025-02-07-use-rust.md
    title: "Decision: Use Rust for Runtime"
    type: decision
    "###);
}

#[test]
fn test_error_event() {
    let temp_dir = TempDir::new().unwrap();
    let tracker = EventsTracker::new(
        Some("test-session".to_string()),
        Some(temp_dir.path().to_path_buf()),
    )
    .unwrap();

    tracker
        .record_error(
            "FileNotFoundError",
            "File 'config.yaml' not found",
            "  at src/main.rs:42",
            true,
        )
        .unwrap();
    tracker.flush().unwrap();

    let events = read_events(temp_dir.path().join("events.jsonl"));
    assert_eq!(events.len(), 1);

    let normalized = normalize_event(events[0].clone());
    assert_yaml_snapshot!(normalized, @r###"
    ---
    error_type: FileNotFoundError
    event_type: error
    message: "File 'config.yaml' not found"
    recoverable: true
    traceback: "  at src/main.rs:42"
    "###);
}

#[test]
fn test_log_event() {
    let temp_dir = TempDir::new().unwrap();
    let tracker = EventsTracker::new(
        Some("test-session".to_string()),
        Some(temp_dir.path().to_path_buf()),
    )
    .unwrap();

    tracker
        .record_log(LogLevel::Info, "Starting iteration 0", "orchestrator")
        .unwrap();
    tracker.flush().unwrap();

    let events = read_events(temp_dir.path().join("events.jsonl"));
    assert_eq!(events.len(), 1);

    let normalized = normalize_event(events[0].clone());
    assert_yaml_snapshot!(normalized, @r###"
    ---
    event_type: log
    level: info
    message: Starting iteration 0
    source: orchestrator
    "###);
}

#[test]
fn test_state_change_event() {
    let temp_dir = TempDir::new().unwrap();
    let tracker = EventsTracker::new(
        Some("test-session".to_string()),
        Some(temp_dir.path().to_path_buf()),
    )
    .unwrap();

    tracker
        .record_state_change("pending", "running", "User requested execution")
        .unwrap();
    tracker.flush().unwrap();

    let events = read_events(temp_dir.path().join("events.jsonl"));
    assert_eq!(events.len(), 1);

    let normalized = normalize_event(events[0].clone());
    assert_yaml_snapshot!(normalized, @r###"
    ---
    event_type: state_change
    new_state: running
    old_state: pending
    reason: User requested execution
    "###);
}

#[test]
fn test_multiple_events_sequence() {
    let temp_dir = TempDir::new().unwrap();
    let mut tracker = EventsTracker::new(
        Some("test-session".to_string()),
        Some(temp_dir.path().to_path_buf()),
    )
    .unwrap();

    // Simulate a complete iteration workflow
    tracker.record_iteration_start(0, 0).unwrap();

    let mut input = HashMap::new();
    input.insert("file_path".to_string(), serde_json::json!("src/main.rs"));
    tracker
        .record_tool_use("Write", &input, None, false, "", None)
        .unwrap();

    tracker
        .record_file_change("src/main.rs", FileAction::Write, 10, 0)
        .unwrap();

    tracker
        .record_test_result("cargo", 5, 0, 0, 100.0, None)
        .unwrap();

    tracker
        .record_iteration_complete(0, 95.0, None, None, 2.3)
        .unwrap();

    tracker.flush().unwrap();

    let events = read_events(temp_dir.path().join("events.jsonl"));
    assert_eq!(events.len(), 5);

    // Verify event types in order
    assert_eq!(events[0]["event_type"], "iteration_start");
    assert_eq!(events[1]["event_type"], "tool_use");
    assert_eq!(events[2]["event_type"], "file_change");
    assert_eq!(events[3]["event_type"], "test_result");
    assert_eq!(events[4]["event_type"], "iteration_complete");
}
