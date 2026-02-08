use crate::bridge::grpc_client::GrpcClient;
use crate::state::AppState;
use serde::Serialize;

#[derive(Debug, Serialize)]
pub struct DaemonStatus {
    pub online: bool,
    pub version: String,
    pub active_executions: i32,
}

#[tauri::command]
pub async fn ping_daemon(state: tauri::State<'_, AppState>) -> Result<DaemonStatus, String> {
    // Try to connect if not already connected
    let needs_connect = {
        let client_guard = state.grpc_client.read();
        client_guard.is_none()
    };

    if needs_connect {
        match GrpcClient::connect("127.0.0.1:50051").await {
            Ok(client) => {
                *state.grpc_client.write() = Some(client);
            }
            Err(_e) => {
                return Ok(DaemonStatus {
                    online: false,
                    version: String::new(),
                    active_executions: 0,
                });
            }
        }
    }

    // Clone the client to avoid holding the lock across await
    let mut client = {
        let client_guard = state.grpc_client.read();
        match client_guard.as_ref() {
            Some(c) => c.clone(),
            None => {
                return Ok(DaemonStatus {
                    online: false,
                    version: String::new(),
                    active_executions: 0,
                });
            }
        }
    };

    // Ping the daemon
    match client.ping().await {
        Ok(response) => {
            // Update the client back to state
            *state.grpc_client.write() = Some(client);
            Ok(DaemonStatus {
                online: true,
                version: response.version,
                active_executions: response.active_executions,
            })
        }
        Err(_e) => {
            // Connection failed, clear client
            *state.grpc_client.write() = None;
            Ok(DaemonStatus {
                online: false,
                version: String::new(),
                active_executions: 0,
            })
        }
    }
}

#[tauri::command]
pub async fn get_daemon_config(
    state: tauri::State<'_, AppState>,
) -> Result<String, String> {
    // Clone the client to avoid holding the lock across await
    let mut client = {
        let client_guard = state.grpc_client.read();
        match client_guard.as_ref() {
            Some(c) => c.clone(),
            None => return Err("Not connected to daemon".to_string()),
        }
    };

    match client.get_configuration().await {
        Ok(config) => {
            // Update the client back to state
            *state.grpc_client.write() = Some(client);
            Ok(format!("{:?}", config))
        }
        Err(e) => Err(format!("Failed to get config: {}", e)),
    }
}
