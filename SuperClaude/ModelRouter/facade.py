"""
Facade that wires ModelRouter and ConsensusBuilder for offline execution.

Provides a deterministic, dependency-free pathway so the command executor
can invoke consensus checks without reaching external model providers.
"""

import logging
from typing import Any, Dict, List, Optional

from .router import ModelRouter, RoutingDecision
from .consensus import ConsensusBuilder, ConsensusResult, VoteType

logger = logging.getLogger(__name__)


class ModelRouterFacade:
    """Convenience wrapper around the router + consensus builder."""

    def __init__(
        self,
        router: Optional[ModelRouter] = None,
        consensus: Optional[ConsensusBuilder] = None,
    ) -> None:
        self.router = router or ModelRouter()
        self.consensus = consensus or ConsensusBuilder(self.router)

        if not self.consensus.model_executors:
            self._register_default_executors()

    async def run_consensus(
        self,
        prompt: str,
        *,
        models: Optional[List[str]] = None,
        vote_type: VoteType = VoteType.MAJORITY,
        context: Optional[Dict[str, Any]] = None,
        think_level: Optional[int] = None,
        task_type: str = "consensus",
    ) -> Dict[str, Any]:
        """Execute consensus evaluation and return a JSON-serializable payload."""
        effective_think = think_level if think_level is not None else 2
        if effective_think < 1:
            effective_think = 1
        if effective_think > 3:
            effective_think = 3

        routing_decision = None
        selected_models = models
        if not selected_models:
            routing_decision = self.router.route(
                task_type=task_type,
                think_level=effective_think
            )
            selected_models = [routing_decision.primary_model, *routing_decision.fallback_chain]
            # Ensure uniqueness and limit ensemble size
            unique_models = []
            for model_name in selected_models:
                if model_name not in unique_models:
                    unique_models.append(model_name)
            selected_models = unique_models[:3] or self.router.get_ensemble()

        context_payload = dict(context or {})
        context_payload.setdefault('think_level', effective_think)
        if routing_decision:
            context_payload.setdefault('routing_decision', self._serialize_routing(routing_decision))

        try:
            result = await self.consensus.build_consensus(
                prompt,
                models=selected_models,
                vote_type=vote_type,
                context=context_payload,
            )
        except Exception as exc:
            logger.error(f"Consensus execution failed: {exc}")
            return {
                "consensus_reached": False,
                "error": str(exc),
                "models": selected_models,
                "routing_decision": self._serialize_routing(routing_decision) if routing_decision else None,
                "think_level": effective_think,
            }

        payload = self._serialize_consensus(result)
        payload["models"] = selected_models
        payload["think_level"] = effective_think
        if routing_decision:
            payload["routing_decision"] = self._serialize_routing(routing_decision)
        return payload

    def _serialize_routing(self, decision: Optional[RoutingDecision]) -> Optional[Dict[str, Any]]:
        if not decision:
            return None
        return {
            "primary_model": decision.primary_model,
            "fallback_chain": decision.fallback_chain,
            "reason": decision.reason,
            "token_budget": decision.token_budget,
            "estimated_cost": decision.estimated_cost,
            "confidence": decision.confidence,
        }

    def _serialize_consensus(self, result: ConsensusResult) -> Dict[str, Any]:
        """Convert ConsensusResult into a plain dictionary."""
        payload = {
            "consensus_reached": result.consensus_reached,
            "agreement_score": result.agreement_score,
            "vote_type": result.vote_type.value if hasattr(result.vote_type, "value") else str(result.vote_type),
            "total_tokens": result.total_tokens,
            "total_time": result.total_time,
            "final_decision": result.final_decision,
            "disagreements": result.disagreements,
            "synthesis": result.synthesis,
        }

        votes = []
        for vote in result.votes:
            votes.append({
                "model": vote.model_name,
                "confidence": vote.confidence,
                "reasoning": vote.reasoning,
                "response": vote.response,
                "stance": vote.stance.value if vote.stance else None,
                "tokens_used": vote.tokens_used,
                "metadata": vote.metadata,
            })
        payload["votes"] = votes
        return payload

    def _register_default_executors(self) -> None:
        """Install deterministic executors for offline consensus."""
        for model_name in self.router.MODEL_CAPABILITIES.keys():

            async def executor(prompt: str, *, model=model_name) -> Dict[str, Any]:
                return self._default_executor(model, prompt)

            self.consensus.register_executor(model_name, executor)

    def _default_executor(self, model_name: str, prompt: str) -> Dict[str, Any]:
        """Simple heuristic executor used in offline mode."""
        prompt_lower = prompt.lower()
        negative_keywords = ("fail", "error", "bug", "reject", "issue", "missing")
        positive_keywords = ("pass", "success", "complete", "approve", "ready", "implement", "implementation")

        if any(word in prompt_lower for word in negative_keywords):
            decision = "revise"
            confidence = 0.55
            reasoning = "Signals of failure detected; recommending revision."
        elif any(word in prompt_lower for word in positive_keywords):
            decision = "approve"
            confidence = 0.78
            reasoning = "Positive completion phrases detected."
        else:
            decision = "approve"
            confidence = 0.72
            reasoning = "No risk signals detected; approving by default."

        token_estimate = max(32, len(prompt) // 4)

        return {
            "response": decision,
            "confidence": confidence,
            "reasoning": reasoning,
            "tokens_used": token_estimate,
            "metadata": {
                "model": model_name,
                "heuristic": "keyword",
            },
        }
