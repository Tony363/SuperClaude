# Task #11: Loop Runner Architecture & Implementation Plan

**Author:** skills-porter
**Date:** 2026-02-07
**Status:** PLANNING
**Python Reference:** `/SuperClaude/Orchestrator/loop_runner.py` (414 lines)

## Executive Summary

This document provides the complete architecture and implementation plan for porting SuperClaude's agentic loop from Python to Rust. The loop runner is the orchestrator that coordinates all other modules (evidence, quality, hooks, events, skills, API) to implement SuperClaude's iterative quality improvement system.

**Complexity:** HIGH - This is the integration point for all 10 other modules
**Estimated LOC:** ~600-800 lines of Rust
**Critical Dependencies:** All modules must compile first

---

## 1. Current Python Architecture Analysis

### 1.1 Core Flow

```
┌────────────────────────────────────────────────────────┐
│                  run_agentic_loop()                     │
│  ┌──────────────────────────────────────────────────┐  │
│  │ 1. Initialize Evidence Collector                 │  │
│  │ 2. Setup SDK Hooks (safety + evidence + events) │  │
│  │ 3. FOR iteration in range(max_iterations):       │  │
│  │    a. Reset evidence                             │  │
│  │    b. Build iteration prompt                     │  │
│  │    c. Query Claude SDK with hooks                │  │
│  │    d. Assess quality from evidence               │  │
│  │    e. Check termination conditions               │  │
│  │    f. Record iteration result                    │  │
│  │    g. Call on_iteration callback                 │  │
│  │ 4. Return LoopResult                             │  │
│  └──────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────┘
```

### 1.2 Module Integration Points

| Module | Used For | Integration Point |
|--------|----------|-------------------|
| **Evidence** | Track file changes, commands, tests | EvidenceCollector injected into hooks |
| **Quality** | Assess iteration quality | assess_quality(evidence, config) |
| **Hooks** | Safety + evidence collection | create_sdk_hooks(evidence) |
| **Events** | Zed panel real-time updates | EventsTracker records events |
| **Skills** | Retrieve relevant learned skills | (Future: inject into prompt) |
| **API** | Execute Claude queries | query(prompt, options) |

### 1.3 Key Data Structures

```python
# Configuration
@dataclass
class LoopConfig:
    max_iterations: int = 3
    hard_max_iterations: int = 5
    quality_threshold: float = 70.0
    min_improvement: float = 5.0
    oscillation_window: int = 3
    stagnation_threshold: float = 2.0
    timeout_seconds: float | None = None
    iteration_timeout_seconds: float = 300.0
    model: str = "sonnet"
    max_turns: int = 50
    pal_review_enabled: bool = False
    pal_model: str = "gpt-5"

# Iteration result
@dataclass
class IterationResult:
    iteration: int
    score: float
    improvements: list[str]
    evidence: dict[str, Any]
    duration_seconds: float
    messages_count: int

# Final result
@dataclass
class LoopResult:
    status: str  # "success" or "terminated"
    reason: TerminationReason
    final_score: float
    total_iterations: int
    iteration_history: list[IterationResult]
    total_duration_seconds: float
    evidence_summary: dict[str, Any]
```

### 1.4 Termination Conditions

```python
class TerminationReason(Enum):
    QUALITY_MET = "quality_threshold_met"
    MAX_ITERATIONS = "max_iterations_reached"
    OSCILLATION = "oscillation_detected"      # Alternating up/down scores
    STAGNATION = "stagnation_detected"        # No improvement
    TIMEOUT = "timeout_exceeded"
    USER_CANCELLED = "user_cancelled"
    ERROR = "error"
```

**Detection Logic:**
- **Oscillation:** Check if deltas alternate positive/negative (up/down/up pattern)
- **Stagnation:** Check if improvement < min_improvement OR variance < threshold
- **Timeout:** Track elapsed time vs config.timeout_seconds

### 1.5 Prompt Building

```python
def _build_iteration_prompt(task, iteration, history):
    prompt = task
    if iteration > 0:
        last = history[-1]
        prompt += f"\n\nIteration {iteration + 1}. Previous: {last.score:.1f}/100"
        prompt += "\nPrioritize: " + "\n".join(last.improvements[:3])
        if tests_run:
            prompt += f"\nTests: {passed} passed, {failed} failed"
    return prompt
```

