// Skill Persistence Layer for SuperClaude
//
// Enables cross-session learning by:
// 1. Storing learned patterns from successful iterations
// 2. Extracting generalizable skills from execution results
// 3. Retrieving relevant skills for new tasks
// 4. Gating skill promotion through quality thresholds
//
// Architecture:
//     SkillStore (YAML files) -> SkillExtractor -> SkillRetriever
//                               |
//                               v
//                        PromotionGate (PAL/tests)
//                               |
//                               v
//                     .claude/skills/learned/
//
// Storage:
//     - Skills: ~/.claude/skills/learned/{skill-id}/metadata.yaml
//     - Feedback: ~/.claude/feedback/{session-id}.jsonl
//     - Applications: ~/.claude/feedback/{skill-id}_applications.jsonl

use anyhow::{Context, Result};
use chrono::{DateTime, Utc};
use fs2::FileExt;
use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::fs::{self, File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};

// ============================================================================
// Core Data Structures
// ============================================================================

/// A skill extracted from successful execution patterns
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct LearnedSkill {
    pub skill_id: String,
    pub name: String,
    pub description: String,
    pub triggers: Vec<String>,
    pub domain: String,
    pub source_session: String,
    pub source_repo: String,
    pub learned_at: String,
    pub patterns: Vec<String>,
    pub anti_patterns: Vec<String>,
    pub quality_score: f64,
    pub iteration_count: usize,
    pub provenance: HashMap<String, serde_json::Value>,
    pub applicability_conditions: Vec<String>,
    #[serde(default)]
    pub promoted: bool,
    #[serde(default)]
    pub promotion_reason: String,
}

impl LearnedSkill {
    /// Generate SKILL.md content for this learned skill
    pub fn to_skill_md(&self) -> String {
        let triggers_str = self.triggers.join(", ");
        let patterns_str = self
            .patterns
            .iter()
            .map(|p| format!("- {}", p))
            .collect::<Vec<_>>()
            .join("\n");
        let anti_patterns_str = self
            .anti_patterns
            .iter()
            .map(|p| format!("- {}", p))
            .collect::<Vec<_>>()
            .join("\n");
        let conditions_str = self
            .applicability_conditions
            .iter()
            .map(|c| format!("- {}", c))
            .collect::<Vec<_>>()
            .join("\n");

        let name_title = self.name.replace("-", " ");

        format!(
            r#"---
name: {}
description: {}
learned: true
source_session: {}
learned_at: {}
quality_score: {}
---

# {}

{}

## Domain

{}

## Triggers

{}

## Learned Patterns

These patterns were extracted from successful executions:

{}

## Anti-Patterns

Avoid these approaches (they failed or caused issues):

{}

## Applicability Conditions

This skill applies when:

{}

## Provenance

- **Source Session**: `{}`
- **Source Repository**: `{}`
- **Learned At**: {}
- **Quality Score**: {}/100
- **Iterations**: {}
- **Promoted**: {} ({})

## Integration

This is a **learned skill** automatically extracted from execution feedback.
It should be reviewed periodically and may be promoted to a permanent skill
after sufficient validation.
"#,
            self.name,
            self.description,
            self.source_session,
            self.learned_at,
            self.quality_score,
            name_title
                .split_whitespace()
                .map(|w| {
                    let mut chars = w.chars();
                    match chars.next() {
                        None => String::new(),
                        Some(c) => c.to_uppercase().collect::<String>() + chars.as_str(),
                    }
                })
                .collect::<Vec<_>>()
                .join(" "),
            self.description,
            self.domain,
            triggers_str,
            patterns_str,
            anti_patterns_str,
            conditions_str,
            self.source_session,
            self.source_repo,
            self.learned_at,
            self.quality_score,
            self.iteration_count,
            self.promoted,
            if self.promotion_reason.is_empty() {
                "pending"
            } else {
                &self.promotion_reason
            }
        )
    }
}

/// Feedback from a single loop iteration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IterationFeedback {
    pub session_id: String,
    pub iteration: usize,
    pub quality_before: f64,
    pub quality_after: f64,
    pub improvements_applied: Vec<String>,
    pub improvements_needed: Vec<String>,
    pub changed_files: Vec<String>,
    pub test_results: HashMap<String, serde_json::Value>,
    pub duration_seconds: f64,
    pub success: bool,
    pub termination_reason: String,
    #[serde(default = "Utc::now")]
    pub timestamp: DateTime<Utc>,
}

