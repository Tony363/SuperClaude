//! Configuration file parsers for SuperClaude YAML config.

use std::path::Path;

use anyhow::{Context, Result};

use crate::types::SuperClaudeConfig;

/// Load the main SuperClaude configuration from `config/superclaud.yaml`.
pub fn load_config(project_root: &Path) -> Result<SuperClaudeConfig> {
    let config_path = project_root.join("config/superclaud.yaml");
    if !config_path.is_file() {
        return Ok(SuperClaudeConfig::default());
    }

    let content = std::fs::read_to_string(&config_path)
        .context("Failed to read config/superclaud.yaml")?;
    let config: SuperClaudeConfig =
        serde_yaml::from_str(&content).context("Failed to parse config/superclaud.yaml")?;

    Ok(config)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use tempfile::TempDir;

    #[test]
    fn test_load_config() {
        let tmp = TempDir::new().unwrap();
        let config_dir = tmp.path().join("config");
        fs::create_dir_all(&config_dir).unwrap();
        fs::write(
            config_dir.join("superclaud.yaml"),
            r#"
version: "7.0.0"
name: SuperClaude Framework
modes:
  default: normal
  available:
    - normal
    - brainstorming
quality:
  enabled: true
  default_threshold: 70.0
  max_iterations: 5
"#,
        )
        .unwrap();

        let config = load_config(tmp.path()).unwrap();
        assert_eq!(config.version, "7.0.0");
        assert_eq!(config.modes.available.len(), 2);
        assert!(config.quality.enabled);
    }

    #[test]
    fn test_load_config_missing() {
        let tmp = TempDir::new().unwrap();
        let config = load_config(tmp.path()).unwrap();
        assert_eq!(config.version, "");
    }
}
