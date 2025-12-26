"""Tests for SDK executor."""

import pytest

from SuperClaude.SDK.executor import (
    SDKExecutionResult,
    SDKExecutor,
    SDKExecutorConfig,
)


class MockCommand:
    """Mock command for testing."""

    def __init__(
        self,
        name: str = "test",
        arguments: list | None = None,
        parameters: dict | None = None,
        flags: dict | None = None,
    ):
        self.name = name
        self.arguments = arguments or []
        self.parameters = parameters or {}
        self.flags = flags or {}


class MockCommandContext:
    """Mock command context for testing."""

    def __init__(
        self,
        command: MockCommand | None = None,
        session_id: str = "test-session",
        cwd: str = "/test",
        requires_evidence: bool = False,
    ):
        self.command = command or MockCommand()
        self.session_id = session_id
        self.cwd = cwd
        self.requires_evidence = requires_evidence


class MockSDKClient:
    """Mock SDK client for testing."""

    def __init__(self, sdk_available: bool = True, should_fail: bool = False):
        self._sdk_available = sdk_available
        self._should_fail = should_fail
        self._messages = []

    def set_messages(self, messages: list):
        """Set messages to return from execute_with_agent."""
        self._messages = messages

    async def execute_with_agent(self, **kwargs):
        """Mock execution that yields configured messages."""
        if self._should_fail:
            raise RuntimeError("Mock SDK failure")
        for msg in self._messages:
            yield msg


class MockSDKMessage:
    """Mock SDK message."""

    def __init__(self, type: str, content: str):
        self.type = type
        self.content = content
        self.metadata = {}


class MockSelector:
    """Mock selector for testing."""

    def __init__(self, use_sdk: bool = True, confidence: float = 0.8):
        self._use_sdk = use_sdk
        self._confidence = confidence

    def select_for_sdk(self, context):
        """Return mock selection result."""
        from SuperClaude.Agents.selector import SDKSelectionResult
        from SuperClaude.SDK.adapter import SDKAgentDefinition

        sdk_def = SDKAgentDefinition(
            description="Test agent",
            prompt="You are a test agent.",
            tools=["Read"],
        )

        return SDKSelectionResult(
            agent_name="test-agent",
            confidence=self._confidence,
            use_sdk=self._use_sdk,
            sdk_definition=sdk_def if self._use_sdk else None,
            ranked_alternatives=[],
            reason="Test selection",
        )


