"""
Multi-Model Router System for SuperClaude Framework.

Provides intelligent model selection, routing, and consensus building
for GPT-5, Gemini, Claude, Grok, and other models.
"""

from .consensus import ConsensusBuilder, ConsensusResult, ModelVote, Stance, VoteType
from .facade import ModelRouterFacade
from .models import ModelConfig, ModelManager
from .router import ModelCapabilities, ModelProvider, ModelRouter, RoutingDecision

__all__ = [
    "ConsensusBuilder",
    "ConsensusResult",
    "ModelCapabilities",
    "ModelConfig",
    "ModelManager",
    "ModelProvider",
    "ModelRouter",
    "ModelRouterFacade",
    "ModelVote",
    "RoutingDecision",
    "Stance",
    "VoteType",
]

__version__ = "1.0.0"
