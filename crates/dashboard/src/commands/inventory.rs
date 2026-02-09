use crate::state::AppState;
use serde::Serialize;
use superclaude_core::{inventory, types::InventoryItem};

#[derive(Debug, Clone, Serialize)]
pub struct InventoryItemDto {
    pub name: String,
    pub kind: String,
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
    #[serde(default)]
    pub source_file: String,
}

#[derive(Debug, Clone, Serialize)]
pub struct InventoryDto {
    pub items: Vec<InventoryItemDto>,
}

impl From<InventoryItem> for InventoryItemDto {
    fn from(item: InventoryItem) -> Self {
        Self {
            name: item.name,
            kind: item.kind.to_string(),
            description: item.description,
            category: item.category,
            triggers: item.triggers,
            tools: item.tools,
            aliases: item.aliases,
            flags: item.flags,
            source_file: item.source_file,
        }
    }
}

#[tauri::command]
pub async fn get_inventory(
    state: tauri::State<'_, AppState>,
) -> Result<InventoryDto, String> {
    // Check cache first
    {
        let cache = state.inventory_cache.read();
        if let Some(items) = cache.as_ref() {
            let dto_items = items.iter().map(|i| i.clone().into()).collect();
            return Ok(InventoryDto { items: dto_items });
        }
    }

    // Scan filesystem
    match inventory::scan_all(&state.project_root) {
        Ok(inv) => {
            let items = inv.items;
            // Update cache
            *state.inventory_cache.write() = Some(items.clone());

            // Convert to DTO
            let dto_items = items.into_iter().map(|i| i.into()).collect();
            Ok(InventoryDto { items: dto_items })
        }
        Err(e) => Err(format!("Failed to scan inventory: {}", e)),
    }
}

#[tauri::command]
pub async fn get_agent_config(
    state: tauri::State<'_, AppState>,
) -> Result<String, String> {
    let config_path = state.project_root.join("config/agents.yaml");
    std::fs::read_to_string(config_path)
        .map_err(|e| format!("Failed to read agents.yaml: {}", e))
}
