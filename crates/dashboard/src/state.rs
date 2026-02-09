use crate::bridge::grpc_client::GrpcClient;
use anyhow::{Context, Result};
use parking_lot::RwLock;
use std::path::PathBuf;
use superclaude_core::types::InventoryItem;

pub struct AppState {
    pub grpc_client: RwLock<Option<GrpcClient>>,
    pub project_root: PathBuf,
    pub inventory_cache: RwLock<Option<Vec<InventoryItem>>>,
}

impl AppState {
    pub fn new(project_root: PathBuf) -> Self {
        Self {
            grpc_client: RwLock::new(None),
            project_root,
            inventory_cache: RwLock::new(None),
        }
    }

    /// Get a cloned gRPC client, connecting if necessary.
    pub async fn get_client(&self) -> Result<GrpcClient> {
        // Check if client exists
        {
            let guard = self.grpc_client.read();
            if let Some(client) = guard.as_ref() {
                return Ok(client.clone());
            }
        }

        // Connect if not connected
        let client = GrpcClient::connect("127.0.0.1:50051")
            .await
            .context("Failed to connect to daemon")?;

        // Store and return
        *self.grpc_client.write() = Some(client.clone());
        Ok(client)
    }
}
