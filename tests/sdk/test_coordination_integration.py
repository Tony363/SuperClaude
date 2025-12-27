"""Integration tests for SDK coordination functionality.

These tests require the archived SDK to be properly installed.
Skip if the archived SDK compatibility layer has import issues.
"""

import pytest

# Check if archived SDK imports work - skip entire module if not
try:
    from SuperClaude.Agents.coordination import (
        CoordinationManager,
        ExecutionContext,
        SDKDelegationValidation,
    )
    from SuperClaude.SDK.adapter import SDKAgentDefinition
except ImportError:
    pytest.skip(
        "Archived SDK compatibility layer not available",
        allow_module_level=True,
    )


class MockRegistry:
    """Mock registry for testing."""

    def __init__(self):
        self._agents = {}
        self._configs = {}

    def add_agent(self, name: str, agent: object, config: dict):
        """Add a mock agent."""
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

    def execute(self, context: dict) -> dict:
        """Mock execution."""
        return {"success": True, "output": "Mock result"}


class MockSelector:
    """Mock selector for testing."""

    def __init__(self, registry):
        self.registry = registry

    def select_agent(self, context, category_hint=None, exclude_agents=None):
        """Mock agent selection."""
        agents = self.registry.get_all_agents()
        if exclude_agents:
            agents = [a for a in agents if a not in exclude_agents]
        if agents:
            return [(agents[0], 0.8)]
        return []


class MockLoader:
    """Mock loader for testing."""

    def __init__(self, registry):
        self.registry = registry

    def load_agent(self, name: str):
        """Load agent by name."""
        return self.registry.get_agent(name)


class TestValidateSDKDelegation:
    """Tests for CoordinationManager.validate_sdk_delegation() method."""

    @pytest.fixture
    def registry(self):
        """Create mock registry with test agents."""
        registry = MockRegistry()

        # Add test agents
        for name in ["agent-a", "agent-b", "agent-c", "general-purpose"]:
            agent = MockAgent(
                name=name,
                description=f"Test agent {name}",
                tools=["Read", "Write"],
            )
            registry.add_agent(
                name,
                agent,
                {
                    "name": name,
                    "description": f"Test agent {name}",
                    "tools": ["Read", "Write"],
                    "capability_tier": "heuristic-wrapper",
                },
            )

        return registry

    @pytest.fixture
    def coordinator(self, registry):
        """Create coordinator with mocks."""
        selector = MockSelector(registry)
        loader = MockLoader(registry)
        return CoordinationManager(registry, selector, loader)

    def test_validate_returns_validation_result(self, coordinator):
        """Test that validate_sdk_delegation returns SDKDelegationValidation."""
        result = coordinator.validate_sdk_delegation(None, "agent-a")

        assert isinstance(result, SDKDelegationValidation)
        assert result.current_depth >= 0
        assert result.remaining_depth >= 0

    def test_validate_allows_valid_delegation(self, coordinator):
        """Test that valid delegation is allowed."""
        result = coordinator.validate_sdk_delegation(None, "agent-a")

        assert result.allowed is True
        assert result.delegate_to == "agent-a"
        assert "allowed" in result.reason.lower()

    def test_validate_includes_sdk_definition(self, coordinator):
        """Test that SDK definition is included when requested."""
        result = coordinator.validate_sdk_delegation(None, "agent-a", include_sdk_definition=True)

        assert result.allowed is True
        assert result.sdk_compatible is True
        assert result.sdk_definition is not None
        assert isinstance(result.sdk_definition, SDKAgentDefinition)

    def test_validate_without_sdk_definition(self, coordinator):
        """Test validation without SDK definition."""
        result = coordinator.validate_sdk_delegation(None, "agent-a", include_sdk_definition=False)

        assert result.allowed is True
        assert result.sdk_definition is None

    def test_validate_rejects_nonexistent_agent(self, coordinator):
        """Test that nonexistent agent is rejected."""
        result = coordinator.validate_sdk_delegation(None, "nonexistent-agent")

        assert result.allowed is False
        assert result.delegate_to is None
        assert "not found" in result.reason.lower()

    def test_validate_rejects_active_agent(self, coordinator):
        """Test that already active agent is rejected."""
        # Simulate agent being active
        coordinator.active_agents.add("agent-a")

        result = coordinator.validate_sdk_delegation(None, "agent-a")

        assert result.allowed is False
        assert "already active" in result.reason.lower()

        # Cleanup
        coordinator.active_agents.discard("agent-a")

    def test_validate_rejects_blocked_delegation(self, coordinator):
        """Test that blocked delegation pairs are rejected."""
        # Block delegation from agent-a to agent-b
        coordinator.blocked_delegations.add(("agent-a", "agent-b"))

        result = coordinator.validate_sdk_delegation("agent-a", "agent-b")

        assert result.allowed is False
        assert result.blocked_pair == ("agent-a", "agent-b")
        assert "blocked" in result.reason.lower()

        # Cleanup
        coordinator.blocked_delegations.discard(("agent-a", "agent-b"))

    def test_validate_rejects_circular_delegation(self, coordinator):
        """Test that circular delegation is detected and rejected."""
        # Simulate agent-a being in the execution stack
        from datetime import datetime

        exec_ctx = ExecutionContext(
            agent_name="agent-a",
            task="test",
            start_time=datetime.now(),
        )
        coordinator.execution_stack.append(exec_ctx)
        coordinator.active_agents.add("agent-a")

        # Try to delegate back to agent-a
        result = coordinator.validate_sdk_delegation("agent-b", "agent-a")

        assert result.allowed is False
        # Either already active or cycle detected
        assert result.cycle_detected or "active" in result.reason.lower()

        # Cleanup
        coordinator.execution_stack.pop()
        coordinator.active_agents.discard("agent-a")

    def test_validate_respects_max_depth(self, coordinator):
        """Test that max delegation depth is respected."""
        from datetime import datetime

        # Fill up execution stack to max depth
        for i in range(coordinator.MAX_DELEGATION_DEPTH):
            exec_ctx = ExecutionContext(
                agent_name=f"agent-{i}",
                task="test",
                start_time=datetime.now(),
                depth=i,
            )
            coordinator.execution_stack.append(exec_ctx)

        result = coordinator.validate_sdk_delegation(None, "agent-a")

        assert result.allowed is False
        assert result.remaining_depth == 0
        assert "max" in result.reason.lower() and "depth" in result.reason.lower()

        # Cleanup
        coordinator.execution_stack.clear()

    def test_validate_reports_remaining_depth(self, coordinator):
        """Test that remaining depth is correctly reported."""
        from datetime import datetime

        # Add 2 items to stack
        for i in range(2):
            exec_ctx = ExecutionContext(
                agent_name=f"agent-{i}",
                task="test",
                start_time=datetime.now(),
                depth=i,
            )
            coordinator.execution_stack.append(exec_ctx)

        result = coordinator.validate_sdk_delegation(None, "agent-a")

        assert result.current_depth == 2
        # remaining_depth should be MAX_DELEGATION_DEPTH - current_depth - 1 (for the new delegation)
        expected_remaining = coordinator.MAX_DELEGATION_DEPTH - 2 - 1
        assert result.remaining_depth == expected_remaining

        # Cleanup
        coordinator.execution_stack.clear()


