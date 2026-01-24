"""Tests for SDK hooks in SuperClaude.Orchestrator.hooks."""

import pytest

from SuperClaude.Orchestrator.evidence import EvidenceCollector
from SuperClaude.Orchestrator.hooks import (
    DANGEROUS_PATTERNS,
    create_evidence_hooks,
    create_logging_hooks,
    create_safety_hooks,
    create_sdk_hooks,
    merge_hooks,
)


class TestDangerousPatterns:
    """Tests for dangerous command patterns."""

    def test_dangerous_patterns_exists(self):
        """Test that dangerous patterns list exists."""
        assert len(DANGEROUS_PATTERNS) > 0

    def test_includes_rm_rf_root(self):
        """Test includes rm -rf / pattern."""
        assert "rm -rf /" in DANGEROUS_PATTERNS

    def test_includes_force_push_main(self):
        """Test includes force push to main."""
        assert "git push --force origin main" in DANGEROUS_PATTERNS

    def test_includes_drop_table(self):
        """Test includes DROP TABLE pattern."""
        assert "DROP TABLE" in DANGEROUS_PATTERNS


class TestCreateSafetyHooks:
    """Tests for create_safety_hooks function."""

    def test_returns_hook_config(self):
        """Test returns hook configuration dict."""
        hooks = create_safety_hooks()

        assert isinstance(hooks, dict)
        assert "PreToolUse" in hooks

    def test_pretooluse_has_matchers(self):
        """Test PreToolUse hooks have matchers."""
        hooks = create_safety_hooks()

        assert len(hooks["PreToolUse"]) > 0
        assert "matcher" in hooks["PreToolUse"][0]


class TestBlockDangerousCommands:
    """Tests for blocking dangerous bash commands."""

    @pytest.fixture
    def safety_hooks(self):
        """Create safety hooks."""
        return create_safety_hooks()

    @pytest.mark.asyncio
    async def test_blocks_rm_rf_root(self, safety_hooks):
        """Test blocks rm -rf / command."""
        hook_fn = safety_hooks["PreToolUse"][0]["hooks"][0]

        result = await hook_fn(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "rm -rf /"},
            },
            None,
            {},
        )

        assert "hookSpecificOutput" in result
        assert result["hookSpecificOutput"]["permissionDecision"] == "deny"

    @pytest.mark.asyncio
    async def test_blocks_git_reset_hard(self, safety_hooks):
        """Test blocks git reset --hard."""
        hook_fn = safety_hooks["PreToolUse"][0]["hooks"][0]

        result = await hook_fn(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "git reset --hard HEAD~5"},
            },
            None,
            {},
        )

        assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"

    @pytest.mark.asyncio
    async def test_allows_safe_commands(self, safety_hooks):
        """Test allows safe commands."""
        hook_fn = safety_hooks["PreToolUse"][0]["hooks"][0]

        result = await hook_fn(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "ls -la"},
            },
            None,
            {},
        )

        # Empty result means allow
        assert result == {}

    @pytest.mark.asyncio
    async def test_ignores_non_bash_tools(self, safety_hooks):
        """Test ignores non-Bash tools."""
        hook_fn = safety_hooks["PreToolUse"][0]["hooks"][0]

        result = await hook_fn(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "test.py"},
            },
            None,
            {},
        )

        assert result == {}


class TestValidateFilePaths:
    """Tests for file path validation hooks."""

    @pytest.fixture
    def safety_hooks(self):
        """Create safety hooks."""
        return create_safety_hooks()

    @pytest.mark.asyncio
    async def test_blocks_etc_writes(self, safety_hooks):
        """Test blocks writes to /etc/."""
        hook_fn = safety_hooks["PreToolUse"][1]["hooks"][0]

        result = await hook_fn(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Write",
                "tool_input": {"file_path": "/etc/passwd"},
            },
            None,
            {},
        )

        assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"

    @pytest.mark.asyncio
    async def test_blocks_ssh_writes(self, safety_hooks):
        """Test blocks writes to ~/.ssh/."""
        hook_fn = safety_hooks["PreToolUse"][1]["hooks"][0]

        result = await hook_fn(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Write",
                "tool_input": {"file_path": "~/.ssh/id_rsa"},
            },
            None,
            {},
        )

        assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"

    @pytest.mark.asyncio
    async def test_blocks_env_files(self, safety_hooks):
        """Test blocks writes to .env files."""
        hook_fn = safety_hooks["PreToolUse"][1]["hooks"][0]

        result = await hook_fn(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Write",
                "tool_input": {"file_path": "/project/.env"},
            },
            None,
            {},
        )

        assert result.get("hookSpecificOutput", {}).get("permissionDecision") == "deny"

    @pytest.mark.asyncio
    async def test_allows_safe_paths(self, safety_hooks):
        """Test allows safe file paths."""
        hook_fn = safety_hooks["PreToolUse"][1]["hooks"][0]

        result = await hook_fn(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Write",
                "tool_input": {"file_path": "/home/user/project/src/main.py"},
            },
            None,
            {},
        )

        assert result == {}


