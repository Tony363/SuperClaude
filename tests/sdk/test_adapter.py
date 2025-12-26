"""Tests for AgentToSDKAdapter."""

import pytest

from SuperClaude.SDK.adapter import AgentToSDKAdapter, SDKAgentDefinition


class MockAgent:
    """Mock agent for testing."""

    def __init__(
        self,
        name: str = "test-agent",
        description: str = "A test agent",
        category: str = "testing",
        tools: list | None = None,
        triggers: list | None = None,
        focus_areas: dict | None = None,
        boundaries: dict | None = None,
        mindset: str = "",
        config: dict | None = None,
    ):
        self.name = name
        self.description = description
        self.category = category
        self.tools = tools or ["Read", "Write", "Edit"]
        self.triggers = triggers or ["test", "testing"]
        self.focus_areas = focus_areas or {"testing": "unit tests"}
        self.boundaries = boundaries or {
            "will": ["run tests", "validate code"],
            "will_not": ["deploy to production"],
        }
        self.mindset = mindset
        self.config = config or {}


class TestSDKAgentDefinition:
    """Tests for SDKAgentDefinition dataclass."""

    def test_creation(self):
        """Test basic creation of SDKAgentDefinition."""
        definition = SDKAgentDefinition(
            description="Test agent",
            prompt="You are a test agent.",
            tools=["Read", "Write"],
            model="sonnet",
        )

        assert definition.description == "Test agent"
        assert definition.prompt == "You are a test agent."
        assert definition.tools == ["Read", "Write"]
        assert definition.model == "sonnet"

    def test_default_model(self):
        """Test default model is sonnet."""
        definition = SDKAgentDefinition(
            description="Test",
            prompt="Test prompt",
        )

        assert definition.model == "sonnet"

    def test_default_tools(self):
        """Test default tools is empty list."""
        definition = SDKAgentDefinition(
            description="Test",
            prompt="Test prompt",
        )

        assert definition.tools == []


