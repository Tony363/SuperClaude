//! Quality Assessment - Score output based on evidence from SDK hooks.
//!
//! Quality is assessed using deterministic signals (evidence) rather than
//! LLM self-evaluation. This ensures consistent, reproducible scoring.
//!
//! Scoring Dimensions:
//! - Code Changes: Were files actually modified?
//! - Test Execution: Were tests run?
//! - Test Results: Did tests pass?
//! - Code Coverage: Is coverage sufficient?
//! - Build Status: Does the build pass?

use crate::evidence::EvidenceCollector;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Quality score bands for categorization.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum QualityBand {
    /// 90-100
    Excellent,
    /// 70-89
    Good,
    /// 50-69
    Acceptable,
    /// 30-49
    NeedsWork,
    /// 0-29
    Poor,
}

impl QualityBand {
    /// Convert score to quality band.
    pub fn from_score(score: f64) -> Self {
        if score >= 90.0 {
            QualityBand::Excellent
        } else if score >= 70.0 {
            QualityBand::Good
        } else if score >= 50.0 {
            QualityBand::Acceptable
        } else if score >= 30.0 {
            QualityBand::NeedsWork
        } else {
            QualityBand::Poor
        }
    }

    /// Get string value for the band.
    pub fn as_str(&self) -> &'static str {
        match self {
            QualityBand::Excellent => "excellent",
            QualityBand::Good => "good",
            QualityBand::Acceptable => "acceptable",
            QualityBand::NeedsWork => "needs_work",
            QualityBand::Poor => "poor",
        }
    }
}

/// Quality assessment result.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityAssessment {
    /// Overall quality score (0-100)
    pub score: f64,
    /// Whether score meets threshold
    pub passed: bool,
    /// Quality band categorization
    pub band: QualityBand,
    /// List of suggested improvements
    pub improvements_needed: Vec<String>,
    /// Breakdown by dimension
    pub dimension_scores: HashMap<String, f64>,
}

impl QualityAssessment {
    /// Create assessment from a score.
    pub fn from_score(score: f64, threshold: f64) -> Self {
        let band = QualityBand::from_score(score);
        Self {
            score,
            passed: score >= threshold,
            band,
            improvements_needed: Vec::new(),
            dimension_scores: HashMap::new(),
        }
    }
}

/// Configuration for quality assessment.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct QualityConfig {
    // Dimension weights (must sum to 1.0)
    pub weight_code_changes: f64,
    pub weight_tests_run: f64,
    pub weight_tests_pass: f64,
    pub weight_coverage: f64,
    pub weight_no_errors: f64,

    // Thresholds
    pub min_coverage: f64,       // Minimum coverage percentage
    pub quality_threshold: f64,  // Score to pass

    // Scoring
    pub max_score: f64,
}

impl Default for QualityConfig {
    fn default() -> Self {
        Self {
            weight_code_changes: 0.30,
            weight_tests_run: 0.25,
            weight_tests_pass: 0.25,
            weight_coverage: 0.10,
            weight_no_errors: 0.10,
            min_coverage: 80.0,
            quality_threshold: 70.0,
            max_score: 100.0,
        }
    }
}

// Evidence types are now imported from evidence.rs module