/// Record of a skill being applied in a session
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SkillApplication {
    pub skill_id: String,
    pub session_id: String,
    pub applied_at: String,
    pub was_helpful: Option<bool>,
    pub quality_impact: Option<f64>,
    pub feedback: String,
}

// ============================================================================
// SkillStore - File-based persistent storage
// ============================================================================

/// File-based persistent storage for learned skills.
/// Uses YAML files for skills and JSONL for feedback/applications.
/// Thread-safe with file locking.
pub struct SkillStore {
    skills_dir: PathBuf,
    feedback_dir: PathBuf,
    skills_cache: Option<HashMap<String, LearnedSkill>>,
}

impl SkillStore {
    /// Default skills directory
    pub fn default_skills_dir() -> PathBuf {
        dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".claude")
            .join("skills")
            .join("learned")
    }

    /// Default feedback directory
    pub fn default_feedback_dir() -> PathBuf {
        dirs::home_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join(".claude")
            .join("feedback")
    }

    /// Create a new SkillStore with custom directories
    pub fn new(skills_dir: Option<PathBuf>, feedback_dir: Option<PathBuf>) -> Result<Self> {
        let skills_dir = skills_dir.unwrap_or_else(Self::default_skills_dir);
        let feedback_dir = feedback_dir.unwrap_or_else(Self::default_feedback_dir);

        fs::create_dir_all(&skills_dir)
            .context("Failed to create skills directory")?;
        fs::create_dir_all(&feedback_dir)
            .context("Failed to create feedback directory")?;

        Ok(Self {
            skills_dir,
            feedback_dir,
            skills_cache: None,
        })
    }

    /// Create with default directories
    pub fn default() -> Result<Self> {
        Self::new(None, None)
    }

    /// Load all skills from disk into memory
    fn load_skills(&mut self) -> Result<&HashMap<String, LearnedSkill>> {
        if self.skills_cache.is_some() {
            return Ok(self.skills_cache.as_ref().unwrap());
        }

        let mut skills = HashMap::new();

        for entry in fs::read_dir(&self.skills_dir)? {
            let entry = entry?;
            let path = entry.path();

            if !path.is_dir() {
                continue;
            }

            let metadata_path = path.join("metadata.yaml");
            if !metadata_path.exists() {
                // Try JSON fallback for backwards compatibility
                let json_path = path.join("metadata.json");
                if json_path.exists() {
                    if let Ok(content) = fs::read_to_string(&json_path) {
                        if let Ok(skill) = serde_json::from_str::<LearnedSkill>(&content) {
                            skills.insert(skill.skill_id.clone(), skill);
                        }
                    }
                }
                continue;
            }

            let content = fs::read_to_string(&metadata_path)
                .with_context(|| format!("Failed to read {:?}", metadata_path))?;

            match serde_yaml::from_str::<LearnedSkill>(&content) {
                Ok(skill) => {
                    skills.insert(skill.skill_id.clone(), skill);
                }
                Err(e) => {
                    eprintln!("[SkillStore] Failed to parse {:?}: {}", metadata_path, e);
                }
            }
        }

        self.skills_cache = Some(skills);
        Ok(self.skills_cache.as_ref().unwrap())
    }

    /// Invalidate the skills cache after writes
    fn invalidate_cache(&mut self) {
        self.skills_cache = None;
    }

    /// Write content to file with exclusive lock
    fn write_with_lock(&self, path: &Path, content: &str) -> Result<()> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }

        let file = OpenOptions::new()
            .write(true)
            .create(true)
            .truncate(true)
            .open(path)?;

        file.lock_exclusive()?;
        let result = {
            let mut file = file;
            file.write_all(content.as_bytes())?;
            file.flush()?;
            Ok(())
        };
        // File lock released on drop
        result
    }

    /// Append a JSONL record with lock
    fn append_jsonl(&self, path: &Path, data: &serde_json::Value) -> Result<()> {
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }

        let file = OpenOptions::new()
            .write(true)
            .create(true)
            .append(true)
            .open(path)?;

        file.lock_exclusive()?;
        let result = {
            let mut file = file;
            writeln!(file, "{}", serde_json::to_string(data)?)?;
            file.flush()?;
            Ok(())
        };
        // File lock released on drop
        result
    }

    /// Read all records from a JSONL file
    fn read_jsonl(&self, path: &Path) -> Result<Vec<serde_json::Value>> {
        if !path.exists() {
            return Ok(Vec::new());
        }

        let file = File::open(path)?;
        let reader = BufReader::new(file);
        let mut records = Vec::new();

        for line in reader.lines() {
            if let Ok(line) = line {
                let line = line.trim();
                if !line.is_empty() {
                    if let Ok(value) = serde_json::from_str(line) {
                        records.push(value);
                    }
                }
            }
        }

        Ok(records)
    }

    // --- Skill CRUD Operations ---

    /// Save or update a learned skill. Returns true on success.
    pub fn save_skill(&mut self, skill: &LearnedSkill) -> Result<()> {
        let skill_dir = self.skills_dir.join(&skill.skill_id);
        fs::create_dir_all(&skill_dir)?;

        let metadata_path = skill_dir.join("metadata.yaml");
        let content = serde_yaml::to_string(skill)?;
        self.write_with_lock(&metadata_path, &content)?;

        let skill_md_path = skill_dir.join("SKILL.md");
        self.write_with_lock(&skill_md_path, &skill.to_skill_md())?;

        self.invalidate_cache();
        Ok(())
    }

    /// Retrieve a skill by ID
    pub fn get_skill(&mut self, skill_id: &str) -> Result<Option<LearnedSkill>> {
        let skills = self.load_skills()?;
        Ok(skills.get(skill_id).cloned())
    }

    /// Get all promoted skills
    pub fn get_promoted_skills(&mut self) -> Result<Vec<LearnedSkill>> {
        let skills = self.load_skills()?;
        let mut promoted: Vec<_> = skills
            .values()
            .filter(|s| s.promoted)
            .cloned()
            .collect();
        promoted.sort_by(|a, b| b.quality_score.partial_cmp(&a.quality_score).unwrap());
        Ok(promoted)
    }

    /// Get skills matching a domain
    pub fn get_skills_by_domain(&mut self, domain: &str) -> Result<Vec<LearnedSkill>> {
        let skills = self.load_skills()?;
        let mut domain_skills: Vec<_> = skills
            .values()
            .filter(|s| s.domain == domain)
            .cloned()
            .collect();
        domain_skills.sort_by(|a, b| b.quality_score.partial_cmp(&a.quality_score).unwrap());
        Ok(domain_skills)
    }

    /// Search skills by trigger keywords and filters
    pub fn search_skills(
        &mut self,
        query: &str,
        domain: Option<&str>,
        min_quality: f64,
        promoted_only: bool,
    ) -> Result<Vec<LearnedSkill>> {
        let skills = self.load_skills()?;

        // Apply filters
        let candidates: Vec<_> = skills
            .values()
            .filter(|skill| {
                if skill.quality_score < min_quality {
                    return false;
                }
                if let Some(d) = domain {
                    if skill.domain != d {
                        return false;
                    }
                }
                if promoted_only && !skill.promoted {
                    return false;
                }
                true
            })
            .collect();

        // Filter by trigger match
        let query_terms: HashSet<String> = query.split_whitespace()
            .map(|s| s.to_lowercase())
            .collect();

        let mut results: Vec<_> = candidates
            .into_iter()
            .filter(|skill| {
                let skill_triggers: HashSet<String> = skill.triggers
                    .iter()
                    .map(|t| t.to_lowercase())
                    .collect();
                !query_terms.is_disjoint(&skill_triggers)
            })
            .cloned()
            .collect();

        // Sort by quality
        results.sort_by(|a, b| b.quality_score.partial_cmp(&a.quality_score).unwrap());
        Ok(results)
    }

    // --- Iteration Feedback ---

    /// Record iteration feedback for learning
    pub fn save_feedback(&self, feedback: &IterationFeedback) -> Result<()> {
        let feedback_path = self.feedback_dir.join(format!("{}.jsonl", feedback.session_id));
        let data = serde_json::to_value(feedback)?;
        self.append_jsonl(&feedback_path, &data)
    }

    /// Get all feedback for a session
    pub fn get_session_feedback(&self, session_id: &str) -> Result<Vec<IterationFeedback>> {
        let feedback_path = self.feedback_dir.join(format!("{}.jsonl", session_id));
        let records = self.read_jsonl(&feedback_path)?;

        let mut feedbacks = Vec::new();
        for record in records {
            match serde_json::from_value::<IterationFeedback>(record) {
                Ok(feedback) => feedbacks.push(feedback),
                Err(e) => {
                    eprintln!("[SkillStore] Invalid feedback record: {}", e);
                }
            }
        }

        feedbacks.sort_by_key(|f| f.iteration);
        Ok(feedbacks)
    }

    // --- Skill Application Tracking ---

    /// Record when a skill was applied and its effectiveness
    pub fn record_skill_application(
        &self,
        skill_id: &str,
        session_id: &str,
        was_helpful: Option<bool>,
        quality_impact: Option<f64>,
        feedback: &str,
    ) -> Result<()> {
        let app_path = self.feedback_dir.join(format!("{}_applications.jsonl", skill_id));
        let application = SkillApplication {
            skill_id: skill_id.to_string(),
            session_id: session_id.to_string(),
            applied_at: Utc::now().to_rfc3339(),
            was_helpful,
            quality_impact,
            feedback: feedback.to_string(),
        };
        let data = serde_json::to_value(&application)?;
        self.append_jsonl(&app_path, &data)
    }

    /// Calculate skill effectiveness metrics
    pub fn get_skill_effectiveness(&self, skill_id: &str) -> Result<SkillEffectiveness> {
        let app_path = self.feedback_dir.join(format!("{}_applications.jsonl", skill_id));
        let records = self.read_jsonl(&app_path)?;

        let mut applications = 0;
        let mut helpful_count = 0;
        let mut unhelpful_count = 0;
        let mut quality_impacts = Vec::new();

        for record in records {
            applications += 1;
            if let Some(was_helpful) = record.get("was_helpful").and_then(|v| v.as_bool()) {
                if was_helpful {
                    helpful_count += 1;
                } else {
                    unhelpful_count += 1;
                }
            }
            if let Some(quality_impact) = record.get("quality_impact").and_then(|v| v.as_f64()) {
                quality_impacts.push(quality_impact);
            }
        }

        let avg_quality_impact = if quality_impacts.is_empty() {
            0.0
        } else {
            quality_impacts.iter().sum::<f64>() / quality_impacts.len() as f64
        };

        let success_rate = if applications > 0 {
            helpful_count as f64 / applications as f64
        } else {
            0.0
        };

        Ok(SkillEffectiveness {
            applications,
            helpful_count,
            unhelpful_count,
            success_rate,
            avg_quality_impact,
        })
    }

    /// Calculate skill effectiveness metrics for multiple skills
    pub fn get_bulk_skill_effectiveness(
        &self,
        skill_ids: &[String],
    ) -> Result<HashMap<String, SkillEffectiveness>> {
        let mut results = HashMap::new();
        for skill_id in skill_ids {
            results.insert(skill_id.clone(), self.get_skill_effectiveness(skill_id)?);
        }
        Ok(results)
    }
}

