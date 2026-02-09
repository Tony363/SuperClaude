//! Inventory scanner — parses agents, commands, skills, and modes from the project tree.

use std::path::Path;

use anyhow::{Context, Result};
use gray_matter::engine::YAML;
use gray_matter::Matter;

use crate::types::{Inventory, InventoryItem, InventoryKind};

/// Frontmatter from agent/trait/extension `.md` files.
#[derive(Debug, serde::Deserialize)]
struct AgentFrontmatter {
    name: String,
    #[serde(default)]
    description: String,
    #[serde(default)]
    #[allow(dead_code)]
    tier: String,
    #[serde(default)]
    category: String,
    #[serde(default)]
    triggers: Vec<String>,
    #[serde(default)]
    tools: Vec<String>,
}

/// A command entry from `commands/index.yaml`.
#[derive(Debug, serde::Deserialize)]
struct CommandEntry {
    name: String,
    #[serde(default)]
    description: String,
    #[serde(default)]
    aliases: Vec<String>,
    #[serde(default)]
    flags: Vec<String>,
    #[serde(default)]
    file: String,
}

/// Top-level structure of `commands/index.yaml`.
#[derive(Debug, serde::Deserialize)]
struct CommandsIndex {
    #[serde(default)]
    commands: Vec<CommandEntry>,
}

/// Skill frontmatter from `.claude/skills/*/SKILL.md`.
#[derive(Debug, serde::Deserialize)]
struct SkillFrontmatter {
    name: String,
    #[serde(default)]
    description: String,
}

/// Scan the entire project tree and return a complete inventory.
pub fn scan_all(project_root: &Path) -> Result<Inventory> {
    let mut items = Vec::new();

    // Agents (core/)
    scan_agent_dir(project_root, "agents/core", InventoryKind::Agent, &mut items)?;

    // Traits (traits/)
    scan_agent_dir(project_root, "agents/traits", InventoryKind::Trait, &mut items)?;

    // Extensions (extensions/)
    scan_agent_dir(project_root, "agents/extensions", InventoryKind::Extension, &mut items)?;

    // Commands
    scan_commands(project_root, &mut items)?;

    // Skills
    scan_skills(project_root, &mut items)?;

    // Modes
    scan_modes(project_root, &mut items)?;

    Ok(Inventory { items })
}

/// Parse all `.md` files in a directory that have YAML frontmatter.
fn scan_agent_dir(
    project_root: &Path,
    relative_dir: &str,
    kind: InventoryKind,
    out: &mut Vec<InventoryItem>,
) -> Result<()> {
    let dir = project_root.join(relative_dir);
    if !dir.is_dir() {
        return Ok(());
    }

    let pattern = format!("{}/*.md", dir.display());
    for entry in glob::glob(&pattern).context("glob pattern error")? {
        let path = entry.context("glob entry error")?;
        if let Some(item) = parse_agent_md(&path, &kind, project_root) {
            out.push(item);
        }
    }

    Ok(())
}

fn parse_agent_md(
    path: &Path,
    kind: &InventoryKind,
    project_root: &Path,
) -> Option<InventoryItem> {
    let content = std::fs::read_to_string(path).ok()?;
    let matter = Matter::<YAML>::new();
    let parsed = matter.parse(&content);

    let fm: AgentFrontmatter = parsed.data?.deserialize().ok()?;

    let source_file = path
        .strip_prefix(project_root)
        .unwrap_or(path)
        .to_string_lossy()
        .to_string();

    Some(InventoryItem {
        name: fm.name,
        kind: kind.clone(),
        description: fm.description,
        category: fm.category,
        triggers: fm.triggers,
        tools: fm.tools,
        aliases: Vec::new(),
        flags: Vec::new(),
        source_file,
    })
}

/// Parse `commands/index.yaml`.
fn scan_commands(project_root: &Path, out: &mut Vec<InventoryItem>) -> Result<()> {
    let index_path = project_root.join("commands/index.yaml");
    if !index_path.is_file() {
        return Ok(());
    }

    let content = std::fs::read_to_string(&index_path)
        .context("Failed to read commands/index.yaml")?;
    let index: CommandsIndex =
        serde_yaml::from_str(&content).context("Failed to parse commands/index.yaml")?;

    for cmd in index.commands {
        out.push(InventoryItem {
            name: cmd.name,
            kind: InventoryKind::Command,
            description: cmd.description,
            category: "command".to_string(),
            triggers: Vec::new(),
            tools: Vec::new(),
            aliases: cmd.aliases,
            flags: cmd.flags,
            source_file: format!("commands/{}", cmd.file),
        });
    }

    Ok(())
}

