"""Tests for BehavioralModeManager."""

import json

from SuperClaude.Modes.behavioral_manager import (
    BehavioralMode,
    BehavioralModeManager,
    ModeConfiguration,
    ModeTransition,
)


class TestBehavioralModeManagerInitialization:
    """Initialization tests."""

    def test_default_mode_is_normal(self):
        """Manager starts in NORMAL mode."""
        manager = BehavioralModeManager()
        assert manager.get_current_mode() == BehavioralMode.NORMAL

    def test_default_configurations_exist(self):
        """All three modes have default configurations."""
        manager = BehavioralModeManager()

        for mode in BehavioralMode:
            config = manager.get_mode_configuration(mode)
            assert config is not None
            assert isinstance(config, ModeConfiguration)
            assert config.name == mode.value

    def test_normal_mode_config(self):
        """NORMAL mode has expected configuration."""
        manager = BehavioralModeManager()
        config = manager.get_mode_configuration(BehavioralMode.NORMAL)

        assert config.name == "normal"
        assert config.description == "Standard operational mode"
        assert "default" in config.triggers
        assert config.output_format == "standard"

    def test_task_management_mode_config(self):
        """TASK_MANAGEMENT mode has expected configuration."""
        manager = BehavioralModeManager()
        config = manager.get_mode_configuration(BehavioralMode.TASK_MANAGEMENT)

        assert config.name == "task_management"
        assert "--task-manage" in config.triggers
        assert config.output_format == "structured"
        assert "TodoWrite" in config.active_tools

    def test_token_efficiency_mode_config(self):
        """TOKEN_EFFICIENCY mode has expected configuration."""
        manager = BehavioralModeManager()
        config = manager.get_mode_configuration(BehavioralMode.TOKEN_EFFICIENCY)

        assert config.name == "token_efficiency"
        assert "--uc" in config.triggers
        assert config.output_format == "compressed"
        assert config.symbol_system is not None
        assert config.token_reduction_target == 0.5

    def test_empty_mode_stack_on_init(self):
        """Mode stack is empty on initialization."""
        manager = BehavioralModeManager()
        assert manager.mode_stack == []

    def test_empty_transition_history_on_init(self):
        """Transition history is empty on initialization."""
        manager = BehavioralModeManager()
        assert manager.transition_history == []


class TestBehavioralModeManagerSwitching:
    """Mode switching tests."""

    def test_switch_mode_updates_current_mode(self):
        """switch_mode() changes current_mode."""
        manager = BehavioralModeManager()
        assert manager.get_current_mode() == BehavioralMode.NORMAL

        result = manager.switch_mode(BehavioralMode.TASK_MANAGEMENT)
        assert result is True
        assert manager.get_current_mode() == BehavioralMode.TASK_MANAGEMENT

    def test_switch_to_same_mode_returns_true(self):
        """Switching to current mode is no-op, returns True."""
        manager = BehavioralModeManager()

        result = manager.switch_mode(BehavioralMode.NORMAL)
        assert result is True
        assert manager.get_current_mode() == BehavioralMode.NORMAL

    def test_switch_mode_records_transition(self):
        """Transition is added to transition_history."""
        manager = BehavioralModeManager()
        assert len(manager.transition_history) == 0

        manager.switch_mode(BehavioralMode.TOKEN_EFFICIENCY, trigger="test")
        assert len(manager.transition_history) == 1

        transition = manager.transition_history[0]
        assert transition.from_mode == "normal"
        assert transition.to_mode == "token_efficiency"
        assert transition.trigger == "test"

    def test_switch_mode_with_context(self):
        """switch_mode() stores context in transition."""
        manager = BehavioralModeManager()
        context = {"reason": "testing", "user": "admin"}

        manager.switch_mode(BehavioralMode.TASK_MANAGEMENT, context=context)

        transition = manager.transition_history[0]
        assert transition.context == context

    def test_switch_mode_notifies_callbacks(self):
        """Registered callbacks are called on mode change."""
        manager = BehavioralModeManager()
        callback_called = []

        def callback(prev_mode, new_mode, context):
            callback_called.append((prev_mode, new_mode, context))

        manager.register_mode_change_callback(callback)
        manager.switch_mode(BehavioralMode.TOKEN_EFFICIENCY, context={"test": True})

        assert len(callback_called) == 1
        prev, new, ctx = callback_called[0]
        assert prev == BehavioralMode.NORMAL
        assert new == BehavioralMode.TOKEN_EFFICIENCY
        assert ctx == {"test": True}

    def test_multiple_callbacks_all_called(self):
        """All registered callbacks are called."""
        manager = BehavioralModeManager()
        call_counts = {"cb1": 0, "cb2": 0}

        def callback1(prev, new, ctx):
            call_counts["cb1"] += 1

        def callback2(prev, new, ctx):
            call_counts["cb2"] += 1

        manager.register_mode_change_callback(callback1)
        manager.register_mode_change_callback(callback2)
        manager.switch_mode(BehavioralMode.TASK_MANAGEMENT)

        assert call_counts["cb1"] == 1
        assert call_counts["cb2"] == 1