**Key insight:** Each iteration builds on previous results to guide improvement.

---

## 2. Rust Architecture Design

### 2.1 Core Types

```rust
// crates/superclaude-runtime/src/loop_runner.rs

/// Configuration for the agentic loop
#[derive(Debug, Clone)]
pub struct LoopConfig {
    // Iteration limits
    pub max_iterations: usize,
    pub hard_max_iterations: usize,  // Safety cap (5)

    // Quality settings
    pub quality_threshold: f64,
    pub min_improvement: f64,

    // Termination detection
    pub oscillation_window: usize,
    pub stagnation_threshold: f64,

    // Timeouts
    pub timeout_seconds: Option<f64>,
    pub iteration_timeout_seconds: f64,

    // Model settings
    pub model: String,
    pub max_turns: usize,

    // PAL integration (future)
    pub pal_review_enabled: bool,
    pub pal_model: String,
}

impl Default for LoopConfig {
    fn default() -> Self {
        Self {
            max_iterations: 3,
            hard_max_iterations: 5,
            quality_threshold: 70.0,
            min_improvement: 5.0,
            oscillation_window: 3,
            stagnation_threshold: 2.0,
            timeout_seconds: None,
            iteration_timeout_seconds: 300.0,
            model: "sonnet".to_string(),
            max_turns: 50,
            pal_review_enabled: false,
            pal_model: "gpt-5".to_string(),
        }
    }
}

/// Result of a single loop iteration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IterationResult {
    pub iteration: usize,
    pub score: f64,
    pub improvements: Vec<String>,
    pub evidence: HashMap<String, serde_json::Value>,
    pub duration_seconds: f64,
    pub messages_count: usize,
}

/// Reasons for loop termination
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TerminationReason {
    QualityMet,
    MaxIterations,
    Oscillation,
    Stagnation,
    Timeout,
    UserCancelled,
    Error,
}

impl TerminationReason {
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::QualityMet => "quality_threshold_met",
            Self::MaxIterations => "max_iterations_reached",
            Self::Oscillation => "oscillation_detected",
            Self::Stagnation => "stagnation_detected",
            Self::Timeout => "timeout_exceeded",
            Self::UserCancelled => "user_cancelled",
            Self::Error => "error",
        }
    }
}

/// Final result of the agentic loop
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoopResult {
    pub status: String,  // "success" or "terminated"
    pub reason: TerminationReason,
    pub final_score: f64,
    pub total_iterations: usize,
    pub iteration_history: Vec<IterationResult>,
    pub total_duration_seconds: f64,
    pub evidence_summary: HashMap<String, serde_json::Value>,
}

impl LoopResult {
    /// Whether the loop achieved its quality threshold
    pub fn passed(&self) -> bool {
        self.status == "success"
    }
}
```

### 2.2 Main Loop Runner

