"""
Generic Markdown Agent for SuperClaude Framework

This module provides a generic agent implementation that works with
any agent defined in markdown without requiring a specific Python class.
"""

from typing import Dict, Any, List, Iterable, Optional
import re
from datetime import datetime
from pathlib import Path
import textwrap

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
            'planned_actions': [],
            'warnings': [],
            'errors': [],
            'status': 'plan-only'
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
            parameters = context.get('parameters', {})

            # Build execution plan based on key actions
            execution_plan = self._build_execution_plan(task, parameters)
            result['planned_actions'] = execution_plan

            executed_operations = self._extract_executed_operations(context)

            synthesized_changes = self._synthesise_change_plan(
                context,
                task,
                execution_plan,
                executed_operations
            )

            if synthesized_changes:
                result['proposed_changes'] = synthesized_changes
                result['auto_generated_stub'] = True
                result['actions_taken'].extend(
                    f"write {change['path']}" for change in synthesized_changes
                )
                if executed_operations:
                    result['actions_taken'].extend(executed_operations)
                result['output'] = self._generate_output(
                    task,
                    execution_plan,
                    result['actions_taken']
                )
                result['success'] = True
                result['status'] = 'executed'
            elif executed_operations:
                result['actions_taken'].extend(executed_operations)
                result['output'] = self._generate_output(
                    task,
                    execution_plan,
                    executed_operations
                )
                result['success'] = True
                result['status'] = 'executed'
            else:
                result['warnings'].append(
                    "No concrete file or command changes detected; returning plan-only guidance."
                )
                result['output'] = self._generate_plan_output(task, execution_plan)

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

    def _generate_output(
        self,
        task: str,
        planned_actions: List[str],
        executed_operations: List[str]
    ) -> str:
        """
        Generate output summarizing both the plan and executed work.

        Args:
            task: Task description
            planned_actions: Planned steps
            executed_operations: Concrete operations supplied in context

        Returns:
            Output string
        """
        output_lines: List[str] = []

        output_lines.append(f"# {self.name.replace('-', ' ').title()} Summary")
        output_lines.append("")
        output_lines.append(f"**Task**: {task}")
        output_lines.append("")

        if self.mindset:
            output_lines.append("## Approach")
            output_lines.append(self.mindset)
            output_lines.append("")

        if executed_operations:
            output_lines.append("## Confirmed Execution")
            for i, op in enumerate(executed_operations, 1):
                output_lines.append(f"{i}. {op}")
            output_lines.append("")

        if planned_actions:
            output_lines.append("## Remaining Plan")
            for i, action in enumerate(planned_actions, 1):
                output_lines.append(f"{i}. {action}")
            output_lines.append("")

        if self.outputs:
            output_lines.append("## Expected Deliverables")
            for output in self.outputs[:3]:
                output_type = output.split(':')[0].strip()
                output_lines.append(f"- {output_type}")
            output_lines.append("")

        if self.tools:
            output_lines.append("## Tools Suggested")
            output_lines.append(f"Recommended: {', '.join(self.tools)}")

        return '\n'.join(output_lines)

    def _generate_plan_output(self, task: str, planned_actions: List[str]) -> str:
        """
        Generate plan-only output when no execution evidence is present.

        Args:
            task: Task description
            planned_actions: Planned steps

        Returns:
            Output string
        """
        output_lines: List[str] = []

        output_lines.append(f"# {self.name.replace('-', ' ').title()} Plan")
        output_lines.append("")
        output_lines.append(f"**Task**: {task}")
        output_lines.append("")

        output_lines.append("⚠️ No concrete repository changes were executed by this agent. "
                            "Below is a recommended plan for manual follow-up.")
        output_lines.append("")

        if planned_actions:
            output_lines.append("## Proposed Steps")
            for i, action in enumerate(planned_actions, 1):
                output_lines.append(f"{i}. {action}")
            output_lines.append("")

        if self.tools:
            output_lines.append("## Suggested Tools")
            output_lines.append(f"Use: {', '.join(self.tools)}")

        if self.outputs:
            output_lines.append("## Expected Deliverables")
            for output in self.outputs[:3]:
                output_lines.append(f"- {output.split(':')[0].strip()}")

        return '\n'.join(output_lines)

    def _extract_executed_operations(self, context: Dict[str, Any]) -> List[str]:
        """
        Extract concrete operations from execution context.

        Args:
            context: Execution context

        Returns:
            List of executed operation descriptions
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

    # --- Change synthesis helpers -------------------------------------------------

    def _synthesise_change_plan(
        self,
        context: Dict[str, Any],
        task: str,
        planned_actions: List[str],
        executed_operations: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Best-effort synthesis of a concrete change plan so downstream components
        apply tangible repo edits instead of plan-only guidance.
        """
        change_entries: List[Dict[str, Any]] = []

        provided_changes = context.get('proposed_changes') or context.get('changes')
        if isinstance(provided_changes, list):
            for entry in provided_changes:
                if isinstance(entry, dict) and entry.get('path') and 'content' in entry:
                    change_entries.append({
                        'path': str(entry['path']),
                        'content': entry.get('content', ''),
                        'mode': entry.get('mode', 'replace')
                    })
            if change_entries:
                return change_entries

        if executed_operations:
            return change_entries

        stub_extension = self._infer_extension(context, task)
        stub_path = self._build_stub_path(task, stub_extension)
        stub_content = self._render_stub_content(
            task=task,
            planned_actions=planned_actions,
            extension=stub_extension,
        )

        change_entries.append({
            'path': stub_path,
            'content': stub_content,
            'mode': 'replace'
        })

        return change_entries

    def _infer_extension(self, context: Dict[str, Any], task: str) -> str:
        """Infer file extension for generated stub."""
        parameters = context.get('parameters', {}) or {}
        framework = str(parameters.get('framework') or '').lower()
        language = str(parameters.get('language') or '').lower()
        request = f"{task} {' '.join(context.get('flags', []))} {framework} {language}".lower()

        def has_any(*needles: str) -> bool:
            return any(needle in request for needle in needles)

        if has_any('readme', 'docs', 'documentation', 'spec', 'note', 'adr'):
            return 'md'
        if framework in {'react', 'next', 'nextjs'} or has_any('component', 'frontend', 'ui', 'tsx'):
            return 'tsx'
        if framework == 'vue' or has_any('vue'):
            return 'vue'
        if framework in {'svelte', 'solid'} or has_any('svelte'):
            return 'svelte'
        if framework in {'express', 'node'} or has_any('typescript', 'ts', 'lambda', 'api endpoint'):
            return 'ts'
        if framework in {'go', 'golang'} or has_any('golang', ' go'):
            return 'go'
        if framework in {'rust'} or has_any(' rust', 'rust '):
            return 'rs'
        if framework in {'java', 'spring'} or has_any('java ', 'spring'):
            return 'java'
        if framework in {'csharp', '.net', 'dotnet'} or has_any('c#', 'csharp', '.net', 'dotnet'):
            return 'cs'

        if isinstance(self.default_extension, str) and self.default_extension:
            return self.default_extension

        if has_any('frontend', 'javascript', 'typescript'):
            return 'ts'

        return 'py'

    def _build_stub_path(self, task: str, extension: str) -> str:
        """Construct stub file path under SuperClaude/Implementation/Auto."""
        slug = self._slugify(task or self.name)
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        file_name = f"{slug}-{timestamp}.{extension}"
        subdir = self._slugify(self.category or "general")
        rel_path = Path('SuperClaude') / 'Implementation' / 'Auto' / subdir / file_name
        return str(rel_path)

    def _render_stub_content(
        self,
        task: str,
        planned_actions: List[str],
        extension: str,
    ) -> str:
        """Render language-appropriate stub content describing the plan."""
        plan_lines = [line.strip() for line in planned_actions if line and line.strip()]
        timestamp = datetime.utcnow().isoformat()
        agent_name = self.name.replace('-', ' ').title()

        if extension == 'py':
            function_name = self._to_snake(self._slugify(task or agent_name))
            plan_comment = '\n'.join(f"#  - {step}" for step in plan_lines) or "#  - flesh out behaviour"
            return textwrap.dedent(f"""
                \"\"\"Auto-generated implementation stub for {task or agent_name}.

                Generated by {agent_name} on {timestamp}. Replace with real implementation.
                \"\"\"

                from __future__ import annotations


                # TODO: follow the implementation plan
                {plan_comment}


                def {function_name}() -> None:
                    \"\"\"Replace with actual logic for {task or 'this task'}.\"
                    \"\"\"
                    raise NotImplementedError(
                        "Auto-generated stub created by SuperClaude; implement actual behaviour."
                    )
            """).strip() + "\n"

        if extension in {'ts', 'tsx'}:
            component_name = self._to_pascal(self._slugify(task or agent_name) or "AutoComponent")
            plan_comment = '\n'.join(f" *  - {step}" for step in plan_lines) or " *  - flesh out behaviour"
            if extension == 'tsx':
                body = textwrap.dedent(f"""
                    import React from 'react';

                    export function {component_name}(): React.ReactElement {{
                      return (
                        <div className="auto-generated">
                          TODO: Replace with real implementation for {task or agent_name}.
                        </div>
                      );
                    }}
                """).strip()
            else:
                body = textwrap.dedent(f"""
                    export function {component_name}(): void {{
                      throw new Error('Auto-generated stub for {task or agent_name}');
                    }}
                """).strip()

            return textwrap.dedent(f"""
                /**
                 * Auto-generated implementation stub for {task or agent_name}.
                 * Generated: {timestamp}
                 * Plan:
{plan_comment}
                 */
                {body}
            """).strip() + "\n"

        if extension == 'md':
            plan_section = '\n'.join(f"- {step}" for step in plan_lines) or "- Flesh out the behaviour."
            return textwrap.dedent(f"""
                # Auto-generated Implementation Stub

                - Agent: {agent_name}
                - Generated: {timestamp}
                - Task: {task or 'unspecified'}

                ## Recommended Steps
                {plan_section}

                Replace this stub with detailed documentation once the work is complete.
            """).strip() + "\n"

        plan_comment = '\n'.join(f"//  - {step}" for step in plan_lines) or "//  - flesh out behaviour"
        function_name = self._to_pascal(self._slugify(task or agent_name) or "AutoStub")
        return textwrap.dedent(f"""
            // Auto-generated implementation stub for {task or agent_name}
            // Generated: {timestamp}
            // Plan:
            {plan_comment}

            function {function_name}() {{
              throw new Error("Auto-generated stub created by SuperClaude; replace with real code.");
            }}
        """).strip() + "\n"

    @staticmethod
    def _slugify(value: str) -> str:
        sanitized = ''.join(ch if ch.isalnum() or ch in {'-', '_'} else '-' for ch in value.lower())
        sanitized = '-'.join(part for part in sanitized.split('-') if part)
        return sanitized or 'auto-task'

    @staticmethod
    def _to_snake(value: str) -> str:
        return value.replace('-', '_')

    @staticmethod
    def _to_pascal(value: str) -> str:
        parts = [part for part in value.replace('_', '-').split('-') if part]
        return ''.join(part.capitalize() for part in parts) or 'AutoStub'
