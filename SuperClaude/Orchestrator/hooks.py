"""
SDK Hook Factories - Create hooks for the Official Anthropic Agent SDK.

These hooks integrate with the SDK's query() function to:
1. Collect evidence (files, tests, commands) via PostToolUse
2. Block dangerous operations via PreToolUse
3. Track session lifecycle via Stop/SubagentStop

Usage:
    from claude_agent_sdk import query, ClaudeAgentOptions

    evidence = EvidenceCollector()
    hooks = create_sdk_hooks(evidence)

    async for msg in query(prompt, options=ClaudeAgentOptions(hooks=hooks)):
        pass
"""

from typing import Any, Awaitable, Callable

from .evidence import EvidenceCollector

# Type alias for SDK hook callbacks
HookCallback = Callable[
    [dict[str, Any], str | None, dict[str, Any]],
    Awaitable[dict[str, Any]],
]


# Dangerous command patterns to block
DANGEROUS_PATTERNS = [
    "rm -rf /",
    "rm -rf /*",
    "rm -rf ~",
    ":(){:|:&};:",  # Fork bomb
    "dd if=/dev/zero",
    "mkfs.",
    "chmod 777 /",
    "chmod -R 777",
    "> /dev/sda",
    "git reset --hard",
    "git clean -fdx",
    "git push --force origin main",
    "git push --force origin master",
    "DROP TABLE",
    "DROP DATABASE",
    "DELETE FROM",
    "TRUNCATE TABLE",
]


def create_sdk_hooks(evidence: EvidenceCollector) -> dict[str, list[dict]]:
    """
    Create a complete set of SDK hooks for the agentic loop.

    Combines safety hooks (PreToolUse) and evidence hooks (PostToolUse).

    Args:
        evidence: EvidenceCollector instance to populate during execution

    Returns:
        Hook configuration dict for ClaudeAgentOptions
    """
    safety_hooks = create_safety_hooks()
    evidence_hooks = create_evidence_hooks(evidence)

    # Merge hook configurations
    return {
        "PreToolUse": safety_hooks.get("PreToolUse", [])
        + evidence_hooks.get("PreToolUse", []),
        "PostToolUse": safety_hooks.get("PostToolUse", [])
        + evidence_hooks.get("PostToolUse", []),
        "Stop": evidence_hooks.get("Stop", []),
        "SubagentStop": evidence_hooks.get("SubagentStop", []),
    }