class TestBehavioralModeManagerStack:
    """Mode stack (push/pop) tests."""

    def test_push_mode_adds_to_stack(self):
        """push_mode() adds current mode to stack."""
        manager = BehavioralModeManager()
        assert len(manager.mode_stack) == 0

        manager.push_mode(BehavioralMode.TASK_MANAGEMENT)

        assert len(manager.mode_stack) == 1
        assert manager.mode_stack[0] == BehavioralMode.NORMAL
        assert manager.get_current_mode() == BehavioralMode.TASK_MANAGEMENT

    def test_pop_mode_restores_previous(self):
        """pop_mode() restores mode from stack."""
        manager = BehavioralModeManager()
        manager.push_mode(BehavioralMode.TOKEN_EFFICIENCY)
        assert manager.get_current_mode() == BehavioralMode.TOKEN_EFFICIENCY

        popped = manager.pop_mode()
        assert popped == BehavioralMode.TOKEN_EFFICIENCY
        assert manager.get_current_mode() == BehavioralMode.NORMAL

    def test_pop_empty_stack_returns_none(self):
        """pop_mode() with empty stack returns None."""
        manager = BehavioralModeManager()
        result = manager.pop_mode()
        assert result is None
        assert manager.get_current_mode() == BehavioralMode.NORMAL

    def test_nested_push_pop(self):
        """Multiple push/pop operations work correctly."""
        manager = BehavioralModeManager()

        manager.push_mode(BehavioralMode.TASK_MANAGEMENT)
        manager.push_mode(BehavioralMode.TOKEN_EFFICIENCY)

        assert manager.get_current_mode() == BehavioralMode.TOKEN_EFFICIENCY
        assert len(manager.mode_stack) == 2

        manager.pop_mode()
        assert manager.get_current_mode() == BehavioralMode.TASK_MANAGEMENT

        manager.pop_mode()
        assert manager.get_current_mode() == BehavioralMode.NORMAL


class TestBehavioralModeManagerDetection:
    """Mode detection tests."""

    def test_detect_mode_from_trigger_in_context(self):
        """Triggers in context text activate correct mode."""
        manager = BehavioralModeManager()

        # Task management trigger
        context = {"task": "organize my todo list"}
        detected = manager.detect_mode_from_context(context)
        assert detected == BehavioralMode.TASK_MANAGEMENT

    def test_detect_mode_from_flags(self):
        """Flag triggers detect correct mode."""
        manager = BehavioralModeManager()

        context = {"flags": "--uc"}
        detected = manager.detect_mode_from_context(context)
        assert detected == BehavioralMode.TOKEN_EFFICIENCY

    def test_detect_task_management_pattern(self):
        """Task-related keywords trigger TASK_MANAGEMENT."""
        manager = BehavioralModeManager()

        for keyword in ["todo", "task", "plan", "schedule", "workflow"]:
            context = {"prompt": f"Help me with {keyword}"}
            detected = manager.detect_mode_from_context(context)
            assert detected == BehavioralMode.TASK_MANAGEMENT, f"Failed for keyword: {keyword}"

    def test_detect_efficiency_need_large_context(self):
        """Large context (>10000 chars) triggers TOKEN_EFFICIENCY."""
        manager = BehavioralModeManager()

        # Create context larger than 10000 chars
        large_text = "x" * 15000
        context = {"data": large_text}

        detected = manager.detect_mode_from_context(context)
        assert detected == BehavioralMode.TOKEN_EFFICIENCY

    def test_detect_efficiency_from_resource_constraint(self):
        """resource_constrained flag triggers TOKEN_EFFICIENCY."""
        manager = BehavioralModeManager()

        context = {"resource_constrained": True}
        detected = manager.detect_mode_from_context(context)
        assert detected == BehavioralMode.TOKEN_EFFICIENCY

    def test_detect_efficiency_from_low_token_limit(self):
        """Low token_limit triggers TOKEN_EFFICIENCY."""
        manager = BehavioralModeManager()

        context = {"token_limit": 3000}
        detected = manager.detect_mode_from_context(context)
        assert detected == BehavioralMode.TOKEN_EFFICIENCY

    def test_no_detection_returns_none(self):
        """No matching trigger returns None."""
        manager = BehavioralModeManager()

        context = {"prompt": "hello world"}
        detected = manager.detect_mode_from_context(context)
        assert detected is None


