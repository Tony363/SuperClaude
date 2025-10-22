"""
Base Agent Abstract Class for SuperClaude Framework

This module provides the abstract base class for all agents in the SuperClaude
Framework. All agents must inherit from BaseAgent and implement the required
abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
import json


class BaseAgent(ABC):
    """
    Abstract base class for all SuperClaude agents.

    Each agent must implement the core methods for execution, validation,
    and capability reporting. Agents are configured from markdown files
    that define their behavior, tools, and focus areas.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the base agent with configuration.

        Args:
            config: Dictionary containing agent configuration from markdown
                   Expected keys: name, description, category, tools,
                   triggers, focus_areas, boundaries
        """
        self.config = dict(config)

        self.name = config.get('name', 'unnamed-agent')
        self.description = config.get('description', '')
        self.category = config.get('category', 'general')
        self.tools = config.get('tools', [])
        self.triggers = config.get('triggers', [])
        self.focus_areas = config.get('focus_areas', {})
        self.boundaries = config.get('boundaries', {})
        self.mindset = config.get('behavioral_mindset', '')

        # Setup logging
        self.logger = logging.getLogger(f"agent.{self.name}")

        # Metadata
        self.version = config.get('version', '1.0.0')
        self.source_file = config.get('source_file', None)

        # Runtime state
        self._initialized = False
        self._execution_count = 0

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent's main logic.

        Args:
            context: Dictionary containing execution context
                    Expected keys: task, files, parameters, environment

        Returns:
            Dictionary containing execution results
                   Expected keys: success, output, actions_taken, errors
        """
        pass

    @abstractmethod
    def validate(self, context: Dict[str, Any]) -> bool:
        """
        Validate if this agent can handle the given context.

        Args:
            context: Dictionary containing validation context

        Returns:
            True if agent can handle the context, False otherwise
        """
        pass

    def get_capabilities(self) -> List[str]:
        """
        Return list of agent capabilities.

        Returns:
            List of capability descriptions
        """
        capabilities = []

        # Add focus areas as capabilities
        for area, details in self.focus_areas.items():
            capabilities.append(f"{area}: {details}")

        # Add tool capabilities
        if self.tools:
            capabilities.append(f"Tools: {', '.join(self.tools)}")

        return capabilities

    def get_trigger_keywords(self) -> List[str]:
        """
        Return list of keywords that trigger this agent.

        Returns:
            List of trigger keywords
        """
        return self.triggers

    def get_metadata(self) -> Dict[str, Any]:
        """
        Return agent metadata.

        Returns:
            Dictionary containing agent metadata
        """
        return {
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'version': self.version,
            'tools': self.tools,
            'triggers': self.triggers,
            'source_file': str(self.source_file) if self.source_file else None,
            'execution_count': self._execution_count
        }

    def initialize(self) -> bool:
        """
        Initialize the agent for execution.

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True

        try:
            # Perform any agent-specific initialization
            self._setup()
            self._initialized = True
            self.logger.info(f"Agent {self.name} initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize agent {self.name}: {e}")
            return False

    def _setup(self):
        """
        Optional setup method for agent-specific initialization.
        Override in subclasses if needed.
        """
        pass

    def reset(self):
        """
        Reset agent state between executions.
        """
        self._execution_count = 0
        self.logger.debug(f"Agent {self.name} state reset")

    def can_handle_task(self, task: str) -> float:
        """
        Calculate confidence score for handling a given task.

        Args:
            task: Task description string

        Returns:
            Confidence score between 0.0 and 1.0
        """
        task_lower = task.lower()
        score = 0.0

        # Check for trigger keyword matches
        for trigger in self.triggers:
            if trigger.lower() in task_lower:
                score += 0.3

        # Check for category relevance
        if self.category.lower() in task_lower:
            score += 0.2

        # Check for tool mentions
        for tool in self.tools:
            if tool.lower() in task_lower:
                score += 0.1

        # Cap at 1.0
        return min(score, 1.0)

    def log_execution(self, context: Dict[str, Any], result: Dict[str, Any]):
        """
        Log agent execution for debugging and monitoring.

        Args:
            context: Execution context
            result: Execution result
        """
        self._execution_count += 1
        self.logger.info(
            f"Agent {self.name} executed (#{self._execution_count}): "
            f"success={result.get('success', False)}"
        )
        self.logger.debug(f"Context: {json.dumps(context, indent=2)}")
        self.logger.debug(f"Result: {json.dumps(result, indent=2)}")

    def __str__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(name={self.name}, category={self.category})"

    def __repr__(self) -> str:
        """Developer representation of the agent."""
        return (
            f"<{self.__class__.__name__} "
            f"name='{self.name}' "
            f"category='{self.category}' "
            f"tools={len(self.tools)} "
            f"triggers={len(self.triggers)}>"
        )
