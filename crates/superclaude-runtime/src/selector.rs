//! Agent Selector for SuperClaude Framework.
//!
//! Updated to work with the v7 tiered architecture.
//! Provides intelligent agent selection based on context, keywords, and task requirements.

use crate::registry::{AgentConfig, AgentRegistry};
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

/// Result of agent selection with detailed breakdown
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SelectionResult {
    /// Name of the selected agent
    pub agent_name: String,

    /// Confidence score (0.0 to 1.0)
    pub confidence: f64,

    /// Human-readable confidence level
    pub confidence_level: String,

    /// Score breakdown by component
    pub breakdown: HashMap<String, f64>,

    /// List of matched criteria
    pub matched_criteria: Vec<String>,

    /// Alternative agents with scores and details
    pub alternatives: Vec<AlternativeAgent>,

    /// Traits applied to the selection
    pub traits_applied: Vec<String>,

    /// Path to the agent file
    pub agent_path: String,

    /// Paths to trait files
    pub trait_paths: Vec<String>,

    /// Invalid traits that were requested but not found
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub invalid_traits: Vec<String>,

    /// Trait conflicts detected (pairs of conflicting trait names)
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub trait_conflicts: Vec<(String, String)>,

    /// Trait tensions detected (non-blocking but notable)
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub trait_tensions: Vec<(String, String)>,
}

/// Details about an alternative agent candidate
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AlternativeAgent {
    pub agent_name: String,
    pub score: f64,
    pub confidence_level: String,
    pub agent_path: String,
}

// Trait conflict detection
lazy_static::lazy_static! {
    static ref TRAIT_CONFLICTS: HashMap<&'static str, HashSet<&'static str>> = {
        let mut m = HashMap::new();
        m.insert("minimal-changes", ["rapid-prototype"].iter().copied().collect());
        m.insert("rapid-prototype", ["minimal-changes"].iter().copied().collect());
        m
    };

    static ref TRAIT_TENSIONS: HashMap<&'static str, HashSet<&'static str>> = {
        let mut m = HashMap::new();
        m.insert("legacy-friendly", ["cloud-native"].iter().copied().collect());
        m.insert("cloud-native", ["legacy-friendly"].iter().copied().collect());
        m
    };
}

/// Context for agent selection
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum SelectionContext {
    /// Simple string context
    Text(String),

    /// Structured context with task details (matches Python's 7-field context)
    Structured {
        task: Option<String>,
        description: Option<String>,
        files: Option<Vec<String>>,
        #[serde(default)]
        domains: Option<Vec<String>>,
        #[serde(default)]
        keywords: Option<Vec<String>>,
        #[serde(default)]
        languages: Option<Vec<String>>,
        #[serde(default)]
        imports: Option<Vec<String>>,
    },
}

impl SelectionContext {
    /// Convert context to a searchable string
    fn to_search_string(&self) -> String {
        match self {
            SelectionContext::Text(s) => s.clone(),
            SelectionContext::Structured {
                task,
                description,
                files,
                domains,
                keywords,
                ..
            } => {
                let mut parts = Vec::new();
                if let Some(t) = task {
                    parts.push(t.clone());
                }
                if let Some(d) = description {
                    parts.push(d.clone());
                }
                if let Some(f) = files {
                    parts.extend(f.clone());
                }
                if let Some(d) = domains {
                    parts.extend(d.clone());
                }
                if let Some(k) = keywords {
                    parts.extend(k.clone());
                }
                parts.join(" ")
            }
        }
    }

    /// Get file list from context
    fn files(&self) -> Vec<String> {
        match self {
            SelectionContext::Structured {
                files: Some(files), ..
            } => files.clone(),
            _ => Vec::new(),
        }
    }

    /// Get keywords from context
    fn keywords(&self) -> Vec<String> {
        match self {
            SelectionContext::Structured {
                keywords: Some(keywords),
                ..
            } => keywords.clone(),
            _ => Vec::new(),
        }
    }

    /// Get domains from context
    fn domains(&self) -> Vec<String> {
        match self {
            SelectionContext::Structured {
                domains: Some(domains),
                ..
            } => domains.clone(),
            _ => Vec::new(),
        }
    }
}