/// Skill effectiveness metrics
#[derive(Debug, Clone, Default)]
pub struct SkillEffectiveness {
    pub applications: usize,
    pub helpful_count: usize,
    pub unhelpful_count: usize,
    pub success_rate: f64,
    pub avg_quality_impact: f64,
}

// ============================================================================
// SkillExtractor - Extract skills from feedback
// ============================================================================

/// Extracts generalizable skills from iteration feedback
pub struct SkillExtractor<'a> {
    store: &'a SkillStore,
}

impl<'a> SkillExtractor<'a> {
    pub fn new(store: &'a SkillStore) -> Self {
        Self { store }
    }

    /// Extract a learned skill from a completed session
    pub fn extract_from_session(
        &self,
        session_id: &str,
        repo_path: &str,
        domain: &str,
    ) -> Result<Option<LearnedSkill>> {
        let feedback_list = self.store.get_session_feedback(session_id)?;

        if feedback_list.is_empty() {
            return Ok(None);
        }

        // Only extract from successful sessions
        let final_feedback = feedback_list.last().unwrap();
        if !final_feedback.success || final_feedback.quality_after < 70.0 {
            return Ok(None);
        }

        // Need at least 2 iterations to learn from
        if feedback_list.len() < 2 {
            return Ok(None);
        }

        // Extract patterns
        let patterns = self.extract_patterns(&feedback_list);
        let anti_patterns = self.extract_anti_patterns(&feedback_list);
        let triggers = self.extract_triggers(&feedback_list);
        let conditions = self.extract_conditions(&feedback_list);

        // Generate skill ID and name
        let skill_id = self.generate_skill_id(session_id, &patterns);
        let name = self.generate_skill_name(&patterns, domain);

        // Build provenance
        let mut provenance = HashMap::new();
        provenance.insert("session_id".to_string(), serde_json::json!(session_id));
        provenance.insert("repo_path".to_string(), serde_json::json!(repo_path));
        provenance.insert("iterations".to_string(), serde_json::json!(feedback_list.len()));

        let quality_progression: Vec<_> = feedback_list.iter().map(|f| {
            serde_json::json!({
                "iteration": f.iteration,
                "before": f.quality_before,
                "after": f.quality_after
            })
        }).collect();
        provenance.insert("quality_progression".to_string(), serde_json::json!(quality_progression));

        let total_duration: f64 = feedback_list.iter().map(|f| f.duration_seconds).sum();
        provenance.insert("total_duration".to_string(), serde_json::json!(total_duration));
        provenance.insert("termination_reason".to_string(), serde_json::json!(final_feedback.termination_reason));

        Ok(Some(LearnedSkill {
            skill_id,
            name,
            description: format!("Learned skill extracted from session {}", &session_id[..8.min(session_id.len())]),
            triggers,
            domain: domain.to_string(),
            source_session: session_id.to_string(),
            source_repo: repo_path.to_string(),
            learned_at: Utc::now().to_rfc3339(),
            patterns,
            anti_patterns,
            quality_score: final_feedback.quality_after,
            iteration_count: feedback_list.len(),
            provenance,
            applicability_conditions: conditions,
            promoted: false,
            promotion_reason: String::new(),
        }))
    }

