"""
Behavioral Mode Manager for SuperClaude Framework

Manages different behavioral modes that change how the framework
operates, including brainstorming, introspection, task management,
token efficiency, and orchestration modes.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


class BehavioralMode(Enum):
    """Enumeration of available behavioral modes."""

    NORMAL = "normal"
    BRAINSTORMING = "brainstorming"
    INTROSPECTION = "introspection"
    TASK_MANAGEMENT = "task_management"
    TOKEN_EFFICIENCY = "token_efficiency"
    ORCHESTRATION = "orchestration"


@dataclass
class ModeConfiguration:
    """Configuration for a behavioral mode."""

    name: str
    description: str
    triggers: List[str]
    behaviors: Dict[str, Any]
    symbol_system: Optional[Dict[str, str]] = None
    output_format: str = "standard"
    token_reduction_target: float = 0.0
    active_tools: List[str] = field(default_factory=list)
    disabled_tools: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ModeTransition:
    """Records a mode transition."""

    from_mode: str
    to_mode: str
    timestamp: datetime
    trigger: str
    context: Dict[str, Any]


class BehavioralModeManager:
    """
    Manages behavioral modes for the SuperClaude Framework.

    Each mode changes how the system operates, from verbose brainstorming
    to ultra-compressed token efficiency mode.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the behavioral mode manager.

        Args:
            config_path: Optional path to mode configuration file
        """
        self.logger = logging.getLogger(__name__)

        # Current mode
        self.current_mode = BehavioralMode.NORMAL
        self.mode_stack: List[BehavioralMode] = []

        # Mode configurations
        self.configurations: Dict[BehavioralMode, ModeConfiguration] = {}

        # Mode history
        self.transition_history: List[ModeTransition] = []
        self.mode_metrics: Dict[str, Dict[str, Any]] = {}

        # Initialize default configurations
        self._initialize_default_configurations()

        # Load custom configuration if provided
        if config_path:
            self.load_configuration(config_path)

        # Mode change callbacks
        self.mode_change_callbacks: List[Callable] = []

    def _initialize_default_configurations(self):
        """Initialize default mode configurations."""

        # Normal mode
        self.configurations[BehavioralMode.NORMAL] = ModeConfiguration(
            name="normal",
            description="Standard operational mode",
            triggers=["default", "standard", "normal"],
            behaviors={
                "verbosity": "normal",
                "question_asking": "minimal",
                "exploration": "focused",
                "output_style": "balanced",
            },
            output_format="standard",
        )

        # Brainstorming mode
        self.configurations[BehavioralMode.BRAINSTORMING] = ModeConfiguration(
            name="brainstorming",
            description="Collaborative discovery mindset",
            triggers=["--brainstorm", "explore", "discover", "ideate"],
            behaviors={
                "verbosity": "high",
                "question_asking": "socratic",
                "exploration": "broad",
                "output_style": "interactive",
                "discovery_questions": True,
                "assumption_challenging": True,
                "idea_generation": "expansive",
            },
            output_format="conversational",
            active_tools=["TodoWrite", "WebSearch"],
        )

        # Introspection mode
        self.configurations[BehavioralMode.INTROSPECTION] = ModeConfiguration(
            name="introspection",
            description="Meta-cognitive analysis mindset",
            triggers=["--introspect", "analyze reasoning", "self-reflect"],
            behaviors={
                "verbosity": "high",
                "thinking_visibility": "transparent",
                "decision_analysis": True,
                "pattern_detection": True,
                "self_correction": True,
                "reasoning_markers": ["🤔", "🎯", "⚡", "📊", "💡"],
            },
            output_format="analytical",
            metadata={"expose_thinking": True},
        )

        # Task Management mode
        self.configurations[BehavioralMode.TASK_MANAGEMENT] = ModeConfiguration(
            name="task_management",
            description="Systematic task organization",
            triggers=["--task-manage", "organize", "plan tasks"],
            behaviors={
                "verbosity": "structured",
                "organization": "hierarchical",
                "tracking": "comprehensive",
                "delegation": True,
                "progress_monitoring": True,
                "task_hierarchy": ["plan", "phase", "task", "todo"],
            },
            output_format="structured",
            active_tools=["TodoWrite", "Task", "Grep"],
            metadata={"auto_todo": True},
        )

        # Token Efficiency mode
        self.configurations[BehavioralMode.TOKEN_EFFICIENCY] = ModeConfiguration(
            name="token_efficiency",
            description="Ultra-compressed communication",
            triggers=["--uc", "--ultracompressed", "save tokens"],
            behaviors={
                "verbosity": "minimal",
                "abbreviation": True,
                "symbol_usage": "maximum",
                "output_compression": "aggressive",
                "explanation": "none",
            },
            symbol_system={
                "→": "leads to",
                "✅": "complete",
                "❌": "failed",
                "🔄": "in progress",
                "⚠️": "warning",
                "∴": "therefore",
                "∵": "because",
            },
            output_format="compressed",
            token_reduction_target=0.5,
            disabled_tools=["WebSearch"],  # Disable verbose tools
        )

        # Orchestration mode
        self.configurations[BehavioralMode.ORCHESTRATION] = ModeConfiguration(
            name="orchestration",
            description="Intelligent tool selection and coordination",
            triggers=["--orchestrate", "coordinate", "multi-tool"],
            behaviors={
                "verbosity": "strategic",
                "tool_selection": "optimized",
                "parallel_execution": True,
                "resource_awareness": True,
                "performance_focus": True,
                "delegation": "automatic",
            },
            output_format="strategic",
            active_tools=["Task", "MultiEdit", "Bash"],
            metadata={"parallel_by_default": True},
        )

    def get_current_mode(self) -> BehavioralMode:
        """
        Get the current behavioral mode.

        Returns:
            Current mode
        """
        return self.current_mode

    def get_mode_configuration(
        self, mode: Optional[BehavioralMode] = None
    ) -> ModeConfiguration:
        """
        Get configuration for a mode.

        Args:
            mode: Mode to get configuration for (current if None)

        Returns:
            Mode configuration
        """
        target_mode = mode or self.current_mode
        return self.configurations.get(
            target_mode, self.configurations[BehavioralMode.NORMAL]
        )

    def detect_mode_from_context(
        self, context: Dict[str, Any]
    ) -> Optional[BehavioralMode]:
        """
        Detect appropriate mode from context.

        Args:
            context: Execution context

        Returns:
            Detected mode or None
        """
        # Extract text from context
        text_parts = []
        for field in ["task", "prompt", "flags", "command"]:
            if field in context:
                text_parts.append(str(context[field]).lower())

        text = " ".join(text_parts)

        # Check each mode's triggers
        for mode, config in self.configurations.items():
            for trigger in config.triggers:
                if trigger.lower() in text:
                    self.logger.debug(f"Detected mode {mode} from trigger: {trigger}")
                    return mode

        # Check for specific patterns
        if self._detect_brainstorming_pattern(text):
            return BehavioralMode.BRAINSTORMING

        if self._detect_task_management_pattern(text):
            return BehavioralMode.TASK_MANAGEMENT

        if self._detect_efficiency_need(context):
            return BehavioralMode.TOKEN_EFFICIENCY

        return None

    def switch_mode(
        self,
        mode: BehavioralMode,
        context: Optional[Dict[str, Any]] = None,
        trigger: str = "manual",
    ) -> bool:
        """
        Switch to a different behavioral mode.

        Args:
            mode: Target mode
            context: Optional context for transition
            trigger: What triggered the switch

        Returns:
            True if switched successfully
        """
        if mode == self.current_mode:
            return True

        try:
            # Record transition
            transition = ModeTransition(
                from_mode=self.current_mode.value,
                to_mode=mode.value,
                timestamp=datetime.now(),
                trigger=trigger,
                context=context or {},
            )
            self.transition_history.append(transition)

            # Update mode
            previous_mode = self.current_mode
            self.current_mode = mode

            # Update metrics
            self._update_mode_metrics(mode)

            # Notify callbacks
            for callback in self.mode_change_callbacks:
                try:
                    callback(previous_mode, mode, context)
                except Exception as e:
                    self.logger.error(f"Mode change callback error: {e}")

            self.logger.info(
                f"Switched from {previous_mode.value} to {mode.value} mode"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to switch mode: {e}")
            return False

    def push_mode(self, mode: BehavioralMode, context: Optional[Dict[str, Any]] = None):
        """
        Push a new mode onto the stack (temporary switch).

        Args:
            mode: Mode to push
            context: Optional context
        """
        self.mode_stack.append(self.current_mode)
        self.switch_mode(mode, context, trigger="push")

    def pop_mode(self) -> Optional[BehavioralMode]:
        """
        Pop mode from stack and restore previous.

        Returns:
            Popped mode or None
        """
        if self.mode_stack:
            previous = self.current_mode
            restored = self.mode_stack.pop()
            self.switch_mode(restored, trigger="pop")
            return previous
        return None

    def apply_mode_behaviors(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply current mode behaviors to context.

        Args:
            context: Original context

        Returns:
            Enhanced context with mode behaviors
        """
        config = self.get_mode_configuration()
        enhanced = context.copy()

        # Add mode information
        enhanced["_mode"] = {
            "name": config.name,
            "behaviors": config.behaviors,
            "output_format": config.output_format,
        }

        # Add symbol system for token efficiency
        if config.symbol_system:
            enhanced["_symbols"] = config.symbol_system

        # Add tool preferences
        if config.active_tools:
            enhanced["_preferred_tools"] = config.active_tools

        if config.disabled_tools:
            enhanced["_disabled_tools"] = config.disabled_tools

        # Apply token reduction target
        if config.token_reduction_target > 0:
            enhanced["_token_target"] = config.token_reduction_target

        # Apply specific behavioral modifications
        enhanced = self._apply_specific_behaviors(enhanced, config)

        return enhanced

    def format_output(self, output: str, context: Dict[str, Any]) -> str:
        """
        Format output according to current mode.

        Args:
            output: Original output
            context: Execution context

        Returns:
            Formatted output
        """
        config = self.get_mode_configuration()

        if config.output_format == "compressed":
            return self._compress_output(output, config)
        elif config.output_format == "conversational":
            return self._conversational_output(output)
        elif config.output_format == "structured":
            return self._structured_output(output)
        elif config.output_format == "analytical":
            return self._analytical_output(output, config)
        elif config.output_format == "strategic":
            return self._strategic_output(output)

        return output

    def get_mode_metrics(self, mode: Optional[BehavioralMode] = None) -> Dict[str, Any]:
        """
        Get metrics for a specific mode.

        Args:
            mode: Mode to get metrics for (all if None)

        Returns:
            Mode metrics
        """
        if mode:
            mode_name = mode.value
            return self.mode_metrics.get(mode_name, {})

        return self.mode_metrics

    def get_transition_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get mode transition history.

        Args:
            limit: Maximum number of transitions

        Returns:
            List of transitions
        """
        history = self.transition_history[-limit:]
        return [
            {
                "from": t.from_mode,
                "to": t.to_mode,
                "timestamp": t.timestamp.isoformat(),
                "trigger": t.trigger,
            }
            for t in history
        ]

    def register_mode_change_callback(self, callback: Callable):
        """
        Register callback for mode changes.

        Args:
            callback: Function to call on mode change
        """
        self.mode_change_callbacks.append(callback)

    def load_configuration(self, config_path: str) -> bool:
        """
        Load mode configuration from file.

        Args:
            config_path: Path to configuration file

        Returns:
            True if successful
        """
        try:
            path = Path(config_path)
            if not path.exists():
                self.logger.warning(f"Configuration file not found: {config_path}")
                return False

            with open(path, encoding="utf-8") as f:
                config = json.load(f)

            # Load custom mode configurations
            for mode_config in config.get("modes", []):
                mode_name = mode_config.get("name", "").upper()
                if hasattr(BehavioralMode, mode_name):
                    mode_enum = getattr(BehavioralMode, mode_name)
                    self.configurations[mode_enum] = ModeConfiguration(**mode_config)

            self.logger.info(f"Loaded mode configuration from {config_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return False

    def _detect_brainstorming_pattern(self, text: str) -> bool:
        """Detect if text suggests brainstorming mode."""
        patterns = [
            "what if",
            "explore",
            "brainstorm",
            "ideas",
            "possibilities",
            "alternatives",
            "creative",
            "think about",
            "consider",
            "imagine",
        ]
        return any(pattern in text for pattern in patterns)

    def _detect_task_management_pattern(self, text: str) -> bool:
        """Detect if text suggests task management mode."""
        patterns = [
            "todo",
            "task",
            "organize",
            "plan",
            "schedule",
            "track",
            "manage",
            "delegate",
            "workflow",
            "pipeline",
        ]
        return any(pattern in text for pattern in patterns)

    def _detect_efficiency_need(self, context: Dict[str, Any]) -> bool:
        """Detect if token efficiency is needed."""
        # Check context size
        context_str = str(context)
        if len(context_str) > 10000:  # Large context
            return True

        # Check for efficiency hints
        if context.get("resource_constrained"):
            return True

        if context.get("token_limit") and context["token_limit"] < 5000:
            return True

        return False

    def _apply_specific_behaviors(
        self, context: Dict[str, Any], config: ModeConfiguration
    ) -> Dict[str, Any]:
        """Apply mode-specific behavioral modifications."""

        # Brainstorming mode modifications
        if config.name == "brainstorming":
            context["_questions"] = [
                "What problem are we trying to solve?",
                "What constraints do we have?",
                "What alternatives have been considered?",
                "What are the success criteria?",
            ]
            context["_exploration_depth"] = "broad"

        # Introspection mode modifications
        elif config.name == "introspection":
            context["_expose_reasoning"] = True
            context["_decision_tracking"] = True
            context["_pattern_analysis"] = True

        # Task management modifications
        elif config.name == "task_management":
            context["_auto_organize"] = True
            context["_hierarchy_depth"] = 4
            context["_tracking_enabled"] = True

        # Token efficiency modifications
        elif config.name == "token_efficiency":
            context["_max_response_tokens"] = 500
            context["_use_abbreviations"] = True
            context["_skip_explanations"] = True

        # Orchestration modifications
        elif config.name == "orchestration":
            context["_parallel_execution"] = True
            context["_tool_optimization"] = True
            context["_batch_operations"] = True

        return context

    def _compress_output(self, output: str, config: ModeConfiguration) -> str:
        """Compress output for token efficiency."""
        compressed = output

        # Apply symbol replacements
        if config.symbol_system:
            for symbol, meaning in config.symbol_system.items():
                compressed = compressed.replace(meaning, symbol)

        # Remove unnecessary words
        remove_words = ["the", "a", "an", "is", "are", "was", "were"]
        for word in remove_words:
            compressed = compressed.replace(f" {word} ", " ")

        # Truncate long explanations
        lines = compressed.split("\n")
        compressed_lines = []
        for line in lines:
            if len(line) > 80:
                line = line[:77] + "..."
            compressed_lines.append(line)

        return "\n".join(compressed_lines)

    def _conversational_output(self, output: str) -> str:
        """Format output for conversational brainstorming."""
        lines = output.split("\n")
        formatted = []

        for line in lines:
            if line.strip():
                # Add conversational markers
                if line.startswith("-"):
                    line = "💭 " + line[1:].strip()
                elif "?" in line:
                    line = "🤔 " + line

                formatted.append(line)

        return "\n".join(formatted)

    def _structured_output(self, output: str) -> str:
        """Format output for structured task management."""
        # Add structure markers
        lines = output.split("\n")
        formatted = []
        indent_level = 0

        for line in lines:
            if line.strip():
                # Detect hierarchy
                if line.startswith("##"):
                    indent_level = 0
                    line = f"📋 {line}"
                elif line.startswith("#"):
                    indent_level = 0
                    line = f"🎯 {line}"
                elif line.startswith("-"):
                    line = "  " * indent_level + "✓ " + line[1:].strip()

                formatted.append(line)

        return "\n".join(formatted)

    def _analytical_output(self, output: str, config: ModeConfiguration) -> str:
        """Format output for analytical introspection."""
        # Add reasoning markers
        config.behaviors.get("reasoning_markers", [])

        lines = output.split("\n")
        formatted = []

        for line in lines:
            if line.strip():
                # Add appropriate markers
                if "decision" in line.lower():
                    line = "🎯 " + line
                elif "pattern" in line.lower():
                    line = "📊 " + line
                elif "insight" in line.lower():
                    line = "💡 " + line
                elif "thinking" in line.lower() or "reasoning" in line.lower():
                    line = "🤔 " + line

                formatted.append(line)

        return "\n".join(formatted)

    def _strategic_output(self, output: str) -> str:
        """Format output for strategic orchestration."""
        lines = output.split("\n")
        formatted = []

        for line in lines:
            if line.strip():
                # Add strategic markers
                if "parallel" in line.lower():
                    line = "⚡ " + line
                elif "optimize" in line.lower():
                    line = "🎯 " + line
                elif "coordinate" in line.lower():
                    line = "🔄 " + line

                formatted.append(line)

        return "\n".join(formatted)

    def _update_mode_metrics(self, mode: BehavioralMode):
        """Update metrics for mode usage."""
        mode_name = mode.value

        if mode_name not in self.mode_metrics:
            self.mode_metrics[mode_name] = {
                "activation_count": 0,
                "total_time": 0,
                "last_activated": None,
            }

        self.mode_metrics[mode_name]["activation_count"] += 1
        self.mode_metrics[mode_name]["last_activated"] = datetime.now().isoformat()

    def reset_metrics(self):
        """Reset all mode metrics."""
        self.mode_metrics = {}
        self.transition_history = []