```rust
/// Main entry point for the agentic loop
pub async fn run_agentic_loop(
    task: &str,
    config: Option<LoopConfig>,
    additional_hooks: Option<HashMap<String, Vec<HookDefinition>>>,
    on_iteration: Option<Box<dyn Fn(&IterationResult) + Send + Sync>>,
    events_tracker: Option<EventsTracker>,
    enable_events: bool,
) -> Result<LoopResult> {
    let config = config.unwrap_or_default();
    let effective_max = config.max_iterations.min(config.hard_max_iterations);

    // Initialize evidence collector
    let mut evidence = EvidenceCollector::new();

    // Initialize events tracker for Zed panel
    let mut tracker = events_tracker.unwrap_or_else(|| {
        if enable_events {
            EventsTracker::new(None, None).expect("Failed to create tracker")
        } else {
            // Create a no-op tracker
            EventsTracker::disabled()
        }
    });

    // Create SDK hooks (safety + evidence + events)
    let mut sdk_hooks = create_sdk_hooks(&evidence)?;

    if enable_events {
        let events_hooks = create_events_hooks(&evidence, Some(&tracker))?;
        sdk_hooks = merge_hooks(vec![sdk_hooks, events_hooks])?;
    }

    if let Some(extra) = additional_hooks {
        sdk_hooks = merge_hooks(vec![sdk_hooks, extra])?;
    }

    // Quality config
    let quality_config = QualityConfig {
        quality_threshold: config.quality_threshold,
        ..Default::default()
    };

    // Loop state
    let mut score_history: Vec<f64> = Vec::new();
    let mut iteration_history: Vec<IterationResult> = Vec::new();
    let loop_start = Instant::now();

    let mut termination_reason = TerminationReason::MaxIterations;

    // Main iteration loop
    for iteration in 0..effective_max {
        let iteration_start = Instant::now();
        tracing::info!("Starting iteration {}/{}", iteration + 1, effective_max);

        // Record iteration start for Zed panel
        if enable_events {
            tracker.record_iteration_start(iteration, 0)?;
        }

        // Reset evidence for this iteration
        evidence.reset();

        // Build prompt with context from previous iterations
        let prompt = build_iteration_prompt(task, iteration, &iteration_history);

        // Execute via Anthropic API with hooks
        let messages = match execute_with_api(
            &prompt,
            &config,
            &sdk_hooks,
            config.iteration_timeout_seconds,
        ).await {
            Ok(msgs) => msgs,
            Err(e) => {
                tracing::error!("API query failed: {}", e);
                termination_reason = TerminationReason::Error;
                break;
            }
        };

        // Assess quality using evidence collected by hooks
        let assessment = assess_quality(&evidence, Some(&quality_config))?;
        score_history.push(assessment.score);

        // Record iteration result
        let iteration_duration = iteration_start.elapsed().as_secs_f64();
        let iteration_result = IterationResult {
            iteration,
            score: assessment.score,
            improvements: assessment.improvements_needed.clone(),
            evidence: evidence.to_dict(),
            duration_seconds: iteration_duration,
            messages_count: messages.len(),
        };
        iteration_history.push(iteration_result.clone());

        tracing::info!(
            "Iteration {} complete: score={:.1}, passed={}",
            iteration + 1,
            assessment.score,
            assessment.passed
        );

        // Call iteration callback if provided
        if let Some(ref callback) = on_iteration {
            callback(&iteration_result);
        }

        // Check termination conditions
        if assessment.passed {
            termination_reason = TerminationReason::QualityMet;
            tracing::info!("Quality threshold met!");
            break;
        }

        if score_history.len() >= config.oscillation_window {
            let window = &score_history[score_history.len() - config.oscillation_window..];
            if is_oscillating(window, 5.0) {
                termination_reason = TerminationReason::Oscillation;
                tracing::warn!("Oscillation detected, terminating loop");
                break;
            }
        }

        if score_history.len() >= 2 {
            let recent = &score_history[score_history.len() - 2..];
            if is_stagnating(recent, config.stagnation_threshold, config.min_improvement) {
                termination_reason = TerminationReason::Stagnation;
                tracing::warn!("Stagnation detected, terminating loop");
                break;
            }
        }

        // Check timeout
        if let Some(timeout) = config.timeout_seconds {
            let elapsed = loop_start.elapsed().as_secs_f64();
            if elapsed > timeout {
                termination_reason = TerminationReason::Timeout;
                tracing::warn!("Timeout exceeded");
                break;
            }
        }
    }

    // Build final result
    let total_duration = loop_start.elapsed().as_secs_f64();
    let status = if termination_reason == TerminationReason::QualityMet {
        "success"
    } else {
        "terminated"
    };

    // Record final state change for Zed panel
    if enable_events {
        let final_state = if status == "success" { "completed" } else { "failed" };
        tracker.record_state_change("running", final_state, termination_reason.as_str())?;
        tracker.flush()?;
    }

    Ok(LoopResult {
        status: status.to_string(),
        reason: termination_reason,
        final_score: *score_history.last().unwrap_or(&0.0),
        total_iterations: iteration_history.len(),
        iteration_history,
        total_duration_seconds: total_duration,
        evidence_summary: evidence.to_dict(),
    })
}
```

### 2.3 Helper Functions