/// Map a numeric score to a human-readable confidence level (matches Python).
fn confidence_level(score: f64) -> String {
    if score >= 0.7 {
        "excellent".to_string()
    } else if score >= 0.5 {
        "high".to_string()
    } else if score >= 0.3 {
        "medium".to_string()
    } else {
        "low".to_string()
    }
}

/// Simple glob matching (fnmatch equivalent for file patterns).
/// Supports `*` (match any) and `?` (match single char).
fn glob_match(pattern: &str, text: &str) -> bool {
    let pat: Vec<char> = pattern.chars().collect();
    let txt: Vec<char> = text.chars().collect();
    glob_match_inner(&pat, &txt)
}

fn glob_match_inner(pat: &[char], txt: &[char]) -> bool {
    match (pat.first(), txt.first()) {
        (None, None) => true,
        (Some('*'), _) => {
            // * matches zero or more of any character
            glob_match_inner(&pat[1..], txt) || (!txt.is_empty() && glob_match_inner(pat, &txt[1..]))
        }
        (Some('?'), Some(_)) => glob_match_inner(&pat[1..], &txt[1..]),
        (Some(p), Some(t)) if *p == *t => glob_match_inner(&pat[1..], &txt[1..]),
        _ => false,
    }
}

/// Intelligent agent selector for context-based agent matching
pub struct AgentSelector {
    /// Agent registry
    registry: AgentRegistry,

    /// Default agent name for fallback
    default_agent: String,

    /// Minimum confidence threshold
    min_confidence: f64,

    /// High confidence threshold
    high_confidence: f64,
}

impl AgentSelector {
    /// Create a new agent selector
    pub fn new(mut registry: AgentRegistry) -> Self {
        // Ensure agents are discovered
        let _ = registry.discover_agents(false);

        Self {
            registry,
            default_agent: "general-purpose".to_string(),
            min_confidence: 0.15,
            high_confidence: 0.5,
        }
    }

