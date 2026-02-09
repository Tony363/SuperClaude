//! SuperClaude Daemon - Orchestration service for AI agent executions
//!
//! This daemon:
//! - Listens on Unix socket (/tmp/superclaude.sock) and TCP (127.0.0.1:50051)
//! - Manages execution lifecycle (start/stop/pause/resume)
//! - Spawns claude CLI processes for each execution
//! - Watches .superclaude_metrics/ for real-time events
//! - Streams events to connected Zed panels

mod execution;
mod metrics_watcher;
mod server;

use std::path::PathBuf;

use anyhow::Result;
use tokio::net::UnixListener;
use tokio::signal::unix::{signal, SignalKind};
use tonic::transport::Server;
use tracing::{info, warn};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

use superclaude_proto::super_claude_service_server::SuperClaudeServiceServer;
use crate::server::SuperClaudeService;

const UNIX_SOCKET_PATH: &str = "/tmp/superclaude.sock";
const TCP_ADDR: &str = "127.0.0.1:50051";

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize logging
    tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "superclaude_daemon=info,tower_http=debug".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .init();

    info!("SuperClaude Daemon starting...");

    // Create the service
    let service = SuperClaudeService::new();
    let grpc_service = SuperClaudeServiceServer::new(service);

    // Clean up stale socket
    let socket_path = PathBuf::from(UNIX_SOCKET_PATH);
    if socket_path.exists() {
        warn!("Removing stale socket at {}", UNIX_SOCKET_PATH);
        std::fs::remove_file(&socket_path)?;
    }

    // Spawn Unix socket listener
    let unix_service = grpc_service.clone();
    let unix_handle = tokio::spawn(async move {
        let uds = UnixListener::bind(UNIX_SOCKET_PATH)
            .map_err(|e| anyhow::anyhow!("Failed to bind Unix socket: {}", e))?;
        info!("Listening on Unix socket: {}", UNIX_SOCKET_PATH);

        let incoming = async_stream::stream! {
            loop {
                match uds.accept().await {
                    Ok((stream, _)) => yield Ok::<_, std::io::Error>(stream),
                    Err(e) => {
                        tracing::error!("Unix socket accept error: {}", e);
                    }
                }
            }
        };

        Server::builder()
            .add_service(unix_service)
            .serve_with_incoming(incoming)
            .await
            .map_err(|e| anyhow::anyhow!("Unix server error: {}", e))
    });

    // Spawn TCP listener
    let tcp_service = grpc_service;
    let tcp_handle = tokio::spawn(async move {
        let addr = TCP_ADDR.parse()?;
        info!("Listening on TCP: {}", TCP_ADDR);

        Server::builder()
            .add_service(tcp_service)
            .serve(addr)
            .await
            .map_err(|e| anyhow::anyhow!("TCP server error: {}", e))
    });

    // Wait for shutdown signal (SIGTERM or SIGINT)
    // Use Unix signals directly - tokio::signal::ctrl_c() can resolve
    // immediately in non-interactive/backgrounded contexts
    let mut sigterm = signal(SignalKind::terminate())?;
    let mut sigint = signal(SignalKind::interrupt())?;

    info!("SuperClaude Daemon ready. Send SIGTERM or SIGINT to stop.");

    // Wait for shutdown signal. TCP failure is non-fatal — the Unix socket
    // is the primary transport and the daemon keeps running without TCP.
    tokio::select! {
        _ = sigterm.recv() => {
            info!("SIGTERM received, shutting down");
        }
        _ = sigint.recv() => {
            info!("SIGINT received, shutting down");
        }
        result = unix_handle => {
            match result {
                Ok(Err(e)) => tracing::error!("Unix server error: {:?}", e),
                Err(e) => tracing::error!("Unix server task panicked: {:?}", e),
                _ => {}
            }
        }
        result = tcp_handle => {
            match result {
                Ok(Err(e)) => warn!("TCP server failed (non-fatal, Unix socket still active): {e}"),
                Err(e) => warn!("TCP server task panicked (non-fatal): {e}"),
                _ => {}
            }
            // TCP failed but Unix socket is still running — wait for signal or Unix failure
            tokio::select! {
                _ = sigterm.recv() => {
                    info!("SIGTERM received, shutting down");
                }
                _ = sigint.recv() => {
                    info!("SIGINT received, shutting down");
                }
            }
        }
    }

    // Cleanup
    if socket_path.exists() {
        std::fs::remove_file(&socket_path)?;
    }

    info!("SuperClaude Daemon stopped");
    Ok(())
}
