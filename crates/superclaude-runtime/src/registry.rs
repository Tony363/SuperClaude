//! Agent Registry for SuperClaude Framework.
//!
//! Updated to work with the v7 tiered architecture:
//! - agents/core/     - 16 primary agents
//! - agents/traits/   - 10 composable modifiers
//! - agents/extensions/ - 7 domain specialists

use anyhow::{Context, Result};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use tracing::{debug, info, warn};
use walkdir::WalkDir;

/// Agent configuration extracted from frontmatter
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentConfig {
    /// Agent name
    pub name: String,

    /// Description of agent purpose
    #[serde(default)]
    pub description: String,

    /// Agent tier (core, trait, extension)
    pub tier: String,

    /// Category (e.g., general, frontend, backend)
    #[serde(default)]
    pub category: String,

    /// Trigger keywords for agent selection
    #[serde(default)]
    pub triggers: Vec<String>,

    /// Available tools for this agent
    #[serde(default)]
    pub tools: Vec<String>,

    /// File patterns this agent handles
    #[serde(default)]
    pub file_patterns: Vec<String>,

    /// Selection priority (1=highest, lower=higher priority)
    #[serde(default = "default_priority")]
    pub priority: u32,

    /// Whether this is a core agent
    #[serde(default)]
    pub is_core: bool,

    /// Path to the agent markdown file
    #[serde(skip)]
    pub file_path: PathBuf,
}

fn default_priority() -> u32 {
    2
}

impl AgentConfig {
    /// Create a new AgentConfig from frontmatter and file path
    pub fn from_frontmatter(mut frontmatter: HashMap<String, serde_yaml::Value>, file_path: PathBuf) -> Result<Self> {
        // Extract name from frontmatter or use filename
        let name = frontmatter
            .get("name")
            .and_then(|v| v.as_str())
            .map(String::from)
            .unwrap_or_else(|| {
                file_path
                    .file_stem()
                    .and_then(|s| s.to_str())
                    .unwrap_or("unknown")
                    .to_string()
            });

        // Get tier from frontmatter
        let tier = frontmatter
            .get("tier")
            .and_then(|v| v.as_str())
            .map(String::from)
            .unwrap_or_else(|| "core".to_string());

        // Determine is_core based on tier
        let is_core = tier == "core";

        // Set priority based on tier if not specified
        if !frontmatter.contains_key("priority") {
            let priority = match tier.as_str() {
                "core" => 1,
                "extension" => 2,
                _ => 0, // traits don't participate in selection
            };
            frontmatter.insert("priority".to_string(), serde_yaml::Value::Number(priority.into()));
        }

        // Add tier and is_core to frontmatter
        frontmatter.insert("tier".to_string(), serde_yaml::Value::String(tier));
        frontmatter.insert("is_core".to_string(), serde_yaml::Value::Bool(is_core));
        frontmatter.insert("name".to_string(), serde_yaml::Value::String(name));

        // Convert to AgentConfig
        let mut config: AgentConfig = serde_yaml::from_value(serde_yaml::Value::Mapping(
            frontmatter.into_iter().map(|(k, v)| {
                (serde_yaml::Value::String(k), v)
            }).collect()
        ))?;

        config.file_path = file_path;
        Ok(config)
    }
}

/// Agent registry for v7 tiered architecture
pub struct AgentRegistry {
    /// Base agents directory
    agents_dir: PathBuf,

    /// Registered agents (name -> config), excludes traits
    agents: HashMap<String, AgentConfig>,

    /// Registered traits (trait_name -> config)
    traits: HashMap<String, AgentConfig>,

    /// Agents by category
    categories: HashMap<String, Vec<String>>,

    /// Agents by tier
    tier_agents: HashMap<String, Vec<String>>,

    /// Whether discovery has been run
    discovered: bool,
}

impl AgentRegistry {
    /// Create a new agent registry
    pub fn new(agents_dir: Option<PathBuf>) -> Self {
        let agents_dir = agents_dir.unwrap_or_else(|| {
            // Find SuperClaude root by looking for CLAUDE.md
            Self::find_superclaude_root()
                .map(|root| root.join("agents"))
                .unwrap_or_else(|| PathBuf::from("agents"))
        });

        Self {
            agents_dir,
            agents: HashMap::new(),
            traits: HashMap::new(),
            categories: HashMap::new(),
            tier_agents: HashMap::from([
                ("core".to_string(), Vec::new()),
                ("trait".to_string(), Vec::new()),
                ("extension".to_string(), Vec::new()),
            ]),
            discovered: false,
        }
    }