    /// Select the best agent for the given context
    pub fn select_agent(
        &self,
        context: SelectionContext,
        traits: Option<Vec<String>>,
        category_hint: Option<String>,
        exclude_agents: Option<Vec<String>>,
        top_n: usize,
    ) -> SelectionResult {
        let exclude_agents = exclude_agents.unwrap_or_default();
        let traits = traits.unwrap_or_default();

        // Score all agents
        let mut scores: Vec<(String, f64, HashMap<String, f64>, Vec<String>, &AgentConfig)> =
            Vec::new();

        for agent_name in self.registry.get_all_agents() {
            if exclude_agents.contains(&agent_name) {
                continue;
            }

            if let Some(config) = self.registry.get_agent_config(&agent_name) {
                let (score, breakdown, matched) =
                    self.calculate_score(&context, config, category_hint.as_deref());

                if score >= self.min_confidence {
                    scores.push((agent_name, score, breakdown, matched, config));
                }
            }
        }

        // Sort by score (descending)
        scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));

        // Fallback to default if no matches
        if scores.is_empty() && !exclude_agents.contains(&self.default_agent) {
            if let Some(default_config) = self.registry.get_agent_config(&self.default_agent) {
                let mut breakdown = HashMap::new();
                breakdown.insert("fallback".to_string(), 0.5);
                scores.push((
                    self.default_agent.clone(),
                    0.5,
                    breakdown,
                    vec!["default selection".to_string()],
                    default_config,
                ));
            }
        }

        // If still no matches, return a default result
        if scores.is_empty() {
            return SelectionResult {
                agent_name: "general-purpose".to_string(),
                confidence: 0.0,
                confidence_level: "low".to_string(),
                breakdown: HashMap::new(),
                matched_criteria: vec!["no matching agent".to_string()],
                alternatives: Vec::new(),
                traits_applied: Vec::new(),
                agent_path: "agents/core/general-purpose.md".to_string(),
                trait_paths: Vec::new(),
                invalid_traits: Vec::new(),
                trait_conflicts: Vec::new(),
                trait_tensions: Vec::new(),
            };
        }

        // Get top selection
        let (top_name, top_score, top_breakdown, top_matched, top_config) = &scores[0];

        // Process traits
        let (valid_traits, invalid_traits, conflicts, tensions) = self.process_traits(&traits);

        // Build trait paths
        let trait_paths: Vec<String> = valid_traits
            .iter()
            .filter_map(|trait_name| {
                self.registry
                    .get_trait_config(trait_name)
                    .map(|c| c.file_path.to_string_lossy().to_string())
            })
            .collect();

        // Build alternatives list with full details
        let alternatives: Vec<AlternativeAgent> = scores
            .iter()
            .skip(1)
            .take(top_n)
            .map(|(name, score, _, _, config)| AlternativeAgent {
                agent_name: name.clone(),
                score: *score,
                confidence_level: confidence_level(*score),
                agent_path: config.file_path.to_string_lossy().to_string(),
            })
            .collect();

        SelectionResult {
            agent_name: top_name.clone(),
            confidence: *top_score,
            confidence_level: confidence_level(*top_score),
            breakdown: top_breakdown.clone(),
            matched_criteria: top_matched.clone(),
            alternatives,
            traits_applied: valid_traits,
            agent_path: top_config.file_path.to_string_lossy().to_string(),
            trait_paths,
            invalid_traits,
            trait_conflicts: conflicts,
            trait_tensions: tensions,
        }
    }

    /// Calculate match score with detailed breakdown
    fn calculate_score(
        &self,
        context: &SelectionContext,
        config: &AgentConfig,
        category_hint: Option<&str>,
    ) -> (f64, HashMap<String, f64>, Vec<String>) {
        let mut score = 0.0;
        let mut breakdown = HashMap::new();
        let mut matched = Vec::new();

        let context_str = context.to_search_string();
        let context_lower = context_str.to_lowercase();

        // 1. Trigger/keyword matching (35% weight)
        // Enhanced with bidirectional overlap (matching Python behavior)
        let keywords = context.keywords();
        let trigger_score = if !config.triggers.is_empty() {
            let mut trigger_match = 0.0;
            let mut matched_triggers = Vec::new();

            for trigger in &config.triggers {
                let trigger_lower = trigger.to_lowercase();
                if context_lower.contains(&trigger_lower) {
                    // Full match in task text
                    trigger_match += 1.0;
                    matched_triggers.push(trigger.clone());
                } else if !keywords.is_empty()
                    && keywords
                        .iter()
                        .any(|kw| kw.to_lowercase() == trigger_lower)
                {
                    // Match in explicit keywords parameter
                    trigger_match += 0.8;
                    matched_triggers.push(trigger.clone());
                } else if !keywords.is_empty()
                    && keywords.iter().any(|kw| {
                        let kw_lower = kw.to_lowercase();
                        kw_lower.contains(&trigger_lower) || trigger_lower.contains(&kw_lower)
                    })
                {
                    // Bidirectional partial overlap
                    trigger_match += 0.3;
                } else if trigger_lower
                    .split_whitespace()
                    .any(|t| context_lower.contains(t))
                {
                    trigger_match += 0.3;
                }
            }

            let normalized = (trigger_match / config.triggers.len() as f64).min(1.0);

            if !matched_triggers.is_empty() {
                let trigger_list: Vec<String> = matched_triggers.iter().take(3).cloned().collect();
                matched.push(format!("triggers: {}", trigger_list.join(", ")));
            }

            normalized
        } else {
            0.0
        };

        breakdown.insert("triggers".to_string(), trigger_score * 0.35);
        score += trigger_score * 0.35;

        // 2. Category/domain matching (25% weight)
        let domains = context.domains();
        let category_score = if let Some(hint) = category_hint {
            if config.category.to_lowercase() == hint.to_lowercase() {
                matched.push(format!("category: {}", config.category));
                1.0
            } else {
                0.0
            }
        } else if !domains.is_empty() {
            // Check explicit domains against category
            let cat_lower = config.category.to_lowercase();
            if domains.iter().any(|d| d.to_lowercase() == cat_lower) {
                matched.push(format!("category: {} (domain match)", config.category));
                1.0
            } else if domains.iter().any(|d| {
                let d_lower = d.to_lowercase();
                cat_lower.contains(&d_lower) || d_lower.contains(&cat_lower)
            }) {
                matched.push(format!("category: {} (partial)", config.category));
                0.5
            } else {
                0.0
            }
        } else if !config.category.is_empty()
            && context_lower.contains(&config.category.to_lowercase())
        {
            matched.push(format!("category: {}", config.category));
            0.7
        } else {
            0.0
        };

        breakdown.insert("category".to_string(), category_score * 0.25);
        score += category_score * 0.25;

        // 3. Task text matching (20% weight)
        let name_parts: Vec<&str> = config.name.split('-').collect();
        let mut task_score = 0.0;

        for part in name_parts {
            if part.len() > 2 && context_lower.contains(&part.to_lowercase()) {
                task_score += 0.5;
            }
        }

        task_score = f64::min(task_score, 1.0);

        if task_score > 0.0 {
            matched.push(format!("name match: {}", config.name));
        }

        breakdown.insert("task_match".to_string(), task_score * 0.20);
        score += task_score * 0.20;

        // 4. File pattern matching (10% weight)
        // Enhanced with glob matching (fnmatch equivalent)
        let mut file_score = 0.0;
        let files = context.files();

        for pattern in &config.file_patterns {
            let pattern_lower = pattern.to_lowercase();
            for file in &files {
                let file_lower = file.to_lowercase();
                // Try glob first, then substring
                if glob_match(&pattern_lower, &file_lower) || file_lower.contains(&pattern_lower) {
                    file_score = 1.0;
                    matched.push(format!("file: {}", pattern));
                    break;
                }
            }
            if file_score > 0.0 {
                break;
            }
        }

        breakdown.insert("file_patterns".to_string(), file_score * 0.10);
        score += file_score * 0.10;

        // 5. Priority bonus (10% weight)
        let priority_bonus = ((4 - config.priority.min(3)) as f64 / 3.0) * 0.10;
        breakdown.insert("priority".to_string(), priority_bonus);
        score += priority_bonus;

        (score.min(1.0), breakdown, matched)
    }

    /// Process and validate requested traits
    fn process_traits(
        &self,
        requested_traits: &[String],
    ) -> (
        Vec<String>,
        Vec<String>,
        Vec<(String, String)>,
        Vec<(String, String)>,
    ) {
        let mut valid = Vec::new();
        let mut invalid = Vec::new();

        // Validate traits exist
        for trait_name in requested_traits {
            if self.registry.is_valid_trait(trait_name) {
                valid.push(trait_name.clone());
            } else {
                invalid.push(trait_name.clone());
            }
        }

        // Check for conflicts
        let mut conflicts = Vec::new();
        let mut tensions = Vec::new();

        for (i, trait1) in valid.iter().enumerate() {
            for trait2 in valid.iter().skip(i + 1) {
                if let Some(conflict_set) = TRAIT_CONFLICTS.get(trait1.as_str()) {
                    if conflict_set.contains(trait2.as_str()) {
                        conflicts.push((trait1.clone(), trait2.clone()));
                    }
                }

                if let Some(tension_set) = TRAIT_TENSIONS.get(trait1.as_str()) {
                    if tension_set.contains(trait2.as_str()) {
                        tensions.push((trait1.clone(), trait2.clone()));
                    }
                }
            }
        }

        (valid, invalid, conflicts, tensions)
    }

    /// Find the best matching agent for context
    pub fn find_best_match(
        &self,
        context: SelectionContext,
        category_hint: Option<String>,
        exclude_agents: Option<Vec<String>>,
    ) -> (String, f64) {
        let result = self.select_agent(context, None, category_hint, exclude_agents, 3);
        (result.agent_name, result.confidence)
    }

    /// Get top N agent suggestions for context
    pub fn get_agent_suggestions(
        &self,
        context: SelectionContext,
        top_n: usize,
    ) -> Vec<(String, f64)> {
        let result = self.select_agent(context, None, None, None, top_n);
        let mut suggestions = vec![(result.agent_name, result.confidence)];
        suggestions.extend(
            result.alternatives.into_iter().map(|a| (a.agent_name, a.score))
        );
        suggestions.truncate(top_n);
        suggestions
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::registry::AgentRegistry;
    use std::fs;
    use tempfile::TempDir;

    fn create_test_agent(
        dir: &std::path::Path,
        name: &str,
        tier: &str,
        triggers: &[&str],
        category: &str,
    ) -> anyhow::Result<()> {
        let content = format!(
            r#"---
name: {}
description: Test agent
tier: {}
category: {}
triggers: [{}]
---

# Test Agent
"#,
            name,
            tier,
            category,
            triggers
                .iter()
                .map(|t| format!("\"{}\"", t))
                .collect::<Vec<_>>()
                .join(", ")
        );

        fs::write(dir.join(format!("{}.md", name)), content)?;
        Ok(())
    }

    #[test]
    fn test_agent_selection_by_trigger() -> anyhow::Result<()> {
        let temp_dir = TempDir::new()?;
        let agents_dir = temp_dir.path();

        fs::create_dir(agents_dir.join("core"))?;
        create_test_agent(
            &agents_dir.join("core"),
            "test-agent",
            "core",
            &["frontend", "react"],
            "frontend",
        )?;
        create_test_agent(
            &agents_dir.join("core"),
            "backend-agent",
            "core",
            &["backend", "api"],
            "backend",
        )?;

        let registry = AgentRegistry::new(Some(agents_dir.to_path_buf()));
        let selector = AgentSelector::new(registry);

        let context = SelectionContext::Text("Build a react frontend".to_string());
        let result = selector.select_agent(context, None, None, None, 3);

        assert_eq!(result.agent_name, "test-agent");
        assert!(result.confidence > 0.3);

        Ok(())
    }

    #[test]
    fn test_agent_selection_by_category() -> anyhow::Result<()> {
        let temp_dir = TempDir::new()?;
        let agents_dir = temp_dir.path();

        fs::create_dir(agents_dir.join("core"))?;
        create_test_agent(
            &agents_dir.join("core"),
            "frontend-agent",
            "core",
            &[],
            "frontend",
        )?;
        create_test_agent(
            &agents_dir.join("core"),
            "backend-agent",
            "core",
            &[],
            "backend",
        )?;

        let registry = AgentRegistry::new(Some(agents_dir.to_path_buf()));
        let selector = AgentSelector::new(registry);

        let context = SelectionContext::Text("Some task".to_string());
        let result = selector.select_agent(context, None, Some("backend".to_string()), None, 3);

        assert_eq!(result.agent_name, "backend-agent");

        Ok(())
    }

    #[test]
    fn test_trait_conflict_detection() -> anyhow::Result<()> {
        let temp_dir = TempDir::new()?;
        let agents_dir = temp_dir.path();

        fs::create_dir(agents_dir.join("core"))?;
        fs::create_dir(agents_dir.join("traits"))?;

        create_test_agent(&agents_dir.join("core"), "test-agent", "core", &[], "general")?;
        create_test_agent(
            &agents_dir.join("traits"),
            "minimal-changes",
            "trait",
            &[],
            "modifier",
        )?;
        create_test_agent(
            &agents_dir.join("traits"),
            "rapid-prototype",
            "trait",
            &[],
            "modifier",
        )?;

        let registry = AgentRegistry::new(Some(agents_dir.to_path_buf()));
        let selector = AgentSelector::new(registry);

        let (_valid, _invalid, conflicts, _tensions) = selector.process_traits(&[
            "minimal-changes".to_string(),
            "rapid-prototype".to_string(),
        ]);

        assert_eq!(conflicts.len(), 1);
        assert!(
            conflicts[0] == ("minimal-changes".to_string(), "rapid-prototype".to_string())
                || conflicts[0] == ("rapid-prototype".to_string(), "minimal-changes".to_string())
        );

        Ok(())
    }

    #[test]
    fn test_alternatives() -> anyhow::Result<()> {
        let temp_dir = TempDir::new()?;
        let agents_dir = temp_dir.path();

        fs::create_dir(agents_dir.join("core"))?;
        create_test_agent(
            &agents_dir.join("core"),
            "agent1",
            "core",
            &["test"],
            "general",
        )?;
        create_test_agent(
            &agents_dir.join("core"),
            "agent2",
            "core",
            &["test"],
            "general",
        )?;
        create_test_agent(
            &agents_dir.join("core"),
            "agent3",
            "core",
            &["test"],
            "general",
        )?;

        let registry = AgentRegistry::new(Some(agents_dir.to_path_buf()));
        let selector = AgentSelector::new(registry);

        let context = SelectionContext::Text("test task".to_string());
        let result = selector.select_agent(context, None, None, None, 3);

        assert!(result.confidence > 0.0);
        assert!(result.alternatives.len() >= 2);

        Ok(())
    }
}
