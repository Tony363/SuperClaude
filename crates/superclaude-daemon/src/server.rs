//! gRPC server implementation for SuperClaude service

use std::pin::Pin;

use chrono::Utc;
use dashmap::DashMap;
use futures::Stream;
use prost_types::Timestamp;
use tokio_stream::wrappers::BroadcastStream;
use tokio_stream::StreamExt;
use tonic::{Request, Response, Status};
use tracing::{info, warn};
use uuid::Uuid;

use crate::execution::{Execution, ExecutionHandle};
use superclaude_proto::*;
use superclaude_proto::super_claude_service_server::SuperClaudeService as SuperClaudeServiceTrait;

/// Default configuration values
const DEFAULT_MAX_ITERATIONS: i32 = 3;
const DEFAULT_QUALITY_THRESHOLD: f32 = 70.0;
const DEFAULT_TIMEOUT_SECONDS: f32 = 300.0;

/// The main service implementation
pub struct SuperClaudeService {
    /// Active executions by ID
    executions: DashMap<String, ExecutionHandle>,

    /// Default configuration
    default_config: parking_lot::RwLock<ExecutionConfig>,

    /// Obsidian configuration
    obsidian_config: parking_lot::RwLock<Option<ObsidianConfig>>,

    /// Daemon start time
    start_time: chrono::DateTime<Utc>,
}

impl SuperClaudeService {
    pub fn new() -> Self {
        Self {
            executions: DashMap::new(),
            default_config: parking_lot::RwLock::new(ExecutionConfig {
                max_iterations: DEFAULT_MAX_ITERATIONS,
                quality_threshold: DEFAULT_QUALITY_THRESHOLD,
                model: "sonnet".to_string(),
                timeout_seconds: DEFAULT_TIMEOUT_SECONDS,
                pal_review_enabled: true,
                min_improvement: 5.0,
            }),
            obsidian_config: parking_lot::RwLock::new(None),
            start_time: Utc::now(),
        }
    }

    fn now_timestamp() -> Option<Timestamp> {
        let now = Utc::now();
        Some(Timestamp {
            seconds: now.timestamp(),
            nanos: now.timestamp_subsec_nanos() as i32,
        })
    }
}

#[tonic::async_trait]
impl SuperClaudeServiceTrait for SuperClaudeService {
    // =========================================================================
    // Execution Lifecycle
    // =========================================================================

    async fn start_execution(
        &self,
        request: Request<StartExecutionRequest>,
    ) -> Result<Response<StartExecutionResponse>, Status> {
        let req = request.into_inner();
        let execution_id = Uuid::new_v4().to_string();

        info!(
            execution_id = %execution_id,
            task = %req.task,
            "Starting new execution"
        );

        // Merge request config with defaults
        let config = req.config.unwrap_or_else(|| self.default_config.read().clone());

        // Create execution
        let execution = Execution::new(
            execution_id.clone(),
            req.task,
            req.project_root,
            config,
        );

        let handle = execution.start().await.map_err(|e| {
            Status::internal(format!("Failed to start execution: {}", e))
        })?;

        self.executions.insert(execution_id.clone(), handle);

        Ok(Response::new(StartExecutionResponse {
            execution_id,
            state: ExecutionState::Running as i32,
            started_at: SuperClaudeService::now_timestamp(),
        }))
    }

    async fn stop_execution(
        &self,
        request: Request<StopExecutionRequest>,
    ) -> Result<Response<StopExecutionResponse>, Status> {
        let req = request.into_inner();

        info!(execution_id = %req.execution_id, "Stopping execution");

        if let Some((_, handle)) = self.executions.remove(&req.execution_id) {
            handle.stop(req.force).await;
            Ok(Response::new(StopExecutionResponse {
                success: true,
                message: "Execution stopped".to_string(),
            }))
        } else {
            Err(Status::not_found(format!(
                "Execution {} not found",
                req.execution_id
            )))
        }
    }

    async fn pause_execution(
        &self,
        request: Request<PauseExecutionRequest>,
    ) -> Result<Response<PauseExecutionResponse>, Status> {
        let req = request.into_inner();

        if let Some(handle) = self.executions.get(&req.execution_id) {
            handle.pause().await;
            Ok(Response::new(PauseExecutionResponse {
                success: true,
                message: "Execution paused".to_string(),
            }))
        } else {
            Err(Status::not_found(format!(
                "Execution {} not found",
                req.execution_id
            )))
        }
    }

    async fn resume_execution(
        &self,
        request: Request<ResumeExecutionRequest>,
    ) -> Result<Response<ResumeExecutionResponse>, Status> {
        let req = request.into_inner();

        if let Some(handle) = self.executions.get(&req.execution_id) {
            handle.resume().await;
            Ok(Response::new(ResumeExecutionResponse {
                success: true,
                message: "Execution resumed".to_string(),
            }))
        } else {
            Err(Status::not_found(format!(
                "Execution {} not found",
                req.execution_id
            )))
        }
    }

    // =========================================================================
    // Monitoring
    // =========================================================================

    async fn get_status(
        &self,
        request: Request<GetStatusRequest>,
    ) -> Result<Response<GetStatusResponse>, Status> {
        let req = request.into_inner();

        if let Some(handle) = self.executions.get(&req.execution_id) {
            let status = handle.get_status().await;
            Ok(Response::new(GetStatusResponse {
                status: Some(status),
            }))
        } else {
            Err(Status::not_found(format!(
                "Execution {} not found",
                req.execution_id
            )))
        }
    }

