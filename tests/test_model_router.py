"""
Test model router functionality.
"""

import pytest
from pathlib import Path
import sys
from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, Dict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from SuperClaude.APIClients import openai_client as openai_module
from SuperClaude.APIClients.openai_client import CompletionResponse
from SuperClaude.ModelRouter import (
    ModelRouter,
    RoutingDecision,
    ModelManager,
    ConsensusBuilder,
    VoteType,
    Stance,
    ModelRouterFacade
)
from SuperClaude.Commands import (
    CommandExecutor,
    CommandParser,
    CommandContext,
    CommandMetadata
)
from SuperClaude.Quality.quality_scorer import QualityScorer


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


RECORDED_CONSENSUS_FIXTURE_APPROVE = {
    'gpt-5': {
        'response': {'decision': 'approve', 'notes': 'Primary reviewer satisfied.'},
        'confidence': 0.88,
        'reasoning': 'Comprehensive testing evidence and quality loop passed.',
        'tokens_used': 180,
        'metadata': {'fixture': 'approve', 'provider': 'openai'}
    },
    'claude-opus-4.1': {
        'response': {'decision': 'approve', 'notes': 'Risk profile acceptable.'},
        'confidence': 0.82,
        'reasoning': 'Security and maintainability concerns resolved.',
        'tokens_used': 160,
        'metadata': {'fixture': 'approve', 'provider': 'anthropic'}
    },
    'gpt-4.1': {
        'response': {'decision': 'approve', 'notes': 'Fallback review matches.'},
        'confidence': 0.76,
        'reasoning': 'No outstanding issues detected.',
        'tokens_used': 140,
        'metadata': {'fixture': 'approve', 'provider': 'openai'}
    }
}

RECORDED_CONSENSUS_FIXTURE_SPLIT = {
    'gpt-5': {
        'response': {'decision': 'approve', 'notes': 'Meets success criteria.'},
        'confidence': 0.74,
        'reasoning': 'Feature passes regression tests.',
        'tokens_used': 150,
        'metadata': {'fixture': 'split', 'provider': 'openai'}
    },
    'claude-opus-4.1': {
        'response': {'decision': 'revise', 'notes': 'Observability gap discovered.'},
        'confidence': 0.71,
        'reasoning': 'Lack of monitoring in rollout plan.',
        'tokens_used': 155,
        'metadata': {'fixture': 'split', 'provider': 'anthropic'}
    },
    'gpt-4.1': {
        'response': {'decision': 'revise', 'notes': 'Tests insufficient.'},
        'confidence': 0.69,
        'reasoning': 'Negative scenario missing coverage.',
        'tokens_used': 148,
        'metadata': {'fixture': 'split', 'provider': 'openai'}
    }
}


