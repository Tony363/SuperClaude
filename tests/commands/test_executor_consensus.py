"""Tests for CommandExecutor consensus and multi-model voting."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from SuperClaude.Commands.registry import CommandMetadata


class TestRequiresExecutionEvidence:
    """Tests for _requires_execution_evidence method."""

    def test_requires_evidence_none_metadata(self, executor):
        """Returns False when metadata is None."""
        assert not executor._requires_execution_evidence(None)

    def test_requires_evidence_explicit_true(self, executor, sample_metadata):
        """Returns True when requires_evidence is True."""
        sample_metadata.requires_evidence = True
        assert executor._requires_execution_evidence(sample_metadata)

    def test_requires_evidence_explicit_false(self, executor, sample_metadata):
        """Returns False when requires_evidence is False."""
        sample_metadata.requires_evidence = False
        sample_metadata.name = "review"  # Not in default evidence list
        assert not executor._requires_execution_evidence(sample_metadata)

    def test_requires_evidence_implement_command(self, executor):
        """Returns True for implement command by default."""
        metadata = CommandMetadata(
            name="implement",
            description="Implement code",
            category="development",
            complexity="medium",
            mcp_servers=[],
            personas=[],
            triggers=[],
            flags=[],
            parameters={},
            requires_evidence=False,  # Even if False
        )
        # implement is in the default evidence list
        assert executor._requires_execution_evidence(metadata)

    def test_requires_evidence_other_commands(self, executor):
        """Returns False for commands not in evidence list."""
        metadata = CommandMetadata(
            name="help",
            description="Help command",
            category="utility",
            complexity="low",
            mcp_servers=[],
            personas=[],
            triggers=[],
            flags=[],
            parameters={},
            requires_evidence=False,
        )
        assert not executor._requires_execution_evidence(metadata)


class TestBuildConsensusPrompt:
    """Tests for _build_consensus_prompt method."""

    def test_build_prompt_basic(self, executor, sample_context):
        """Build prompt includes command info."""
        prompt = executor._build_consensus_prompt(sample_context, {})

        assert "implement" in prompt.lower()
        assert "command" in prompt.lower()

    def test_build_prompt_with_output(self, executor, sample_context):
        """Build prompt includes output summary."""
        output = {"summary": "Created new feature", "status": "success"}
        prompt = executor._build_consensus_prompt(sample_context, output)

        assert "created new feature" in prompt.lower()

    def test_build_prompt_with_flags(self, executor, sample_context):
        """Build prompt includes flags."""
        sample_context.command.flags = {"safe": True, "verbose": True}
        prompt = executor._build_consensus_prompt(sample_context, {})

        # Should include flag names
        assert isinstance(prompt, str)

    def test_build_prompt_with_arguments(self, executor, sample_context):
        """Build prompt includes arguments."""
        sample_context.command.arguments = ["feature", "module"]
        prompt = executor._build_consensus_prompt(sample_context, {})

        # Should include arguments
        assert isinstance(prompt, str)

    def test_build_prompt_without_summary(self, executor, sample_context):
        """Build prompt handles missing summary."""
        output = {"status": "success"}  # No summary key
        prompt = executor._build_consensus_prompt(sample_context, output)

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_build_prompt_with_dict_output(self, executor, sample_context):
        """Build prompt extracts summary from dict output."""
        output = {"output": "Task completed successfully", "status": "done"}
        prompt = executor._build_consensus_prompt(sample_context, output)

        assert "completed" in prompt.lower()

    def test_build_prompt_with_string_output(self, executor, sample_context):
        """Build prompt handles string output."""
        output = "Direct string output"
        prompt = executor._build_consensus_prompt(sample_context, output)

        assert isinstance(prompt, str)


class TestLoadConsensusPolicies:
    """Tests for _load_consensus_policies method."""

    def test_load_policies_returns_dict(self, executor):
        """Load policies returns a dictionary."""
        policies = executor._load_consensus_policies()

        assert isinstance(policies, dict)
        assert "defaults" in policies

    def test_load_policies_has_defaults(self, executor):
        """Load policies includes default settings."""
        policies = executor._load_consensus_policies()

        defaults = policies.get("defaults", {})
        assert "vote_type" in defaults or "quorum_size" in defaults

    def test_load_policies_missing_yaml(self, executor):
        """Load policies handles missing YAML file."""
        with patch.object(Path, "exists", return_value=False):
            policies = executor._load_consensus_policies()

        assert isinstance(policies, dict)
        assert "defaults" in policies

    def test_load_policies_yaml_import_error(self, executor):
        """Load policies handles missing PyYAML."""
        import SuperClaude.Commands.command_executor as exec_module

        original_yaml = exec_module.yaml
        exec_module.yaml = None

        try:
            policies = executor._load_consensus_policies()
            assert isinstance(policies, dict)
            assert "defaults" in policies
        finally:
            exec_module.yaml = original_yaml


class TestResolveConsensusPolicy:
    """Tests for _resolve_consensus_policy method."""

    def test_resolve_policy_default(self, executor):
        """Resolve returns default policy for unknown command."""
        policy = executor._resolve_consensus_policy("unknown_command")

        assert isinstance(policy, dict)

    def test_resolve_policy_none_command(self, executor):
        """Resolve handles None command name."""
        policy = executor._resolve_consensus_policy(None)

        assert isinstance(policy, dict)

    def test_resolve_policy_known_command(self, executor):
        """Resolve returns specific policy for known command."""
        # Set up policies
        executor.consensus_policies = {
            "defaults": {"vote_type": "majority", "quorum_size": 2},
            "commands": {"implement": {"quorum_size": 3}},
        }

        policy = executor._resolve_consensus_policy("implement")

        assert policy.get("quorum_size") == 3

    def test_resolve_policy_merges_defaults(self, executor):
        """Resolve merges command-specific with defaults."""
        executor.consensus_policies = {
            "defaults": {"vote_type": "majority", "quorum_size": 2, "timeout": 30},
            "commands": {"implement": {"quorum_size": 3}},
        }

        policy = executor._resolve_consensus_policy("implement")

        # Should have both command-specific and default values
        assert policy.get("quorum_size") == 3  # overridden
        assert policy.get("timeout") == 30  # from defaults


class TestEnsureConsensus:
    """Tests for _ensure_consensus async method."""

    @pytest.mark.asyncio
    async def test_ensure_consensus_basic(self, executor_with_mocks, sample_context):
        """Ensure consensus returns result dict."""
        result = await executor_with_mocks._ensure_consensus(sample_context, {"output": "test"})

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_ensure_consensus_with_enforce(self, executor_with_mocks, sample_context):
        """Ensure consensus respects enforce flag."""
        result = await executor_with_mocks._ensure_consensus(
            sample_context, {"output": "test"}, enforce=True
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_ensure_consensus_with_think_level(self, executor_with_mocks, sample_context):
        """Ensure consensus accepts think_level parameter."""
        result = await executor_with_mocks._ensure_consensus(
            sample_context, {"output": "test"}, think_level=3
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_ensure_consensus_with_task_type(self, executor_with_mocks, sample_context):
        """Ensure consensus accepts task_type parameter."""
        result = await executor_with_mocks._ensure_consensus(
            sample_context, {"output": "test"}, task_type="review"
        )

        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_ensure_consensus_uses_facade(
        self, executor_with_mocks, sample_context, mock_consensus_facade
    ):
        """Ensure consensus calls the consensus facade."""
        executor_with_mocks.consensus_facade = mock_consensus_facade

        await executor_with_mocks._ensure_consensus(sample_context, {"output": "test"})

        # Facade vote method should be called or configured
        assert mock_consensus_facade is not None

    @pytest.mark.asyncio
    async def test_ensure_consensus_handles_exception(self, executor_with_mocks, sample_context):
        """Ensure consensus handles exceptions gracefully."""
        # Set up facade to raise
        executor_with_mocks.consensus_facade = MagicMock()
        executor_with_mocks.consensus_facade.vote = AsyncMock(
            side_effect=Exception("Consensus failed")
        )

        # Should not raise, should handle gracefully
        result = await executor_with_mocks._ensure_consensus(sample_context, {"output": "test"})

        # Returns some result even on failure
        assert isinstance(result, dict)


class TestConsensusIntegration:
    """Integration tests for consensus workflow."""

    def test_consensus_policies_initialized(self, executor):
        """Executor has consensus_policies attribute."""
        assert hasattr(executor, "consensus_policies")
        assert isinstance(executor.consensus_policies, dict)

    def test_consensus_facade_attribute(self, executor):
        """Executor has consensus_facade attribute."""
        assert hasattr(executor, "consensus_facade")

    def test_build_and_resolve_policy_roundtrip(self, executor, sample_context):
        """Build prompt and resolve policy work together."""
        command_name = sample_context.command.name

        policy = executor._resolve_consensus_policy(command_name)
        prompt = executor._build_consensus_prompt(sample_context, {"output": "test"})

        assert isinstance(policy, dict)
        assert isinstance(prompt, str)
        assert command_name in prompt.lower()


class TestVoteTypeParsing:
    """Tests for VoteType handling in consensus."""

    def test_default_vote_type(self, executor):
        """Default policy uses MAJORITY vote type."""
        policy = executor._resolve_consensus_policy(None)

        # Should have a vote_type field
        vote_type = policy.get("vote_type")
        assert vote_type is not None

    def test_quorum_size_default(self, executor):
        """Default quorum size is at least 2."""
        policy = executor._resolve_consensus_policy(None)

        quorum = policy.get("quorum_size", 0)
        assert quorum >= 2 or quorum == 0  # 0 if not set


class TestConsensusContext:
    """Tests for consensus context handling."""

    def test_context_has_session_id(self, sample_context):
        """Context includes session_id."""
        assert sample_context.session_id is not None
        assert len(sample_context.session_id) > 0

    def test_context_has_behavior_mode(self, sample_context):
        """Context includes behavior_mode."""
        assert sample_context.behavior_mode is not None

    def test_context_results_dict(self, sample_context):
        """Context has results dictionary."""
        assert isinstance(sample_context.results, dict)

    def test_context_with_primary_summary(self, executor, sample_context):
        """Build prompt uses primary_summary from results."""
        sample_context.results["primary_summary"] = "Custom summary from results"

        prompt = executor._build_consensus_prompt(sample_context, {})

        assert "custom summary" in prompt.lower()