/// Scan `.claude/skills/*/SKILL.md` (skipping DEPRECATED/).
fn scan_skills(project_root: &Path, out: &mut Vec<InventoryItem>) -> Result<()> {
    let skills_dir = project_root.join(".claude/skills");
    if !skills_dir.is_dir() {
        return Ok(());
    }

    let pattern = format!("{}/*/SKILL.md", skills_dir.display());
    let matter = Matter::<YAML>::new();

    for entry in glob::glob(&pattern).context("glob pattern error")? {
        let path = entry.context("glob entry error")?;

        // Skip DEPRECATED
        if path
            .parent()
            .and_then(|p| p.file_name())
            .map(|n| n == "DEPRECATED")
            .unwrap_or(false)
        {
            continue;
        }

        let content = match std::fs::read_to_string(&path) {
            Ok(c) => c,
            Err(_) => continue,
        };

        let parsed = matter.parse(&content);
        let fm: Option<SkillFrontmatter> = parsed.data.and_then(|d| d.deserialize().ok());

        let dir_name = path
            .parent()
            .and_then(|p| p.file_name())
            .map(|n| n.to_string_lossy().to_string())
            .unwrap_or_default();

        let name = fm.as_ref().map(|f| f.name.clone()).unwrap_or_else(|| dir_name.clone());
        let description = fm.map(|f| f.description).unwrap_or_default();

        let source_file = path
            .strip_prefix(project_root)
            .unwrap_or(&path)
            .to_string_lossy()
            .to_string();

        out.push(InventoryItem {
            name,
            kind: InventoryKind::Skill,
            description,
            category: "skill".to_string(),
            triggers: Vec::new(),
            tools: Vec::new(),
            aliases: Vec::new(),
            flags: Vec::new(),
            source_file,
        });
    }

    Ok(())
}

/// Extract modes from `config/superclaud.yaml`.
fn scan_modes(project_root: &Path, out: &mut Vec<InventoryItem>) -> Result<()> {
    let config_path = project_root.join("config/superclaud.yaml");
    if !config_path.is_file() {
        return Ok(());
    }

    let content = std::fs::read_to_string(&config_path)
        .context("Failed to read config/superclaud.yaml")?;
    let value: serde_yaml::Value =
        serde_yaml::from_str(&content).context("Failed to parse config/superclaud.yaml")?;

    if let Some(modes) = value.get("modes").and_then(|m| m.get("available")) {
        if let Some(seq) = modes.as_sequence() {
            for mode in seq {
                if let Some(name) = mode.as_str() {
                    out.push(InventoryItem {
                        name: name.to_string(),
                        kind: InventoryKind::Mode,
                        description: format!("{} mode", name),
                        category: "mode".to_string(),
                        triggers: Vec::new(),
                        tools: Vec::new(),
                        aliases: Vec::new(),
                        flags: Vec::new(),
                        source_file: "config/superclaud.yaml".to_string(),
                    });
                }
            }
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    fn setup_test_project() -> TempDir {
        let tmp = TempDir::new().unwrap();
        let root = tmp.path();

        // Create agent
        let agents_dir = root.join("agents/core");
        fs::create_dir_all(&agents_dir).unwrap();
        fs::write(
            agents_dir.join("test-agent.md"),
            r#"---
name: test-agent
description: A test agent
tier: core
category: testing
triggers: [test, verify]
tools: [Read, Write]
---

# Test Agent
"#,
        )
        .unwrap();

        // Create trait
        let traits_dir = root.join("agents/traits");
        fs::create_dir_all(&traits_dir).unwrap();
        fs::write(
            traits_dir.join("test-trait.md"),
            r#"---
name: test-trait
description: A test trait
tier: trait
category: modifier
triggers: []
tools: []
---

# Test Trait
"#,
        )
        .unwrap();

        // Create commands/index.yaml
        let commands_dir = root.join("commands");
        fs::create_dir_all(&commands_dir).unwrap();
        fs::write(
            commands_dir.join("index.yaml"),
            r#"version: "1.0"
commands:
  - name: analyze
    file: analyze.md
    description: "Test analysis command"
    aliases: [check]
    flags:
      - "--deep: Deep analysis"
"#,
        )
        .unwrap();

        // Create skill
        let skill_dir = root.join(".claude/skills/sc-test");
        fs::create_dir_all(&skill_dir).unwrap();
        fs::write(
            skill_dir.join("SKILL.md"),
            r#"---
name: sc-test
description: Test skill
---

# Test Skill
"#,
        )
        .unwrap();

        // Create config with modes
        let config_dir = root.join("config");
        fs::create_dir_all(&config_dir).unwrap();
        fs::write(
            config_dir.join("superclaud.yaml"),
            r#"version: "1.0"
modes:
  default: normal
  available:
    - normal
    - brainstorming
    - task_management
"#,
        )
        .unwrap();

        tmp
    }

    #[test]
    fn test_scan_all() {
        let tmp = setup_test_project();
        let inventory = scan_all(tmp.path()).unwrap();

        assert_eq!(inventory.agents().len(), 1);
        assert_eq!(inventory.agents()[0].name, "test-agent");

        assert_eq!(inventory.traits().len(), 1);
        assert_eq!(inventory.traits()[0].name, "test-trait");

        assert_eq!(inventory.commands().len(), 1);
        assert_eq!(inventory.commands()[0].name, "analyze");

        assert_eq!(inventory.skills().len(), 1);
        assert_eq!(inventory.skills()[0].name, "sc-test");

        assert_eq!(inventory.modes().len(), 3);
    }

    #[test]
    fn test_search() {
        let tmp = setup_test_project();
        let inventory = scan_all(tmp.path()).unwrap();

        let results = inventory.search("test");
        assert!(results.len() >= 2); // test-agent, sc-test at minimum

        let results = inventory.search("analyze");
        assert_eq!(results.len(), 1);
        assert_eq!(results[0].name, "analyze");
    }
}
