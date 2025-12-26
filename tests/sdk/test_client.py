"""Tests for SuperClaudeSDKClient."""

from SuperClaude.SDK.client import (
    ExecutionResult,
    SDKMessage,
    SDKOptions,
    SuperClaudeSDKClient,
)


class TestSDKMessage:
    """Tests for SDKMessage dataclass."""

    def test_creation(self):
        """Test basic message creation."""
        msg = SDKMessage(
            type="text",
            content="Hello, world!",
        )

        assert msg.type == "text"
        assert msg.content == "Hello, world!"
        assert msg.metadata == {}

    def test_with_metadata(self):
        """Test message with metadata."""
        msg = SDKMessage(
            type="tool_use",
            content={"tool": "Read"},
            metadata={"session_id": "test-123"},
        )

        assert msg.type == "tool_use"
        assert msg.metadata["session_id"] == "test-123"


class TestSDKOptions:
    """Tests for SDKOptions dataclass."""

    def test_defaults(self):
        """Test default option values."""
        options = SDKOptions()

        assert options.model == "sonnet"
        assert options.max_turns == 50
        assert options.timeout_seconds == 300
        assert options.permission_mode == "default"
        assert options.allowed_tools is None
        assert options.session_id is None

    def test_custom_options(self):
        """Test custom option values."""
        options = SDKOptions(
            model="opus",
            allowed_tools=["Read", "Write"],
            max_turns=100,
            permission_mode="acceptEdits",
            session_id="custom-session",
        )

        assert options.model == "opus"
        assert options.allowed_tools == ["Read", "Write"]
        assert options.max_turns == 100
        assert options.permission_mode == "acceptEdits"
        assert options.session_id == "custom-session"


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_success_result(self):
        """Test successful execution result."""
        result = ExecutionResult(
            success=True,
            messages=[SDKMessage(type="text", content="Done!")],
            session_id="session-123",
            cost={"input_tokens": 100, "output_tokens": 50},
            evidence={"files_written": 1},
            quality_score=85.0,
        )

        assert result.success is True
        assert len(result.messages) == 1
        assert result.error is None

    def test_error_result(self):
        """Test error execution result."""
        result = ExecutionResult(
            success=False,
            messages=[],
            session_id=None,
            cost=None,
            evidence=None,
            quality_score=None,
            error="SDK not installed",
        )

        assert result.success is False
        assert result.error == "SDK not installed"


class TestSuperClaudeSDKClient:
    """Tests for SuperClaudeSDKClient."""

    def test_initialization(self):
        """Test client initialization."""
        client = SuperClaudeSDKClient()

        assert client.registry is None
        assert client.selector is None
        assert client.quality_scorer is None
        assert isinstance(client.default_options, SDKOptions)

    def test_initialization_with_options(self):
        """Test client initialization with custom options."""
        custom_options = SDKOptions(model="opus")
        client = SuperClaudeSDKClient(default_options=custom_options)

        assert client.default_options.model == "opus"

    def test_sdk_availability_check(self):
        """Test SDK availability is checked."""
        client = SuperClaudeSDKClient()

        # Will be False unless claude-agent-sdk is installed
        assert isinstance(client._sdk_available, bool)

    def test_generate_session_id(self):
        """Test session ID generation."""
        client = SuperClaudeSDKClient()

        session_id = client._generate_session_id()

        assert session_id.startswith("sc-")
        assert len(session_id) == 15  # "sc-" + 12 hex chars

    def test_generate_unique_session_ids(self):
        """Test session IDs are unique."""
        client = SuperClaudeSDKClient()

        ids = [client._generate_session_id() for _ in range(100)]

        assert len(set(ids)) == 100  # All unique


