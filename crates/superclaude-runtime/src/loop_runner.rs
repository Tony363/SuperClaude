/*!
Agentic Loop Runner - Main orchestration loop for SuperClaude

This module implements SuperClaude's iterative quality improvement loop:
1. Execute task via Anthropic API with hooks
2. Collect evidence from hooks
3. Assess quality from evidence
4. Check termination conditions
5. Prepare improved context for next iteration
6. Repeat until quality threshold or max iterations

Usage:
```rust
use superclaude_runtime::loop_runner::{run_agentic_loop, LoopConfig};

let config = LoopConfig {
    max_iterations: 3,
    quality_threshold: 70.0,
    ..Default::default()
};

let result = run_agentic_loop(
    "Implement user authentication",
    Some(config),
    None,
    None,
    None,
    true,
).await?;

println!("Final score: {}", result.final_score);
```
*/

use crate::api::{AnthropicClient, ContentBlock, CreateMessageRequest, Message, Role};
use crate::events::{EventsTracker, QualityDimensions};
use crate::evidence::EvidenceCollector;
use crate::hooks::{create_sdk_hooks, merge_hooks, HookConfig};
use crate::quality::{assess_quality, QualityConfig};
use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

// ============================================================================
// Core Types
// ============================================================================

/// Configuration for the agentic loop
#[derive(Debug, Clone)]
pub struct LoopConfig {
    /// Maximum iterations to run (capped by hard_max_iterations)
    pub max_iterations: usize,
    /// Hard safety cap that cannot be overridden
    pub hard_max_iterations: usize,

    /// Quality threshold to achieve (0-100)
    pub quality_threshold: f64,
    /// Minimum score improvement to continue (prevents stagnation)
    pub min_improvement: f64,

    /// Window size for oscillation detection
    pub oscillation_window: usize,
    /// Threshold for stagnation detection
    pub stagnation_threshold: f64,

    /// Overall timeout for the entire loop (None = no timeout)
    pub timeout_seconds: Option<f64>,
    /// Timeout for each iteration
    pub iteration_timeout_seconds: f64,

    /// Model to use (sonnet, opus, haiku)
    pub model: String,
    /// Maximum turns per iteration
    pub max_turns: usize,