    async fn list_executions(
        &self,
        request: Request<ListExecutionsRequest>,
    ) -> Result<Response<ListExecutionsResponse>, Status> {
        let req = request.into_inner();

        let executions: Vec<ExecutionSummary> = self
            .executions
            .iter()
            .filter(|entry| {
                if req.include_completed {
                    true
                } else {
                    let state = entry.value().state();
                    state == ExecutionState::Running || state == ExecutionState::Pending
                }
            })
            .take(req.limit as usize)
            .map(|entry| entry.value().to_summary())
            .collect();

        Ok(Response::new(ListExecutionsResponse { executions }))
    }

    type StreamEventsStream = Pin<Box<dyn Stream<Item = Result<AgentEvent, Status>> + Send>>;

    async fn stream_events(
        &self,
        request: Request<StreamEventsRequest>,
    ) -> Result<Response<Self::StreamEventsStream>, Status> {
        let req = request.into_inner();

        if let Some(handle) = self.executions.get(&req.execution_id) {
            let receiver = handle.subscribe_events();

            // Convert broadcast receiver to stream
            let stream = BroadcastStream::new(receiver)
                .filter_map(|result| result.ok())
                .map(Ok);

            // If include_history, prepend historical events
            if req.include_history {
                let history = handle.get_event_history();
                let history_stream = tokio_stream::iter(history.into_iter().map(Ok));
                let combined = history_stream.chain(stream);
                Ok(Response::new(Box::pin(combined)))
            } else {
                Ok(Response::new(Box::pin(stream)))
            }
        } else {
            Err(Status::not_found(format!(
                "Execution {} not found",
                req.execution_id
            )))
        }
    }

    // =========================================================================
    // Configuration
    // =========================================================================

    async fn get_configuration(
        &self,
        _request: Request<GetConfigurationRequest>,
    ) -> Result<Response<GetConfigurationResponse>, Status> {
        let default_config = self.default_config.read().clone();
        let obsidian_config = self.obsidian_config.read().clone();

        Ok(Response::new(GetConfigurationResponse {
            default_config: Some(default_config),
            obsidian_config,
            available_models: vec![
                "sonnet".to_string(),
                "opus".to_string(),
                "haiku".to_string(),
            ],
        }))
    }

    async fn update_configuration(
        &self,
        request: Request<UpdateConfigurationRequest>,
    ) -> Result<Response<UpdateConfigurationResponse>, Status> {
        let req = request.into_inner();

        if let Some(config) = req.config {
            *self.default_config.write() = config;
        }

        if let Some(obsidian) = req.obsidian_config {
            *self.obsidian_config.write() = Some(obsidian);
        }

        Ok(Response::new(UpdateConfigurationResponse {
            success: true,
            message: "Configuration updated".to_string(),
        }))
    }

    // =========================================================================
    // Obsidian Integration
    // =========================================================================

    async fn list_obsidian_notes(
        &self,
        request: Request<ListObsidianNotesRequest>,
    ) -> Result<Response<ListObsidianNotesResponse>, Status> {
        let _req = request.into_inner();

        // TODO: Implement actual Obsidian vault scanning
        // For now, return empty list
        warn!("Obsidian integration not yet implemented");

        Ok(Response::new(ListObsidianNotesResponse { notes: vec![] }))
    }

    async fn get_obsidian_note(
        &self,
        request: Request<GetObsidianNoteRequest>,
    ) -> Result<Response<GetObsidianNoteResponse>, Status> {
        let req = request.into_inner();

        // TODO: Implement actual note reading
        warn!(
            path = %req.relative_path,
            "Obsidian note reading not yet implemented"
        );

        Err(Status::unimplemented("Obsidian integration not yet implemented"))
    }

    // =========================================================================
    // Interactive Input
    // =========================================================================

    async fn send_input(
        &self,
        request: Request<SendInputRequest>,
    ) -> Result<Response<SendInputResponse>, Status> {
        let req = request.into_inner();

        if let Some(handle) = self.executions.get(&req.execution_id) {
            handle.send_input(&req.input).await.map_err(|e| {
                Status::internal(format!("Failed to send input: {}", e))
            })?;
            Ok(Response::new(SendInputResponse {
                success: true,
                message: "Input sent".to_string(),
            }))
        } else {
            Err(Status::not_found(format!(
                "Execution {} not found",
                req.execution_id
            )))
        }
    }

    // =========================================================================
    // Execution Detail
    // =========================================================================

    async fn get_execution_detail(
        &self,
        request: Request<GetExecutionDetailRequest>,
    ) -> Result<Response<GetExecutionDetailResponse>, Status> {
        let req = request.into_inner();
        info!(execution_id = %req.execution_id, "GetExecutionDetail");

        if let Some(handle) = self.executions.get(&req.execution_id) {
            Ok(Response::new(handle.get_detail()))
        } else {
            Err(Status::not_found(format!(
                "Execution {} not found",
                req.execution_id
            )))
        }
    }

    // =========================================================================
    // Health Check
    // =========================================================================

    async fn ping(
        &self,
        _request: Request<PingRequest>,
    ) -> Result<Response<PingResponse>, Status> {
        let active_count = self
            .executions
            .iter()
            .filter(|e| e.value().state() == ExecutionState::Running)
            .count();

        Ok(Response::new(PingResponse {
            version: env!("CARGO_PKG_VERSION").to_string(),
            active_executions: active_count as i32,
            uptime_since: Some(Timestamp {
                seconds: self.start_time.timestamp(),
                nanos: self.start_time.timestamp_subsec_nanos() as i32,
            }),
        }))
    }
}
