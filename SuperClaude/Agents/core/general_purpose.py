"""
General Purpose Agent for SuperClaude Framework

This agent serves as the default fallback and can handle a wide variety
of tasks by delegating to specialized agents when appropriate.
"""

from typing import Dict, Any, List, Optional
import logging

from ..base import BaseAgent
from ..selector import AgentSelector
from ..registry import AgentRegistry


class GeneralPurposeAgent(BaseAgent):
    """
    General purpose agent that can handle various tasks.

    This agent serves as the primary entry point for task delegation
    and can either handle tasks directly or delegate to specialists.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the general purpose agent.

        Args:
            config: Agent configuration
        """
        # Ensure proper configuration
        if 'name' not in config:
            config['name'] = 'general-purpose'
        if 'description' not in config:
            config['description'] = 'General purpose agent for various tasks'
        if 'category' not in config:
            config['category'] = 'general'

        super().__init__(config)

        # Components for delegation
        self.registry = None
        self.selector = None

        # Delegation settings
        self.max_delegation_depth = 3
        self.delegation_confidence_threshold = 0.6

    def _setup(self):
        """Initialize delegation components."""
        try:
            self.registry = AgentRegistry()
            self.selector = AgentSelector(self.registry)
            self.logger.info("Delegation components initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize delegation: {e}")
            # Can still function without delegation

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute task with optional delegation to specialists.

        Args:
            context: Execution context

        Returns:
            Execution results
        """
        result = {
            'success': False,
            'output': '',
            'actions_taken': [],
            'errors': [],
            'delegated_to': None
        }

        try:
            # Initialize if needed
            if not self._initialized:
                if not self.initialize():
                    result['errors'].append("Failed to initialize agent")
                    return result

            task = context.get('task', '')
            if not task:
                result['errors'].append("No task provided")
                return result

            # Log the task
            self.logger.info(f"Processing task: {task[:100]}...")

            # Check if we should delegate
            delegation_result = self._consider_delegation(task, context)

            if delegation_result['should_delegate']:
                # Delegate to specialist
                result.update(self._delegate_task(
                    delegation_result['agent_name'],
                    context
                ))
                result['delegated_to'] = delegation_result['agent_name']
            else:
                # Handle directly
                result.update(self._handle_directly(task, context, delegation_result))

            # Log execution
            self.log_execution(context, result)

        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            result['errors'].append(str(e))

        return result

    def validate(self, context: Dict[str, Any]) -> bool:
        """
        General purpose agent can handle any context.

        Args:
            context: Validation context

        Returns:
            Always returns True
        """
        return True

    def _consider_delegation(
        self, task: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Consider whether to delegate task to a specialist.

        Args:
            task: Task description
            context: Execution context

        Returns:
            Dictionary with delegation decision
        """
        decision = {
            'should_delegate': False,
            'agent_name': None,
            'confidence': 0.0,
            'reason': '',
            'suggestions': []
        }

        # Skip delegation if components not available
        if not self.selector:
            decision['reason'] = "Delegation not available"
            return decision

        # Check delegation depth to prevent infinite loops
        current_depth = context.get('delegation_depth', 0)
        if current_depth >= self.max_delegation_depth:
            decision['reason'] = f"Max delegation depth ({self.max_delegation_depth}) reached"
            return decision

        # Get agent suggestions
        suggestions = self.selector.get_agent_suggestions(task, top_n=3)
        decision['suggestions'] = suggestions

        if suggestions:
            # Check top suggestion
            agent_name, confidence = suggestions[0]

            # Don't delegate to self
            if agent_name == self.name:
                if len(suggestions) > 1:
                    agent_name, confidence = suggestions[1]
                else:
                    decision['reason'] = "No suitable specialist found"
                    return decision

            # Check confidence threshold
            if confidence >= self.delegation_confidence_threshold:
                decision['should_delegate'] = True
                decision['agent_name'] = agent_name
                decision['confidence'] = confidence
                decision['reason'] = f"High confidence match ({confidence:.2f})"
            else:
                decision['reason'] = f"Confidence too low ({confidence:.2f})"
        else:
            decision['reason'] = "No matching specialists"
            decision['suggestions'] = suggestions

        return decision

    def _delegate_task(
        self, agent_name: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Delegate task to another agent.

        Args:
            agent_name: Name of agent to delegate to
            context: Execution context

        Returns:
            Delegation results
        """
        self.logger.info(f"Delegating to {agent_name}")

        try:
            # Get the agent
            agent = self.registry.get_agent(agent_name)

            if not agent:
                return {
                    'success': False,
                    'errors': [f"Failed to load agent: {agent_name}"]
                }

            # Update context with delegation depth
            delegated_context = context.copy()
            delegated_context['delegation_depth'] = context.get('delegation_depth', 0) + 1
            delegated_context['delegated_from'] = self.name

            # Execute delegated task
            result = agent.execute(delegated_context)

            # Add delegation info to actions
            if 'actions_taken' in result:
                result['actions_taken'].insert(
                    0, f"Delegated to {agent_name}"
                )

            return result

        except Exception as e:
            self.logger.error(f"Delegation failed: {e}")
            return {
                'success': False,
                'errors': [f"Delegation error: {str(e)}"]
            }

    def _handle_directly(
        self,
        task: str,
        context: Dict[str, Any],
        delegation_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle task directly without delegation.

        Args:
            task: Task description
            context: Execution context

        Returns:
            Direct handling results
        """
        self.logger.debug("Handling task directly")

        # Basic task handling logic
        planned_steps = []
        output_lines = []

        # Analyze task
        planned_steps.append("Analyze task requirements")
        output_lines.append(f"# Task Analysis\n\nTask: {task}\n")

        # Determine approach based on keywords
        task_lower = task.lower()

        if any(word in task_lower for word in ['implement', 'create', 'build', 'develop']):
            planned_steps.append("Identify task as implementation work")
            output_lines.append("\n## Approach\nImplementation strategy required.\n")
            output_lines.append("\n## Steps\n1. Design component structure\n2. Implement core functionality\n3. Add error handling\n4. Create tests\n")

        elif any(word in task_lower for word in ['fix', 'debug', 'solve', 'issue']):
            planned_steps.append("Identify task as debugging work")
            output_lines.append("\n## Approach\nDebugging strategy required.\n")
            output_lines.append("\n## Steps\n1. Reproduce issue\n2. Identify root cause\n3. Implement fix\n4. Verify solution\n")

        elif any(word in task_lower for word in ['analyze', 'review', 'evaluate']):
            planned_steps.append("Identify task as analysis work")
            output_lines.append("\n## Approach\nAnalysis strategy required.\n")
            output_lines.append("\n## Steps\n1. Gather information\n2. Analyze patterns\n3. Draw conclusions\n4. Provide recommendations\n")

        else:
            planned_steps.append("Apply general problem-solving approach")
            output_lines.append("\n## Approach\nGeneral problem-solving strategy.\n")
            output_lines.append("\n## Steps\n1. Understand requirements\n2. Plan approach\n3. Execute solution\n4. Validate results\n")

        # Add tools information
        if self.tools:
            planned_steps.append(f"Identify available tools: {', '.join(self.tools)}")
            output_lines.append(f"\n## Available Tools\n{', '.join(self.tools)}\n")

        # Context information
        files = context.get('files', [])
        if files:
            planned_steps.append(f"Review {len(files)} relevant files")
            output_lines.append(f"\n## Relevant Files\n")
            for file in files[:5]:  # List first 5
                output_lines.append(f"- {file}\n")

        executed_ops = self._extract_executed_operations(context)
        warnings = []
        success = False
        status = 'plan-only'
        actions_taken: List[str] = []

        if executed_ops:
            success = True
            status = 'executed'
            actions_taken.extend(executed_ops)
        else:
            warning_msg = "No concrete repository operations were executed; escalating to follow-up."
            warnings.append(warning_msg)
            status = 'followup'
            success = False

        response_body = self._render_direct_response(
            task,
            ''.join(output_lines),
            planned_steps,
            executed_ops
        )

        result_payload: Dict[str, Any] = {
            'success': success,
            'status': status,
            'output': response_body,
            'actions_taken': actions_taken,
            'planned_actions': planned_steps,
            'warnings': warnings,
            'errors': []
        }

        if status == 'followup':
            followup_reason = delegation_result.get('reason') or "General-purpose agent could not perform the requested work."
            suggestions = delegation_result.get('suggestions') or self.selector.get_agent_suggestions(task, top_n=3)
            if suggestions:
                suggested_agents = [name for name, _ in suggestions if name != self.name]
            else:
                suggested_agents = []

            if suggested_agents:
                followup_reason = (
                    f"{followup_reason} Recommended specialists: {', '.join(suggested_agents[:3])}."
                )
                result_payload['followup_suggestions'] = suggested_agents

            result_payload['requires_followup'] = followup_reason

        return result_payload

    def _extract_executed_operations(self, context: Dict[str, Any]) -> List[str]:
        """
        Extract evidence of executed work from context.

        Args:
            context: Execution context

        Returns:
            List of executed operations
        """
        executed: List[str] = []
        candidate_keys = [
            'executed_operations',
            'applied_changes',
            'files_modified',
            'commands_run',
            'diff_summary'
        ]

        for key in candidate_keys:
            value = context.get(key)
            if isinstance(value, list):
                executed.extend(str(item) for item in value if item)
            elif isinstance(value, dict):
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, list):
                        executed.extend(f"{subkey}: {item}" for item in subvalue if item)
                    elif subvalue:
                        executed.append(f"{subkey}: {subvalue}")
            elif isinstance(value, str) and value.strip():
                executed.append(value.strip())

        return executed

    def _render_direct_response(
        self,
        task: str,
        analysis: str,
        planned_steps: List[str],
        executed_ops: List[str]
    ) -> str:
        """
        Render the response combining analysis, plan, and execution evidence.

        Args:
            task: Task description
            analysis: Narrative analysis text
            planned_steps: Planned actions
            executed_ops: Executed operations

        Returns:
            Response string
        """
        sections: List[str] = []
        sections.append(f"# General Purpose Agent Summary\n\n**Task**: {task}\n")
        sections.append(analysis)

        if executed_ops:
            sections.append("\n## Confirmed Execution\n")
            for idx, op in enumerate(executed_ops, 1):
                sections.append(f"{idx}. {op}\n")

        if planned_steps:
            sections.append("\n## Next Actions\n")
            for idx, step in enumerate(planned_steps, 1):
                sections.append(f"{idx}. {step}\n")

        if not executed_ops:
            sections.append(
                "\n⚠️ No code changes were applied. Use the plan above to perform the work manually and "
                "rerun validation once concrete changes exist.\n"
            )

        return ''.join(sections)

    def get_capabilities(self) -> List[str]:
        """
        Return general purpose capabilities.

        Returns:
            List of capabilities
        """
        capabilities = super().get_capabilities()

        # Add delegation capability
        capabilities.insert(0, "Task delegation: Can identify and delegate to specialists")
        capabilities.insert(1, "Universal handling: Can process any type of task")

        return capabilities