class TestModelRouterFacade:
    """Tests for ModelRouterFacade convenience wrapper."""

    @pytest.mark.asyncio
    async def test_facade_returns_serializable_payload(self):
        facade = ModelRouterFacade(offline=True)

        result = await facade.run_consensus("Implementation completed successfully.")

        assert isinstance(result, dict)
        assert 'consensus_reached' in result
        assert 'votes' in result
        assert isinstance(result['votes'], list)

    @pytest.mark.asyncio
    async def test_facade_supports_custom_models(self):
        facade = ModelRouterFacade(offline=True)

        async def approve(prompt: str):
            return {'response': 'approve', 'confidence': 0.8, 'reasoning': 'positive', 'tokens_used': 50}

        async def reject(prompt: str):
            return {'response': 'reject', 'confidence': 0.8, 'reasoning': 'negative', 'tokens_used': 50}

        facade.consensus.register_executor('model-approve', approve)
        facade.consensus.register_executor('model-reject', reject)

        result = await facade.run_consensus(
            "Build failed with critical error.",
            models=['model-approve', 'model-reject']
        )

        assert result['consensus_reached'] is False
        assert result['final_decision'] is None

    @pytest.mark.asyncio
    async def test_facade_respects_think_level(self):
        facade = ModelRouterFacade(offline=True)

        deep_result = await facade.run_consensus(
            "Design a complex distributed system",
            think_level=3
        )
        quick_result = await facade.run_consensus(
            "Quick lint fix",
            think_level=1
        )

        assert deep_result['think_level'] == 3
        assert quick_result['think_level'] == 1
        assert deep_result['routing_decision']['primary_model'] in {
            'gpt-5', 'claude-opus-4.1', 'gemini-2.5-pro'
        }
        assert quick_result['routing_decision']['primary_model'] in {
            'gpt-4o', 'gpt-4o-mini', 'grok-code-fast-1'
        }

    @pytest.mark.asyncio
    async def test_facade_consensus_with_recorded_fixture(self):
        facade = ModelRouterFacade(offline=True)
        facade.consensus.model_executors.clear()

        for model_name, payload in RECORDED_CONSENSUS_FIXTURE_APPROVE.items():

            async def executor(prompt: str, *, result=payload) -> Dict[str, Any]:
                return result

            facade.consensus.register_executor(model_name, executor)

        result = await facade.run_consensus(
            "All acceptance criteria satisfied; proceed?",
            models=list(RECORDED_CONSENSUS_FIXTURE_APPROVE.keys())
        )

        assert result['consensus_reached'] is True
        assert result['final_decision']['decision'] == 'approve'
        assert result['offline'] is True
        assert len(result['votes']) == len(RECORDED_CONSENSUS_FIXTURE_APPROVE)

    @pytest.mark.asyncio
    async def test_facade_records_disagreements_from_fixture(self):
        facade = ModelRouterFacade(offline=True)
        facade.consensus.model_executors.clear()

        for model_name, payload in RECORDED_CONSENSUS_FIXTURE_SPLIT.items():

            async def executor(prompt: str, *, result=payload) -> Dict[str, Any]:
                return result

            facade.consensus.register_executor(model_name, executor)

        result = await facade.run_consensus(
            "Risky deployment detected; proceed?",
            models=list(RECORDED_CONSENSUS_FIXTURE_SPLIT.keys())
        )

        assert result['consensus_reached'] is False
        assert result['final_decision'] is None
        assert len(result['disagreements']) >= 1
        responses = {vote['response']['decision'] for vote in result['votes'] if isinstance(vote['response'], dict)}
        assert responses == {'approve', 'revise'}

    @pytest.mark.asyncio
    async def test_facade_invokes_openai_provider_with_api_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        call_log: Dict[str, Any] = {}

        async def fake_complete(self, request):
            call_log.setdefault("models", []).append(request.model)
            return CompletionResponse(
                id="chatcmpl-test",
                model=request.model,
                content="approve — strong evidence of completion",
                usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
                finish_reason="stop",
            )

        monkeypatch.setattr(
            openai_module.OpenAIClient,
            "complete",
            fake_complete,
            raising=False,
        )

        facade = ModelRouterFacade(offline=False)
        result = await facade.run_consensus(
            "Should we approve the implementation?",
            models=["gpt-4o"],
        )

        assert call_log.get("models") == ["gpt-4o"]
        assert result["offline"] is False
        assert result["votes"][0]["metadata"].get("provider") == "openai"
        assert "approve" in str(result["votes"][0]["response"]).lower()


@pytest.mark.asyncio
async def test_executor_think_flag_routes_models(monkeypatch):
    """Command executor should pass --think level through to the model router and consensus facade."""
    parser = CommandParser()
    executor = object.__new__(CommandExecutor)
    executor.quality_scorer = QualityScorer()
    executor.delegate_category_map = {}
    executor.extended_agent_loader = SimpleNamespace()
    executor.consensus_facade = ModelRouterFacade()

    recorded = {}
    original_route = ModelRouter.route

    def tracking_route(self, *args, **kwargs):
        recorded['think_level'] = kwargs.get('think_level')
        return original_route(self, *args, **kwargs)

    parsed = parser.parse('/sc:dummy --consensus --think 3')
    metadata = CommandMetadata(
        name='dummy',
        description='',
        category='general',
        complexity='standard'
    )
    context = CommandContext(
        command=parsed,
        metadata=metadata,
        session_id='test-session'
    )
    context.results['mode'] = {}
    context.results['behavior_mode'] = context.behavior_mode
    context.results['flags'] = sorted(parsed.flags.keys())
    context.results.setdefault('executed_operations', [])
    context.results.setdefault('applied_changes', [])
    context.results.setdefault('artifacts', [])

    executor._apply_execution_flags(context)

    async def stub_consensus(prompt, **kwargs):
        recorded['consensus_think'] = kwargs.get('think_level')
        decision = executor.consensus_facade.router.route(
            task_type=kwargs.get('task_type', 'consensus'),
            think_level=recorded['consensus_think']
        )
        return {
            'consensus_reached': True,
            'final_decision': {'decision': 'approve'},
            'votes': [],
            'think_level': recorded['consensus_think'],
            'routing_decision': executor.consensus_facade._serialize_routing(decision)
        }

    monkeypatch.setattr(ModelRouter, "route", tracking_route)
    monkeypatch.setattr(
        executor.consensus_facade,
        "run_consensus",
        stub_consensus,
        raising=False
    )

    result = await executor._ensure_consensus(
        context,
        output={},
        enforce=context.consensus_forced,
        think_level=context.think_level
    )

    assert context.consensus_forced is True
    assert context.results.get('think_level') == 3
    assert recorded.get('think_level') == 3
    assert recorded.get('consensus_think') == 3
    assert context.think_level == 3
    assert result['think_level'] == 3
    assert context.consensus_summary is not None
    assert context.consensus_summary.get('think_level') == 3