class TestBehavioralModeManagerBehaviors:
    """Behavior application tests."""

    def test_apply_mode_behaviors_adds_mode_info(self):
        """Context gets _mode key with current mode info."""
        manager = BehavioralModeManager()
        context = {"original": "data"}

        enhanced = manager.apply_mode_behaviors(context)

        assert "_mode" in enhanced
        assert enhanced["_mode"]["name"] == "normal"
        assert "behaviors" in enhanced["_mode"]
        assert enhanced["original"] == "data"

    def test_apply_mode_behaviors_does_not_mutate_original(self):
        """apply_mode_behaviors returns new dict, doesn't mutate input."""
        manager = BehavioralModeManager()
        original = {"key": "value"}

        enhanced = manager.apply_mode_behaviors(original)

        assert "_mode" in enhanced
        assert "_mode" not in original

    def test_token_efficiency_adds_symbols(self):
        """TOKEN_EFFICIENCY mode adds _symbols to context."""
        manager = BehavioralModeManager()
        manager.switch_mode(BehavioralMode.TOKEN_EFFICIENCY)

        enhanced = manager.apply_mode_behaviors({})

        assert "_symbols" in enhanced
        assert "→" in enhanced["_symbols"]
        assert "✅" in enhanced["_symbols"]

    def test_token_efficiency_adds_token_target(self):
        """TOKEN_EFFICIENCY mode adds _token_target to context."""
        manager = BehavioralModeManager()
        manager.switch_mode(BehavioralMode.TOKEN_EFFICIENCY)

        enhanced = manager.apply_mode_behaviors({})

        assert "_token_target" in enhanced
        assert enhanced["_token_target"] == 0.5

    def test_task_management_adds_preferences(self):
        """TASK_MANAGEMENT adds _preferred_tools."""
        manager = BehavioralModeManager()
        manager.switch_mode(BehavioralMode.TASK_MANAGEMENT)

        enhanced = manager.apply_mode_behaviors({})

        assert "_preferred_tools" in enhanced
        assert "TodoWrite" in enhanced["_preferred_tools"]


class TestBehavioralModeManagerOutputFormatting:
    """Output formatting tests."""

    def test_normal_mode_no_formatting(self):
        """NORMAL mode returns output unchanged."""
        manager = BehavioralModeManager()
        output = "This is the original output."

        formatted = manager.format_output(output, {})

        assert formatted == output

    def test_compressed_output_applies_symbols(self):
        """Compressed format replaces text with symbols."""
        manager = BehavioralModeManager()
        manager.switch_mode(BehavioralMode.TOKEN_EFFICIENCY)

        output = "This leads to success, therefore complete"
        formatted = manager.format_output(output, {})

        # Symbol replacements should have occurred
        assert "→" in formatted or "∴" in formatted or formatted != output