    fn extract_patterns(&self, feedback_list: &[IterationFeedback]) -> Vec<String> {
        let mut patterns = Vec::new();

        for feedback in feedback_list {
            if feedback.quality_after > feedback.quality_before {
                for improvement in &feedback.improvements_applied {
                    patterns.push(format!("[Iter {}] {}", feedback.iteration, improvement));
                }
            }
        }

        // Deduplicate while preserving order
        let mut seen = HashSet::new();
        let mut unique_patterns = Vec::new();
        for p in patterns {
            let normalized = p.split("] ").nth(1).unwrap_or(&p).to_lowercase().trim().to_string();
            if seen.insert(normalized) {
                unique_patterns.push(p);
            }
        }

        unique_patterns.into_iter().take(10).collect()
    }

    fn extract_anti_patterns(&self, feedback_list: &[IterationFeedback]) -> Vec<String> {
        let mut anti_patterns = Vec::new();

        for feedback in feedback_list {
            if feedback.quality_after <= feedback.quality_before {
                for improvement in &feedback.improvements_applied {
                    anti_patterns.push(format!("[Failed] {}", improvement));
                }
            }

            if !feedback.success {
                for needed in &feedback.improvements_needed {
                    anti_patterns.push(format!("[Unresolved] {}", needed));
                }
            }
        }

        anti_patterns.into_iter().take(5).collect()
    }

