"""
Test model router functionality.
"""

import asyncio
import copy
import hashlib
import json
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
    CommandRegistry,
    CommandContext,
    CommandMetadata
)
from SuperClaude.Quality.quality_scorer import QualityScorer


def run(coro):
    return asyncio.run(coro)


@pytest.fixture(scope="module")
def consensus_fixtures(fixture_root) -> Dict[str, Dict[str, Dict[str, Any]]]:
    base = fixture_root / "consensus"
    return {
        "approve": json.loads((base / "approve.json").read_text(encoding="utf-8")),
        "split": json.loads((base / "split.json").read_text(encoding="utf-8")),
    }


def _build_fixture_executor(payload: Dict[str, Any]):
    template = copy.deepcopy(payload)

    async def executor(prompt: str) -> Dict[str, Any]:
        token_estimate = len(prompt.split()) or 1
        metadata = copy.deepcopy(template.get("metadata", {}))
        metadata["prompt_hash"] = hashlib.sha1(prompt.encode("utf-8")).hexdigest()
        return {
            "response": copy.deepcopy(template.get("response")),
            "confidence": template.get("confidence", 0.75),
            "reasoning": template.get("reasoning", "deterministic fixture response"),
            "tokens_used": max(template.get("tokens_used", 0), token_estimate),
            "metadata": metadata,
        }

    return executor


def _deterministic_executor(decision: Any, confidence: float = 0.8, provider: str = "test"):
    async def executor(prompt: str) -> Dict[str, Any]:
        tokens = len(prompt.split()) or 1
        metadata = {
            "provider": provider,
            "decision": decision,
            "prompt_hash": hashlib.sha1(prompt.encode("utf-8")).hexdigest(),
        }
        reasoning = f"Deterministic verdict '{decision}' for prompt of {tokens} tokens"
        return {
            "response": decision,
            "confidence": confidence,
            "reasoning": reasoning,
            "tokens_used": tokens,
            "metadata": metadata,
        }

    return executor


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

    def test_majority_vote(self):
        """Test majority voting consensus."""
        builder = ConsensusBuilder()

        builder.register_executor('gpt-5', _deterministic_executor('Yes', confidence=0.82, provider='openai'))
        builder.register_executor('claude-opus-4.1', _deterministic_executor('Yes', confidence=0.78, provider='anthropic'))
        builder.register_executor('gpt-4.1', _deterministic_executor('Yes', confidence=0.75, provider='openai'))

        # Build consensus
        result = run(
            builder.build_consensus(
                prompt="Should we implement this feature?",
                models=['gpt-5', 'claude-opus-4.1', 'gpt-4.1'],
                vote_type=VoteType.MAJORITY,
            )
        )

        assert result.consensus_reached == True
        assert result.final_decision == 'Yes'
        assert len(result.votes) == 3

    def test_quorum_vote(self):
        """Test quorum voting consensus."""
        builder = ConsensusBuilder()

        builder.register_executor('model1', _deterministic_executor('A', confidence=0.9, provider='test'))
        builder.register_executor('model2', _deterministic_executor('A', confidence=0.8, provider='test'))
        builder.register_executor('model3', _deterministic_executor('B', confidence=0.7, provider='test'))

        # Build consensus with quorum of 2
        result = run(
            builder.build_consensus(
                prompt="Choose option",
                models=['model1', 'model2', 'model3'],
                vote_type=VoteType.QUORUM,
                quorum_size=2,
            )
        )

        assert result.consensus_reached == True
        assert result.final_decision == 'A'

    def test_debate_consensus(self):
        """Test debate-style consensus."""
        builder = ConsensusBuilder()

        async def debate_executor(prompt: str) -> Dict[str, Any]:
            if "FOR" in prompt.upper():
                decision = {'decision': 'approve', 'stance': 'FOR'}
            elif "AGAINST" in prompt.upper():
                decision = {'decision': 'revise', 'stance': 'AGAINST'}
            else:
                decision = {'decision': 'neutral', 'stance': 'NEUTRAL'}
            tokens = len(prompt.split()) or 1
            return {
                'response': decision,
                'confidence': 0.75,
                'reasoning': f"Debate response for stance {decision['stance']}",
                'tokens_used': tokens,
                'metadata': {'prompt_hash': hashlib.sha1(prompt.encode('utf-8')).hexdigest()},
            }

        builder.register_executor('gpt-5', debate_executor)
        builder.register_executor('claude-opus-4.1', debate_executor)
        builder.register_executor('gpt-4.1', debate_executor)

        # Run debate
        result = run(
            builder.debate_consensus(
                topic="Should we use microservices architecture?",
                models=['gpt-5', 'claude-opus-4.1', 'gpt-4.1'],
                rounds=1,
            )
        )

        assert result is not None
        assert len(result.votes) == 3
        assert result.synthesis is not None