    /// Enable PAL review (future feature)
    pub pal_review_enabled: bool,
    /// PAL model for review
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
    pub status: String,
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

// ============================================================================
// Main Loop Runner
// ============================================================================

/// Run SuperClaude's agentic loop
///
/// This is the main entry point that orchestrates:
/// 1. Evidence collection via hooks
/// 2. Quality assessment from evidence
/// 3. Termination condition checking
/// 4. Context preparation for next iteration
///
/// # Arguments
///
/// * `task` - Task description for Claude to execute
/// * `config` - Loop configuration (uses defaults if None)
/// * `additional_hooks` - Extra hooks to merge with default hooks
/// * `on_iteration` - Callback after each iteration completes
/// * `events_tracker` - Optional EventsTracker for Zed panel integration
/// * `enable_events` - Whether to enable events.jsonl writing
///
/// # Returns
///
/// LoopResult with final score and iteration history
///
/// # Example
///
/// ```no_run
/// use superclaude_runtime::loop_runner::{run_agentic_loop, LoopConfig};
///
/// # async fn example() -> anyhow::Result<()> {
/// let result = run_agentic_loop(
///     "Fix the authentication bug in auth.py",
///     Some(LoopConfig {
///         max_iterations: 3,
///         quality_threshold: 70.0,
///         ..Default::default()
///     }),
///     None,
///     None,
///     None,
///     true,
/// ).await?;
///
/// println!("Status: {}, Score: {}", result.status, result.final_score);
/// # Ok(())
/// # }
/// ```
pub async fn run_agentic_loop(
    task: &str,
    config: Option<LoopConfig>,
    additional_hooks: Option<HookConfig>,
    on_iteration: Option<Box<dyn Fn(&IterationResult) + Send + Sync>>,
    events_tracker: Option<EventsTracker>,
    enable_events: bool,
) -> Result<LoopResult> {
    let config = config.unwrap_or_default();
    let effective_max = config.max_iterations.min(config.hard_max_iterations);

    tracing::info!(
        "Starting agentic loop: max_iterations={}, quality_threshold={}",
        effective_max,
        config.quality_threshold
    );

    // Initialize evidence collector (wrapped in Arc<Mutex<>> for hook access)
    let evidence = Arc::new(Mutex::new(EvidenceCollector::new()));

    // Initialize events tracker for Zed panel (optional)
    let mut tracker = if enable_events {
        Some(events_tracker.unwrap_or_else(|| {
            EventsTracker::new(None, None).expect("Failed to create tracker")
        }))
    } else {
        None
    };

    // Create SDK hooks (safety + evidence collection)
    let evidence_clone = Arc::clone(&evidence);
    let mut sdk_hooks = create_sdk_hooks(evidence_clone);

    // Merge additional hooks if provided
    if let Some(extra) = additional_hooks {
        sdk_hooks = merge_hooks(vec![sdk_hooks, extra]);
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
        if let Some(ref mut t) = tracker {
            t.record_iteration_start(iteration as i32, 0)?;
        }

        // Reset evidence for this iteration
        {
            let mut ev = evidence.lock().unwrap();
            ev.reset();
        }

        // Build prompt with context from previous iterations
        let prompt = build_iteration_prompt(task, iteration, &iteration_history);

        // Execute via Anthropic API with hooks
        let messages = match execute_with_api(
            &prompt,
            &config,
            &sdk_hooks,
            config.iteration_timeout_seconds,
        )
        .await
        {
            Ok(msgs) => msgs,
            Err(e) => {
                tracing::error!("API query failed: {}", e);
                termination_reason = TerminationReason::Error;
                break;
            }
        };

        // Assess quality using evidence collected by hooks
        let assessment = {
            let ev = evidence.lock().unwrap();
            assess_quality(&*ev, Some(&quality_config))
        };
        score_history.push(assessment.score);

        // Record iteration result
        let iteration_duration = iteration_start.elapsed().as_secs_f64();
        let evidence_dict = {
            let ev = evidence.lock().unwrap();
            let dict_value = ev.to_dict();
            // Convert Value to HashMap if it's an object
            if let serde_json::Value::Object(map) = dict_value {
                map.into_iter().collect()
            } else {
                HashMap::new()
            }
        };

        let iteration_result = IterationResult {
            iteration,
            score: assessment.score,
            improvements: assessment.improvements_needed.clone(),
            evidence: evidence_dict,
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

        // Record iteration complete for Zed panel
        if let Some(ref t) = tracker {
            let dimensions = dimensions_to_struct(&assessment.dimension_scores);
            t.record_iteration_complete(
                iteration as i32,
                assessment.score as f32,
                Some(assessment.improvements_needed.clone()),
                Some(dimensions),
                iteration_duration as f32,
            )?;
        }

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
    if let Some(ref mut t) = tracker {
        let final_state = if status == "success" {
            "completed"
        } else {
            "failed"
        };
        t.record_state_change("running", final_state, termination_reason.as_str())?;
        t.flush()?;
    }

    let evidence_summary = {
        let ev = evidence.lock().unwrap();
        let dict_value = ev.to_dict();
        // Convert Value to HashMap if it's an object
        if let serde_json::Value::Object(map) = dict_value {
            map.into_iter().collect()
        } else {
            HashMap::new()
        }
    };

    tracing::info!(
        "Loop complete: status={}, reason={}, final_score={:.1}, iterations={}",
        status,
        termination_reason.as_str(),
        score_history.last().unwrap_or(&0.0),
        iteration_history.len()
    );

    Ok(LoopResult {
        status: status.to_string(),
        reason: termination_reason,
        final_score: *score_history.last().unwrap_or(&0.0),
        total_iterations: iteration_history.len(),
        iteration_history,
        total_duration_seconds: total_duration,
        evidence_summary,
    })
}

// ============================================================================
// Helper Functions
// ============================================================================

/// Build prompt for an iteration with context from previous iterations
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
                let passed = last
                    .evidence
                    .get("tests_passed")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0);
                let failed = last
                    .evidence
                    .get("tests_failed")
                    .and_then(|v| v.as_u64())
                    .unwrap_or(0);
                prompt.push_str(&format!(
                    "\nTest status: {} passed, {} failed\n",
                    passed, failed
                ));
            }
        }
    }

    prompt
}