    /// Find SuperClaude root by searching upward for CLAUDE.md
    fn find_superclaude_root() -> Option<PathBuf> {
        let mut current = std::env::current_dir().ok()?;

        loop {
            if current.join("CLAUDE.md").exists() {
                return Some(current);
            }

            if !current.pop() {
                break;
            }
        }

        None
    }

    /// Discover all agents from the tiered directory structure
    pub fn discover_agents(&mut self, force: bool) -> Result<usize> {
        if self.discovered && !force {
            return Ok(self.agents.len() + self.traits.len());
        }

        self.agents.clear();
        self.categories.clear();
        self.traits.clear();
        self.tier_agents = HashMap::from([
            ("core".to_string(), Vec::new()),
            ("trait".to_string(), Vec::new()),
            ("extension".to_string(), Vec::new()),
        ]);

        let mut total = 0;

        // Discover core agents
        let core_dir = self.agents_dir.join("core");
        if core_dir.exists() {
            let count = self.discover_tiered_agents(&core_dir, "core", true)?;
            total += count;
            debug!("Discovered {} core agents", count);
        }

        // Discover traits
        let traits_dir = self.agents_dir.join("traits");
        if traits_dir.exists() {
            let count = self.discover_tiered_agents(&traits_dir, "trait", false)?;
            total += count;
            debug!("Discovered {} traits", count);
        }

        // Discover extensions
        let extensions_dir = self.agents_dir.join("extensions");
        if extensions_dir.exists() {
            let count = self.discover_tiered_agents(&extensions_dir, "extension", false)?;
            total += count;
            debug!("Discovered {} extension agents", count);
        }

        self.discovered = true;

        info!(
            "Discovered {} agents: {} core, {} traits, {} extensions",
            total,
            self.tier_agents.get("core").map(|v| v.len()).unwrap_or(0),
            self.tier_agents.get("trait").map(|v| v.len()).unwrap_or(0),
            self.tier_agents.get("extension").map(|v| v.len()).unwrap_or(0)
        );

        Ok(total)
    }

    /// Discover agents from a tiered directory
    fn discover_tiered_agents(&mut self, directory: &Path, tier: &str, is_core: bool) -> Result<usize> {
        let mut count = 0;

        for entry in WalkDir::new(directory)
            .max_depth(1)
            .into_iter()
            .filter_map(|e| e.ok())
        {
            let path = entry.path();

            // Only process .md files
            if path.extension().and_then(|s| s.to_str()) != Some("md") {
                continue;
            }

            match self.parse_agent_file(path, tier, is_core) {
                Ok(config) => {
                    let name = config.name.clone();

                    // Store agent or trait
                    if tier == "trait" {
                        self.traits.insert(name.clone(), config);
                    } else {
                        self.agents.insert(name.clone(), config.clone());

                        // Track by category
                        let category = config.category.clone();
                        self.categories
                            .entry(category)
                            .or_insert_with(Vec::new)
                            .push(name.clone());
                    }

                    // Track by tier
                    self.tier_agents
                        .entry(tier.to_string())
                        .or_insert_with(Vec::new)
                        .push(name);

                    count += 1;
                }
                Err(e) => {
                    warn!("Failed to parse agent file {:?}: {}", path, e);
                }
            }
        }

        Ok(count)
    }

    /// Parse an agent markdown file
    fn parse_agent_file(&self, path: &Path, _tier: &str, _is_core: bool) -> Result<AgentConfig> {
        let content = std::fs::read_to_string(path)
            .with_context(|| format!("Failed to read file: {:?}", path))?;

        // Extract frontmatter between --- markers (with multiline and dotall flags)
        let re = regex::Regex::new(r"(?ms)^---\s*\n(.*?)\n---\s*\n").unwrap();

        let frontmatter_str = re
            .captures(&content)
            .and_then(|caps| caps.get(1))
            .map(|m| m.as_str())
            .with_context(|| format!("No frontmatter found in {:?}", path))?;

        // Parse as YAML
        let yaml_value: serde_yaml::Value = serde_yaml::from_str(frontmatter_str)
            .with_context(|| format!("Failed to parse YAML frontmatter from {:?}", path))?;

        let frontmatter: HashMap<String, serde_yaml::Value> = match yaml_value {
            serde_yaml::Value::Mapping(map) => {
                map.into_iter()
                    .map(|(k, v)| {
                        let key = k.as_str().unwrap_or("").to_string();
                        (key, v)
                    })
                    .collect()
            }
            _ => anyhow::bail!("Frontmatter is not a mapping"),
        };

        AgentConfig::from_frontmatter(frontmatter, path.to_path_buf())
    }