    fn extract_triggers(&self, feedback_list: &[IterationFeedback]) -> Vec<String> {
        let mut triggers = HashSet::new();

        for feedback in feedback_list {
            for file_path in &feedback.changed_files {
                let path = Path::new(file_path);
                for component in path.components() {
                    if let Some(part) = component.as_os_str().to_str() {
                        if !["src", "lib", "test", "tests", "spec", "."].contains(&part) {
                            triggers.insert(part.to_lowercase());
                        }
                    }
                }

                if let Some(ext) = path.extension() {
                    if let Some(ext_str) = ext.to_str() {
                        triggers.insert(ext_str.to_string());
                    }
                }
            }

            for improvement in &feedback.improvements_applied {
                for word in improvement.to_lowercase().split_whitespace() {
                    if word.len() > 3 && word.chars().all(|c| c.is_alphabetic()) {
                        triggers.insert(word.to_string());
                    }
                }
            }
        }

        // Filter stopwords
        let stopwords: HashSet<&str> = ["the", "and", "for", "with", "from", "this", "that", "have", "been"].iter().cloned().collect();
        triggers.retain(|t| !stopwords.contains(t.as_str()));

        let mut trigger_vec: Vec<_> = triggers.into_iter().collect();
        trigger_vec.sort();
        trigger_vec.into_iter().take(15).collect()
    }