```rust
/// Build prompt for an iteration with context
fn build_iteration_prompt(
    task: &str,
    iteration: usize,
    history: &[IterationResult],
) -> String {
    let mut prompt = task.to_string();

    if iteration > 0 && !history.is_empty() {
        let last = &history[history.len() - 1];
        prompt.push_str("\n\n---\n");
        prompt.push_str(&format!(
            "This is iteration {}. Previous iteration scored {:.1}/100.\n",
            iteration + 1,
            last.score
        ));

        if !last.improvements.is_empty() {
            prompt.push_str("\nPrioritize these improvements:\n");
            for (i, improvement) in last.improvements.iter().take(3).enumerate() {
                prompt.push_str(&format!("{}. {}\n", i + 1, improvement));
            }
        }

        // Add evidence context
        if let Some(tests_run) = last.evidence.get("tests_run") {
            if tests_run.as_bool().unwrap_or(false) {
                let passed = last.evidence.get("tests_passed")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0);
                let failed = last.evidence.get("tests_failed")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0);
                prompt.push_str(&format!("\nTest status: {} passed, {} failed\n", passed, failed));
            }
        }
    }

    prompt
}

/// Detect oscillating scores (up/down/up pattern)
fn is_oscillating(scores: &[f64], threshold: f64) -> bool {
    if scores.len() < 3 {
        return false;
    }

    let deltas: Vec<f64> = scores.windows(2)
        .map(|w| w[1] - w[0])
        .collect();

    let mut alternating = 0;
    for window in deltas.windows(2) {
        if (window[0] > threshold && window[1] < -threshold) ||
           (window[0] < -threshold && window[1] > threshold) {
            alternating += 1;
        }
    }

    alternating >= 1
}

/// Detect stagnating scores (no meaningful improvement)
fn is_stagnating(scores: &[f64], variance_threshold: f64, min_improvement: f64) -> bool {
    if scores.len() < 2 {
        return false;
    }

    // Check if improvement is below threshold
    let delta = scores[scores.len() - 1] - scores[scores.len() - 2];
    if delta < min_improvement {
        return true;
    }

    // Check variance
    let max = scores.iter().fold(f64::NEG_INFINITY, |a, &b| a.max(b));
    let min = scores.iter().fold(f64::INFINITY, |a, &b| a.min(b));
    let variance = max - min;

    variance < variance_threshold
}

/// Execute Claude API with SDK hooks
async fn execute_with_api(
    prompt: &str,
    config: &LoopConfig,
    hooks: &HashMap<String, Vec<HookDefinition>>,
    timeout_seconds: f64,
) -> Result<Vec<Message>> {
    // This will integrate with the API client module
    // For now, placeholder signature
    let client = AnthropicClient::new()?;

    let request = CreateMessageRequest {
        model: config.model.clone(),
        max_tokens: 4096,
        messages: vec![Message {
            role: Role::User,
            content: vec![ContentBlock::Text { text: prompt.to_string() }],
        }],
        // Hooks would be passed here (SDK integration)
        ..Default::default()
    };

    // Execute with timeout
    let timeout = Duration::from_secs_f64(timeout_seconds);
    let response = tokio::time::timeout(
        timeout,
        client.create_message(request)
    ).await??;

    Ok(vec![response.into()]) // Convert response to messages
}
```

### 2.4 Module Dependencies

```rust
// Imports needed
use crate::{
    evidence::EvidenceCollector,
    quality::{assess_quality, QualityConfig, QualityAssessment},
    hooks::{create_sdk_hooks, merge_hooks, HookDefinition},
    events::EventsTracker,
    api::{AnthropicClient, CreateMessageRequest, Message, ContentBlock, Role},
};
use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::time::{Duration, Instant};
use tokio::time::timeout;
use tracing;
```

---

## 3. Integration Points & Data Flow

### 3.1 Evidence Collection Flow

```
┌──────────────┐
│ LoopRunner   │
│  iteration   │
└──────┬───────┘
       │
       │ 1. Reset evidence
       ▼
┌──────────────────┐
│ EvidenceCollector│◄───── Hooks write to this
└──────┬───────────┘
       │
       │ 2. Pass to assess_quality()
       ▼
┌──────────────────┐
│ QualityAssessment│
└──────────────────┘
```

### 3.2 Hooks Integration

```
┌──────────────┐
│ LoopRunner   │
└──────┬───────┘
       │
       │ Create hooks
       ▼
┌──────────────────────────────────────┐
│ create_sdk_hooks(evidence)           │
│  ├─ Safety hooks (PreToolUse)        │
│  │   ├─ block_dangerous_commands     │
│  │   └─ validate_file_paths          │
│  └─ Evidence hooks (PostToolUse)     │
│      ├─ collect_file_changes         │
│      ├─ collect_command_results      │
│      └─ track_all_tools              │
└────────────────┬─────────────────────┘
                 │
                 │ Merge with events hooks
                 ▼
┌──────────────────────────────────────┐
│ create_events_hooks(evidence, tracker)│
│  └─ PostToolUse: record_tool_use     │
└────────────────┬─────────────────────┘
                 │
                 │ Pass to API client
                 ▼
┌──────────────────────────────────────┐
│ execute_with_api(prompt, hooks)      │
└──────────────────────────────────────┘
```

