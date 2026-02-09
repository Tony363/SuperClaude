//! Reader for historical metrics from `.superclaude_metrics/` JSONL files.

use std::path::Path;
use std::fs::File;
use std::io::{BufRead, BufReader};
use anyhow::{Context, Result};

use crate::types::MetricEvent;

/// Read all events from `.superclaude_metrics/events.jsonl`.
pub fn read_events(project_root: &Path) -> Result<Vec<MetricEvent>> {
    let events_file = project_root.join(".superclaude_metrics/events.jsonl");
    if !events_file.exists() {
        return Ok(Vec::new());
    }

    let file = File::open(&events_file)
        .context(format!("Failed to open {}", events_file.display()))?;
    let reader = BufReader::new(file);

    let mut events = Vec::new();
    for line in reader.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        match serde_json::from_str::<MetricEvent>(&line) {
            Ok(event) => events.push(event),
            Err(_) => {
                // Skip malformed lines
            }
        }
    }

    Ok(events)
}

/// Read all metrics from `.superclaude_metrics/metrics.jsonl`.
pub fn read_metrics(project_root: &Path) -> Result<Vec<MetricEvent>> {
    let metrics_file = project_root.join(".superclaude_metrics/metrics.jsonl");
    if !metrics_file.exists() {
        return Ok(Vec::new());
    }

    let file = File::open(&metrics_file)
        .context(format!("Failed to open {}", metrics_file.display()))?;
    let reader = BufReader::new(file);

    let mut metrics = Vec::new();
    for line in reader.lines() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        match serde_json::from_str::<MetricEvent>(&line) {
            Ok(event) => metrics.push(event),
            Err(_) => {
                // Skip malformed lines
            }
        }
    }

    Ok(metrics)
}

/// Read events for a specific execution ID.
pub fn read_events_for_execution(project_root: &Path, execution_id: &str) -> Result<Vec<MetricEvent>> {
    let all_events = read_events(project_root)?;
    Ok(all_events
        .into_iter()
        .filter(|e| e.execution_id == execution_id)
        .collect())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn test_read_empty_directory() {
        let tmp = TempDir::new().unwrap();
        let events = read_events(tmp.path()).unwrap();
        assert!(events.is_empty());

        let metrics = read_metrics(tmp.path()).unwrap();
        assert!(metrics.is_empty());
    }

    #[test]
    fn test_read_events() {
        let tmp = TempDir::new().unwrap();
        let metrics_dir = tmp.path().join(".superclaude_metrics");
        fs::create_dir(&metrics_dir).unwrap();

        let events_file = metrics_dir.join("events.jsonl");
        fs::write(
            &events_file,
            r#"{"event_type":"test","execution_id":"exec-1","session_id":"sess-1"}
{"event_type":"test2","execution_id":"exec-1","session_id":"sess-1"}
"#,
        )
        .unwrap();

        let events = read_events(tmp.path()).unwrap();
        assert_eq!(events.len(), 2);
        assert_eq!(events[0].event_type, "test");
        assert_eq!(events[1].event_type, "test2");
    }

    #[test]
    fn test_filter_by_execution() {
        let tmp = TempDir::new().unwrap();
        let metrics_dir = tmp.path().join(".superclaude_metrics");
        fs::create_dir(&metrics_dir).unwrap();

        let events_file = metrics_dir.join("events.jsonl");
        fs::write(
            &events_file,
            r#"{"event_type":"test","execution_id":"exec-1","session_id":"sess-1"}
{"event_type":"test2","execution_id":"exec-2","session_id":"sess-1"}
{"event_type":"test3","execution_id":"exec-1","session_id":"sess-1"}
"#,
        )
        .unwrap();

        let events = read_events_for_execution(tmp.path(), "exec-1").unwrap();
        assert_eq!(events.len(), 2);
        assert_eq!(events[0].event_type, "test");
        assert_eq!(events[1].event_type, "test3");
    }
}
