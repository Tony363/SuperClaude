//! Core domain types shared across SuperClaude crates.

use serde::{Deserialize, Serialize};

/// Kind of inventory item.
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum InventoryKind {
    Agent,
    Trait,
    Extension,
    Command,
    Skill,
    Mode,
}

impl std::fmt::Display for InventoryKind {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            InventoryKind::Agent => write!(f, "agent"),
            InventoryKind::Trait => write!(f, "trait"),
            InventoryKind::Extension => write!(f, "extension"),
            InventoryKind::Command => write!(f, "command"),
            InventoryKind::Skill => write!(f, "skill"),
            InventoryKind::Mode => write!(f, "mode"),
        }
    }
}

/// A single entry in the feature inventory.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct InventoryItem {
    pub name: String,
    pub kind: InventoryKind,
    pub description: String,
    #[serde(default)]
    pub category: String,
    #[serde(default)]
    pub triggers: Vec<String>,
    #[serde(default)]
    pub tools: Vec<String>,
    #[serde(default)]
    pub aliases: Vec<String>,
    #[serde(default)]
    pub flags: Vec<String>,
    /// Source file relative to project root.
    #[serde(default)]
    pub source_file: String,
}

/// Complete inventory of all SuperClaude features.
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct Inventory {
    pub items: Vec<InventoryItem>,
}

impl Inventory {
    pub fn agents(&self) -> Vec<&InventoryItem> {
        self.items.iter().filter(|i| i.kind == InventoryKind::Agent).collect()
    }

    pub fn traits(&self) -> Vec<&InventoryItem> {
        self.items.iter().filter(|i| i.kind == InventoryKind::Trait).collect()
    }

    pub fn extensions(&self) -> Vec<&InventoryItem> {
        self.items.iter().filter(|i| i.kind == InventoryKind::Extension).collect()
    }

    pub fn commands(&self) -> Vec<&InventoryItem> {
        self.items.iter().filter(|i| i.kind == InventoryKind::Command).collect()
    }

    pub fn skills(&self) -> Vec<&InventoryItem> {
        self.items.iter().filter(|i| i.kind == InventoryKind::Skill).collect()
    }

    pub fn modes(&self) -> Vec<&InventoryItem> {
        self.items.iter().filter(|i| i.kind == InventoryKind::Mode).collect()
    }

    pub fn search(&self, query: &str) -> Vec<&InventoryItem> {
        let q = query.to_lowercase();
        self.items
            .iter()
            .filter(|item| {
                item.name.to_lowercase().contains(&q)
                    || item.description.to_lowercase().contains(&q)
                    || item.triggers.iter().any(|t| t.to_lowercase().contains(&q))
                    || item.category.to_lowercase().contains(&q)
            })
            .collect()
    }
}

/// A single metric event read from JSONL.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MetricEvent {
    pub event_type: String,
    pub timestamp: Option<String>,
    #[serde(default)]
    pub execution_id: String,
    #[serde(default)]
    pub session_id: String,
    /// All remaining fields as a JSON value.
    #[serde(flatten)]
    pub data: serde_json::Value,
}

/// Parsed SuperClaude main configuration (from config/superclaud.yaml).
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SuperClaudeConfig {
    #[serde(default)]
    pub version: String,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub modes: ModesConfig,
    #[serde(default)]
    pub quality: QualityConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ModesConfig {
    #[serde(default)]
    pub default: String,
    #[serde(default)]
    pub available: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct QualityConfig {
    #[serde(default)]
    pub enabled: bool,
    #[serde(default)]
    pub default_threshold: f64,
    #[serde(default)]
    pub max_iterations: u32,
}