class TestAgentToSDKAdapter:
    """Tests for AgentToSDKAdapter."""

    def test_creation_without_registry(self):
        """Test adapter can be created without registry."""
        adapter = AgentToSDKAdapter()
        assert adapter.registry is None

    def test_tool_mapping_known_tools(self):
        """Test mapping of known SuperClaude tools to SDK tools."""
        adapter = AgentToSDKAdapter()

        # Test direct mappings
        assert adapter._map_tools(["Read"]) == ["Read"]
        assert adapter._map_tools(["Write"]) == ["Write"]
        assert adapter._map_tools(["Edit"]) == ["Edit"]
        assert adapter._map_tools(["Bash"]) == ["Bash"]
        assert adapter._map_tools(["Glob"]) == ["Glob"]
        assert adapter._map_tools(["Grep"]) == ["Grep"]

    def test_tool_mapping_cli_tools(self):
        """Test CLI tools map to Bash."""
        adapter = AgentToSDKAdapter()

        # CLI tools should map to Bash
        tools = adapter._map_tools(["git", "npm", "pytest", "pip"])
        assert tools == ["Bash"]  # Deduplicated

    def test_tool_mapping_multiedit(self):
        """Test MultiEdit maps to Edit."""
        adapter = AgentToSDKAdapter()

        tools = adapter._map_tools(["MultiEdit"])
        assert tools == ["Edit"]

    def test_tool_mapping_mcp_passthrough(self):
        """Test MCP tools pass through unchanged."""
        adapter = AgentToSDKAdapter()

        tools = adapter._map_tools(["mcp__pal__consensus", "mcp__rube__search"])
        assert "mcp__pal__consensus" in tools
        assert "mcp__rube__search" in tools

    def test_tool_mapping_deduplication(self):
        """Test tools are deduplicated."""
        adapter = AgentToSDKAdapter()

        # Multiple tools that map to same SDK tool
        tools = adapter._map_tools(["git", "npm", "pip", "Bash"])
        assert tools == ["Bash"]

    def test_tool_mapping_unknown_tools(self):
        """Test unknown tools are skipped with logging."""
        adapter = AgentToSDKAdapter()

        tools = adapter._map_tools(["UnknownTool", "Read"])
        assert tools == ["Read"]
        assert "UnknownTool" not in tools

    def test_to_agent_definition(self):
        """Test converting agent to SDK definition."""
        adapter = AgentToSDKAdapter()
        agent = MockAgent(
            name="python-expert",
            description="Expert in Python development",
            tools=["Read", "Write", "Edit", "pytest"],
        )

        definition = adapter.to_agent_definition(agent)

        assert isinstance(definition, SDKAgentDefinition)
        assert definition.description == "Expert in Python development"
        assert "Python Expert" in definition.prompt  # Title case name
        assert "Bash" in definition.tools  # pytest maps to Bash
        assert "Read" in definition.tools
        assert "Write" in definition.tools
        assert "Edit" in definition.tools

    def test_build_agent_prompt_includes_identity(self):
        """Test prompt includes agent identity."""
        adapter = AgentToSDKAdapter()
        agent = MockAgent(name="security-agent")

        definition = adapter.to_agent_definition(agent)

        assert "You are Security Agent." in definition.prompt

    def test_build_agent_prompt_includes_mindset(self):
        """Test prompt includes behavioral mindset."""
        adapter = AgentToSDKAdapter()
        agent = MockAgent(mindset="Always prioritize security over convenience.")

        definition = adapter.to_agent_definition(agent)

        assert "## Behavioral Mindset" in definition.prompt
        assert "Always prioritize security" in definition.prompt

    def test_build_agent_prompt_includes_focus_areas(self):
        """Test prompt includes focus areas."""
        adapter = AgentToSDKAdapter()
        agent = MockAgent(
            focus_areas={
                "security": "vulnerability scanning",
                "testing": "unit tests",
            }
        )

        definition = adapter.to_agent_definition(agent)

        assert "## Focus Areas" in definition.prompt
        assert "security" in definition.prompt
        assert "testing" in definition.prompt

    def test_build_agent_prompt_includes_boundaries(self):
        """Test prompt includes boundaries."""
        adapter = AgentToSDKAdapter()
        agent = MockAgent(
            boundaries={
                "will": ["scan for vulnerabilities"],
                "will_not": ["modify production code"],
            }
        )

        definition = adapter.to_agent_definition(agent)

        assert "## What You Will Do" in definition.prompt
        assert "scan for vulnerabilities" in definition.prompt
        assert "## Boundaries" in definition.prompt
        assert "modify production code" in definition.prompt

    def test_model_selection_strategist(self):
        """Test model selection for strategist tier."""
        adapter = AgentToSDKAdapter()
        agent = MockAgent(config={"capability_tier": "strategist"})

        definition = adapter.to_agent_definition(agent)

        assert definition.model == "sonnet"

    def test_model_selection_heuristic_wrapper(self):
        """Test model selection for heuristic-wrapper tier."""
        adapter = AgentToSDKAdapter()
        agent = MockAgent(config={"capability_tier": "heuristic-wrapper"})

        definition = adapter.to_agent_definition(agent)

        assert definition.model == "haiku"

    def test_model_override(self):
        """Test model can be overridden."""
        adapter = AgentToSDKAdapter()
        agent = MockAgent(config={"capability_tier": "heuristic-wrapper"})

        definition = adapter.to_agent_definition(agent, model_override="opus")

        assert definition.model == "opus"

    def test_from_markdown_config(self):
        """Test creating definition from markdown config dict."""
        adapter = AgentToSDKAdapter()

        config = {
            "name": "test-agent",
            "description": "A test agent from config",
            "tools": ["Read", "Write", "git"],
            "behavioral_mindset": "Be thorough",
            "focus_areas": {"testing": "comprehensive tests"},
            "boundaries": {"will_not": ["skip tests"]},
            "capability_tier": "strategist",
        }

        definition = adapter.from_markdown_config(config)

        assert definition.description == "A test agent from config"
        assert "Test Agent" in definition.prompt
        assert "Be thorough" in definition.prompt
        assert "Bash" in definition.tools  # git maps to Bash
        assert definition.model == "sonnet"

    def test_build_agents_requires_registry(self):
        """Test build_agents raises without registry."""
        adapter = AgentToSDKAdapter()

        with pytest.raises(ValueError, match="Registry required"):
            adapter.build_agents("test task", {})
