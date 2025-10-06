"""
Test model router functionality.
"""

import pytest
from pathlib import Path
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from SuperClaude.ModelRouter import (
    ModelRouter,
    RoutingDecision,
    ModelManager,
    ConsensusBuilder,
    VoteType,
    Stance
)


class TestModelRouter:
    """Test model routing functionality."""

    def test_standard_routing(self):
        """Test standard model routing."""
        router = ModelRouter()

        # Route standard task
        decision = router.route(task_type='standard')
        assert decision.primary_model in ['gpt-4o', 'claude-opus-4.1', 'gpt-5']
        assert len(decision.fallback_chain) > 0
        assert decision.confidence > 0

    def test_deep_thinking_routing(self):
        """Test routing for deep thinking tasks."""
        router = ModelRouter()

        # Route deep thinking task
        decision = router.route(task_type='deep_thinking', think_level=3)
        assert decision.primary_model in ['gpt-5', 'claude-opus-4.1']
        assert decision.token_budget >= 50000

    def test_long_context_routing(self):
        """Test routing for long context."""
        router = ModelRouter()

        # Route with large context
        decision = router.route(context_size=500000)
        assert decision.primary_model in ['gemini-2.5-pro', 'gpt-4.1', 'gpt-5']
        assert 'Long context' in decision.reason

    def test_force_model(self):
        """Test forcing specific model."""
        router = ModelRouter()

        # Force specific model
        decision = router.route(force_model='gpt-5')
        assert decision.primary_model == 'gpt-5'
        assert 'Forced' in decision.reason

    def test_exclude_models(self):
        """Test excluding models from selection."""
        router = ModelRouter()

        # Exclude models
        excluded = ['gpt-5', 'gemini-2.5-pro']
        decision = router.route(excluded_models=excluded)
        assert decision.primary_model not in excluded
        assert all(m not in excluded for m in decision.fallback_chain)

    def test_ensemble_generation(self):
        """Test ensemble generation for consensus."""
        router = ModelRouter()

        # Generate ensemble
        ensemble = router.get_ensemble(size=3)
        assert len(ensemble) <= 3
        assert len(set(ensemble)) == len(ensemble)  # No duplicates

    def test_availability_tracking(self):
        """Test model availability tracking."""
        router = ModelRouter()

        # Mark model unavailable
        router.mark_unavailable('gpt-5', duration=timedelta(seconds=10))

        # Check availability
        assert not router._is_available('gpt-5')

        # Route should avoid unavailable model
        decision = router.route(task_type='deep_thinking')
        assert decision.primary_model != 'gpt-5'


class TestModelManager:
    """Test model configuration management."""

    def test_default_configs(self):
        """Test default model configurations."""
        manager = ModelManager()

        # Check default models exist
        assert manager.get_config('gpt-5') is not None
        assert manager.get_config('claude-opus-4.1') is not None
        assert manager.get_config('gemini-2.5-pro') is not None

    def test_update_config(self):
        """Test updating model configuration."""
        manager = ModelManager()

        # Update configuration
        manager.update_config('gpt-5', temperature_default=0.5)
        config = manager.get_config('gpt-5')
        assert config.temperature_default == 0.5

    def test_get_provider_models(self):
        """Test getting models by provider."""
        manager = ModelManager()

        # Get OpenAI models
        openai_models = manager.get_provider_models('openai')
        assert 'gpt-5' in openai_models
        assert 'gpt-4o' in openai_models

    def test_validate_configs(self):
        """Test configuration validation."""
        manager = ModelManager()

        # Validate configurations
        issues = manager.validate_configs()
        # All models should have API key issues in test environment
        assert isinstance(issues, dict)


class TestConsensusBuilder:
    """Test consensus building functionality."""

    @pytest.mark.asyncio
    async def test_majority_vote(self):
        """Test majority voting consensus."""
        builder = ConsensusBuilder()

        # Mock executor for testing
        async def mock_executor(prompt):
            return {
                'response': 'Yes',
                'confidence': 0.8,
                'reasoning': 'Test reasoning',
                'tokens_used': 100
            }

        builder.register_executor('gpt-5', mock_executor)
        builder.register_executor('claude-opus-4.1', mock_executor)
        builder.register_executor('gpt-4.1', mock_executor)

        # Build consensus
        result = await builder.build_consensus(
            prompt="Should we implement this feature?",
            models=['gpt-5', 'claude-opus-4.1', 'gpt-4.1'],
            vote_type=VoteType.MAJORITY
        )

        assert result.consensus_reached == True
        assert result.final_decision == 'Yes'
        assert len(result.votes) == 3

    @pytest.mark.asyncio
    async def test_quorum_vote(self):
        """Test quorum voting consensus."""
        builder = ConsensusBuilder()

        # Mock executors with different responses
        async def executor1(prompt):
            return {'response': 'A', 'confidence': 0.9, 'reasoning': 'Reason A', 'tokens_used': 100}

        async def executor2(prompt):
            return {'response': 'A', 'confidence': 0.8, 'reasoning': 'Reason A2', 'tokens_used': 100}

        async def executor3(prompt):
            return {'response': 'B', 'confidence': 0.7, 'reasoning': 'Reason B', 'tokens_used': 100}

        builder.register_executor('model1', executor1)
        builder.register_executor('model2', executor2)
        builder.register_executor('model3', executor3)

        # Build consensus with quorum of 2
        result = await builder.build_consensus(
            prompt="Choose option",
            models=['model1', 'model2', 'model3'],
            vote_type=VoteType.QUORUM,
            quorum_size=2
        )

        assert result.consensus_reached == True
        assert result.final_decision == 'A'

    @pytest.mark.asyncio
    async def test_debate_consensus(self):
        """Test debate-style consensus."""
        builder = ConsensusBuilder()

        # Mock executors
        async def mock_executor(prompt):
            stance = "FOR" if "FOR" in prompt else "AGAINST" if "AGAINST" in prompt else "NEUTRAL"
            return {
                'response': f"Response {stance}",
                'confidence': 0.75,
                'reasoning': f"Reasoning for {stance}",
                'tokens_used': 150
            }

        builder.register_executor('gpt-5', mock_executor)
        builder.register_executor('claude-opus-4.1', mock_executor)
        builder.register_executor('gpt-4.1', mock_executor)

        # Run debate
        result = await builder.debate_consensus(
            topic="Should we use microservices architecture?",
            models=['gpt-5', 'claude-opus-4.1', 'gpt-4.1'],
            rounds=1
        )

        assert result is not None
        assert len(result.votes) == 3
        assert result.synthesis is not None