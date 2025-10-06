"""
Generic Markdown Agent for SuperClaude Framework

This module provides a generic agent implementation that works with
any agent defined in markdown without requiring a specific Python class.
"""

from typing import Dict, Any, List
import re
from .base import BaseAgent


class GenericMarkdownAgent(BaseAgent):
    """
    Generic agent implementation for markdown-defined agents.

    This class provides a functional agent that operates based on
    configuration extracted from markdown files, without requiring
    a specific Python implementation.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize generic agent with markdown configuration.

        Args:
            config: Agent configuration from markdown parser
        """
        super().__init__(config)

        # Extract specific configuration
        self.key_actions = config.get('key_actions', [])
        self.outputs = config.get('outputs', [])

        # Parse will/will not boundaries
        boundaries = config.get('boundaries', {})
        self.will_do = boundaries.get('will', [])
        self.will_not_do = boundaries.get('will_not', [])

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the agent based on markdown configuration.

        Args:
            context: Execution context

        Returns:
            Execution results
        """
        result = {
            'success': False,
            'output': '',
            'actions_taken': [],
            'errors': []
        }

        try:
            # Initialize if needed
            if not self._initialized:
                if not self.initialize():
                    result['errors'].append("Failed to initialize agent")
                    return result

            # Validate context
            if not self.validate(context):
                result['errors'].append(
                    f"Agent {self.name} cannot handle this context"
                )
                return result

            # Extract task from context
            task = context.get('task', '')
            files = context.get('files', [])
            parameters = context.get('parameters', {})

            # Build execution plan based on key actions
            execution_plan = self._build_execution_plan(task, parameters)

            # Execute the plan (simulation for generic agent)
            for action in execution_plan:
                result['actions_taken'].append(action)

            # Generate output based on agent configuration
            result['output'] = self._generate_output(task, execution_plan)
            result['success'] = True

            # Log execution
            self.log_execution(context, result)

        except Exception as e:
            self.logger.error(f"Execution failed for {self.name}: {e}")
            result['errors'].append(str(e))

        return result

    def validate(self, context: Dict[str, Any]) -> bool:
        """
        Validate if this agent can handle the context.

        Args:
            context: Validation context

        Returns:
            True if agent can handle context
        """
        task = context.get('task', '')

        if not task:
            return False

        # Check against boundaries
        task_lower = task.lower()

        # Check will_not_do boundaries
        for boundary in self.will_not_do:
            if self._matches_boundary(task_lower, boundary.lower()):
                self.logger.debug(
                    f"Agent {self.name} rejected task due to boundary: {boundary}"
                )
                return False

        # Check if task matches agent capabilities
        confidence = self.can_handle_task(task)

        # Accept if confidence is above threshold
        return confidence > 0.3

    def _build_execution_plan(
        self, task: str, parameters: Dict[str, Any]
    ) -> List[str]:
        """
        Build execution plan based on key actions.

        Args:
            task: Task description
            parameters: Execution parameters

        Returns:
            List of actions to take
        """
        plan = []

        # Map key actions to the task
        for action in self.key_actions:
            # Simple keyword matching for action relevance
            if self._is_action_relevant(action, task):
                # Format action with task context
                formatted_action = self._format_action(action, task, parameters)
                plan.append(formatted_action)

        # If no specific actions matched, use general approach
        if not plan:
            plan = [
                f"Analyze: {task}",
                f"Apply {self.category} expertise",
                f"Execute with {', '.join(self.tools) if self.tools else 'available tools'}"
            ]

        return plan

    def _is_action_relevant(self, action: str, task: str) -> bool:
        """
        Check if an action is relevant to the task.

        Args:
            action: Action description
            task: Task description

        Returns:
            True if action is relevant
        """
        # Extract key verbs from action
        action_verbs = re.findall(r'\b(analyze|test|validate|document|refactor|debug|implement|review)\b',
                                 action.lower())

        task_lower = task.lower()

        # Check if any action verb appears in task
        for verb in action_verbs:
            if verb in task_lower:
                return True

        # Check for category relevance
        if self.category.lower() in task_lower:
            return True

        # Default to including the action for generic execution
        return len(self.key_actions) <= 3  # Include all if few actions

    def _format_action(
        self, action: str, task: str, parameters: Dict[str, Any]
    ) -> str:
        """
        Format action with context.

        Args:
            action: Action template
            task: Task description
            parameters: Execution parameters

        Returns:
            Formatted action string
        """
        # Simple variable substitution
        formatted = action

        # Replace common placeholders
        formatted = formatted.replace('{task}', task)
        formatted = formatted.replace('{category}', self.category)

        # Add parameters if mentioned
        if 'parameter' in action.lower() and parameters:
            param_str = ', '.join(f"{k}={v}" for k, v in parameters.items())
            formatted += f" (parameters: {param_str})"

        return formatted

    def _generate_output(self, task: str, actions: List[str]) -> str:
        """
        Generate output based on agent configuration.

        Args:
            task: Task description
            actions: Actions taken

        Returns:
            Output string
        """
        output_lines = []

        # Header with agent identity
        output_lines.append(f"# {self.name.replace('-', ' ').title()} Analysis")
        output_lines.append("")

        # Task
        output_lines.append(f"**Task**: {task}")
        output_lines.append("")

        # Mindset application
        if self.mindset:
            output_lines.append("## Approach")
            output_lines.append(self.mindset)
            output_lines.append("")

        # Actions taken
        if actions:
            output_lines.append("## Actions Taken")
            for i, action in enumerate(actions, 1):
                output_lines.append(f"{i}. {action}")
            output_lines.append("")

        # Expected outputs based on configuration
        if self.outputs:
            output_lines.append("## Deliverables")
            for output in self.outputs[:3]:  # Limit to first 3
                # Extract the main output type (before colon if present)
                output_type = output.split(':')[0].strip()
                output_lines.append(f"- {output_type}")
            output_lines.append("")

        # Tools used
        if self.tools:
            output_lines.append("## Tools Applied")
            output_lines.append(f"Utilized: {', '.join(self.tools)}")

        return '\n'.join(output_lines)

    def _matches_boundary(self, text: str, boundary: str) -> bool:
        """
        Check if text matches a boundary condition.

        Args:
            text: Text to check
            boundary: Boundary condition

        Returns:
            True if matches
        """
        # Simple keyword matching for now
        # Could be enhanced with more sophisticated matching
        keywords = re.findall(r'\b\w+\b', boundary)

        # Check if significant keywords appear in text
        matches = 0
        for keyword in keywords:
            if len(keyword) > 3 and keyword in text:  # Ignore short words
                matches += 1

        # Consider it a match if >50% of significant keywords match
        significant_keywords = [k for k in keywords if len(k) > 3]
        if significant_keywords:
            return matches / len(significant_keywords) > 0.5

        return False