class TestCreateEvidenceHooks:
    """Tests for create_evidence_hooks function."""

    @pytest.fixture
    def evidence(self):
        """Create evidence collector."""
        return EvidenceCollector()

    def test_returns_hook_config(self, evidence):
        """Test returns hook configuration dict."""
        hooks = create_evidence_hooks(evidence)

        assert isinstance(hooks, dict)
        assert "PostToolUse" in hooks
        assert "Stop" in hooks
        assert "SubagentStop" in hooks

    def test_posttooluse_has_multiple_matchers(self, evidence):
        """Test PostToolUse has multiple matchers."""
        hooks = create_evidence_hooks(evidence)

        assert len(hooks["PostToolUse"]) >= 2


class TestCollectFileChanges:
    """Tests for file change collection hooks."""

    @pytest.fixture
    def evidence(self):
        """Create evidence collector."""
        return EvidenceCollector()

    @pytest.fixture
    def evidence_hooks(self, evidence):
        """Create evidence hooks."""
        return create_evidence_hooks(evidence)

    @pytest.mark.asyncio
    async def test_tracks_writes(self, evidence, evidence_hooks):
        """Test tracks file writes."""
        hook_fn = evidence_hooks["PostToolUse"][0]["hooks"][0]

        await hook_fn(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Write",
                "tool_input": {"file_path": "new.py", "content": "code\nmore code"},
            },
            None,
            {},
        )

        assert "new.py" in evidence.files_written

    @pytest.mark.asyncio
    async def test_tracks_edits(self, evidence, evidence_hooks):
        """Test tracks file edits."""
        hook_fn = evidence_hooks["PostToolUse"][0]["hooks"][0]

        await hook_fn(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": "existing.py",
                    "old_string": "old",
                    "new_string": "new",
                },
            },
            None,
            {},
        )

        assert "existing.py" in evidence.files_edited

    @pytest.mark.asyncio
    async def test_tracks_reads(self, evidence, evidence_hooks):
        """Test tracks file reads."""
        hook_fn = evidence_hooks["PostToolUse"][0]["hooks"][0]

        await hook_fn(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "readme.md"},
            },
            None,
            {},
        )

        assert "readme.md" in evidence.files_read


class TestCollectCommandResults:
    """Tests for command result collection hooks."""

    @pytest.fixture
    def evidence(self):
        """Create evidence collector."""
        return EvidenceCollector()

    @pytest.fixture
    def evidence_hooks(self, evidence):
        """Create evidence hooks."""
        return create_evidence_hooks(evidence)

    @pytest.mark.asyncio
    async def test_tracks_commands(self, evidence, evidence_hooks):
        """Test tracks bash commands."""
        hook_fn = evidence_hooks["PostToolUse"][1]["hooks"][0]

        await hook_fn(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "ls -la"},
                "tool_response": "file1.py\nfile2.py",
            },
            None,
            {},
        )

        assert len(evidence.commands_run) == 1
        assert evidence.commands_run[0].command == "ls -la"

    @pytest.mark.asyncio
    async def test_parses_test_output(self, evidence, evidence_hooks):
        """Test parses test output from commands."""
        hook_fn = evidence_hooks["PostToolUse"][1]["hooks"][0]

        await hook_fn(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Bash",
                "tool_input": {"command": "pytest tests/"},
                "tool_response": "===== 10 passed in 2.5s =====",
            },
            None,
            {},
        )

        assert evidence.tests_run is True
        assert len(evidence.test_results) == 1


class TestTrackAllTools:
    """Tests for tracking all tool invocations."""

    @pytest.fixture
    def evidence(self):
        """Create evidence collector."""
        return EvidenceCollector()

    @pytest.fixture
    def evidence_hooks(self, evidence):
        """Create evidence hooks."""
        return create_evidence_hooks(evidence)

    @pytest.mark.asyncio
    async def test_tracks_all_tools(self, evidence, evidence_hooks):
        """Test tracks all tool invocations."""
        # Get the hook without matcher (tracks all)
        hook_fn = evidence_hooks["PostToolUse"][2]["hooks"][0]

        await hook_fn(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Glob",
                "tool_input": {"pattern": "*.py"},
                "tool_response": ["a.py", "b.py"],
            },
            "tool-use-123",
            {},
        )

        assert len(evidence.tool_invocations) == 1
        assert evidence.tool_invocations[0]["tool_name"] == "Glob"