def create_safety_hooks() -> dict[str, list[dict]]:
    """
    Create safety hooks that block dangerous operations.

    Returns:
        Hook configuration with PreToolUse blockers
    """

    async def block_dangerous_commands(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """PreToolUse: Block destructive Bash commands."""
        if input_data.get("hook_event_name") != "PreToolUse":
            return {}

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        if tool_name == "Bash":
            command = tool_input.get("command", "")

            for pattern in DANGEROUS_PATTERNS:
                if pattern.lower() in command.lower():
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": f"Blocked dangerous pattern: {pattern}",
                        }
                    }

        return {}

    async def validate_file_paths(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """PreToolUse: Validate file paths for Write/Edit operations."""
        if input_data.get("hook_event_name") != "PreToolUse":
            return {}

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        if tool_name in ("Write", "Edit"):
            file_path = tool_input.get("file_path", "")

            # Block writes to sensitive locations
            sensitive_paths = [
                "/etc/",
                "/usr/",
                "/bin/",
                "/sbin/",
                "/boot/",
                "/root/",
                "~/.ssh/",
                "~/.gnupg/",
                ".env",
                "credentials",
                "secrets",
            ]

            for sensitive in sensitive_paths:
                if sensitive in file_path:
                    return {
                        "hookSpecificOutput": {
                            "hookEventName": "PreToolUse",
                            "permissionDecision": "deny",
                            "permissionDecisionReason": f"Cannot write to sensitive path: {file_path}",
                        }
                    }

        return {}

    return {
        "PreToolUse": [
            {"matcher": "Bash", "hooks": [block_dangerous_commands]},
            {"matcher": "Write|Edit", "hooks": [validate_file_paths]},
        ]
    }


def create_evidence_hooks(evidence: EvidenceCollector) -> dict[str, list[dict]]:
    """
    Create evidence collection hooks.

    Args:
        evidence: EvidenceCollector instance to populate

    Returns:
        Hook configuration with PostToolUse collectors
    """

    async def collect_file_changes(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """PostToolUse: Track file modifications."""
        if input_data.get("hook_event_name") != "PostToolUse":
            return {}

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})

        file_path = tool_input.get("file_path", "")

        if tool_name == "Write":
            content = tool_input.get("content", "")
            lines = content.count("\n") + 1 if content else 0
            evidence.record_file_write(file_path, lines_changed=lines)

        elif tool_name == "Edit":
            # Estimate lines changed from old/new string lengths
            old_str = tool_input.get("old_string", "")
            new_str = tool_input.get("new_string", "")
            lines = abs(new_str.count("\n") - old_str.count("\n")) + 1
            evidence.record_file_edit(file_path, lines_changed=lines)

        elif tool_name == "Read":
            evidence.record_file_read(file_path)

        return {}

    async def collect_command_results(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """PostToolUse: Track command executions and parse test results."""
        if input_data.get("hook_event_name") != "PostToolUse":
            return {}

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", "")

        if tool_name == "Bash":
            command = tool_input.get("command", "")
            output = str(tool_response) if tool_response else ""

            # Record command (this also parses test output)
            evidence.record_command(command=command, output=output)

        return {}

    async def track_all_tools(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """PostToolUse: Record all tool invocations for debugging."""
        if input_data.get("hook_event_name") != "PostToolUse":
            return {}

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        tool_response = input_data.get("tool_response", "")

        evidence.record_tool_invocation(
            tool_name=tool_name,
            tool_input=tool_input,
            tool_output=tool_response,
        )

        return {}

    async def on_stop(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Stop: Finalize evidence collection."""
        if input_data.get("hook_event_name") != "Stop":
            return {}

        from datetime import datetime

        evidence.end_time = datetime.now()
        evidence.session_id = input_data.get("session_id", "")

        return {}

    async def on_subagent_stop(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """SubagentStop: Track subagent completions."""
        if input_data.get("hook_event_name") != "SubagentStop":
            return {}

        evidence.subagents_spawned += 1
        evidence.subagent_results.append(
            {
                "tool_use_id": tool_use_id,
                "stop_hook_active": input_data.get("stop_hook_active", False),
            }
        )

        return {}

    return {
        "PostToolUse": [
            {"matcher": "Write|Edit|Read", "hooks": [collect_file_changes]},
            {"matcher": "Bash", "hooks": [collect_command_results]},
            {"hooks": [track_all_tools]},  # No matcher = all tools
        ],
        "Stop": [{"hooks": [on_stop]}],
        "SubagentStop": [{"hooks": [on_subagent_stop]}],
    }


def create_logging_hooks(log_fn: Callable[[str], None]) -> dict[str, list[dict]]:
    """
    Create hooks that log all tool invocations.

    Args:
        log_fn: Function to call with log messages

    Returns:
        Hook configuration for logging
    """

    async def log_pre_tool(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """PreToolUse: Log tool invocation."""
        if input_data.get("hook_event_name") != "PreToolUse":
            return {}

        tool_name = input_data.get("tool_name", "")
        tool_input = input_data.get("tool_input", {})
        log_fn(f"[PRE] {tool_name}: {str(tool_input)[:100]}...")

        return {}

    async def log_post_tool(
        input_data: dict[str, Any],
        tool_use_id: str | None,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """PostToolUse: Log tool result."""
        if input_data.get("hook_event_name") != "PostToolUse":
            return {}

        tool_name = input_data.get("tool_name", "")
        tool_response = input_data.get("tool_response", "")
        log_fn(f"[POST] {tool_name}: {str(tool_response)[:100]}...")

        return {}

    return {
        "PreToolUse": [{"hooks": [log_pre_tool]}],
        "PostToolUse": [{"hooks": [log_post_tool]}],
    }


def merge_hooks(*hook_configs: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """
    Merge multiple hook configurations.

    Args:
        *hook_configs: Variable number of hook configuration dicts

    Returns:
        Merged configuration with all hooks combined
    """
    merged: dict[str, list[dict]] = {}

    for config in hook_configs:
        for event_name, matchers in config.items():
            if event_name not in merged:
                merged[event_name] = []
            merged[event_name].extend(matchers)

    return merged