### 3.3 Events Tracking Flow

```
Iteration Start
     │
     ├─> tracker.record_iteration_start()
     │
SDK Execution (hooks fire)
     │
     ├─> tracker.record_tool_use() (from hooks)
     ├─> tracker.record_file_change()
     └─> tracker.record_test_result()
     │
Iteration Complete
     │
     ├─> tracker.record_iteration_complete()
     │
Loop Terminates
     │
     └─> tracker.record_state_change()
```

---

## 4. Implementation Roadmap

### Phase 1: Core Types & Structure (Day 1)
**Prerequisites:** None
**Work:**
1. Create `loop_runner.rs` module
2. Define core types:
   - `LoopConfig` with Default impl
   - `IterationResult` with Serialize/Deserialize
   - `TerminationReason` enum with as_str()
   - `LoopResult` with passed() method
3. Add module to `lib.rs`
4. Write basic unit tests for types

**Deliverable:** Compiling types with tests

### Phase 2: Helper Functions (Day 1-2)
**Prerequisites:** Phase 1 complete
**Work:**
1. Implement `build_iteration_prompt()`
2. Implement `is_oscillating()`
3. Implement `is_stagnating()`
4. Write unit tests for each helper

**Deliverable:** Tested helper functions

### Phase 3: API Integration Stub (Day 2)
**Prerequisites:** API client module complete
**Work:**
1. Implement `execute_with_api()` skeleton
2. Wire up `AnthropicClient::create_message()`
3. Handle timeout wrapping
4. Error handling and Result propagation

**Deliverable:** API integration layer

### Phase 4: Main Loop Implementation (Day 2-3)
**Prerequisites:** Phases 1-3, all modules complete
**Work:**
1. Implement `run_agentic_loop()` main function
2. Evidence collector initialization
3. Hooks creation and merging
4. Iteration loop logic
5. Termination condition checking
6. Result building

**Deliverable:** Complete loop runner

### Phase 5: Events Integration (Day 3)
**Prerequisites:** Phase 4, Events module complete
**Work:**
1. Wire up `EventsTracker` initialization
2. Add iteration start/complete recording
3. Add state change recording
4. Test Zed panel integration

**Deliverable:** Events tracking working

### Phase 6: Testing & Validation (Day 4)
**Prerequisites:** Phase 5 complete
**Work:**
1. Integration tests with all modules
2. Test termination conditions (oscillation, stagnation)
3. Test timeout handling
4. Test callback invocation
5. Benchmark performance vs Python

**Deliverable:** Fully tested loop runner

### Phase 7: Skills Integration (Future)
**Prerequisites:** Phase 6, Skills retrieval API
**Work:**
1. Add skill retrieval to prompt building
2. Inject relevant learned skills into context
3. Test skill application tracking

**Deliverable:** Skills-aware loop

---

## 5. Testing Strategy

