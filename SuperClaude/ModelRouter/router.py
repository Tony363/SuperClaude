"""
Multi-Model Router for SuperClaude Framework.

Intelligent model selection with context-aware routing, fallback chains,
and token budget management for GPT-5, Gemini, Claude, and Grok.
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Available model providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    XAI = "xai"


@dataclass
class ModelCapabilities:
    """Model capability specifications."""
    name: str
    provider: ModelProvider
    reasoning_score: int  # 1-5
    speed_score: int  # 1-5
    cost_tier: str  # $ / $$ / $$$
    context_window: int  # in tokens
    supports_thinking: bool = False
    supports_vision: bool = False
    supports_tools: bool = True
    best_for: List[str] = field(default_factory=list)
    availability: float = 1.0  # 0.0-1.0
    last_error: Optional[datetime] = None


@dataclass
class RoutingDecision:
    """Model routing decision with reasoning."""
    primary_model: str
    fallback_chain: List[str]
    reason: str
    token_budget: int
    estimated_cost: float
    confidence: float  # 0.0-1.0


class ModelRouter:
    """
    Intelligent model router for optimal selection.

    Features:
    - Context-aware routing based on task type
    - Automatic fallback chains
    - Token budget management
    - Availability tracking with backoff
    - Cost optimization
    """

    # Model capability matrix
    MODEL_CAPABILITIES = {
        'gpt-5': ModelCapabilities(
            name='gpt-5',
            provider=ModelProvider.OPENAI,
            reasoning_score=5,
            speed_score=3,
            cost_tier='$$$',
            context_window=400000,
            supports_thinking=True,
            supports_vision=True,
            best_for=['deep_thinking', 'planning', 'complex_analysis', 'architecture']
        ),
        'gemini-2.5-pro': ModelCapabilities(
            name='gemini-2.5-pro',
            provider=ModelProvider.GOOGLE,
            reasoning_score=4,
            speed_score=3,
            cost_tier='$$',
            context_window=2000000,
            supports_thinking=True,
            supports_vision=True,
            best_for=['long_context', 'bulk_analysis', 'documentation', 'multi_file']
        ),
        'claude-opus-4.1': ModelCapabilities(
            name='claude-opus-4.1',
            provider=ModelProvider.ANTHROPIC,
            reasoning_score=5,
            speed_score=4,
            cost_tier='$$',
            context_window=200000,
            supports_thinking=False,
            supports_vision=True,
            best_for=['fallback', 'validation', 'code_generation', 'general']
        ),
        'gpt-4.1': ModelCapabilities(
            name='gpt-4.1',
            provider=ModelProvider.OPENAI,
            reasoning_score=4,
            speed_score=3,
            cost_tier='$$',
            context_window=1000000,
            supports_thinking=False,
            supports_vision=True,
            best_for=['large_context', 'secondary_fallback', 'validation']
        ),
        'gpt-4o': ModelCapabilities(
            name='gpt-4o',
            provider=ModelProvider.OPENAI,
            reasoning_score=4,
            speed_score=4,
            cost_tier='$',
            context_window=128000,
            supports_thinking=False,
            supports_vision=True,
            best_for=['standard', 'quick_tasks', 'cost_effective']
        ),
        'gpt-4o-mini': ModelCapabilities(
            name='gpt-4o-mini',
            provider=ModelProvider.OPENAI,
            reasoning_score=3,
            speed_score=5,
            cost_tier='$',
            context_window=128000,
            supports_thinking=False,
            supports_vision=True,
            best_for=['simple', 'quick', 'high_volume', 'cost_sensitive']
        ),
        'grok-4': ModelCapabilities(
            name='grok-4',
            provider=ModelProvider.XAI,
            reasoning_score=4,
            speed_score=4,
            cost_tier='$$',
            context_window=256000,
            supports_thinking=True,
            supports_vision=False,
            best_for=['code_analysis', 'technical', 'fast_iteration']
        ),
        'grok-code-fast-1': ModelCapabilities(
            name='grok-code-fast-1',
            provider=ModelProvider.XAI,
            reasoning_score=3,
            speed_score=5,
            cost_tier='$',
            context_window=128000,
            supports_thinking=False,
            supports_vision=False,
            best_for=['fast_code_analysis', 'quick_iteration', 'syntax_checking']
        )
    }

    # Task type to model preferences
    TASK_PREFERENCES = {
        'deep_thinking': ['gpt-5', 'claude-opus-4.1', 'gpt-4.1'],
        'consensus': ['gpt-5', 'claude-opus-4.1', 'gpt-4.1', 'gpt-4o'],
        'planning': ['gpt-5', 'claude-opus-4.1', 'gemini-2.5-pro'],
        'debugging': ['gpt-5', 'grok-4', 'claude-opus-4.1'],
        'code_review': ['gpt-5', 'grok-code-fast-1', 'claude-opus-4.1'],
        'long_context': ['gemini-2.5-pro', 'gpt-4.1', 'gpt-5'],
        'bulk_analysis': ['gemini-2.5-pro', 'gpt-4.1', 'claude-opus-4.1'],
        'quick_task': ['gpt-4o-mini', 'gpt-4o', 'grok-code-fast-1'],
        'standard': ['gpt-4o', 'claude-opus-4.1', 'gpt-5']
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize model router.

        Args:
            config: Optional configuration overrides
        """
        self.config = config or {}
        self.availability_cache: Dict[str, Tuple[bool, datetime]] = {}
        self.backoff_duration = timedelta(seconds=60)  # 1 minute backoff
        self.usage_history: List[Dict[str, Any]] = []

    def route(self,
              task_type: str = 'standard',
              context_size: int = 0,
              think_level: int = 2,
              excluded_models: Optional[List[str]] = None,
              force_model: Optional[str] = None) -> RoutingDecision:
        """
        Route to optimal model based on context.

        Args:
            task_type: Type of task (deep_thinking, consensus, etc.)
            context_size: Estimated context size in tokens
            think_level: Thinking depth (1-3)
            excluded_models: Models to exclude from selection
            force_model: Force specific model if available

        Returns:
            RoutingDecision with selected model and fallbacks
        """
        excluded_models = excluded_models or []

        # Handle forced model
        if force_model:
            if force_model in self.MODEL_CAPABILITIES and self._is_available(force_model):
                return self._create_decision(
                    force_model,
                    self._get_fallback_chain(force_model, excluded_models),
                    f"Forced model: {force_model}",
                    context_size,
                    think_level
                )
            else:
                logger.warning(f"Forced model {force_model} not available, routing normally")

        # Determine if long context routing needed
        if context_size > 400000:
            return self._route_long_context(context_size, excluded_models)

        # Get task preferences
        preferred_models = self.TASK_PREFERENCES.get(task_type, self.TASK_PREFERENCES['standard'])

        # Adjust for think level
        if think_level >= 3:
            # Prefer high reasoning models for deep thinking
            preferred_models = ['gpt-5', 'claude-opus-4.1', 'gemini-2.5-pro']
        elif think_level == 1:
            # Prefer fast models for quick tasks
            preferred_models = ['gpt-4o-mini', 'grok-code-fast-1', 'gpt-4o']

        # Select primary model
        primary = self._select_primary_model(preferred_models, excluded_models, context_size)

        # Build fallback chain
        fallback_chain = self._get_fallback_chain(primary, excluded_models)

        # Determine reason
        reason = self._get_routing_reason(task_type, think_level, context_size)

        return self._create_decision(primary, fallback_chain, reason, context_size, think_level)

    def _route_long_context(self,
                            context_size: int,
                            excluded_models: List[str]) -> RoutingDecision:
        """
        Route for long context scenarios.

        Args:
            context_size: Context size in tokens
            excluded_models: Models to exclude

        Returns:
            RoutingDecision optimized for long context
        """
        # Prioritize models by context window size
        long_context_models = [
            ('gemini-2.5-pro', 2000000),
            ('gpt-4.1', 1000000),
            ('gpt-5', 400000),
            ('grok-4', 256000),
            ('claude-opus-4.1', 200000)
        ]

        # Find first available model that fits
        for model_name, window_size in long_context_models:
            if (model_name not in excluded_models and
                window_size >= context_size and
                self._is_available(model_name)):

                fallback_chain = self._get_fallback_chain(model_name, excluded_models)
                reason = f"Long context routing: {context_size:,} tokens → {model_name} ({window_size:,} window)"

                return self._create_decision(
                    model_name,
                    fallback_chain,
                    reason,
                    context_size,
                    2  # Standard think level for long context
                )

        # Fallback to chunking with GPT-5
        return self._create_decision(
            'gpt-5',
            ['claude-opus-4.1', 'gpt-4o'],
            f"Context too large ({context_size:,} tokens), will chunk",
            400000,  # Max for GPT-5
            2
        )

    def _select_primary_model(self,
                              preferred_models: List[str],
                              excluded_models: List[str],
                              context_size: int) -> str:
        """
        Select primary model from preferences.

        Args:
            preferred_models: Ordered list of preferred models
            excluded_models: Models to exclude
            context_size: Required context window

        Returns:
            Selected model name
        """
        for model_name in preferred_models:
            if model_name in excluded_models:
                continue

            capability = self.MODEL_CAPABILITIES.get(model_name)
            if not capability:
                continue

            # Check context window
            if context_size > capability.context_window:
                continue

            # Check availability
            if not self._is_available(model_name):
                continue

            return model_name

        # Fallback to Claude Opus 4.1 as ultimate default
        return 'claude-opus-4.1'

    def _get_fallback_chain(self,
                            primary: str,
                            excluded_models: List[str]) -> List[str]:
        """
        Build fallback chain for primary model.

        Args:
            primary: Primary model name
            excluded_models: Models to exclude

        Returns:
            Ordered list of fallback models
        """
        # Standard fallback chains
        fallback_chains = {
            'gpt-5': ['claude-opus-4.1', 'gpt-4.1', 'gpt-4o'],
            'gemini-2.5-pro': ['gpt-4.1', 'gpt-5', 'claude-opus-4.1'],
            'claude-opus-4.1': ['gpt-5', 'gpt-4.1', 'gpt-4o'],
            'gpt-4.1': ['gpt-5', 'claude-opus-4.1', 'gemini-2.5-pro'],
            'gpt-4o': ['gpt-4o-mini', 'claude-opus-4.1', 'gpt-5'],
            'gpt-4o-mini': ['gpt-4o', 'claude-opus-4.1'],
            'grok-4': ['grok-code-fast-1', 'gpt-5', 'claude-opus-4.1'],
            'grok-code-fast-1': ['grok-4', 'gpt-4o', 'claude-opus-4.1']
        }

        chain = fallback_chains.get(primary, ['claude-opus-4.1', 'gpt-5', 'gpt-4o'])

        # Filter excluded models
        chain = [m for m in chain if m not in excluded_models and m != primary]

        return chain[:3]  # Limit to 3 fallbacks

    def _is_available(self, model_name: str) -> bool:
        """
        Check if model is currently available.

        Args:
            model_name: Model to check

        Returns:
            True if available
        """
        # Check cache
        if model_name in self.availability_cache:
            available, last_check = self.availability_cache[model_name]
            if datetime.now() - last_check < self.backoff_duration:
                return available

        # Check model capability
        capability = self.MODEL_CAPABILITIES.get(model_name)
        if not capability:
            return False

        # Check if in backoff period
        if capability.last_error:
            if datetime.now() - capability.last_error < self.backoff_duration:
                return False

        # Update cache
        self.availability_cache[model_name] = (capability.availability > 0.5, datetime.now())
        return capability.availability > 0.5

    def mark_unavailable(self, model_name: str, duration: Optional[timedelta] = None) -> None:
        """
        Mark model as temporarily unavailable.

        Args:
            model_name: Model to mark unavailable
            duration: Unavailability duration (defaults to backoff_duration)
        """
        duration = duration or self.backoff_duration

        if model_name in self.MODEL_CAPABILITIES:
            self.MODEL_CAPABILITIES[model_name].last_error = datetime.now()
            self.MODEL_CAPABILITIES[model_name].availability = 0.0
            self.availability_cache[model_name] = (False, datetime.now())

            logger.info(f"Model {model_name} marked unavailable for {duration}")

    def _create_decision(self,
                         primary: str,
                         fallback_chain: List[str],
                         reason: str,
                         context_size: int,
                         think_level: int) -> RoutingDecision:
        """
        Create routing decision with cost estimation.

        Args:
            primary: Primary model
            fallback_chain: Fallback models
            reason: Routing reason
            context_size: Context size
            think_level: Think level

        Returns:
            RoutingDecision object
        """
        # Calculate token budget
        token_budgets = {
            1: 5000,
            2: 15000,
            3: 50000
        }
        token_budget = token_budgets.get(think_level, 15000)

        # Adjust for context size
        total_tokens = context_size + token_budget

        # Estimate cost (simplified)
        cost_per_1k = {
            '$': 0.001,
            '$$': 0.01,
            '$$$': 0.02
        }

        capability = self.MODEL_CAPABILITIES.get(primary)
        cost_tier = capability.cost_tier if capability else '$$'
        estimated_cost = (total_tokens / 1000) * cost_per_1k[cost_tier]

        # Calculate confidence
        confidence = 0.9 if primary == 'gpt-5' else 0.8
        if 'fallback' in reason.lower():
            confidence *= 0.8

        return RoutingDecision(
            primary_model=primary,
            fallback_chain=fallback_chain,
            reason=reason,
            token_budget=token_budget,
            estimated_cost=estimated_cost,
            confidence=confidence
        )

    def _get_routing_reason(self,
                            task_type: str,
                            think_level: int,
                            context_size: int) -> str:
        """Generate human-readable routing reason."""
        reasons = []

        if think_level >= 3:
            reasons.append(f"Deep thinking (level {think_level})")
        elif think_level == 1:
            reasons.append("Quick task")

        if context_size > 100000:
            reasons.append(f"Large context ({context_size:,} tokens)")

        if task_type != 'standard':
            reasons.append(f"Task type: {task_type}")

        return " | ".join(reasons) if reasons else "Standard routing"

    def get_ensemble(self,
                     size: int = 3,
                     exclude_duplicates: bool = True) -> List[str]:
        """
        Get ensemble of models for consensus.

        Args:
            size: Number of models in ensemble
            exclude_duplicates: Exclude same provider models

        Returns:
            List of model names for ensemble
        """
        ensemble = []
        providers_used = set()

        # Preferred ensemble order
        preferred = ['gpt-5', 'claude-opus-4.1', 'gpt-4.1', 'gemini-2.5-pro', 'grok-4']

        for model_name in preferred:
            if len(ensemble) >= size:
                break

            capability = self.MODEL_CAPABILITIES.get(model_name)
            if not capability:
                continue

            if not self._is_available(model_name):
                continue

            if exclude_duplicates and capability.provider in providers_used:
                continue

            ensemble.append(model_name)
            providers_used.add(capability.provider)

        # Fill remaining slots if needed
        if len(ensemble) < size:
            for model_name in self.MODEL_CAPABILITIES:
                if len(ensemble) >= size:
                    break
                if model_name not in ensemble and self._is_available(model_name):
                    ensemble.append(model_name)

        return ensemble[:size]

    def record_usage(self,
                     model: str,
                     tokens_used: int,
                     success: bool,
                     task_type: str = 'standard') -> None:
        """
        Record model usage for optimization.

        Args:
            model: Model used
            tokens_used: Tokens consumed
            success: Whether execution succeeded
            task_type: Type of task
        """
        usage = {
            'model': model,
            'tokens_used': tokens_used,
            'success': success,
            'task_type': task_type,
            'timestamp': datetime.now().isoformat()
        }

        self.usage_history.append(usage)

        # Update availability based on success
        if not success and model in self.MODEL_CAPABILITIES:
            self.MODEL_CAPABILITIES[model].availability *= 0.9
        elif success and model in self.MODEL_CAPABILITIES:
            self.MODEL_CAPABILITIES[model].availability = min(1.0,
                                                               self.MODEL_CAPABILITIES[model].availability * 1.1)

    def get_statistics(self) -> Dict[str, Any]:
        """Get routing statistics."""
        stats = {
            'total_requests': len(self.usage_history),
            'model_usage': {},
            'success_rate': {},
            'average_tokens': {}
        }

        for usage in self.usage_history:
            model = usage['model']
            if model not in stats['model_usage']:
                stats['model_usage'][model] = 0
                stats['success_rate'][model] = []
                stats['average_tokens'][model] = []

            stats['model_usage'][model] += 1
            stats['success_rate'][model].append(usage['success'])
            stats['average_tokens'][model].append(usage['tokens_used'])

        # Calculate averages
        for model in stats['success_rate']:
            success_list = stats['success_rate'][model]
            stats['success_rate'][model] = sum(success_list) / len(success_list) if success_list else 0

            tokens_list = stats['average_tokens'][model]
            stats['average_tokens'][model] = sum(tokens_list) / len(tokens_list) if tokens_list else 0

        return stats