class TestModelRouterFacade:
    """Tests for ModelRouterFacade convenience wrapper."""

    def test_facade_returns_serializable_payload(self):
        facade = ModelRouterFacade(offline=True)

        _register_uniform_stub_executors(facade)

        result = run(facade.run_consensus("Implementation completed successfully."))

        assert isinstance(result, dict)
        assert 'consensus_reached' in result
        assert 'votes' in result
        assert isinstance(result['votes'], list)
        assert result['consensus_reached'] is True

    def test_facade_supports_custom_models(self):
        facade = ModelRouterFacade(offline=True)

        async def approve(prompt: str):
            return {'response': 'approve', 'confidence': 0.8, 'reasoning': 'positive', 'tokens_used': 50}

        async def reject(prompt: str):
            return {'response': 'reject', 'confidence': 0.8, 'reasoning': 'negative', 'tokens_used': 50}

        facade.consensus.register_executor('model-approve', approve)
        facade.consensus.register_executor('model-reject', reject)

        result = run(
            facade.run_consensus(
                "Build failed with critical error.",
                models=['model-approve', 'model-reject']
            )
        )

        assert result['consensus_reached'] is False
        assert result['final_decision'] is None

    def test_facade_respects_think_level(self):
        facade = ModelRouterFacade(offline=True)

        _register_uniform_stub_executors(facade)

        deep_result = run(
            facade.run_consensus(
                "Design a complex distributed system",
                think_level=3
            )
        )
        quick_result = run(
            facade.run_consensus(
                "Quick lint fix",
                think_level=1
            )
        )

        assert deep_result['think_level'] == 3
        assert quick_result['think_level'] == 1
        assert deep_result['routing_decision']['primary_model'] in {
            'gpt-5', 'claude-opus-4.1', 'gemini-2.5-pro'
        }
        assert quick_result['routing_decision']['primary_model'] in {
            'gpt-4o', 'gpt-4o-mini', 'grok-code-fast-1'
        }

    def test_facade_consensus_with_recorded_fixture(self, consensus_fixtures):
        facade = ModelRouterFacade(offline=True)
        facade.consensus.model_executors.clear()

        approve_fixture = consensus_fixtures["approve"]

        for model_name, payload in approve_fixture.items():
            facade.consensus.register_executor(model_name, _build_fixture_executor(payload))

        result = run(
            facade.run_consensus(
                "All acceptance criteria satisfied; proceed?",
                models=list(approve_fixture.keys())
            )
        )

        assert result['consensus_reached'] is True
        assert result['final_decision']['decision'] == 'approve'
        assert result['offline'] is True
        assert len(result['votes']) == len(approve_fixture)

    def test_facade_records_disagreements_from_fixture(self, consensus_fixtures):
        facade = ModelRouterFacade(offline=True)
        facade.consensus.model_executors.clear()

        split_fixture = consensus_fixtures["split"]

        for model_name, payload in split_fixture.items():
            facade.consensus.register_executor(model_name, _build_fixture_executor(payload))

        result = run(
            facade.run_consensus(
                "Risky deployment detected; proceed?",
                models=list(split_fixture.keys())
            )
        )

        assert len(result['disagreements']) >= 1
        responses = {vote['response']['decision'] for vote in result['votes'] if isinstance(vote['response'], dict)}
        assert responses == {'approve', 'revise'}

    def test_facade_reports_missing_executors(self):
        facade = ModelRouterFacade(offline=True)
        result = run(
            facade.run_consensus(
                "Should fail when no executors are available?",
                models=['gpt-4o'],
            )
        )

        assert result['consensus_reached'] is False
        assert 'No consensus executors registered' in result['error']

    def test_facade_invokes_openai_provider_with_api_key(self, monkeypatch):
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
        result = run(
            facade.run_consensus(
                "Should we approve the implementation?",
                models=["gpt-4o"],
            )
        )

        assert call_log.get("models") == ["gpt-4o"]
        assert result["offline"] is False
        assert result["votes"][0]["metadata"].get("provider") == "openai"
        assert "approve" in str(result["votes"][0]["response"]).lower()


def test_executor_think_flag_routes_models(monkeypatch):
    """Command executor should pass --think level through to the model router and consensus facade."""
    registry = CommandRegistry()
    parser = CommandParser(registry=registry)
    executor = CommandExecutor(registry, parser)

    recorded = {}
    original_route = ModelRouter.route

    def tracking_route(self, *args, **kwargs):
        recorded['think_level'] = kwargs.get('think_level')
        return original_route(self, *args, **kwargs)

    parsed = parser.parse('/sc:implement --think 3')
    metadata = registry.get_command('implement')
    assert metadata is not None
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

    result = run(
        executor._ensure_consensus(
            context,
            output={},
            enforce=context.consensus_forced,
            think_level=context.think_level
        )
    )

    assert context.results.get('think_level') == 3
    assert recorded.get('think_level') == 3
    assert recorded.get('consensus_think') == 3
    assert context.think_level == 3
    assert result['think_level'] == 3
    assert context.consensus_summary is not None
    assert context.consensus_summary.get('think_level') == 3
def _register_uniform_stub_executors(facade: ModelRouterFacade, decision: str = 'approve') -> None:
    """Register simple deterministic executors for every known model."""

    for model_name in facade.router.MODEL_CAPABILITIES.keys():

        async def executor(prompt: str, *, model=model_name) -> Dict[str, Any]:
            tokens = len(prompt.split()) or 1
            reasoning = f"{model} voting {decision} for prompt ({tokens} tokens)"
            return {
                'response': {
                    'decision': decision,
                    'confidence': 0.8,
                    'reasoning': reasoning,
                },
                'confidence': 0.8,
                'reasoning': reasoning,
                'tokens_used': max(32, tokens * 4),
                'metadata': {
                    'model': model,
                    'source': 'uniform_stub',
                    'prompt_hash': hashlib.sha1(prompt.encode('utf-8')).hexdigest(),
                }
            }

        facade.consensus.register_executor(model_name, executor)
