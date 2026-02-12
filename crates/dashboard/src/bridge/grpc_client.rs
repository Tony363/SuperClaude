use superclaude_proto::super_claude_service_client::SuperClaudeServiceClient;
use superclaude_proto::*;
use tonic::transport::Channel;
use tonic::Streaming;
use anyhow::Result;

#[derive(Clone)]
pub struct GrpcClient {
    client: SuperClaudeServiceClient<Channel>,
}

impl GrpcClient {
    pub async fn connect(addr: &str) -> Result<Self> {
        let channel = Channel::from_shared(format!("http://{}", addr))?
            .connect()
            .await?;
        
        Ok(Self {
            client: SuperClaudeServiceClient::new(channel),
        })
    }

    pub async fn ping(&mut self) -> Result<superclaude_proto::PingResponse> {
        let request = tonic::Request::new(superclaude_proto::PingRequest {});
        let response = self.client.ping(request).await?;
        Ok(response.into_inner())
    }

    pub async fn get_configuration(&mut self) -> Result<GetConfigurationResponse> {
        let request = tonic::Request::new(GetConfigurationRequest {});
        let response = self.client.get_configuration(request).await?;
        Ok(response.into_inner())
    }

    pub async fn start_execution(&mut self, req: StartExecutionRequest) -> Result<StartExecutionResponse> {
        let response = self.client.start_execution(tonic::Request::new(req)).await?;
        Ok(response.into_inner())
    }

    pub async fn stop_execution(&mut self, req: StopExecutionRequest) -> Result<StopExecutionResponse> {
        let response = self.client.stop_execution(tonic::Request::new(req)).await?;
        Ok(response.into_inner())
    }

    pub async fn pause_execution(&mut self, req: PauseExecutionRequest) -> Result<PauseExecutionResponse> {
        let response = self.client.pause_execution(tonic::Request::new(req)).await?;
        Ok(response.into_inner())
    }

    pub async fn resume_execution(&mut self, req: ResumeExecutionRequest) -> Result<ResumeExecutionResponse> {
        let response = self.client.resume_execution(tonic::Request::new(req)).await?;
        Ok(response.into_inner())
    }

    pub async fn list_executions(&mut self, req: ListExecutionsRequest) -> Result<ListExecutionsResponse> {
        let response = self.client.list_executions(tonic::Request::new(req)).await?;
        Ok(response.into_inner())
    }

    pub async fn stream_events(&mut self, req: StreamEventsRequest) -> Result<Streaming<AgentEvent>> {
        let response = self.client.stream_events(tonic::Request::new(req)).await?;
        Ok(response.into_inner())
    }

    pub async fn get_execution_detail(&mut self, req: GetExecutionDetailRequest) -> Result<GetExecutionDetailResponse> {
        let response = self.client.get_execution_detail(tonic::Request::new(req)).await?;
        Ok(response.into_inner())
    }

    pub async fn send_input(&mut self, req: SendInputRequest) -> Result<SendInputResponse> {
        let response = self.client.send_input(tonic::Request::new(req)).await?;
        Ok(response.into_inner())
    }
}