/// Assess quality based on collected evidence.
///
/// Uses deterministic signals from tool outputs rather than
/// LLM self-evaluation. This ensures consistent scoring.
pub fn assess_quality(
    evidence: &EvidenceCollector,
    config: Option<&QualityConfig>,
) -> QualityAssessment {
    // Use a static default config to avoid lifetime issues
    static DEFAULT_CONFIG: once_cell::sync::Lazy<QualityConfig> =
        once_cell::sync::Lazy::new(QualityConfig::default);

    let config = config.unwrap_or(&DEFAULT_CONFIG);

    let mut score = 0.0;
    let mut improvements = Vec::new();
    let mut dimension_scores = HashMap::new();

    // Dimension 1: Code Changes (30%)
    let code_change_score = score_code_changes(evidence);
    dimension_scores.insert("code_changes".to_string(), code_change_score);
    score += code_change_score * config.weight_code_changes;

    if code_change_score < 100.0 {
        if evidence.files_written.is_empty() && evidence.files_edited.is_empty() {
            improvements.push("No code changes detected - verify implementation".to_string());
        }
    }

    // Dimension 2: Tests Run (25%)
    let tests_run_score = score_tests_run(evidence);
    dimension_scores.insert("tests_run".to_string(), tests_run_score);
    score += tests_run_score * config.weight_tests_run;

    if tests_run_score < 100.0 {
        improvements.push("Run tests to verify changes work correctly".to_string());
    }

    // Dimension 3: Tests Pass (25%)
    let tests_pass_score = score_tests_pass(evidence);
    dimension_scores.insert("tests_pass".to_string(), tests_pass_score);
    score += tests_pass_score * config.weight_tests_pass;

    if evidence.tests_run && evidence.total_tests_failed() > 0 {
        improvements.push(format!("Fix {} failing test(s)", evidence.total_tests_failed()));
    }

    // Dimension 4: Coverage (10%)
    let coverage_score = score_coverage(evidence, config.min_coverage);
    dimension_scores.insert("coverage".to_string(), coverage_score);
    score += coverage_score * config.weight_coverage;

    if coverage_score < 100.0 && evidence.tests_run {
        let avg_coverage = get_average_coverage(evidence);
        if avg_coverage > 0.0 {
            improvements.push(format!(
                "Increase test coverage from {:.1}% to {:.1}%",
                avg_coverage, config.min_coverage
            ));
        }
    }

    // Dimension 5: No Errors (10%)
    let no_errors_score = score_no_errors(evidence);
    dimension_scores.insert("no_errors".to_string(), no_errors_score);
    score += no_errors_score * config.weight_no_errors;

    if no_errors_score < 100.0 {
        improvements.push("Fix errors in test or command output".to_string());
    }

    // Apply caps for critical failures
    if evidence.tests_run && evidence.total_tests_failed() > evidence.total_tests_passed() {
        // More failing than passing = cap at 40
        score = score.min(40.0);
        improvements.insert(0, "CRITICAL: Majority of tests failing".to_string());
    }

    // Round score to 1 decimal place
    score = (score * 10.0).round() / 10.0;

    // Limit improvements to top 5
    improvements.truncate(5);

    QualityAssessment {
        score,
        passed: score >= config.quality_threshold,
        band: QualityBand::from_score(score),
        improvements_needed: improvements,
        dimension_scores,
    }
}

/// Score based on code changes made.
fn score_code_changes(evidence: &EvidenceCollector) -> f64 {
    if !evidence.files_written.is_empty() || !evidence.files_edited.is_empty() {
        // Bonus for multiple files changed
        let total = evidence.total_files_modified();
        if total >= 3 {
            100.0
        } else if total >= 1 {
            80.0
        } else {
            0.0
        }
    } else {
        0.0
    }
}

/// Score based on whether tests were run.
fn score_tests_run(evidence: &EvidenceCollector) -> f64 {
    if evidence.tests_run {
        100.0
    } else {
        0.0
    }
}

/// Score based on test pass rate.
fn score_tests_pass(evidence: &EvidenceCollector) -> f64 {
    if !evidence.tests_run {
        return 50.0; // Neutral if no tests
    }

    let total = evidence.total_tests_passed() + evidence.total_tests_failed();
    if total == 0 {
        return 50.0;
    }

    let pass_rate = evidence.total_tests_passed() as f64 / total as f64;
    pass_rate * 100.0
}

/// Score based on code coverage.
fn score_coverage(evidence: &EvidenceCollector, min_coverage: f64) -> f64 {
    if !evidence.tests_run {
        return 50.0; // Neutral if no tests
    }

    let avg_coverage = get_average_coverage(evidence);
    if avg_coverage <= 0.0 {
        return 50.0; // No coverage data
    }

    if avg_coverage >= min_coverage {
        100.0
    } else {
        // Partial credit
        (avg_coverage / min_coverage) * 100.0
    }
}

/// Get average coverage across test results.
fn get_average_coverage(evidence: &EvidenceCollector) -> f64 {
    let coverages: Vec<f64> = evidence
        .test_results
        .iter()
        .filter(|r| r.coverage > 0.0)
        .map(|r| r.coverage)
        .collect();

    if coverages.is_empty() {
        0.0
    } else {
        coverages.iter().sum::<f64>() / coverages.len() as f64
    }
}