class TestSessionHooks:
    """Tests for session lifecycle hooks."""

    @pytest.fixture
    def evidence(self):
        """Create evidence collector."""
        return EvidenceCollector()

    @pytest.fixture
    def evidence_hooks(self, evidence):
        """Create evidence hooks."""
        return create_evidence_hooks(evidence)

    @pytest.mark.asyncio
    async def test_on_stop(self, evidence, evidence_hooks):
        """Test Stop hook sets end time."""
        hook_fn = evidence_hooks["Stop"][0]["hooks"][0]

        await hook_fn(
            {
                "hook_event_name": "Stop",
                "session_id": "session-123",
            },
            None,
            {},
        )

        assert evidence.end_time is not None
        assert evidence.session_id == "session-123"

    @pytest.mark.asyncio
    async def test_on_subagent_stop(self, evidence, evidence_hooks):
        """Test SubagentStop hook tracks subagents."""
        hook_fn = evidence_hooks["SubagentStop"][0]["hooks"][0]

        await hook_fn(
            {
                "hook_event_name": "SubagentStop",
                "stop_hook_active": True,
            },
            "subagent-tool-use-456",
            {},
        )

        assert evidence.subagents_spawned == 1
        assert len(evidence.subagent_results) == 1


class TestCreateSdkHooks:
    """Tests for create_sdk_hooks function."""

    def test_combines_safety_and_evidence(self):
        """Test combines safety and evidence hooks."""
        evidence = EvidenceCollector()
        hooks = create_sdk_hooks(evidence)

        assert "PreToolUse" in hooks
        assert "PostToolUse" in hooks
        assert "Stop" in hooks
        assert "SubagentStop" in hooks

    def test_pretooluse_has_safety_hooks(self):
        """Test PreToolUse includes safety hooks."""
        evidence = EvidenceCollector()
        hooks = create_sdk_hooks(evidence)

        # Should have multiple PreToolUse matchers
        assert len(hooks["PreToolUse"]) >= 2


class TestCreateLoggingHooks:
    """Tests for create_logging_hooks function."""

    def test_returns_hook_config(self):
        """Test returns hook configuration."""
        logs = []
        hooks = create_logging_hooks(logs.append)

        assert "PreToolUse" in hooks
        assert "PostToolUse" in hooks

    @pytest.mark.asyncio
    async def test_logs_pre_tool_use(self):
        """Test logs PreToolUse events."""
        logs = []
        hooks = create_logging_hooks(logs.append)
        hook_fn = hooks["PreToolUse"][0]["hooks"][0]

        await hook_fn(
            {
                "hook_event_name": "PreToolUse",
                "tool_name": "Read",
                "tool_input": {"file_path": "test.py"},
            },
            None,
            {},
        )

        assert len(logs) == 1
        assert "[PRE]" in logs[0]
        assert "Read" in logs[0]

    @pytest.mark.asyncio
    async def test_logs_post_tool_use(self):
        """Test logs PostToolUse events."""
        logs = []
        hooks = create_logging_hooks(logs.append)
        hook_fn = hooks["PostToolUse"][0]["hooks"][0]

        await hook_fn(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Read",
                "tool_response": "file contents",
            },
            None,
            {},
        )

        assert len(logs) == 1
        assert "[POST]" in logs[0]


class TestMergeHooks:
    """Tests for merge_hooks function."""

    def test_merges_pretooluse(self):
        """Test merges PreToolUse hooks."""
        config1 = {"PreToolUse": [{"matcher": "Bash", "hooks": ["hook1"]}]}
        config2 = {"PreToolUse": [{"matcher": "Write", "hooks": ["hook2"]}]}

        merged = merge_hooks(config1, config2)

        assert len(merged["PreToolUse"]) == 2

    def test_merges_different_events(self):
        """Test merges different event types."""
        config1 = {"PreToolUse": [{"hooks": ["hook1"]}]}
        config2 = {"PostToolUse": [{"hooks": ["hook2"]}]}

        merged = merge_hooks(config1, config2)

        assert "PreToolUse" in merged
        assert "PostToolUse" in merged

    def test_preserves_order(self):
        """Test preserves hook order."""
        config1 = {"PreToolUse": [{"hooks": ["first"]}]}
        config2 = {"PreToolUse": [{"hooks": ["second"]}]}

        merged = merge_hooks(config1, config2)

        assert merged["PreToolUse"][0]["hooks"] == ["first"]
        assert merged["PreToolUse"][1]["hooks"] == ["second"]

    def test_handles_empty_configs(self):
        """Test handles empty configurations."""
        config1 = {}
        config2 = {"PreToolUse": [{"hooks": ["hook"]}]}

        merged = merge_hooks(config1, config2)

        assert "PreToolUse" in merged