### 5.1 Unit Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_loop_config_defaults() {
        let config = LoopConfig::default();
        assert_eq!(config.max_iterations, 3);
        assert_eq!(config.hard_max_iterations, 5);
        assert_eq!(config.quality_threshold, 70.0);
    }

    #[test]
    fn test_termination_reason_strings() {
        assert_eq!(
            TerminationReason::QualityMet.as_str(),
            "quality_threshold_met"
        );
    }

    #[test]
    fn test_build_iteration_prompt_first_iteration() {
        let prompt = build_iteration_prompt("Fix bug", 0, &[]);
        assert_eq!(prompt, "Fix bug");
    }

    #[test]
    fn test_build_iteration_prompt_with_history() {
        let history = vec![
            IterationResult {
                iteration: 0,
                score: 60.0,
                improvements: vec!["Add tests".to_string()],
                evidence: HashMap::new(),
                duration_seconds: 30.0,
                messages_count: 5,
            }
        ];

        let prompt = build_iteration_prompt("Fix bug", 1, &history);
        assert!(prompt.contains("iteration 2"));
        assert!(prompt.contains("60.0/100"));
        assert!(prompt.contains("Add tests"));
    }

    #[test]
    fn test_is_oscillating() {
        let scores = vec![50.0, 70.0, 55.0, 75.0]; // up, down, up
        assert!(is_oscillating(&scores, 5.0));
    }

    #[test]
    fn test_is_not_oscillating() {
        let scores = vec![50.0, 60.0, 70.0]; // steady increase
        assert!(!is_oscillating(&scores, 5.0));
    }

    #[test]
    fn test_is_stagnating() {
        let scores = vec![50.0, 51.0]; // improvement < 5.0
        assert!(is_stagnating(&scores, 2.0, 5.0));
    }

    #[test]
    fn test_loop_result_passed() {
        let result = LoopResult {
            status: "success".to_string(),
            reason: TerminationReason::QualityMet,
            final_score: 85.0,
            total_iterations: 2,
            iteration_history: vec![],
            total_duration_seconds: 60.0,
            evidence_summary: HashMap::new(),
        };
        assert!(result.passed());
    }
}
```

### 5.2 Integration Tests

```rust
// tests/test_loop_runner.rs

#[tokio::test]
async fn test_run_agentic_loop_success() {
    // Test that loop terminates on quality threshold
    let config = LoopConfig {
        max_iterations: 5,
        quality_threshold: 70.0,
        ..Default::default()
    };

    let result = run_agentic_loop(
        "Simple task",
        Some(config),
        None,
        None,
        None,
        false,
    ).await.unwrap();

    assert_eq!(result.status, "success");
    assert_eq!(result.reason, TerminationReason::QualityMet);
    assert!(result.final_score >= 70.0);
}

#[tokio::test]
async fn test_run_agentic_loop_max_iterations() {
    // Test that loop terminates at max iterations
    let config = LoopConfig {
        max_iterations: 2,
        quality_threshold: 100.0, // Unreachable
        ..Default::default()
    };

    let result = run_agentic_loop(
        "Complex task",
        Some(config),
        None,
        None,
        None,
        false,
    ).await.unwrap();

    assert_eq!(result.status, "terminated");
    assert_eq!(result.reason, TerminationReason::MaxIterations);
    assert_eq!(result.total_iterations, 2);
}