class TestClientPromptBuilding:
    """Tests for prompt building methods."""

    def test_build_enhanced_prompt_basic(self):
        """Test basic prompt enhancement."""
        from SuperClaude.SDK.adapter import SDKAgentDefinition

        client = SuperClaudeSDKClient()
        agent_def = SDKAgentDefinition(
            description="Test agent",
            prompt="You are a helpful agent.",
            tools=["Read"],
        )

        prompt = client._build_enhanced_prompt(
            task="Fix the bug",
            agent_def=agent_def,
            context={},
        )

        assert "You are a helpful agent." in prompt
        assert "## Task" in prompt
        assert "Fix the bug" in prompt

    def test_build_enhanced_prompt_with_context(self):
        """Test prompt enhancement with context."""
        from SuperClaude.SDK.adapter import SDKAgentDefinition

        client = SuperClaudeSDKClient()
        agent_def = SDKAgentDefinition(
            description="Test agent",
            prompt="You are a helpful agent.",
            tools=["Read"],
        )

        prompt = client._build_enhanced_prompt(
            task="Fix the bug",
            agent_def=agent_def,
            context={
                "cwd": "/project",
                "files": ["auth.py", "test_auth.py"],
            },
        )

        assert "/project" in prompt
        assert "auth.py" in prompt

    def test_build_orchestrator_prompt(self):
        """Test orchestrator prompt for multi-agent execution."""
        from SuperClaude.SDK.adapter import SDKAgentDefinition

        client = SuperClaudeSDKClient()
        agents = {
            "security-agent": SDKAgentDefinition(
                description="Security expert",
                prompt="Check for vulnerabilities",
                tools=["Read"],
            ),
            "test-agent": SDKAgentDefinition(
                description="Test expert",
                prompt="Run tests",
                tools=["Bash"],
            ),
        }

        prompt = client._build_orchestrator_prompt(
            task="Review the code",
            agents=agents,
            context={},
        )

        assert "orchestrator" in prompt.lower()
        assert "security-agent" in prompt
        assert "test-agent" in prompt
        assert "Security expert" in prompt
        assert "Test expert" in prompt


class TestClientMessageConversion:
    """Tests for message conversion."""

    def test_convert_message_text(self):
        """Test converting text message."""

        class MockSDKMessage:
            type = "text"
            content = "Hello!"

        client = SuperClaudeSDKClient()
        result = client._convert_message(MockSDKMessage())

        assert result.type == "text"
        assert result.content == "Hello!"

    def test_convert_message_with_text_attr(self):
        """Test converting message with text attribute."""

        class MockSDKMessage:
            type = "text"
            text = "Hello via text!"

        client = SuperClaudeSDKClient()
        result = client._convert_message(MockSDKMessage())

        assert result.content == "Hello via text!"

    def test_convert_message_with_metadata(self):
        """Test converting message with tool metadata."""

        class MockSDKMessage:
            type = "tool_use"
            content = {"action": "read"}
            tool_name = "Read"
            session_id = "session-123"

        client = SuperClaudeSDKClient()
        result = client._convert_message(MockSDKMessage())

        assert result.type == "tool_use"
        assert result.metadata["tool_name"] == "Read"
        assert result.metadata["session_id"] == "session-123"


class TestClientHookConversion:
    """Tests for hook conversion."""

    def test_convert_hooks(self):
        """Test converting CompositeHooks to SDK format."""
        from SuperClaude.SDK.hooks import CompositeHooks, QualityHooks

        client = SuperClaudeSDKClient()
        composite = CompositeHooks([QualityHooks()])

        sdk_hooks = client._convert_hooks(composite)

        # Should have the expected methods
        assert hasattr(sdk_hooks, "pre_tool_use")
        assert hasattr(sdk_hooks, "post_tool_use")
        assert hasattr(sdk_hooks, "session_start")
        assert hasattr(sdk_hooks, "session_end")

    def test_converted_hooks_delegate(self):
        """Test converted hooks delegate to composite."""
        from SuperClaude.SDK.hooks import BaseHook, CompositeHooks

        class TrackingHook(BaseHook):
            def __init__(self):
                self.pre_called = False
                self.post_called = False

            def pre_tool_use(self, tool_name, tool_input):
                self.pre_called = True
                return None

            def post_tool_use(self, tool_name, tool_input, tool_output):
                self.post_called = True

        tracking = TrackingHook()
        client = SuperClaudeSDKClient()
        composite = CompositeHooks([tracking])

        sdk_hooks = client._convert_hooks(composite)

        sdk_hooks.pre_tool_use("Read", {"file_path": "test.py"})
        sdk_hooks.post_tool_use("Read", {"file_path": "test.py"}, "content")

        assert tracking.pre_called
        assert tracking.post_called


class TestClientIntegration:
    """Integration tests for SuperClaudeSDKClient."""

    def test_get_session_evidence_no_session(self):
        """Test getting evidence for non-existent session."""
        client = SuperClaudeSDKClient()

        evidence = client.get_session_evidence("non-existent")

        assert evidence is None
