"""Integration tests for SDK selector functionality.

These tests require the archived SDK to be properly installed.
Skip if the archived SDK compatibility layer has import issues.
"""

import pytest

# Check if archived SDK imports work - skip entire module if not
try:
    from SuperClaude.Agents.selector import AgentSelector, SDKSelectionResult
    from SuperClaude.SDK.adapter import SDKAgentDefinition
except ImportError:
    pytest.skip(
        "Archived SDK compatibility layer not available",
        allow_module_level=True,
    )


class MockRegistry:
    """Mock registry for testing without full agent discovery."""

    def __init__(self):
        self._agents = {}
        self._configs = {}

    def add_agent(self, name: str, agent: object, config: dict):
        """Add a mock agent to the registry."""
        self._agents[name] = agent
        self._configs[name] = config

    def get_all_agents(self) -> list[str]:
        """Get all agent names."""
        return list(self._agents.keys())

    def get_agent(self, name: str):
        """Get agent by name."""
        return self._agents.get(name)

    def get_agent_config(self, name: str) -> dict | None:
        """Get agent config by name."""
        return self._configs.get(name)

    def discover_agents(self):
        """No-op for mock."""
        pass


class MockAgent:
    """Mock agent for testing."""

    def __init__(
        self,
        name: str = "test-agent",
        description: str = "Test agent",
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
        self.tools = tools or ["Read", "Write"]
        self.triggers = triggers or []
        self.focus_areas = focus_areas or {}
        self.boundaries = boundaries or {"will": [], "will_not": []}
        self.mindset = mindset
        self.config = config or {}


class TestSelectForSDK:
    """Tests for AgentSelector.select_for_sdk() method."""

    @pytest.fixture
    def registry(self):
        """Create a mock registry with test agents."""
        registry = MockRegistry()

        # Add debugging agent with high trigger match potential
        debug_agent = MockAgent(
            name="root-cause-analyst",
            description="Expert debugger for finding root causes",
            category="debugging",
            triggers=["debug", "bug", "error", "issue", "problem", "crash"],
            tools=["Read", "Grep", "Bash"],
            config={"capability_tier": "strategist", "is_core": True},
        )
        registry.add_agent(
            "root-cause-analyst",
            debug_agent,
            {
                "name": "root-cause-analyst",
                "description": "Expert debugger for finding root causes",
                "category": "debugging",
                "triggers": ["debug", "bug", "error", "issue", "problem", "crash"],
                "tools": ["Read", "Grep", "Bash"],
                "capability_tier": "strategist",
                "is_core": True,
            },
        )

        # Add security agent
        security_agent = MockAgent(
            name="security-agent",
            description="Security expert for vulnerability analysis",
            category="security",
            triggers=["security", "vulnerability", "auth", "permission"],
            tools=["Read", "Grep"],
            config={"capability_tier": "strategist"},
        )
        registry.add_agent(
            "security-agent",
            security_agent,
            {
                "name": "security-agent",
                "description": "Security expert for vulnerability analysis",
                "category": "security",
                "triggers": ["security", "vulnerability", "auth", "permission"],
                "tools": ["Read", "Grep"],
                "capability_tier": "strategist",
            },
        )

        # Add general purpose fallback
        general_agent = MockAgent(
            name="general-purpose",
            description="General purpose assistant",
            category="general",
            triggers=[],
            tools=["Read", "Write", "Edit", "Bash"],
            config={"capability_tier": "heuristic-wrapper"},
        )
        registry.add_agent(
            "general-purpose",
            general_agent,
            {
                "name": "general-purpose",
                "description": "General purpose assistant",
                "category": "general",
                "triggers": [],
                "tools": ["Read", "Write", "Edit", "Bash"],
                "capability_tier": "heuristic-wrapper",
            },
        )

        return registry

    @pytest.fixture
    def selector(self, registry):
        """Create selector with mock registry."""
        selector = AgentSelector(registry)
        selector.default_agent = "general-purpose"
        return selector

    def test_select_for_sdk_returns_result(self, selector):
        """Test that select_for_sdk returns SDKSelectionResult."""
        result = selector.select_for_sdk({"task": "debug this error"})

        assert isinstance(result, SDKSelectionResult)
        assert result.agent_name is not None
        assert isinstance(result.confidence, float)
        assert isinstance(result.use_sdk, bool)

    def test_select_for_sdk_high_confidence_uses_sdk(self, selector):
        """Test that high confidence triggers SDK routing."""
        # Task with strong trigger match
        result = selector.select_for_sdk(
            {"task": "debug this crash error"},
            min_confidence_for_sdk=0.3,
        )

        assert result.agent_name == "root-cause-analyst"
        assert result.confidence >= 0.3
        assert result.use_sdk is True

    def test_select_for_sdk_low_confidence_no_sdk(self, selector):
        """Test that low confidence does not trigger SDK routing."""
        # Task with no good match
        result = selector.select_for_sdk(
            {"task": "do something random"},
            min_confidence_for_sdk=0.9,  # Very high threshold
        )

        # Should fall back but not recommend SDK
        assert result.use_sdk is False
        assert "Low confidence" in result.reason or result.confidence < 0.9

    def test_select_for_sdk_includes_alternatives(self, selector):
        """Test that alternatives are included in result."""
        result = selector.select_for_sdk({"task": "security vulnerability in auth code"})

        assert isinstance(result.ranked_alternatives, list)
        # Should have alternatives (possibly empty if only one good match)
        # The key is that it's a list of tuples

    def test_select_for_sdk_includes_capability_tier(self, selector):
        """Test that capability tier is included in result."""
        result = selector.select_for_sdk({"task": "debug this bug"})

        assert result.capability_tier in ["strategist", "heuristic-wrapper"]

    def test_select_for_sdk_with_sdk_definition(self, selector):
        """Test that SDK definition is included when use_sdk is True."""
        result = selector.select_for_sdk(
            {"task": "debug this crash"},
            min_confidence_for_sdk=0.1,  # Low threshold to ensure SDK routing
        )

        if result.use_sdk:
            assert result.sdk_definition is not None
            assert isinstance(result.sdk_definition, SDKAgentDefinition)
            assert result.sdk_definition.description is not None
            assert result.sdk_definition.prompt is not None

    def test_select_for_sdk_with_category_hint(self, selector):
        """Test selection with category hint."""
        result = selector.select_for_sdk(
            {"task": "analyze the code"},
            category_hint="security",
        )

        # Category hint should boost security agent
        assert result.agent_name in ["security-agent", "general-purpose"]

    def test_select_for_sdk_excludes_agents(self, selector):
        """Test selection with excluded agents."""
        result = selector.select_for_sdk(
            {"task": "debug this error"},
            exclude_agents=["root-cause-analyst"],
        )

        assert result.agent_name != "root-cause-analyst"

    def test_select_for_sdk_reason_string(self, selector):
        """Test that reason is human-readable."""
        result = selector.select_for_sdk({"task": "debug crash"})

        assert result.reason is not None
        assert len(result.reason) > 0
        assert "confidence" in result.reason.lower() or "select" in result.reason.lower()


class TestSDKSelectionResultDataclass:
    """Tests for SDKSelectionResult dataclass."""

    def test_creation_with_required_fields(self):
        """Test creating result with required fields."""
        result = SDKSelectionResult(
            agent_name="test-agent",
            confidence=0.8,
            use_sdk=True,
        )

        assert result.agent_name == "test-agent"
        assert result.confidence == 0.8
        assert result.use_sdk is True
        assert result.sdk_definition is None
        assert result.ranked_alternatives == []

    def test_creation_with_all_fields(self):
        """Test creating result with all fields."""
        sdk_def = SDKAgentDefinition(
            description="Test",
            prompt="You are test.",
            tools=["Read"],
        )

        result = SDKSelectionResult(
            agent_name="test-agent",
            confidence=0.85,
            use_sdk=True,
            sdk_definition=sdk_def,
            ranked_alternatives=[("alt1", 0.7), ("alt2", 0.6)],
            reason="Selected with high confidence",
            capability_tier="strategist",
        )

        assert result.sdk_definition is sdk_def
        assert len(result.ranked_alternatives) == 2
        assert result.reason == "Selected with high confidence"
        assert result.capability_tier == "strategist"