class TestSDKExecutorConfig:
    """Tests for SDKExecutorConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = SDKExecutorConfig()

        assert config.enabled is False
        assert config.confidence_threshold == 0.5
        assert config.allowlist == set()

    def test_config_with_values(self):
        """Test configuration with values."""
        config = SDKExecutorConfig(
            enabled=True,
            confidence_threshold=0.7,
            allowlist={"analyze", "test"},
        )

        assert config.enabled is True
        assert config.confidence_threshold == 0.7
        assert "analyze" in config.allowlist
        assert "test" in config.allowlist

    def test_from_env_disabled(self, monkeypatch):
        """Test loading disabled config from env."""
        monkeypatch.delenv("SUPERCLAUDE_SDK_ENABLED", raising=False)
        monkeypatch.delenv("SUPERCLAUDE_SDK_COMMANDS", raising=False)

        config = SDKExecutorConfig.from_env()

        assert config.enabled is False
        assert config.allowlist == set()

    def test_from_env_enabled(self, monkeypatch):
        """Test loading enabled config from env."""
        monkeypatch.setenv("SUPERCLAUDE_SDK_ENABLED", "true")
        monkeypatch.setenv("SUPERCLAUDE_SDK_COMMANDS", "analyze,test,debug")

        config = SDKExecutorConfig.from_env()

        assert config.enabled is True
        assert config.allowlist == {"analyze", "test", "debug"}

    def test_from_env_empty_allowlist(self, monkeypatch):
        """Test empty allowlist means no commands allowed."""
        monkeypatch.setenv("SUPERCLAUDE_SDK_ENABLED", "true")
        monkeypatch.setenv("SUPERCLAUDE_SDK_COMMANDS", "")

        config = SDKExecutorConfig.from_env()

        assert config.enabled is True
        assert config.allowlist == set()


class TestSDKExecutionResult:
    """Tests for SDKExecutionResult."""

    def test_success_result(self):
        """Test successful execution result."""
        result = SDKExecutionResult(
            success=True,
            output={"status": "completed"},
            should_fallback=False,
            routing_decision="sdk_executed",
            agent_used="test-agent",
            confidence=0.85,
        )

        assert result.success is True
        assert result.should_fallback is False
        assert result.agent_used == "test-agent"

    def test_fallback_result(self):
        """Test fallback execution result."""
        result = SDKExecutionResult(
            success=False,
            output={},
            should_fallback=True,
            routing_decision="sdk_not_enabled",
            fallback_reason="SDK execution not enabled",
        )

        assert result.success is False
        assert result.should_fallback is True
        assert result.fallback_reason is not None


class TestSDKExecutor:
    """Tests for SDKExecutor."""

    def test_initialization(self):
        """Test executor initialization."""
        executor = SDKExecutor()

        assert executor.config is not None
        assert executor._client is None  # Lazy initialized
        assert executor._selector is None

    def test_initialization_with_config(self):
        """Test executor with custom config."""
        config = SDKExecutorConfig(enabled=True)
        executor = SDKExecutor(config=config)

        assert executor.config.enabled is True

    def test_is_command_allowed_empty_allowlist(self):
        """Test empty allowlist allows no commands."""
        config = SDKExecutorConfig(enabled=True, allowlist=set())
        executor = SDKExecutor(config=config)

        assert executor._is_command_allowed("analyze") is False
        assert executor._is_command_allowed("test") is False

    def test_is_command_allowed_with_allowlist(self):
        """Test allowlist filtering."""
        config = SDKExecutorConfig(enabled=True, allowlist={"analyze", "test"})
        executor = SDKExecutor(config=config)

        assert executor._is_command_allowed("analyze") is True
        assert executor._is_command_allowed("test") is True
        assert executor._is_command_allowed("debug") is False

    def test_build_task_from_context(self):
        """Test task string building."""
        executor = SDKExecutor()
        command = MockCommand(
            name="analyze",
            arguments=["file.py"],
            parameters={"depth": "3"},
        )
        context = MockCommandContext(command=command)

        task = executor._build_task_from_context(context)

        assert "analyze" in task
        assert "file.py" in task
        assert "depth=3" in task


class TestSDKExecutorGates:
    """Tests for SDK executor routing gates."""

    @pytest.fixture
    def enabled_config(self):
        """Create enabled config with allowlist."""
        return SDKExecutorConfig(
            enabled=True,
            confidence_threshold=0.5,
            allowlist={"test"},
        )

    @pytest.fixture
    def mock_client(self):
        """Create mock SDK client."""
        client = MockSDKClient(sdk_available=True)
        client.set_messages([MockSDKMessage("text", "Result")])
        return client

    @pytest.fixture
    def mock_selector(self):
        """Create mock selector."""
        return MockSelector(use_sdk=True, confidence=0.8)

    @pytest.mark.asyncio
    async def test_gate_disable_sdk_override(self, enabled_config, mock_client):
        """Test disable_sdk override blocks execution."""
        executor = SDKExecutor(
            client=mock_client,
            config=enabled_config,
        )
        context = MockCommandContext(command=MockCommand(name="test"))

        result = await executor.execute(context, disable_sdk=True)

        assert result.should_fallback is True
        assert result.routing_decision == "sdk_disabled_override"

    @pytest.mark.asyncio
    async def test_gate_sdk_unavailable(self, enabled_config):
        """Test SDK unavailable triggers fallback."""
        client = MockSDKClient(sdk_available=False)
        executor = SDKExecutor(
            client=client,
            config=enabled_config,
        )
        context = MockCommandContext(command=MockCommand(name="test"))

        result = await executor.execute(context)

        assert result.should_fallback is True
        assert result.routing_decision == "sdk_unavailable"

    @pytest.mark.asyncio
    async def test_gate_sdk_not_enabled(self, mock_client):
        """Test disabled config triggers fallback."""
        config = SDKExecutorConfig(enabled=False)
        executor = SDKExecutor(
            client=mock_client,
            config=config,
        )
        context = MockCommandContext(command=MockCommand(name="test"))

        result = await executor.execute(context)

        assert result.should_fallback is True
        assert result.routing_decision == "sdk_not_enabled"

    @pytest.mark.asyncio
    async def test_gate_command_not_allowed(self, enabled_config, mock_client):
        """Test command not in allowlist triggers fallback."""
        executor = SDKExecutor(
            client=mock_client,
            config=enabled_config,
        )
        # Command "debug" is not in allowlist {"test"}
        context = MockCommandContext(command=MockCommand(name="debug"))

        result = await executor.execute(context)

        assert result.should_fallback is True
        assert result.routing_decision == "command_not_allowed"

    @pytest.mark.asyncio
    async def test_gate_no_selector(self, enabled_config, mock_client):
        """Test no selector triggers fallback."""
        executor = SDKExecutor(
            client=mock_client,
            selector=None,
            config=enabled_config,
        )
        context = MockCommandContext(command=MockCommand(name="test"))

        result = await executor.execute(context)

        assert result.should_fallback is True
        assert result.routing_decision == "no_selector"

    @pytest.mark.asyncio
    async def test_gate_low_confidence(
        self, enabled_config, mock_client
    ):
        """Test low confidence triggers fallback."""
        low_confidence_selector = MockSelector(use_sdk=True, confidence=0.3)
        executor = SDKExecutor(
            client=mock_client,
            selector=low_confidence_selector,
            config=enabled_config,  # threshold is 0.5
        )
        context = MockCommandContext(command=MockCommand(name="test"))

        result = await executor.execute(context)

        assert result.should_fallback is True
        assert result.routing_decision == "low_confidence"

    @pytest.mark.asyncio
    async def test_gate_selection_declined(
        self, enabled_config, mock_client
    ):
        """Test selection declined triggers fallback."""
        declined_selector = MockSelector(use_sdk=False, confidence=0.8)
        executor = SDKExecutor(
            client=mock_client,
            selector=declined_selector,
            config=enabled_config,
        )
        context = MockCommandContext(command=MockCommand(name="test"))

        result = await executor.execute(context)

        assert result.should_fallback is True
        assert result.routing_decision == "selection_declined"


class TestSDKExecutorExecution:
    """Tests for SDK executor execution."""

    @pytest.fixture
    def enabled_config(self):
        """Create enabled config with allowlist."""
        return SDKExecutorConfig(
            enabled=True,
            confidence_threshold=0.5,
            allowlist={"test"},
        )

    @pytest.mark.asyncio
    async def test_successful_execution(self, enabled_config):
        """Test successful SDK execution."""
        client = MockSDKClient(sdk_available=True)
        client.set_messages([
            MockSDKMessage("text", "Processing..."),
            MockSDKMessage("result", "Final result"),
        ])
        selector = MockSelector(use_sdk=True, confidence=0.8)

        executor = SDKExecutor(
            client=client,
            selector=selector,
            config=enabled_config,
        )
        context = MockCommandContext(command=MockCommand(name="test"))

        result = await executor.execute(context)

        assert result.success is True
        assert result.should_fallback is False
        assert result.routing_decision == "sdk_executed"
        assert result.agent_used == "test-agent"
        assert result.confidence == 0.8

    @pytest.mark.asyncio
    async def test_execution_with_error_message(self, enabled_config):
        """Test SDK returning error message triggers fallback."""
        client = MockSDKClient(sdk_available=True)
        client.set_messages([MockSDKMessage("error", "Something went wrong")])
        selector = MockSelector(use_sdk=True, confidence=0.8)

        executor = SDKExecutor(
            client=client,
            selector=selector,
            config=enabled_config,
        )
        context = MockCommandContext(command=MockCommand(name="test"))

        result = await executor.execute(context)

        assert result.should_fallback is True
        assert result.routing_decision == "sdk_error_message"

    @pytest.mark.asyncio
    async def test_execution_exception(self, enabled_config):
        """Test SDK exception triggers fallback."""
        client = MockSDKClient(sdk_available=True, should_fail=True)
        selector = MockSelector(use_sdk=True, confidence=0.8)

        executor = SDKExecutor(
            client=client,
            selector=selector,
            config=enabled_config,
        )
        context = MockCommandContext(command=MockCommand(name="test"))

        result = await executor.execute(context)

        assert result.should_fallback is True
        assert result.routing_decision == "sdk_exception"
        assert result.error_type == "RuntimeError"

    @pytest.mark.asyncio
    async def test_force_sdk_bypasses_gates(self, enabled_config):
        """Test force_sdk bypasses config and confidence gates."""
        client = MockSDKClient(sdk_available=True)
        client.set_messages([MockSDKMessage("text", "Forced result")])
        # Low confidence selector that would normally be rejected
        selector = MockSelector(use_sdk=False, confidence=0.1)

        executor = SDKExecutor(
            client=client,
            selector=selector,
            config=enabled_config,
        )
        # Command not in allowlist
        context = MockCommandContext(command=MockCommand(name="not-allowed"))

        result = await executor.execute(context, force_sdk=True)

        # With force_sdk, should still execute (but selector returns no sdk_definition)
        # So it fails at no_sdk_definition gate
        assert result.routing_decision in ["sdk_executed", "no_sdk_definition"]


class TestSDKExecutorAggregation:
    """Tests for message aggregation."""

    def test_aggregate_result_messages(self):
        """Test aggregating result messages."""
        executor = SDKExecutor()
        messages = [
            MockSDKMessage("text", "Processing"),
            MockSDKMessage("result", "Final result"),
        ]

        output = executor._aggregate_messages(messages, "test-agent")

        assert output["status"] == "completed"
        assert output["execution_mode"] == "sdk"
        assert output["agent"] == "test-agent"
        assert output["output"] == "Final result"

    def test_aggregate_text_messages(self):
        """Test aggregating text messages when no result."""
        executor = SDKExecutor()
        messages = [
            MockSDKMessage("text", "First"),
            MockSDKMessage("text", "Last text"),
        ]

        output = executor._aggregate_messages(messages, "test-agent")

        assert output["output"] == "Last text"

    def test_aggregate_empty_messages(self):
        """Test aggregating empty message list."""
        executor = SDKExecutor()

        output = executor._aggregate_messages([], "test-agent")

        assert output["output"] == ""
        assert output["message_count"] == 0