/// Convert HashMap dimension scores to QualityDimensions struct
fn dimensions_to_struct(scores: &HashMap<String, f64>) -> QualityDimensions {
    QualityDimensions {
        code_changes: scores.get("code_changes").map(|&v| v as f32),
        tests_run: scores.get("tests_run").or_else(|| scores.get("test_execution")).map(|&v| v as f32),
        tests_pass: scores.get("tests_pass").or_else(|| scores.get("test_results")).map(|&v| v as f32),
        coverage: scores.get("coverage").or_else(|| scores.get("code_coverage")).map(|&v| v as f32),
        no_errors: scores.get("no_errors").map(|&v| v as f32),
    }
}

/// Detect oscillating scores (up/down/up pattern)
fn is_oscillating(scores: &[f64], threshold: f64) -> bool {
    if scores.len() < 3 {
        return false;
    }

    let deltas: Vec<f64> = scores.windows(2).map(|w| w[1] - w[0]).collect();

    let mut alternating = 0;
    for window in deltas.windows(2) {
        if (window[0] > threshold && window[1] < -threshold)
            || (window[0] < -threshold && window[1] > threshold)
        {
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
    let max = scores
        .iter()
        .fold(f64::NEG_INFINITY, |a, &b| a.max(b));
    let min = scores.iter().fold(f64::INFINITY, |a, &b| a.min(b));
    let variance = max - min;

    variance < variance_threshold
}

/// Execute Claude API with hooks
async fn execute_with_api(
    prompt: &str,
    config: &LoopConfig,
    _hooks: &HookConfig,
    timeout_seconds: f64,
) -> Result<Vec<Message>> {
    // Initialize API client
    let api_key = std::env::var("ANTHROPIC_API_KEY")
        .context("ANTHROPIC_API_KEY not set")?;
    let client = AnthropicClient::new(
        api_key,
        "https://api.anthropic.com".to_string(),
        "2023-06-01".to_string(),
    )
    .context("Failed to create API client")?;

    // Build request
    let request = CreateMessageRequest {
        model: config.model.clone(),
        max_tokens: 4096,
        messages: vec![Message {
            role: Role::User,
            content: vec![ContentBlock::Text {
                text: prompt.to_string(),
            }],
        }],
        system: None,
        metadata: None,
        stop_sequences: None,
        stream: Some(false),
        temperature: None,
        top_k: None,
        top_p: None,
        tools: None, // No tools for now
    };

    // Execute with timeout
    let timeout = Duration::from_secs_f64(timeout_seconds);
    let response = tokio::time::timeout(timeout, client.create_message(request))
        .await
        .context("API call timed out")??;

    // Convert response to messages
    let message = Message {
        role: Role::Assistant,
        content: response.content,
    };

    Ok(vec![message])
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_loop_config_defaults() {
        let config = LoopConfig::default();
        assert_eq!(config.max_iterations, 3);
        assert_eq!(config.hard_max_iterations, 5);
        assert_eq!(config.quality_threshold, 70.0);
        assert_eq!(config.min_improvement, 5.0);
    }

    #[test]
    fn test_termination_reason_strings() {
        assert_eq!(
            TerminationReason::QualityMet.as_str(),
            "quality_threshold_met"
        );
        assert_eq!(
            TerminationReason::MaxIterations.as_str(),
            "max_iterations_reached"
        );
        assert_eq!(
            TerminationReason::Oscillation.as_str(),
            "oscillation_detected"
        );
        assert_eq!(
            TerminationReason::Stagnation.as_str(),
            "stagnation_detected"
        );
    }

    #[test]
    fn test_build_iteration_prompt_first_iteration() {
        let prompt = build_iteration_prompt("Fix bug", 0, &[]);
        assert_eq!(prompt, "Fix bug");
    }

    #[test]
    fn test_build_iteration_prompt_with_history() {
        let history = vec![IterationResult {
            iteration: 0,
            score: 60.0,
            improvements: vec!["Add tests".to_string()],
            evidence: HashMap::new(),
            duration_seconds: 30.0,
            messages_count: 5,
        }];

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
    fn test_is_not_stagnating() {
        let scores = vec![50.0, 60.0]; // improvement >= 5.0
        assert!(!is_stagnating(&scores, 2.0, 5.0));
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

    #[test]
    fn test_loop_result_not_passed() {
        let result = LoopResult {
            status: "terminated".to_string(),
            reason: TerminationReason::MaxIterations,
            final_score: 65.0,
            total_iterations: 3,
            iteration_history: vec![],
            total_duration_seconds: 90.0,
            evidence_summary: HashMap::new(),
        };
        assert!(!result.passed());
    }
}
