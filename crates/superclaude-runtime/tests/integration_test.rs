//! Integration tests for SuperClaude Runtime modules
//!
//! These tests verify that module interfaces work correctly together
//! before integrating into the main agentic loop.

use std::collections::HashMap;
use std::fs;

use superclaude_runtime::evidence::{EvidenceCollector, TestResult};
use superclaude_runtime::events::{EventsTracker, FileAction, LogLevel, QualityDimensions};
use superclaude_runtime::quality::{assess_quality, QualityBand, QualityConfig};
use tempfile::TempDir;

// ============================================================================
// Test 1: Evidence + Quality Flow
// ============================================================================

#[test]
fn test_evidence_quality_integration() {
    let mut evidence = EvidenceCollector::new();

    // Record some file writes
    evidence.record_file_write("src/main.rs".to_string(), 50);
    evidence.record_file_edit("src/lib.rs".to_string(), 20);

    // Record test execution
    evidence.tests_run = true;
    let mut test_result = TestResult::new("cargo".to_string());
    test_result.passed = 10;
    test_result.failed = 0;
    test_result.coverage = 85.0;
    evidence.test_results.push(test_result);

    // Record successful command
    evidence.record_command("cargo build".to_string(), "Finished".to_string(), 0, 1000);

    // Assess quality
    let config = QualityConfig::default();
    let assessment = assess_quality(&evidence, Some(&config));

    // Verify quality score
    assert!(
        assessment.score > 70.0,
        "Expected high score for good evidence, got {}",
        assessment.score
    );
    // Score can be Good or Excellent depending on exact calculation
    assert!(matches!(assessment.band, QualityBand::Good | QualityBand::Excellent));
    assert!(assessment.passed, "Quality should pass default threshold");

    // Check evidence consistency
    assert_eq!(evidence.files_written.len(), 1);
    assert_eq!(evidence.files_edited.len(), 1);
    assert_eq!(evidence.test_results.len(), 1);
    assert!(evidence.tests_run);
}

#[test]
fn test_quality_with_failures() {
    let mut evidence = EvidenceCollector::new();

    // Record file changes but failing tests
    evidence.record_file_write("src/main.rs".to_string(), 50);

    evidence.tests_run = true;
    let mut test_result = TestResult::new("pytest".to_string());
    test_result.passed = 5;
    test_result.failed = 3;
    test_result.coverage = 45.0;
    evidence.test_results.push(test_result);

    let assessment = assess_quality(&evidence, None);

    // Should have some tests failing reflected in score
    // Note: Score may still be acceptable if some tests pass
    println!("Score with test failures: {}", assessment.score);
    assert!(!assessment.improvements_needed.is_empty(), "Should suggest improvements");
}

// ============================================================================
// Test 2: Events + Evidence Flow
// ============================================================================

#[test]
fn test_events_evidence_integration() {
    let temp_dir = TempDir::new().unwrap();

    // Create evidence collector
    let mut evidence = EvidenceCollector::new();
    evidence.record_file_write("src/main.rs".to_string(), 50);
    evidence.record_file_edit("src/lib.rs".to_string(), 20);

    evidence.tests_run = true;
    let mut test_result = TestResult::new("cargo".to_string());
    test_result.passed = 10;
    test_result.failed = 0;
    test_result.coverage = 85.0;
    evidence.test_results.push(test_result);

    // Assess quality
    let assessment = assess_quality(&evidence, None);

    // Create EventsTracker
    let mut tracker = EventsTracker::new(
        Some("test-session".to_string()),
        Some(temp_dir.path().to_path_buf()),
    )
    .unwrap();

    // Record iteration start
    tracker.record_iteration_start(0, 0).unwrap();

    // Record iteration complete with quality dimensions
    let dims = QualityDimensions {
        code_changes: Some(100.0),
        tests_run: Some(100.0),
        tests_pass: Some(100.0),
        coverage: Some(85.0),
        no_errors: Some(100.0),
    };

    tracker
        .record_iteration_complete(
            0,
            assessment.score as f32,
            Some(assessment.improvements_needed.clone()),
            Some(dims),
            1.5,
        )
        .unwrap();

    tracker.flush().unwrap();

    // Read and verify JSONL
    let events_file = temp_dir.path().join("events.jsonl");
    assert!(events_file.exists(), "Events file should exist");

    let content = fs::read_to_string(&events_file).unwrap();
    let lines: Vec<&str> = content.lines().collect();

    assert_eq!(lines.len(), 2, "Should have 2 events");

    // Parse events
    let event1: serde_json::Value = serde_json::from_str(lines[0]).unwrap();
    assert_eq!(event1["event_type"], "iteration_start");

    let event2: serde_json::Value = serde_json::from_str(lines[1]).unwrap();
    assert_eq!(event2["event_type"], "iteration_complete");
}

#[test]
fn test_full_iteration_workflow() {
    let temp_dir = TempDir::new().unwrap();

    let mut evidence = EvidenceCollector::new();
    let mut tracker = EventsTracker::new(
        Some("full-test".to_string()),
        Some(temp_dir.path().to_path_buf()),
    )
    .unwrap();

    // Start iteration
    tracker.record_iteration_start(0, 0).unwrap();

    // Tool use
    let mut tool_input = HashMap::new();
    tool_input.insert("file_path".to_string(), serde_json::json!("src/auth.rs"));
    tracker
        .record_tool_use("Write", &tool_input, None, false, "", None)
        .unwrap();

    // Record evidence
    evidence.record_file_write("src/auth.rs".to_string(), 100);

    tracker
        .record_file_change("src/auth.rs", FileAction::Write, 100, 0)
        .unwrap();

    // Run tests
    evidence.tests_run = true;
    let mut test_result = TestResult::new("cargo".to_string());
    test_result.passed = 15;
    test_result.coverage = 90.0;
    evidence.test_results.push(test_result);

    tracker
        .record_test_result("cargo", 15, 0, 0, 90.0, None)
        .unwrap();

    // Assess quality
    let assessment = assess_quality(&evidence, None);
    assert!(assessment.score >= 70.0);
    // Score can be Good or Excellent
    assert!(matches!(assessment.band, QualityBand::Good | QualityBand::Excellent));

    // Complete iteration
    let dims = QualityDimensions {
        code_changes: Some(100.0),
        tests_run: Some(100.0),
        tests_pass: Some(100.0),
        coverage: Some(90.0),
        no_errors: Some(100.0),
    };

    tracker
        .record_iteration_complete(0, assessment.score as f32, None, Some(dims), 3.5)
        .unwrap();

    tracker.flush().unwrap();

    // Verify workflow
    let content = fs::read_to_string(temp_dir.path().join("events.jsonl")).unwrap();
    let events: Vec<serde_json::Value> = content
        .lines()
        .map(|line| serde_json::from_str(line).unwrap())
        .collect();

    assert!(events.len() >= 5);
    assert_eq!(evidence.files_written.len(), 1);
    assert!(evidence.tests_run);
}