    fn extract_conditions(&self, feedback_list: &[IterationFeedback]) -> Vec<String> {
        let mut conditions = Vec::new();

        // Analyze file types
        let mut extensions = HashSet::new();
        for feedback in feedback_list {
            for file_path in &feedback.changed_files {
                if let Some(ext) = Path::new(file_path).extension() {
                    if let Some(ext_str) = ext.to_str() {
                        extensions.insert(format!(".{}", ext_str));
                    }
                }
            }
        }

        if !extensions.is_empty() {
            let mut ext_vec: Vec<_> = extensions.into_iter().collect();
            ext_vec.sort();
            conditions.push(format!("File types: {}", ext_vec.join(", ")));
        }

        // Analyze test presence
        let had_tests = feedback_list.iter().any(|f| {
            f.test_results.get("ran").and_then(|v| v.as_bool()).unwrap_or(false)
        });
        if had_tests {
            conditions.push("Project has test suite".to_string());
        }

        // Analyze iteration count
        if feedback_list.len() >= 3 {
            conditions.push("Complex task requiring multiple iterations".to_string());
        }

        conditions
    }

    fn generate_skill_id(&self, session_id: &str, patterns: &[String]) -> String {
        use std::collections::hash_map::DefaultHasher;
        use std::hash::{Hash, Hasher};

        let content = format!("{}:{}", session_id, patterns.join(":"));
        let mut hasher = DefaultHasher::new();
        content.hash(&mut hasher);
        let hash = hasher.finish();
        format!("learned-{:012x}", hash & 0xFFFFFFFFFFFF)
    }

    fn generate_skill_name(&self, patterns: &[String], domain: &str) -> String {
        if patterns.is_empty() {
            return format!("learned-{}-skill", domain);
        }

        let first_pattern = patterns[0].split("] ").nth(1).unwrap_or(&patterns[0]);
        let words: Vec<_> = first_pattern
            .split_whitespace()
            .take(3)
            .filter(|w| w.len() > 2)
            .collect();

        if words.is_empty() {
            format!("learned-{}-general", domain)
        } else {
            format!("learned-{}-{}", domain, words.join("-").to_lowercase())
        }
    }
}

// ============================================================================
// SkillRetriever - Find relevant skills
// ============================================================================

/// Retrieves relevant learned skills for a given task context
pub struct SkillRetriever<'a> {
    store: &'a mut SkillStore,
}

impl<'a> SkillRetriever<'a> {
    pub fn new(store: &'a mut SkillStore) -> Self {
        Self { store }
    }

    /// Retrieve relevant skills for a task
    pub fn retrieve(
        &mut self,
        task_description: &str,
        file_paths: Option<&[String]>,
        domain: Option<&str>,
        max_skills: usize,
        promoted_only: bool,
    ) -> Result<Vec<(LearnedSkill, f64)>> {
        let search_terms = self.extract_search_terms(task_description, file_paths);

        let candidates = self.store.search_skills(
            &search_terms.iter().cloned().collect::<Vec<_>>().join(" "),
            domain,
            50.0,
            promoted_only,
        )?;

        if candidates.is_empty() {
            return Ok(Vec::new());
        }

        // Batch fetch effectiveness data
        let skill_ids: Vec<_> = candidates.iter().map(|s| s.skill_id.clone()).collect();
        let effectiveness_map = self.store.get_bulk_skill_effectiveness(&skill_ids)?;

        // Score and rank
        let mut scored: Vec<_> = candidates
            .into_iter()
            .filter_map(|skill| {
                let effectiveness = effectiveness_map.get(&skill.skill_id);
                let score = self.score_relevance(&skill, &search_terms, file_paths, effectiveness);
                if score > 0.0 {
                    Some((skill, score))
                } else {
                    None
                }
            })
            .collect();

        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
        Ok(scored.into_iter().take(max_skills).collect())
    }

    fn extract_search_terms(&self, task_description: &str, file_paths: Option<&[String]>) -> HashSet<String> {
        let mut terms = HashSet::new();

        // From task description
        for word in task_description.to_lowercase().split_whitespace() {
            if word.len() > 3 && word.chars().all(|c| c.is_alphabetic()) {
                terms.insert(word.to_string());
            }
        }

        // From file paths
        if let Some(paths) = file_paths {
            for path_str in paths {
                let path = Path::new(path_str);
                for component in path.components() {
                    if let Some(part) = component.as_os_str().to_str() {
                        if !["src", "lib", "test", "."].contains(&part) {
                            terms.insert(part.to_lowercase());
                        }
                    }
                }

                if let Some(ext) = path.extension() {
                    if let Some(ext_str) = ext.to_str() {
                        terms.insert(ext_str.to_string());
                    }
                }
            }
        }

        terms
    }