    /// Get all selectable agent names (excludes traits)
    pub fn get_all_agents(&self) -> Vec<String> {
        self.agents.keys().cloned().collect()
    }

    /// Get all trait names
    pub fn get_all_traits(&self) -> Vec<String> {
        self.traits.keys().cloned().collect()
    }

    /// Get an agent by name
    pub fn get_agent(&self, name: &str) -> Option<&AgentConfig> {
        self.agents.get(name)
    }

    /// Get agent configuration by name
    pub fn get_agent_config(&self, name: &str) -> Option<&AgentConfig> {
        self.agents.get(name)
    }

    /// Get trait configuration by name
    pub fn get_trait_config(&self, trait_name: &str) -> Option<&AgentConfig> {
        self.traits.get(trait_name)
    }

    /// Get agent names for a specific tier
    pub fn get_agents_by_tier(&self, tier: &str) -> Vec<String> {
        self.tier_agents
            .get(tier)
            .cloned()
            .unwrap_or_default()
    }

    /// Get agent names for a specific category
    pub fn get_agents_by_category(&self, category: &str) -> Vec<String> {
        self.categories
            .get(category)
            .cloned()
            .unwrap_or_default()
    }

    /// Check if a trait name is valid
    pub fn is_valid_trait(&self, trait_name: &str) -> bool {
        self.traits.contains_key(trait_name)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    fn create_test_agent(dir: &Path, name: &str, tier: &str, triggers: &[&str]) -> Result<()> {
        let content = format!(
            r#"---
name: {}
description: Test agent
tier: {}
category: test
triggers: [{}]
---

# Test Agent
"#,
            name,
            tier,
            triggers.iter().map(|t| format!("\"{}\"", t)).collect::<Vec<_>>().join(", ")
        );

        fs::write(dir.join(format!("{}.md", name)), content)?;
        Ok(())
    }

    #[test]
    fn test_agent_discovery() -> Result<()> {
        let temp_dir = TempDir::new()?;
        let agents_dir = temp_dir.path();

        // Create directory structure
        fs::create_dir(agents_dir.join("core"))?;
        fs::create_dir(agents_dir.join("traits"))?;
        fs::create_dir(agents_dir.join("extensions"))?;

        // Create test agents
        create_test_agent(&agents_dir.join("core"), "test-core", "core", &["test", "core"])?;
        create_test_agent(&agents_dir.join("traits"), "test-trait", "trait", &[])?;
        create_test_agent(&agents_dir.join("extensions"), "test-ext", "extension", &["extension"])?;

        // Create registry and discover
        let mut registry = AgentRegistry::new(Some(agents_dir.to_path_buf()));
        let count = registry.discover_agents(false)?;

        assert_eq!(count, 3);
        assert_eq!(registry.get_all_agents().len(), 2); // core + extension
        assert_eq!(registry.get_all_traits().len(), 1);

        Ok(())
    }

    #[test]
    fn test_agent_retrieval() -> Result<()> {
        let temp_dir = TempDir::new()?;
        let agents_dir = temp_dir.path();

        fs::create_dir(agents_dir.join("core"))?;
        create_test_agent(&agents_dir.join("core"), "test-agent", "core", &["test"])?;

        let mut registry = AgentRegistry::new(Some(agents_dir.to_path_buf()));
        registry.discover_agents(false)?;

        let agent = registry.get_agent("test-agent");
        assert!(agent.is_some());

        let config = agent.unwrap();
        assert_eq!(config.name, "test-agent");
        assert_eq!(config.tier, "core");
        assert!(config.is_core);

        Ok(())
    }

    #[test]
    fn test_tier_filtering() -> Result<()> {
        let temp_dir = TempDir::new()?;
        let agents_dir = temp_dir.path();

        fs::create_dir(agents_dir.join("core"))?;
        fs::create_dir(agents_dir.join("extensions"))?;

        create_test_agent(&agents_dir.join("core"), "core-agent", "core", &[])?;
        create_test_agent(&agents_dir.join("extensions"), "ext-agent", "extension", &[])?;

        let mut registry = AgentRegistry::new(Some(agents_dir.to_path_buf()));
        registry.discover_agents(false)?;

        let core_agents = registry.get_agents_by_tier("core");
        assert_eq!(core_agents.len(), 1);
        assert!(core_agents.contains(&"core-agent".to_string()));

        let ext_agents = registry.get_agents_by_tier("extension");
        assert_eq!(ext_agents.len(), 1);
        assert!(ext_agents.contains(&"ext-agent".to_string()));

        Ok(())
    }
}