/// Score based on absence of errors.
fn score_no_errors(evidence: &EvidenceCollector) -> f64 {
    // Check for errors in test results
    let total_errors: u32 = evidence.test_results.iter().map(|r| r.errors).sum();
    if total_errors > 0 {
        return 0.0;
    }

    // Check for error patterns in command output
    let error_patterns = ["error:", "exception:", "traceback:", "failed:"];
    for cmd in &evidence.commands_run {
        let output_lower = cmd.output.to_lowercase();
        for pattern in &error_patterns {
            if output_lower.contains(pattern) {
                return 50.0; // Partial credit
            }
        }
    }

    100.0
}

/// Comparison metrics between two assessments.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AssessmentComparison {
    pub score_delta: f64,
    pub improved: bool,
    pub regressed: bool,
    pub stagnant: bool,
    pub current_band: String,
    pub previous_band: String,
    pub band_changed: bool,
}

/// Compare two assessments to track progress.
pub fn compare_assessments(
    current: &QualityAssessment,
    previous: &QualityAssessment,
) -> AssessmentComparison {
    let delta = current.score - previous.score;

    AssessmentComparison {
        score_delta: (delta * 10.0).round() / 10.0,
        improved: delta > 0.0,
        regressed: delta < 0.0,
        stagnant: delta.abs() < 2.0,
        current_band: current.band.as_str().to_string(),
        previous_band: previous.band.as_str().to_string(),
        band_changed: current.band != previous.band,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::evidence::{TestResult, CommandResult};

    #[test]
    fn test_quality_band_from_score() {
        assert_eq!(QualityBand::from_score(95.0), QualityBand::Excellent);
        assert_eq!(QualityBand::from_score(75.0), QualityBand::Good);
        assert_eq!(QualityBand::from_score(60.0), QualityBand::Acceptable);
        assert_eq!(QualityBand::from_score(40.0), QualityBand::NeedsWork);
        assert_eq!(QualityBand::from_score(20.0), QualityBand::Poor);
    }

    #[test]
    fn test_quality_band_as_str() {
        assert_eq!(QualityBand::Excellent.as_str(), "excellent");
        assert_eq!(QualityBand::Good.as_str(), "good");
        assert_eq!(QualityBand::Acceptable.as_str(), "acceptable");
        assert_eq!(QualityBand::NeedsWork.as_str(), "needs_work");
        assert_eq!(QualityBand::Poor.as_str(), "poor");
    }

    #[test]
    fn test_quality_assessment_from_score() {
        let assessment = QualityAssessment::from_score(95.0, 70.0);
        assert_eq!(assessment.score, 95.0);
        assert!(assessment.passed);
        assert_eq!(assessment.band, QualityBand::Excellent);
    }

    #[test]
    fn test_quality_assessment_from_score_below_threshold() {
        let assessment = QualityAssessment::from_score(60.0, 70.0);
        assert_eq!(assessment.score, 60.0);
        assert!(!assessment.passed);
        assert_eq!(assessment.band, QualityBand::Acceptable);
    }

    #[test]
    fn test_default_config_weights_sum_to_one() {
        let config = QualityConfig::default();
        let total = config.weight_code_changes
            + config.weight_tests_run
            + config.weight_tests_pass
            + config.weight_coverage
            + config.weight_no_errors;
        assert!((total - 1.0).abs() < 0.001);
    }

    #[test]
    fn test_empty_evidence_low_score() {
        let evidence = EvidenceCollector::default();
        let assessment = assess_quality(&evidence, None);

        assert!(assessment.score < 50.0);
        assert!(!assessment.passed);
        assert!(assessment
            .improvements_needed
            .iter()
            .any(|s| s.contains("No code changes")));
    }

    #[test]
    fn test_files_only_partial_score() {
        let mut evidence = EvidenceCollector::default();
        evidence.files_written.push("test.py".to_string());

        let assessment = assess_quality(&evidence, None);

        assert!(assessment.score > 0.0);
        assert!(assessment
            .improvements_needed
            .iter()
            .any(|s| s.contains("Run tests")));
    }

    #[test]
    fn test_passing_tests_high_score() {
        let mut evidence = EvidenceCollector::default();
        evidence.files_written.push("feature.py".to_string());
        evidence.tests_run = true;
        evidence.test_results.push(TestResult {
            framework: "pytest".to_string(),
            passed: 10,
            failed: 0,
            skipped: 0,
            errors: 0,
            coverage: 0.0,
            duration_seconds: 2.5,
        });
        evidence.commands_run.push(
            CommandResult::new(
                "pytest tests/".to_string(),
                "===== 10 passed in 2.5s =====".to_string(),
            )
            .with_exit_code(0)
            .with_duration(2500),
        );

        let assessment = assess_quality(&evidence, None);

        assert!(assessment.score >= 70.0);
        assert!(assessment.passed);
    }

    #[test]
    fn test_failing_tests_medium_score() {
        let mut evidence = EvidenceCollector::default();
        evidence.files_written.push("buggy.py".to_string());
        evidence.tests_run = true;
        evidence.test_results.push(TestResult {
            framework: "pytest".to_string(),
            passed: 5,
            failed: 3,
            skipped: 0,
            errors: 0,
            coverage: 0.0,
            duration_seconds: 1.5,
        });

        let assessment = assess_quality(&evidence, None);

        assert!(assessment.score < 90.0);
        assert!(assessment
            .improvements_needed
            .iter()
            .any(|s| s.to_lowercase().contains("failing test")));
    }

    #[test]
    fn test_majority_failing_capped() {
        let mut evidence = EvidenceCollector::default();
        evidence.files_written.push("test.py".to_string());
        evidence.tests_run = true;
        evidence.test_results.push(TestResult {
            framework: "pytest".to_string(),
            passed: 2,
            failed: 10,
            skipped: 0,
            errors: 0,
            coverage: 0.0,
            duration_seconds: 1.0,
        });

        let assessment = assess_quality(&evidence, None);

        assert!(assessment.score <= 40.0);
        assert!(assessment.improvements_needed[0].contains("CRITICAL"));
    }

    #[test]
    fn test_dimension_scores_populated() {
        let mut evidence = EvidenceCollector::default();
        evidence.files_written.push("feature.py".to_string());
        evidence.tests_run = true;
        evidence.test_results.push(TestResult {
            framework: "pytest".to_string(),
            passed: 10,
            failed: 0,
            skipped: 0,
            errors: 0,
            coverage: 0.0,
            duration_seconds: 2.5,
        });

        let assessment = assess_quality(&evidence, None);

        assert!(assessment.dimension_scores.contains_key("code_changes"));
        assert!(assessment.dimension_scores.contains_key("tests_run"));
        assert!(assessment.dimension_scores.contains_key("tests_pass"));
        assert!(assessment.dimension_scores.contains_key("coverage"));
        assert!(assessment.dimension_scores.contains_key("no_errors"));
    }

    #[test]
    fn test_compare_assessments_improvement() {
        let prev = QualityAssessment::from_score(50.0, 70.0);
        let curr = QualityAssessment::from_score(70.0, 70.0);

        let comparison = compare_assessments(&curr, &prev);

        assert!(comparison.improved);
        assert!(!comparison.regressed);
        assert_eq!(comparison.score_delta, 20.0);
    }

    #[test]
    fn test_compare_assessments_regression() {
        let prev = QualityAssessment::from_score(80.0, 70.0);
        let curr = QualityAssessment::from_score(60.0, 70.0);

        let comparison = compare_assessments(&curr, &prev);

        assert!(!comparison.improved);
        assert!(comparison.regressed);
        assert_eq!(comparison.score_delta, -20.0);
    }

    #[test]
    fn test_compare_assessments_stagnant() {
        let prev = QualityAssessment::from_score(70.0, 70.0);
        let curr = QualityAssessment::from_score(71.0, 70.0);

        let comparison = compare_assessments(&curr, &prev);

        assert!(comparison.stagnant);
        assert!(comparison.score_delta.abs() < 2.0);
    }

    #[test]
    fn test_compare_assessments_band_change() {
        let prev = QualityAssessment::from_score(60.0, 70.0); // Acceptable
        let curr = QualityAssessment::from_score(75.0, 70.0); // Good

        let comparison = compare_assessments(&curr, &prev);

        assert!(comparison.band_changed);
        assert_eq!(comparison.previous_band, "acceptable");
        assert_eq!(comparison.current_band, "good");
    }

    #[test]
    fn test_score_code_changes_no_changes() {
        let evidence = EvidenceCollector::default();
        assert_eq!(score_code_changes(&evidence), 0.0);
    }

    #[test]
    fn test_score_code_changes_single_file() {
        let mut evidence = EvidenceCollector::default();
        evidence.files_written.push("test.py".to_string());
        assert_eq!(score_code_changes(&evidence), 80.0);
    }

    #[test]
    fn test_score_code_changes_multiple_files() {
        let mut evidence = EvidenceCollector::default();
        evidence.files_written.push("a.py".to_string());
        evidence.files_written.push("b.py".to_string());
        evidence.files_edited.push("c.py".to_string());
        assert_eq!(score_code_changes(&evidence), 100.0);
    }

    #[test]
    fn test_score_tests_run() {
        let mut evidence = EvidenceCollector::default();
        assert_eq!(score_tests_run(&evidence), 0.0);

        evidence.tests_run = true;
        assert_eq!(score_tests_run(&evidence), 100.0);
    }

    #[test]
    fn test_score_tests_pass_no_tests() {
        let evidence = EvidenceCollector::default();
        assert_eq!(score_tests_pass(&evidence), 50.0); // Neutral
    }

    #[test]
    fn test_score_tests_pass_all_passing() {
        let mut evidence = EvidenceCollector::default();
        evidence.tests_run = true;
        evidence.test_results.push(TestResult {
            framework: "pytest".to_string(),
            passed: 10,
            failed: 0,
            skipped: 0,
            errors: 0,
            coverage: 0.0,
            duration_seconds: 2.5,
        });
        assert_eq!(score_tests_pass(&evidence), 100.0);
    }

    #[test]
    fn test_score_tests_pass_partial() {
        let mut evidence = EvidenceCollector::default();
        evidence.tests_run = true;
        evidence.test_results.push(TestResult {
            framework: "pytest".to_string(),
            passed: 5,
            failed: 5,
            skipped: 0,
            errors: 0,
            coverage: 0.0,
            duration_seconds: 1.5,
        });
        assert_eq!(score_tests_pass(&evidence), 50.0);
    }

    #[test]
    fn test_score_coverage_no_tests() {
        let evidence = EvidenceCollector::default();
        assert_eq!(score_coverage(&evidence, 80.0), 50.0); // Neutral
    }

    #[test]
    fn test_score_coverage_meets_threshold() {
        let mut evidence = EvidenceCollector::default();
        evidence.tests_run = true;
        evidence.test_results.push(TestResult {
            framework: "pytest".to_string(),
            passed: 10,
            failed: 0,
            skipped: 0,
            errors: 0,
            coverage: 85.0,
            duration_seconds: 2.5,
        });
        assert_eq!(score_coverage(&evidence, 80.0), 100.0);
    }

    #[test]
    fn test_score_coverage_partial() {
        let mut evidence = EvidenceCollector::default();
        evidence.tests_run = true;
        evidence.test_results.push(TestResult {
            framework: "pytest".to_string(),
            passed: 10,
            failed: 0,
            skipped: 0,
            errors: 0,
            coverage: 40.0,
            duration_seconds: 2.5,
        });
        assert_eq!(score_coverage(&evidence, 80.0), 50.0); // 40/80 * 100
    }

    #[test]
    fn test_score_no_errors_clean() {
        let evidence = EvidenceCollector::default();
        assert_eq!(score_no_errors(&evidence), 100.0);
    }

    #[test]
    fn test_score_no_errors_with_test_errors() {
        let mut evidence = EvidenceCollector::default();
        evidence.test_results.push(TestResult {
            framework: "pytest".to_string(),
            passed: 5,
            failed: 0,
            skipped: 0,
            errors: 2,
            coverage: 0.0,
            duration_seconds: 1.0,
        });
        assert_eq!(score_no_errors(&evidence), 0.0);
    }

    #[test]
    fn test_score_no_errors_with_error_pattern() {
        let mut evidence = EvidenceCollector::default();
        evidence.commands_run.push(
            CommandResult::new(
                "python test.py".to_string(),
                "Error: something went wrong".to_string(),
            )
            .with_exit_code(1)
            .with_duration(100),
        );
        assert_eq!(score_no_errors(&evidence), 50.0); // Partial credit
    }

    #[test]
    fn test_improvements_limited_to_five() {
        let evidence = EvidenceCollector::default();
        let assessment = assess_quality(&evidence, None);
        assert!(assessment.improvements_needed.len() <= 5);
    }
}