    fn score_relevance(
        &self,
        skill: &LearnedSkill,
        search_terms: &HashSet<String>,
        _file_paths: Option<&[String]>,
        effectiveness: Option<&SkillEffectiveness>,
    ) -> f64 {
        let mut score = 0.0;

        // Trigger match (40%)
        let skill_triggers: HashSet<String> = skill.triggers.iter().map(|t| t.to_lowercase()).collect();
        if !skill_triggers.is_empty() {
            let trigger_overlap = search_terms.intersection(&skill_triggers).count();
            score += 0.4 * (trigger_overlap as f64 / skill_triggers.len() as f64);
        }

        // Quality score (30%)
        score += 0.3 * (skill.quality_score / 100.0);

        // Promoted bonus (20%)
        if skill.promoted {
            score += 0.2;
        }

        // Effectiveness history (10%)
        if let Some(eff) = effectiveness {
            if eff.applications > 0 {
                score += 0.1 * eff.success_rate;
            }
        }

        score
    }
}

// ============================================================================
// PromotionGate - Quality gating for skill promotion
// ============================================================================

/// Gates skill promotion based on quality thresholds and validation
pub struct PromotionGate<'a> {
    store: &'a SkillStore,
    skills_dir: PathBuf,
}

impl<'a> PromotionGate<'a> {
    pub const MIN_QUALITY_SCORE: f64 = 85.0;
    pub const MIN_APPLICATIONS: usize = 2;
    pub const MIN_SUCCESS_RATE: f64 = 0.7;

    pub fn new(store: &'a SkillStore, skills_dir: Option<PathBuf>) -> Self {
        let skills_dir = skills_dir.unwrap_or_else(SkillStore::default_skills_dir);
        Self { store, skills_dir }
    }

    /// Evaluate if a skill should be promoted
    pub fn evaluate(&self, skill: &LearnedSkill) -> Result<(bool, String)> {
        let mut reasons = Vec::new();

        // Check quality score
        if skill.quality_score < Self::MIN_QUALITY_SCORE {
            reasons.push(format!(
                "Quality score {:.1} below threshold {}",
                skill.quality_score, Self::MIN_QUALITY_SCORE
            ));
        }

        // Check application history
        let effectiveness = self.store.get_skill_effectiveness(&skill.skill_id)?;

        if effectiveness.applications < Self::MIN_APPLICATIONS {
            reasons.push(format!(
                "Only {} applications, need {}",
                effectiveness.applications, Self::MIN_APPLICATIONS
            ));
        } else if effectiveness.success_rate < Self::MIN_SUCCESS_RATE {
            reasons.push(format!(
                "Success rate {:.1}% below {:.0}%",
                effectiveness.success_rate * 100.0,
                Self::MIN_SUCCESS_RATE * 100.0
            ));
        }

        if reasons.is_empty() {
            Ok((true, "Meets all promotion criteria".to_string()))
        } else {
            Ok((false, reasons.join("; ")))
        }
    }

    /// Promote a skill to permanent status
    pub fn promote(&self, skill: &mut LearnedSkill, reason: Option<&str>) -> Result<Option<PathBuf>> {
        let (should_promote, eval_reason) = self.evaluate(skill)?;

        if !should_promote {
            return Ok(None);
        }

        // Store original state for rollback
        let original_promoted = skill.promoted;
        let original_reason = skill.promotion_reason.clone();

        // Update skill status
        skill.promoted = true;
        skill.promotion_reason = reason.unwrap_or(&eval_reason).to_string();

        let skill_dir = self.skills_dir.join(&skill.skill_id);
        let skill_md_path = skill_dir.join("SKILL.md");
        let metadata_path = skill_dir.join("metadata.yaml");

        // Attempt promotion with rollback on failure
        let result = (|| -> Result<PathBuf> {
            fs::create_dir_all(&skill_dir)?;

            self.store.write_with_lock(&skill_md_path, &skill.to_skill_md())?;

            let content = serde_yaml::to_string(skill)?;
            self.store.write_with_lock(&metadata_path, &content)?;

            Ok(skill_md_path.clone())
        })();

        match result {
            Ok(path) => Ok(Some(path)),
            Err(e) => {
                // Rollback
                skill.promoted = original_promoted;
                skill.promotion_reason = original_reason;

                // Cleanup
                let _ = fs::remove_file(&metadata_path);
                let _ = fs::remove_file(&skill_md_path);
                if skill_dir.read_dir().map(|mut d| d.next().is_none()).unwrap_or(false) {
                    let _ = fs::remove_dir(&skill_dir);
                }

                eprintln!("[PromotionGate] Failed to promote skill {}: {}", skill.skill_id, e);
                Ok(None)
            }
        }
    }

