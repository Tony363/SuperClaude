//! SuperClaude Runtime Library
//!
//! Core modules for the SuperClaude agentic loop execution engine.

pub mod api;
pub mod events;
pub mod evidence;
pub mod safety;
pub mod hooks;
pub mod quality;
pub mod skills;

// Re-export commonly used types
pub use events::{EventsTracker, FileAction, LogLevel, QualityDimensions};
pub use evidence::{CommandResult, EvidenceCollector, FileChange, TestResult, ToolInvocation};
pub use safety::{DangerousPattern, PatternCategory, SafetyValidator, ValidationError};
pub use hooks::{
    create_evidence_hooks, create_logging_hooks, create_safety_hooks, create_sdk_hooks,
    merge_hooks, HookCallback, HookConfig, HookInput, HookMatcher, HookOutput,
};
pub use quality::{assess_quality, QualityAssessment, QualityBand, QualityConfig};
pub use skills::{LearnedSkill, learn_from_session, retrieve_skills_for_task};
