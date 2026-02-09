//! Obsidian Vault Integration for SuperClaude
//!
//! Syncs decision artifacts to Obsidian vault with YAML frontmatter,
//! extracts decisions from tool invocations, and manages backlinks.

use chrono::{DateTime, Utc};
use regex::Regex;
use serde::{Deserialize, Serialize};
use serde_yaml;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use tracing::{debug, error, info, warn};

use crate::evidence::ToolInvocation;

// ============================================================================
// Configuration Structures
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VaultConfig {
    pub path: PathBuf,
    #[serde(default = "default_read_paths")]
    pub read_paths: Vec<String>,
    #[serde(default = "default_output_base")]
    pub output_base: String,
}

fn default_read_paths() -> Vec<String> {
    vec!["Knowledge/".to_string()]
}

fn default_output_base() -> String {
    "Claude/".to_string()
}

impl Default for VaultConfig {
    fn default() -> Self {
        Self {
            path: dirs::home_dir()
                .unwrap_or_else(|| PathBuf::from("."))
                .join("Documents/Obsidian"),
            read_paths: default_read_paths(),
            output_base: default_output_base(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RelevanceFilter {
    #[serde(default = "default_filter_type")]
    pub filter_type: String, // "project_name", "tags", "path"
    #[serde(default = "default_filter_field")]
    pub field: String,
}

fn default_filter_type() -> String {
    "project_name".to_string()
}

fn default_filter_field() -> String {
    "project".to_string()
}

impl Default for RelevanceFilter {
    fn default() -> Self {
        Self {
            filter_type: default_filter_type(),
            field: default_filter_field(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContextConfig {
    #[serde(default)]
    pub relevance_filter: RelevanceFilter,
    #[serde(default = "default_extract_fields")]
    pub extract_fields: Vec<String>,
}

fn default_extract_fields() -> Vec<String> {
    vec![
        "summary".to_string(),
        "tags".to_string(),
        "category".to_string(),
    ]
}

impl Default for ContextConfig {
    fn default() -> Self {
        Self {
            relevance_filter: RelevanceFilter::default(),
            extract_fields: default_extract_fields(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BacklinksConfig {
    #[serde(default = "default_backlinks_enabled")]
    pub enabled: bool,
    #[serde(default = "default_backlinks_section")]
    pub section: String,
}

fn default_backlinks_enabled() -> bool {
    true
}

fn default_backlinks_section() -> String {
    "## Claude References".to_string()
}

impl Default for BacklinksConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            section: default_backlinks_section(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArtifactConfig {
    #[serde(default = "default_sync_on")]
    pub sync_on: String, // "task_completion", "manual", "never"
    #[serde(default = "default_artifact_types")]
    pub types: Vec<String>,
    #[serde(default = "default_output_paths")]
    pub output_paths: HashMap<String, String>,
    #[serde(default)]
    pub backlinks: BacklinksConfig,
}

fn default_sync_on() -> String {
    "task_completion".to_string()
}

fn default_artifact_types() -> Vec<String> {
    vec!["decisions".to_string()]
}

fn default_output_paths() -> HashMap<String, String> {
    let mut map = HashMap::new();
    map.insert("decisions".to_string(), "Claude/Decisions/".to_string());
    map
}

impl Default for ArtifactConfig {
    fn default() -> Self {
        Self {
            sync_on: default_sync_on(),
            types: default_artifact_types(),
            output_paths: default_output_paths(),
            backlinks: BacklinksConfig::default(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NoteConfig {
    #[serde(default = "default_note_format")]
    pub format: String, // "rich", "minimal"
    #[serde(default = "default_frontmatter_include")]
    pub frontmatter_include: Vec<String>,
}

fn default_note_format() -> String {
    "rich".to_string()
}

fn default_frontmatter_include() -> Vec<String> {
    vec![
        "title".to_string(),
        "type".to_string(),
        "decision_type".to_string(),
        "project".to_string(),
        "created".to_string(),
        "session_id".to_string(),
        "tags".to_string(),
        "related".to_string(),
    ]
}

impl Default for NoteConfig {
    fn default() -> Self {
        Self {
            format: default_note_format(),
            frontmatter_include: default_frontmatter_include(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ObsidianConfig {
    pub vault: VaultConfig,
    #[serde(default)]
    pub context: ContextConfig,
    #[serde(default)]
    pub artifacts: ArtifactConfig,
    #[serde(default)]
    pub notes: NoteConfig,
}

impl ObsidianConfig {
    pub fn from_yaml(yaml_str: &str) -> Result<Self, serde_yaml::Error> {
        serde_yaml::from_str(yaml_str)
    }

    pub fn from_file(path: &Path) -> Result<Self, Box<dyn std::error::Error>> {
        let contents = fs::read_to_string(path)?;
        Ok(Self::from_yaml(&contents)?)
    }
}

impl Default for ObsidianConfig {
    fn default() -> Self {
        Self {
            vault: VaultConfig::default(),
            context: ContextConfig::default(),
            artifacts: ArtifactConfig::default(),
            notes: NoteConfig::default(),
        }
    }
}

// ============================================================================
// Decision Record
// ============================================================================

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DecisionRecord {
    pub title: String,
    pub summary: String,
    pub decision_type: String, // "architecture", "consensus", "technical"
    pub context: String,
    pub rationale: String,
    #[serde(default)]
    pub source_notes: Vec<String>,
    #[serde(default)]
    pub session_id: String,
    #[serde(default)]
    pub project: String,
    #[serde(with = "chrono::serde::ts_seconds")]
    pub created: DateTime<Utc>,
    #[serde(default)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl DecisionRecord {
    pub fn new(
        title: String,
        summary: String,
        decision_type: String,
        context: String,
        rationale: String,
    ) -> Self {
        Self {
            title,
            summary,
            decision_type,
            context,
            rationale,
            source_notes: Vec::new(),
            session_id: String::new(),
            project: String::new(),
            created: Utc::now(),
            metadata: HashMap::new(),
        }
    }

    /// Generate URL-safe slug from title
    pub fn to_slug(&self) -> String {
        let slug = self.title.to_lowercase();

        // Remove non-alphanumeric characters except spaces and hyphens
        let re = Regex::new(r"[^a-z0-9\s-]").unwrap();
        let slug = re.replace_all(&slug, "");

        // Replace spaces/underscores with hyphens
        let re = Regex::new(r"[\s_]+").unwrap();
        let slug = re.replace_all(&slug, "-");

        // Replace multiple hyphens with single hyphen
        let re = Regex::new(r"-+").unwrap();
        let slug = re.replace_all(&slug, "-");

        // Truncate to 50 chars and trim trailing hyphens
        slug.chars().take(50).collect::<String>().trim_end_matches('-').to_string()
    }

    /// Generate filename with date prefix and hash suffix
    pub fn to_filename(&self) -> String {
        let date_str = self.created.format("%Y-%m-%d").to_string();
        let slug = self.to_slug();

        // Add short hash for uniqueness
        let hash_input = format!("{}{}", self.title, self.created.to_rfc3339());
        let hash = format!("{:x}", md5::compute(hash_input.as_bytes()));
        let short_hash = &hash[..6];

        format!("{}-{}-{}.md", date_str, slug, short_hash)
    }
}

// ============================================================================
// Obsidian Artifact Writer
// ============================================================================

pub struct ObsidianArtifactWriter {
    config: ObsidianConfig,
}

impl ObsidianArtifactWriter {
    pub fn new(config: ObsidianConfig) -> Self {
        Self { config }
    }

    pub fn from_config_file(path: &Path) -> Result<Self, Box<dyn std::error::Error>> {
        let config = ObsidianConfig::from_file(path)?;
        Ok(Self::new(config))
    }

    /// Write a decision record to the Obsidian vault
    pub fn write_decision(&self, decision: &DecisionRecord) -> Result<PathBuf, Box<dyn std::error::Error>> {
        // Check if decisions are enabled
        if !self.config.artifacts.types.contains(&"decisions".to_string()) {
            debug!("Decision artifacts disabled in config");
            return Err("Decision artifacts disabled".into());
        }

        // Get output path
        let output_rel = self.config.artifacts.output_paths
            .get("decisions")
            .cloned()
            .unwrap_or_else(|| "Claude/Decisions/".to_string());

        let output_dir = self.config.vault.path.join(&output_rel);

        // Ensure output directory exists
        fs::create_dir_all(&output_dir)?;

        // Generate content
        let filename = decision.to_filename();
        let file_path = output_dir.join(&filename);
        let content = self.generate_decision_content(decision);

        // Write file
        fs::write(&file_path, content)?;
        info!("Wrote decision artifact: {}", filename);

        // Inject backlinks if enabled
        if self.config.artifacts.backlinks.enabled {
            if let Err(e) = self.inject_backlinks(decision, &file_path) {
                warn!("Failed to inject backlinks: {}", e);
            }
        }

        Ok(file_path)
    }

    /// Generate markdown content for a decision
    fn generate_decision_content(&self, decision: &DecisionRecord) -> String {
        let mut lines = Vec::new();

        // Frontmatter
        let frontmatter = self.build_frontmatter(decision);
        lines.push("---".to_string());
        lines.push(serde_yaml::to_string(&frontmatter).unwrap().trim().to_string());
        lines.push("---".to_string());
        lines.push(String::new());

        // Title
        lines.push(format!("# {}", decision.title));
        lines.push(String::new());

        // Decision type callout
        lines.push(format!(
            "> [!info] Decision Type: {}",
            capitalize_first(&decision.decision_type)
        ));
        lines.push(String::new());

        // Summary section
        lines.push("## Summary".to_string());
        lines.push(String::new());
        lines.push(decision.summary.clone());
        lines.push(String::new());

        // Context section
        if !decision.context.is_empty() {
            lines.push("## Context".to_string());
            lines.push(String::new());
            lines.push(decision.context.clone());
            lines.push(String::new());
        }

        // Rationale section
        if !decision.rationale.is_empty() {
            lines.push("## Rationale".to_string());
            lines.push(String::new());
            lines.push(decision.rationale.clone());
            lines.push(String::new());
        }

        // Related notes section
        if !decision.source_notes.is_empty() {
            lines.push("## Related Notes".to_string());
            lines.push(String::new());
            for note_path in &decision.source_notes {
                lines.push(format!("- [[{}]]", note_path));
            }
            lines.push(String::new());
        }

        // Footer
        lines.push("---".to_string());
        lines.push(String::new());
        lines.push(format!(
            "*Generated by SuperClaude on {}*",
            decision.created.format("%Y-%m-%d %H:%M")
        ));

        lines.join("\n")
    }

    /// Build YAML frontmatter dictionary
    fn build_frontmatter(&self, decision: &DecisionRecord) -> HashMap<String, serde_json::Value> {
        let mut frontmatter = HashMap::new();
        let includes = &self.config.notes.frontmatter_include;

        if includes.contains(&"title".to_string()) {
            frontmatter.insert("title".to_string(), serde_json::json!(decision.title));
        }
        if includes.contains(&"type".to_string()) {
            frontmatter.insert("type".to_string(), serde_json::json!("decision"));
        }
        if includes.contains(&"decision_type".to_string()) {
            frontmatter.insert("decision_type".to_string(), serde_json::json!(decision.decision_type));
        }
        if includes.contains(&"project".to_string()) && !decision.project.is_empty() {
            frontmatter.insert("project".to_string(), serde_json::json!(decision.project));
        }
        if includes.contains(&"created".to_string()) {
            frontmatter.insert("created".to_string(), serde_json::json!(decision.created.to_rfc3339()));
        }
        if includes.contains(&"session_id".to_string()) && !decision.session_id.is_empty() {
            frontmatter.insert("session_id".to_string(), serde_json::json!(decision.session_id));
        }
        if includes.contains(&"tags".to_string()) {
            let mut tags = vec!["decision".to_string(), decision.decision_type.clone()];
            if !decision.project.is_empty() {
                tags.push(decision.project.to_lowercase().replace(' ', "-"));
            }
            frontmatter.insert("tags".to_string(), serde_json::json!(tags));
        }
        if includes.contains(&"related".to_string()) && !decision.source_notes.is_empty() {
            let related: Vec<String> = decision.source_notes
                .iter()
                .map(|note| format!("[[{}]]", note))
                .collect();
            frontmatter.insert("related".to_string(), serde_json::json!(related));
        }

        // Add any extra metadata
        for (key, value) in &decision.metadata {
            if !frontmatter.contains_key(key) {
                frontmatter.insert(key.clone(), value.clone());
            }
        }

        frontmatter
    }

    /// Inject backlinks into source notes
    fn inject_backlinks(&self, decision: &DecisionRecord, decision_path: &Path) -> Result<(), Box<dyn std::error::Error>> {
        if decision.source_notes.is_empty() {
            return Ok(());
        }

        let vault_path = &self.config.vault.path;
        let section_header = &self.config.artifacts.backlinks.section;
        let decision_relative = decision_path.strip_prefix(vault_path)?
            .to_string_lossy()
            .to_string();
        let date_str = decision.created.format("%Y-%m-%d").to_string();

        for note_path in &decision.source_notes {
            let full_path = vault_path.join(note_path);
            if !full_path.exists() {
                debug!("Source note not found: {}", note_path);
                continue;
            }

            match self.inject_backlink_into_file(&full_path, &decision_relative, &decision.title, &date_str, section_header) {
                Ok(_) => debug!("Injected backlink into {}", note_path),
                Err(e) => warn!("Failed to inject backlink into {}: {}", note_path, e),
            }
        }

        Ok(())
    }

    fn inject_backlink_into_file(
        &self,
        file_path: &Path,
        decision_path: &str,
        decision_title: &str,
        date_str: &str,
        section_header: &str,
    ) -> Result<(), Box<dyn std::error::Error>> {
        let content = fs::read_to_string(file_path)?;
        let backlink = format!("- [[{}|{}]] - {}", decision_path, decision_title, date_str);

        let new_content = if content.contains(section_header) {
            // Section exists, append to it
            let lines: Vec<&str> = content.lines().collect();
            let mut new_lines = Vec::new();
            let mut found_section = false;
            let mut added = false;

            for line in lines {
                new_lines.push(line.to_string());
                if line.trim() == section_header {
                    found_section = true;
                } else if found_section && !added && !line.starts_with("- ") {
                    // Found end of list, insert before this line
                    new_lines.insert(new_lines.len() - 1, backlink.clone());
                    added = true;
                    found_section = false;
                }
            }

            if !added {
                // Add at end of file
                new_lines.push(backlink);
            }

            new_lines.join("\n")
        } else {
            // Add new section at end
            format!("{}\n\n{}\n\n{}\n", content.trim_end(), section_header, backlink)
        };

        fs::write(file_path, new_content)?;
        Ok(())
    }

    pub fn should_sync(&self) -> bool {
        self.config.artifacts.sync_on != "never"
    }

    pub fn get_output_dir(&self, artifact_type: &str) -> Option<PathBuf> {
        self.config.artifacts.output_paths
            .get(artifact_type)
            .map(|rel_path| self.config.vault.path.join(rel_path))
    }
}

// ============================================================================
// Decision Extraction from Evidence
// ============================================================================

/// Extract decision records from tool invocations
pub fn extract_decisions_from_evidence(
    tool_invocations: &[ToolInvocation],
    project_name: &str,
    session_id: &str,
) -> Vec<DecisionRecord> {
    let mut decisions = Vec::new();

    for invocation in tool_invocations {
        let tool_name = &invocation.tool_name;

        // Check for PAL consensus tool
        if tool_name.to_lowercase().contains("consensus") {
            if let Some(decision) = parse_consensus_decision(invocation, project_name, session_id) {
                decisions.push(decision);
            }
        }
        // Check for PAL thinkdeep tool
        else if tool_name.to_lowercase().contains("thinkdeep") {
            if let Some(decision) = parse_thinkdeep_decision(invocation, project_name, session_id) {
                decisions.push(decision);
            }
        }
        // Check for architecture patterns in tool input
        else if invocation.tool_input.to_string().to_lowercase().contains("architecture") {
            if let Some(decision) = parse_architecture_decision(invocation, project_name, session_id) {
                decisions.push(decision);
            }
        }
    }

    decisions
}

fn parse_consensus_decision(
    invocation: &ToolInvocation,
    project_name: &str,
    session_id: &str,
) -> Option<DecisionRecord> {
    let tool_input = &invocation.tool_input;

    // Try to extract question/prompt
    let question = tool_input.get("question")
        .or_else(|| tool_input.get("prompt"))
        .and_then(|v| v.as_str())?;

    let summary = if invocation.tool_output.len() > 500 {
        &invocation.tool_output[..500]
    } else {
        &invocation.tool_output
    };

    let title = if question.len() > 100 {
        format!("Consensus: {}...", &question[..100])
    } else {
        format!("Consensus: {}", question)
    };

    Some(DecisionRecord {
        title,
        summary: summary.to_string(),
        decision_type: "consensus".to_string(),
        context: format!("Multi-model consensus requested for: {}", question),
        rationale: invocation.tool_output.clone(),
        project: project_name.to_string(),
        session_id: session_id.to_string(),
        created: Utc::now(),
        source_notes: Vec::new(),
        metadata: HashMap::new(),
    })
}

fn parse_thinkdeep_decision(
    invocation: &ToolInvocation,
    project_name: &str,
    session_id: &str,
) -> Option<DecisionRecord> {
    let tool_input = &invocation.tool_input;

    let topic = tool_input.get("topic")
        .or_else(|| tool_input.get("prompt"))
        .and_then(|v| v.as_str())?;

    let summary = if invocation.tool_output.len() > 500 {
        &invocation.tool_output[..500]
    } else {
        &invocation.tool_output
    };

    let title = if topic.len() > 100 {
        format!("Analysis: {}...", &topic[..100])
    } else {
        format!("Analysis: {}", topic)
    };

    Some(DecisionRecord {
        title,
        summary: summary.to_string(),
        decision_type: "technical".to_string(),
        context: format!("Deep analysis requested for: {}", topic),
        rationale: invocation.tool_output.clone(),
        project: project_name.to_string(),
        session_id: session_id.to_string(),
        created: Utc::now(),
        source_notes: Vec::new(),
        metadata: HashMap::new(),
    })
}

fn parse_architecture_decision(
    invocation: &ToolInvocation,
    project_name: &str,
    session_id: &str,
) -> Option<DecisionRecord> {
    let tool_input = &invocation.tool_input;

    // Try to extract meaningful title
    let mut title = "Architecture Decision".to_string();
    for key in &["topic", "question", "prompt", "command"] {
        if let Some(value) = tool_input.get(*key).and_then(|v| v.as_str()) {
            let truncated = if value.len() > 80 {
                format!("{}...", &value[..80])
            } else {
                value.to_string()
            };
            title = format!("Architecture: {}", truncated);
            break;
        }
    }

    let summary = if invocation.tool_output.len() > 500 {
        &invocation.tool_output[..500]
    } else {
        &invocation.tool_output
    };

    Some(DecisionRecord {
        title,
        summary: summary.to_string(),
        decision_type: "architecture".to_string(),
        context: tool_input.to_string(),
        rationale: invocation.tool_output.clone(),
        project: project_name.to_string(),
        session_id: session_id.to_string(),
        created: Utc::now(),
        source_notes: Vec::new(),
        metadata: HashMap::new(),
    })
}

// ============================================================================
// Config Service
// ============================================================================

pub struct ObsidianConfigService {
    project_root: PathBuf,
    config_cache: Option<ObsidianConfig>,
}

impl ObsidianConfigService {
    pub const CONFIG_FILENAME: &'static str = ".obsidian.yaml";

    pub fn new(project_root: PathBuf) -> Self {
        Self {
            project_root,
            config_cache: None,
        }
    }

    pub fn config_path(&self) -> PathBuf {
        self.project_root.join(Self::CONFIG_FILENAME)
    }

    pub fn config_exists(&self) -> bool {
        self.config_path().exists()
    }

    pub fn load_config(&mut self) -> Result<ObsidianConfig, Box<dyn std::error::Error>> {
        if let Some(ref config) = self.config_cache {
            return Ok(config.clone());
        }

        if !self.config_exists() {
            return Err("No Obsidian config found".into());
        }

        let config = ObsidianConfig::from_file(&self.config_path())?;
        self.config_cache = Some(config.clone());
        Ok(config)
    }

    pub fn clear_cache(&mut self) {
        self.config_cache = None;
    }
}

// ============================================================================
// Utilities
// ============================================================================

fn capitalize_first(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        None => String::new(),
        Some(first) => first.to_uppercase().collect::<String>() + chars.as_str(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_decision_to_slug() {
        let decision = DecisionRecord::new(
            "Test Decision: Architecture Change!".to_string(),
            "Summary".to_string(),
            "architecture".to_string(),
            "Context".to_string(),
            "Rationale".to_string(),
        );

        let slug = decision.to_slug();
        assert_eq!(slug, "test-decision-architecture-change");
    }

    #[test]
    fn test_decision_to_filename() {
        let mut decision = DecisionRecord::new(
            "Test Decision".to_string(),
            "Summary".to_string(),
            "technical".to_string(),
            "Context".to_string(),
            "Rationale".to_string(),
        );
        decision.created = DateTime::parse_from_rfc3339("2024-01-15T10:30:00Z")
            .unwrap()
            .with_timezone(&Utc);

        let filename = decision.to_filename();
        assert!(filename.starts_with("2024-01-15-test-decision-"));
        assert!(filename.ends_with(".md"));
    }

    #[test]
    fn test_extract_consensus_decision() {
        let invocation = ToolInvocation {
            tool_name: "mcp__pal__consensus".to_string(),
            tool_input: serde_json::json!({
                "question": "Should we use Rust or Python?"
            }),
            tool_output: "Based on consensus, Rust is recommended for performance".to_string(),
            timestamp: Utc::now().to_rfc3339(),
        };

        let decisions = extract_decisions_from_evidence(
            &[invocation],
            "TestProject",
            "session-123",
        );

        assert_eq!(decisions.len(), 1);
        assert_eq!(decisions[0].decision_type, "consensus");
        assert!(decisions[0].title.contains("Should we use Rust"));
    }

    #[test]
    fn test_extract_thinkdeep_decision() {
        let invocation = ToolInvocation {
            tool_name: "mcp__pal__thinkdeep".to_string(),
            tool_input: serde_json::json!({
                "topic": "Performance optimization strategies"
            }),
            tool_output: "Analysis of caching and parallelization approaches".to_string(),
            timestamp: Utc::now().to_rfc3339(),
        };

        let decisions = extract_decisions_from_evidence(
            &[invocation],
            "TestProject",
            "session-456",
        );

        assert_eq!(decisions.len(), 1);
        assert_eq!(decisions[0].decision_type, "technical");
        assert!(decisions[0].title.contains("Performance optimization"));
    }

    #[test]
    fn test_config_defaults() {
        let config = ObsidianConfig::default();
        assert_eq!(config.artifacts.sync_on, "task_completion");
        assert!(config.artifacts.types.contains(&"decisions".to_string()));
        assert_eq!(config.notes.format, "rich");
    }

    #[test]
    fn test_vault_config_default_paths() {
        let vault = VaultConfig::default();
        assert!(vault.read_paths.contains(&"Knowledge/".to_string()));
        assert_eq!(vault.output_base, "Claude/");
    }
}