class TestBehavioralModeManagerConfiguration:
    """Configuration loading tests."""

    def test_load_configuration_from_file(self, tmp_path):
        """Custom config file overrides defaults."""
        config_file = tmp_path / "config.json"
        config_data = {
            "modes": [
                {
                    "name": "normal",
                    "description": "Custom normal mode",
                    "triggers": ["custom"],
                    "behaviors": {"custom": True},
                }
            ]
        }
        config_file.write_text(json.dumps(config_data))

        manager = BehavioralModeManager(config_path=str(config_file))
        config = manager.get_mode_configuration(BehavioralMode.NORMAL)

        assert config.description == "Custom normal mode"
        assert "custom" in config.triggers

    def test_load_missing_file_returns_false(self):
        """Missing config file returns False, logs warning."""
        manager = BehavioralModeManager()
        result = manager.load_configuration("/nonexistent/path.json")
        assert result is False

    def test_load_invalid_json_returns_false(self, tmp_path):
        """Invalid JSON returns False."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("not valid json {{{")

        manager = BehavioralModeManager()
        result = manager.load_configuration(str(config_file))
        assert result is False


class TestBehavioralModeManagerMetrics:
    """Metrics and history tests."""

    def test_get_transition_history_returns_recent(self):
        """get_transition_history() returns last N transitions."""
        manager = BehavioralModeManager()

        # Make several transitions
        for i in range(15):
            manager.switch_mode(BehavioralMode.TASK_MANAGEMENT)
            manager.switch_mode(BehavioralMode.NORMAL)

        # Should return limited history
        history = manager.get_transition_history(limit=5)
        assert len(history) == 5

        # Each entry should have expected fields
        for entry in history:
            assert "from" in entry
            assert "to" in entry
            assert "timestamp" in entry
            assert "trigger" in entry

    def test_get_transition_history_default_limit(self):
        """get_transition_history() has default limit of 10."""
        manager = BehavioralModeManager()

        for _ in range(20):
            manager.switch_mode(BehavioralMode.TOKEN_EFFICIENCY)
            manager.switch_mode(BehavioralMode.NORMAL)

        history = manager.get_transition_history()
        assert len(history) == 10


class TestBehavioralModeManagerCallbacks:
    """Callback tests."""

    def test_callback_receives_previous_and_new_mode(self):
        """Callbacks get (previous_mode, new_mode, context)."""
        manager = BehavioralModeManager()
        received = {}

        def callback(prev, new, ctx):
            received["prev"] = prev
            received["new"] = new
            received["ctx"] = ctx

        manager.register_mode_change_callback(callback)
        manager.switch_mode(BehavioralMode.TASK_MANAGEMENT, context={"key": "val"})

        assert received["prev"] == BehavioralMode.NORMAL
        assert received["new"] == BehavioralMode.TASK_MANAGEMENT
        assert received["ctx"] == {"key": "val"}

    def test_callback_error_is_logged(self):
        """Callback exceptions are caught and logged."""
        manager = BehavioralModeManager()

        def bad_callback(prev, new, ctx):
            raise ValueError("Intentional error")

        manager.register_mode_change_callback(bad_callback)

        # Should not raise - error is caught and logged
        result = manager.switch_mode(BehavioralMode.TOKEN_EFFICIENCY)
        assert result is True
        assert manager.get_current_mode() == BehavioralMode.TOKEN_EFFICIENCY

    def test_callback_error_does_not_stop_other_callbacks(self):
        """One failing callback doesn't prevent others from running."""
        manager = BehavioralModeManager()
        calls = []

        def callback1(prev, new, ctx):
            calls.append("cb1")

        def bad_callback(prev, new, ctx):
            raise ValueError("Error")

        def callback2(prev, new, ctx):
            calls.append("cb2")

        manager.register_mode_change_callback(callback1)
        manager.register_mode_change_callback(bad_callback)
        manager.register_mode_change_callback(callback2)

        manager.switch_mode(BehavioralMode.TASK_MANAGEMENT)

        assert "cb1" in calls
        assert "cb2" in calls


class TestModeConfigurationDataclass:
    """ModeConfiguration dataclass tests."""

    def test_mode_configuration_defaults(self):
        """ModeConfiguration has sensible defaults."""
        config = ModeConfiguration(
            name="test",
            description="Test mode",
            triggers=["test"],
            behaviors={},
        )

        assert config.symbol_system is None
        assert config.output_format == "standard"
        assert config.token_reduction_target == 0.0
        assert config.active_tools == []
        assert config.disabled_tools == []
        assert config.metadata == {}


class TestModeTransitionDataclass:
    """ModeTransition dataclass tests."""

    def test_mode_transition_stores_all_fields(self):
        """ModeTransition stores all provided fields."""
        from datetime import datetime

        now = datetime.now()
        transition = ModeTransition(
            from_mode="normal",
            to_mode="task_management",
            timestamp=now,
            trigger="manual",
            context={"reason": "test"},
        )

        assert transition.from_mode == "normal"
        assert transition.to_mode == "task_management"
        assert transition.timestamp == now
        assert transition.trigger == "manual"
        assert transition.context == {"reason": "test"}


class TestBehavioralModeEnum:
    """BehavioralMode enum tests."""

    def test_all_modes_have_string_values(self):
        """All BehavioralMode members have string values."""
        for mode in BehavioralMode:
            assert isinstance(mode.value, str)

    def test_mode_values_are_lowercase(self):
        """Mode values are lowercase."""
        for mode in BehavioralMode:
            assert mode.value == mode.value.lower()

    def test_expected_modes_exist(self):
        """Expected modes are defined."""
        assert hasattr(BehavioralMode, "NORMAL")
        assert hasattr(BehavioralMode, "TASK_MANAGEMENT")
        assert hasattr(BehavioralMode, "TOKEN_EFFICIENCY")