class TestSDKDelegationValidationDataclass:
    """Tests for SDKDelegationValidation dataclass."""

    def test_creation_with_required_fields(self):
        """Test creating validation with required fields."""
        validation = SDKDelegationValidation(
            allowed=True,
            delegate_to="agent-a",
            reason="Allowed",
            current_depth=0,
            remaining_depth=4,
            sdk_compatible=True,
        )

        assert validation.allowed is True
        assert validation.delegate_to == "agent-a"
        assert validation.current_depth == 0
        assert validation.remaining_depth == 4

    def test_creation_with_failure_fields(self):
        """Test creating validation for failed delegation."""
        validation = SDKDelegationValidation(
            allowed=False,
            delegate_to=None,
            reason="Circular delegation detected",
            current_depth=3,
            remaining_depth=1,
            sdk_compatible=False,
            cycle_detected=True,
        )

        assert validation.allowed is False
        assert validation.delegate_to is None
        assert validation.cycle_detected is True

    def test_creation_with_blocked_pair(self):
        """Test creating validation with blocked pair info."""
        validation = SDKDelegationValidation(
            allowed=False,
            delegate_to=None,
            reason="Delegation blocked",
            current_depth=1,
            remaining_depth=3,
            sdk_compatible=False,
            blocked_pair=("agent-a", "agent-b"),
        )

        assert validation.blocked_pair == ("agent-a", "agent-b")

    def test_optional_sdk_definition(self):
        """Test SDK definition is optional."""
        validation = SDKDelegationValidation(
            allowed=True,
            delegate_to="agent-a",
            reason="Allowed",
            current_depth=0,
            remaining_depth=4,
            sdk_compatible=True,
            sdk_definition=None,
        )

        assert validation.sdk_definition is None

        # With definition
        sdk_def = SDKAgentDefinition(
            description="Test",
            prompt="You are test.",
            tools=["Read"],
        )
        validation_with_def = SDKDelegationValidation(
            allowed=True,
            delegate_to="agent-a",
            reason="Allowed",
            current_depth=0,
            remaining_depth=4,
            sdk_compatible=True,
            sdk_definition=sdk_def,
        )

        assert validation_with_def.sdk_definition is sdk_def