#[tokio::test]
async fn test_on_iteration_callback() {
    use std::sync::{Arc, Mutex};

    let iterations_seen = Arc::new(Mutex::new(Vec::new()));
    let iterations_clone = iterations_seen.clone();

    let callback = Box::new(move |result: &IterationResult| {
        iterations_clone.lock().unwrap().push(result.iteration);
    });

    let config = LoopConfig {
        max_iterations: 3,
        ..Default::default()
    };

    let _result = run_agentic_loop(
        "Test task",
        Some(config),
        None,
        Some(callback),
        None,
        false,
    ).await.unwrap();

    let seen = iterations_seen.lock().unwrap();
    assert!(!seen.is_empty());
    assert_eq!(seen[0], 0);
}
```

---

## 6. Gaps & Missing Pieces

### 6.1 Known Gaps

1. **SDK Hooks in Rust**
   - Python uses Official Anthropic Agent SDK with hooks
   - Rust implementation will need to:
     - Either wrap Python SDK via PyO3
     - Or implement hooks natively with Anthropic API
   - **Decision needed:** PyO3 wrapper vs native implementation

2. **Async Hook Callbacks**
   - Python SDK hooks are async functions
   - Rust hooks module needs to support `async fn` callbacks
   - **Requirement:** `hooks.rs` must export async-compatible types

3. **Skills Integration**
   - Not yet wired into prompt building
   - **Future work:** Add `retrieve_skills_for_task()` call before prompt building
   - Inject top 3 relevant skills into iteration prompt

4. **PAL Review Integration**
   - `config.pal_review_enabled` not yet implemented
   - **Future work:** Call PAL consensus after each iteration
   - Use for quality validation and improvement suggestions

5. **Subagent Tracking**
   - Evidence collector tracks `subagents_spawned`
   - Events tracker has `record_subagent_spawn/complete`
   - **Gap:** No integration point in loop runner yet
   - **Future work:** Hook into SDK's subagent lifecycle

### 6.2 Compatibility Concerns

| Concern | Python | Rust | Mitigation |
|---------|--------|------|------------|
| Hook signature | `async def(input, tool_use_id, context)` | `async fn(&HookInput) -> Result<HookOutput>` | Define equivalent types in `hooks.rs` |
| Callback ownership | Python GC | Rust lifetimes | Use `Box<dyn Fn + Send + Sync>` |
| Evidence mutability | Injected reference | `&mut EvidenceCollector` | Wrap in `Arc<Mutex<>>` if needed |
| Timeout handling | asyncio.timeout | tokio::time::timeout | Direct equivalent ✓ |

### 6.3 Performance Considerations

| Metric | Target | Notes |
|--------|--------|-------|
| Iteration latency | < Python + 10% | Mostly API wait time |
| Memory usage | < Python / 2 | Rust should be more efficient |
| Hook overhead | < 5ms per hook | Measure with `tracing` |
| Evidence serialization | < 10ms | Use `serde_json` |

---

## 7. Success Criteria

### 7.1 Functional Requirements

- [ ] Loop executes up to `max_iterations`
- [ ] Loop terminates on quality threshold met
- [ ] Oscillation detection works correctly
- [ ] Stagnation detection works correctly
- [ ] Timeout handling works correctly
- [ ] Callbacks are invoked after each iteration
- [ ] Evidence is collected and assessed
- [ ] Events are written to `.superclaude_metrics/events.jsonl`
- [ ] Prompt builds with iteration context
- [ ] LoopResult contains complete history

### 7.2 Quality Requirements

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] No memory leaks (valgrind/ASAN clean)
- [ ] No panics under normal operation
- [ ] Error handling covers all failure modes
- [ ] Logging at appropriate levels (trace/debug/info/warn/error)
- [ ] Documentation complete (rustdoc)

### 7.3 Performance Requirements

- [ ] Iteration latency within 10% of Python
- [ ] Memory usage < 50% of Python
- [ ] Hook overhead < 5ms per invocation
- [ ] Evidence serialization < 10ms

---

## 8. Dependencies & Blockers

### 8.1 Hard Dependencies (MUST be complete)

1. ✅ **Evidence module** - Complete
2. ✅ **Quality module** - Complete
3. ✅ **Safety module** - Complete
4. ✅ **Hooks module** - Complete (may need async updates)
5. ✅ **Events module** - Complete
6. ✅ **API client** - Complete
7. 🔄 **Registry/Selector** - In progress (not blocking for basic loop)

### 8.2 Soft Dependencies (Nice to have)

1. **Skills retrieval** - Can be added later
2. **PAL integration** - Can be added later
3. **Obsidian artifacts** - Already works via hooks

### 8.3 External Dependencies

```toml
# Additional dependencies needed for loop_runner.rs
[dependencies]
tokio = { workspace = true, features = ["time", "macros"] }
tracing = { workspace = true }
serde = { workspace = true }
serde_json = { workspace = true }
anyhow = { workspace = true }
```

---

## 9. Next Steps

### For Team Lead

1. **Review this plan** - Confirm architecture aligns with vision
2. **Prioritize gaps** - Decide on SDK hooks strategy (PyO3 vs native)
3. **Assign implementation** - Can be split across multiple agents:
   - Agent A: Core types + helpers (Phase 1-2)
   - Agent B: API integration + main loop (Phase 3-4)
   - Agent C: Events integration + testing (Phase 5-6)

### For Implementation Team

1. **Start with Phase 1** - Get types compiling
2. **Write tests early** - TDD approach for helpers
3. **Stub external calls** - Mock API client for initial testing
4. **Integrate incrementally** - Wire up one module at a time
5. **Benchmark continuously** - Compare with Python at each phase

### For skills-porter (Me)

- Standing by for assignment to any phase
- Can start Phase 1 immediately if approved
- Happy to pair on integration challenges

---

## 10. Questions for Team Lead

1. **SDK Hooks Strategy:** PyO3 wrapper or native Rust implementation?
2. **Skills Integration Timeline:** Should we block on skills retrieval or add later?
3. **PAL Integration Priority:** Include in initial implementation or defer?
4. **Testing Approach:** Mock API calls or use real API with test account?
5. **Parallelization:** Should we support running multiple iterations in parallel (future optimization)?

---

**End of Architecture Document**

Ready for review and approval! 🚀