    /// List skills pending promotion review
    pub fn list_pending(&self, store: &mut SkillStore) -> Result<Vec<LearnedSkill>> {
        let skills = store.load_skills()?;
        let mut pending: Vec<_> = skills
            .values()
            .filter(|s| !s.promoted && s.quality_score >= (Self::MIN_QUALITY_SCORE - 10.0))
            .cloned()
            .collect();
        pending.sort_by(|a, b| b.quality_score.partial_cmp(&a.quality_score).unwrap());
        Ok(pending)
    }
}

// ============================================================================
// Convenience Functions
// ============================================================================

/// Get the default skill store instance
pub fn get_default_store() -> Result<SkillStore> {
    SkillStore::default()
}

/// Extract and optionally promote a skill from a session
pub fn learn_from_session(
    session_id: &str,
    repo_path: &str,
    domain: &str,
    auto_promote: bool,
) -> Result<Option<LearnedSkill>> {
    let mut store = get_default_store()?;
    let extractor = SkillExtractor::new(&store);

    let skill = extractor.extract_from_session(session_id, repo_path, domain)?;

    if let Some(mut skill) = skill {
        store.save_skill(&skill)?;

        if auto_promote {
            let gate = PromotionGate::new(&store, None);
            gate.promote(&mut skill, None)?;
        }

        Ok(Some(skill))
    } else {
        Ok(None)
    }
}

/// Retrieve relevant skills for a task
pub fn retrieve_skills_for_task(
    task_description: &str,
    file_paths: Option<&[String]>,
    domain: Option<&str>,
) -> Result<Vec<LearnedSkill>> {
    let mut store = get_default_store()?;
    let mut retriever = SkillRetriever::new(&mut store);

    let results = retriever.retrieve(task_description, file_paths, domain, 3, false)?;
    Ok(results.into_iter().map(|(skill, _score)| skill).collect())
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::TempDir;

    fn create_temp_store() -> (TempDir, SkillStore) {
        let temp_dir = TempDir::new().unwrap();
        let skills_dir = temp_dir.path().join("skills").join("learned");
        let feedback_dir = temp_dir.path().join("feedback");
        let store = SkillStore::new(Some(skills_dir), Some(feedback_dir)).unwrap();
        (temp_dir, store)
    }

    fn sample_skill() -> LearnedSkill {
        LearnedSkill {
            skill_id: "test-skill-001".to_string(),
            name: "Test Skill".to_string(),
            description: "A test skill for unit testing".to_string(),
            triggers: vec!["test".to_string(), "unit".to_string(), "pytest".to_string()],
            domain: "testing".to_string(),
            source_session: "session-abc123".to_string(),
            source_repo: "/path/to/repo".to_string(),
            learned_at: "2025-01-01T00:00:00Z".to_string(),
            patterns: vec!["Use pytest fixtures".to_string(), "Mock external calls".to_string()],
            anti_patterns: vec!["Don't test implementation details".to_string()],
            quality_score: 85.0,
            iteration_count: 3,
            provenance: HashMap::new(),
            applicability_conditions: vec!["Python projects".to_string(), "Has test suite".to_string()],
            promoted: false,
            promotion_reason: String::new(),
        }
    }

    #[test]
    fn test_save_and_get_skill() {
        let (_temp, mut store) = create_temp_store();
        let skill = sample_skill();

        store.save_skill(&skill).unwrap();
        let retrieved = store.get_skill(&skill.skill_id).unwrap();

        assert!(retrieved.is_some());
        let retrieved = retrieved.unwrap();
        assert_eq!(retrieved.name, skill.name);
        assert_eq!(retrieved.domain, skill.domain);
        assert_eq!(retrieved.quality_score, skill.quality_score);
    }

    #[test]
    fn test_search_skills() {
        let (_temp, mut store) = create_temp_store();
        let skill = sample_skill();

        store.save_skill(&skill).unwrap();
        let results = store.search_skills("test", None, 50.0, false).unwrap();

        assert_eq!(results.len(), 1);
    }

    #[test]
    fn test_skill_to_md() {
        let skill = sample_skill();
        let md = skill.to_skill_md();

        assert!(md.contains("---"));
        assert!(md.contains("name: Test Skill"));
        assert!(md.contains("Use pytest fixtures"));
    }
}
