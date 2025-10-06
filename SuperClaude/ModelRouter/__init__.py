"""
Multi-Model Router System for SuperClaude Framework.

Provides intelligent model selection, routing, and consensus building
for GPT-5, Gemini, Claude, Grok, and other models.
"""

from .router import ModelRouter, RoutingDecision, ModelCapabilities, ModelProvider
from .models import ModelManager, ModelConfig
from .consensus import ConsensusBuilder, ConsensusResult, ModelVote, VoteType, Stance

__all__ = [
    'ModelRouter',
    'RoutingDecision',
    'ModelCapabilities',
    'ModelProvider',
    'ModelManager',
    'ModelConfig',
    'ConsensusBuilder',
    'ConsensusResult',
    'ModelVote',
    'VoteType',
    'Stance'
]

__version__ = '1.0.0'