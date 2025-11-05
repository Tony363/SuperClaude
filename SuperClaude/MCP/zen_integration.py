"""
Zen MCP Integration

Lightweight local implementation that provides a consensus-style facade
compatible with SuperClaude's command executor. This avoids any network
use and interoperates with the framework's concepts.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..ModelRouter.facade import ModelRouterFacade
from ..ModelRouter.consensus import VoteType


class ThinkingMode(Enum):
    minimal = "minimal"
    low = "low"
    medium = "medium"
    high = "high"
    max = "max"


class ConsensusType(Enum):
    majority = "majority"
    unanimous = "unanimous"
    quorum = "quorum"
    weighted = "weighted"


@dataclass
class ModelConfig:
    name: str
    weight: float = 1.0
    role: Optional[str] = None


@dataclass
class ConsensusResult:
    consensus_reached: bool
    final_decision: Any
    votes: List[Dict[str, Any]] = field(default_factory=list)
    agreement_score: float = 0.0
    vote_type: str = "majority"
    total_time: float = 0.0
    total_tokens: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class ZenIntegration:
    """
    Minimal in-process consensus orchestrator.

    Notes:
    - No external API calls; simulates responses locally.
    - Provides initialize/initialize_session to satisfy executor hooks.
    - The `consensus` method performs a simple weighted frequency vote.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        facade: Optional[ModelRouterFacade] = None,
    ):
        self.config = config or {}
        self.initialized = False
        self.session_active = False
        self._facade: Optional[ModelRouterFacade] = facade

    def initialize(self):
        if self._facade is None:
            self._facade = ModelRouterFacade(offline=self.config.get("offline"))
        self.initialized = True
        return True

    async def initialize_session(self):
        self._ensure_facade()
        self.session_active = True
        return True

    async def consensus(
        self,
        prompt: str,
        models: Optional[List[ModelConfig]] = None,
        vote: ConsensusType = ConsensusType.majority,
        thinking: ThinkingMode = ThinkingMode.low,
        context: Optional[Dict[str, Any]] = None,
    ) -> ConsensusResult:
        facade = self._ensure_facade()
        model_names = [m.name for m in models] if models else None
        router_vote = self._resolve_vote_type(vote)
        think_level = self._resolve_think_level(thinking)

        payload = await facade.run_consensus(
            prompt,
            models=model_names,
            vote_type=router_vote,
            quorum_size=self._resolve_quorum(vote, models),
            context=context,
            think_level=think_level,
        )

        if payload.get("error"):
            raise RuntimeError(payload["error"])

        votes: List[Dict[str, Any]] = []
        for entry in payload.get("votes", []):
            votes.append({
                "model": entry.get("model"),
                "vote": entry.get("response"),
                "confidence": entry.get("confidence"),
                "weight": next((m.weight for m in (models or []) if m.name == entry.get("model")), 1.0),
                "metadata": entry.get("metadata"),
            })

        return ConsensusResult(
            consensus_reached=payload.get("consensus_reached", False),
            final_decision=payload.get("final_decision"),
            votes=votes,
            agreement_score=payload.get("agreement_score", 0.0),
            vote_type=router_vote.value,
            total_time=payload.get("total_time", 0.0),
            total_tokens=payload.get("total_tokens", 0),
            created_at=datetime.now().isoformat(),
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _ensure_facade(self) -> ModelRouterFacade:
        if self._facade is None:
            self._facade = ModelRouterFacade(offline=self.config.get("offline"))
        if not self.initialized:
            self.initialized = True
        return self._facade

    @staticmethod
    def _resolve_vote_type(vote: ConsensusType) -> VoteType:
        mapping = {
            ConsensusType.majority: VoteType.MAJORITY,
            ConsensusType.unanimous: VoteType.UNANIMOUS,
            ConsensusType.quorum: VoteType.QUORUM,
            ConsensusType.weighted: VoteType.WEIGHTED,
        }
        return mapping.get(vote, VoteType.MAJORITY)

    @staticmethod
    def _resolve_think_level(mode: ThinkingMode) -> int:
        ordering = [
            ThinkingMode.minimal,
            ThinkingMode.low,
            ThinkingMode.medium,
            ThinkingMode.high,
            ThinkingMode.max,
        ]
        return max(1, ordering.index(mode) + 1)

    @staticmethod
    def _resolve_quorum(vote: ConsensusType, models: Optional[List[ModelConfig]]) -> int:
        if vote != ConsensusType.quorum or not models:
            return 2
        return max(1, (len(models) // 2) + 1)
