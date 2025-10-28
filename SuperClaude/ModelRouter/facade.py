"""
Model router facade with provider-aware consensus orchestration.

This module wires together the `ModelRouter` and `ConsensusBuilder`, providing
live access to provider adapters (OpenAI, Anthropic, Google, X.AI) when
credentials are available, while retaining deterministic mock executors for
offline or test environments.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Dict, List, Optional

from .router import ModelRouter, RoutingDecision, ModelProvider
from .consensus import ConsensusBuilder, ConsensusResult, VoteType
from ..APIClients.openai_client import OpenAIClient, CompletionRequest
from ..APIClients.anthropic_client import AnthropicClient, ClaudeRequest
from ..APIClients.google_client import GoogleClient, GeminiRequest
from ..APIClients.xai_client import XAIClient, GrokRequest

logger = logging.getLogger(__name__)


class ModelRouterFacade:
    """Convenience wrapper around routing + consensus with provider integration."""

    def __init__(
        self,
        router: Optional[ModelRouter] = None,
        consensus: Optional[ConsensusBuilder] = None,
        offline: Optional[bool] = None,
    ) -> None:
        self.router = router or ModelRouter()
        self.consensus = consensus or ConsensusBuilder(self.router)
        self._provider_clients: Dict[str, Any] = {}
        self.offline_mode = self._resolve_offline_mode(offline)

        self._initialize_executors()

    async def run_consensus(
        self,
        prompt: str,
        *,
        models: Optional[List[str]] = None,
        vote_type: VoteType = VoteType.MAJORITY,
        quorum_size: int = 2,
        context: Optional[Dict[str, Any]] = None,
        think_level: Optional[int] = None,
        task_type: str = "consensus",
    ) -> Dict[str, Any]:
        """Execute consensus evaluation and return a JSON-serializable payload."""
        effective_think = think_level if think_level is not None else 2
        effective_think = max(1, min(3, effective_think))

        routing_decision: Optional[RoutingDecision] = None
        selected_models = models
        if not selected_models:
            routing_decision = self.router.route(
                task_type=task_type,
                think_level=effective_think
            )
            selected_models = [routing_decision.primary_model, *routing_decision.fallback_chain]
            unique_models: List[str] = []
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
                quorum_size=quorum_size,
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
                "offline": self.offline_mode,
                "quorum_size": quorum_size,
            }

        payload = self._serialize_consensus(result)
        payload["models"] = selected_models
        payload["think_level"] = effective_think
        payload["offline"] = self.offline_mode
        payload["quorum_size"] = quorum_size
        if routing_decision:
            payload["routing_decision"] = self._serialize_routing(routing_decision)
        return payload

    def _initialize_executors(self) -> None:
        """Initialise consensus executors for available providers or fall back."""
        self.consensus.model_executors.clear()

        if self.offline_mode:
            logger.info("ModelRouterFacade running in offline mode; using heuristic executors.")
            self._register_default_executors()
            return

        missing = self._register_provider_executors()
        if missing:
            logger.warning(
                "Falling back to deterministic consensus executors for models without live adapters: %s",
                ", ".join(sorted(missing))
            )
            self._register_default_executors(models=missing)
        if len(missing) == len(self.router.MODEL_CAPABILITIES):
            # No providers registered successfully; keep offline semantics for telemetry.
            self.offline_mode = True

    def _resolve_offline_mode(self, offline: Optional[bool]) -> bool:
        if offline is not None:
            return bool(offline)

        env_flag = os.getenv("SUPERCLAUDE_OFFLINE_MODE")
        if env_flag is not None:
            return env_flag.strip().lower() in {"1", "true", "yes", "on"}

        has_key = any(
            os.getenv(var)
            for var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "XAI_API_KEY")
        )
        return not has_key

    def _register_provider_executors(self) -> List[str]:
        unavailable: List[str] = []

        for model_name, capabilities in self.router.MODEL_CAPABILITIES.items():
            executor = self._build_provider_executor(model_name, capabilities.provider)
            if executor is None:
                unavailable.append(model_name)
            else:
                self.consensus.register_executor(model_name, executor)

        return unavailable

    def _build_provider_executor(self, model_name: str, provider: ModelProvider):
        client = self._get_provider_client(provider)
        if not client:
            return None

        async def executor(prompt: str, *, model=model_name, provider_enum=provider) -> Dict[str, Any]:
            try:
                return await self._execute_provider_model(provider_enum, model, prompt)
            except Exception as exc:
                logger.warning(
                    "Consensus provider %s for %s failed (%s); falling back to heuristic response.",
                    provider_enum.value,
                    model,
                    exc
                )
                return self._default_executor(model, prompt)

        return executor

    def _get_provider_client(self, provider: ModelProvider):
        key = provider.value
        if key in self._provider_clients:
            return self._provider_clients[key]

        try:
            if provider == ModelProvider.OPENAI:
                client = OpenAIClient()
            elif provider == ModelProvider.ANTHROPIC:
                client = AnthropicClient()
            elif provider == ModelProvider.GOOGLE:
                client = GoogleClient()
            elif provider == ModelProvider.XAI:
                client = XAIClient()
            else:
                client = None
        except Exception as exc:
            logger.info("Provider client unavailable for %s: %s", provider.value, exc)
            client = None

        self._provider_clients[key] = client
        return client

    async def _execute_provider_model(self, provider: ModelProvider, model: str, prompt: str) -> Dict[str, Any]:
        start = time.monotonic()
        response_text = ""
        tokens_used = 0
        metadata: Dict[str, Any] = {"provider": provider.value, "model": model}

        if provider == ModelProvider.OPENAI:
            client: OpenAIClient = self._provider_clients.get(provider.value)
            if not client:
                raise RuntimeError("OpenAI client unavailable")
            request = CompletionRequest(
                model=model,
                messages=self._build_chat_messages(prompt),
                temperature=0.2,
            )
            response = await client.complete(request)
            response_text = response.content
            usage = response.usage or {}
            tokens_used = usage.get('total_tokens') or (
                usage.get('prompt_tokens', 0) + usage.get('completion_tokens', 0)
            )
            metadata.update({
                "usage": usage,
                "finish_reason": response.finish_reason,
            })

        elif provider == ModelProvider.ANTHROPIC:
            client: AnthropicClient = self._provider_clients.get(provider.value)
            if not client:
                raise RuntimeError("Anthropic client unavailable")
            messages = self._build_chat_messages(prompt)
            request = ClaudeRequest(
                model=model,
                messages=messages,
                max_tokens=2048,
                temperature=0.2,
            )
            request.system = self._build_system_prompt()
            response = await client.complete(request)
            response_text = response.content
            usage = response.usage or {}
            tokens_used = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
            metadata.update({
                "usage": usage,
                "stop_reason": response.stop_reason,
            })

        elif provider == ModelProvider.GOOGLE:
            client: GoogleClient = self._provider_clients.get(provider.value)
            if not client:
                raise RuntimeError("Google client unavailable")
            request = GeminiRequest(
                model=model,
                prompt=self._build_longform_prompt(prompt),
                temperature=0.2,
            )
            response = await client.complete(request)
            response_text = response.text
            token_count = response.token_count or {}
            tokens_used = token_count.get('total_tokens', 0)
            metadata.update({
                "token_count": token_count,
                "finish_reason": response.finish_reason,
            })

        elif provider == ModelProvider.XAI:
            client: XAIClient = self._provider_clients.get(provider.value)
            if not client:
                raise RuntimeError("X.AI client unavailable")
            messages = self._build_chat_messages(prompt)
            request = GrokRequest(
                model=model,
                messages=messages,
                max_tokens=2048,
                temperature=0.2,
            )
            response = await client.complete(request)
            response_text = response.content
            usage = response.usage or {}
            tokens_used = usage.get('total_tokens') or (
                usage.get('prompt_tokens', 0) + usage.get('completion_tokens', 0)
            )
            metadata.update({
                "usage": usage,
                "finish_reason": response.finish_reason,
            })

        else:
            raise RuntimeError(f"Unsupported provider: {provider}")

        duration = time.monotonic() - start
        confidence = self._infer_confidence(response_text)
        reasoning = self._extract_reasoning(response_text)

        metadata.update({
            "duration": duration,
            "offline": False,
        })

        return {
            "response": response_text,
            "confidence": confidence,
            "reasoning": reasoning,
            "tokens_used": tokens_used,
            "metadata": metadata,
        }

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

    def _register_default_executors(self, models: Optional[List[str]] = None) -> None:
        """Install deterministic executors for offline consensus."""
        target_models = models or list(self.router.MODEL_CAPABILITIES.keys())
        for model_name in target_models:

            async def executor(prompt: str, *, model=model_name) -> Dict[str, Any]:
                return self._default_executor(model, prompt)

            self.consensus.register_executor(model_name, executor)

    def _default_executor(self, model_name: str, prompt: str) -> Dict[str, Any]:
        """Deterministic heuristic executor used in offline mode."""
        prompt_lower = prompt.lower()
        negative_keywords = ("fail", "error", "bug", "reject", "issue", "missing", "panic")
        positive_keywords = ("pass", "success", "complete", "approve", "ready", "implement", "implementation", "ship")

        import hashlib

        hashed = hashlib.sha1(f"{model_name}:{prompt_lower}".encode("utf-8"))
        score = int(hashed.hexdigest()[:8], 16) / 0xFFFFFFFF

        if any(word in prompt_lower for word in negative_keywords):
            decision = "revise"
            confidence = round(0.45 + (1 - score) * 0.35, 2)
            reasoning = "Failure cues detected in prompt context; requesting revision."
        elif any(word in prompt_lower for word in positive_keywords):
            decision = "approve" if score > 0.25 else "revise"
            confidence = round(0.55 + score * 0.4, 2) if decision == "approve" else round(0.4 + score * 0.2, 2)
            reasoning = (
                "Strong success language present; approving with confidence." if decision == "approve"
                else "Positive language detected but heuristic vote recommends revision for caution."
            )
        else:
            decision = "approve" if score >= 0.5 else "revise"
            confidence = round(0.5 + abs(0.5 - score), 2)
            reasoning = (
                "Neutral prompt; defaulting to approval after balanced heuristic." if decision == "approve"
                else "Neutral prompt but heuristic variance triggered revision recommendation."
            )

        token_estimate = max(32, len(prompt) // 4)

        return {
            "response": {
                "decision": decision,
                "confidence": confidence,
                "reasoning": reasoning,
            },
            "confidence": confidence,
            "reasoning": reasoning,
            "tokens_used": token_estimate,
            "metadata": {
                "model": model_name,
                "heuristic": "deterministic_offline",
                "offline": True,
                "score": score,
            },
        }

    def _build_chat_messages(self, prompt: str) -> List[Dict[str, str]]:
        system_prompt = self._build_system_prompt()
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ]

    def _build_longform_prompt(self, prompt: str) -> str:
        return (
            "You are participating in a safety-critical consensus evaluation. "
            "Provide a structured answer with decision, reasoning, risks, and confidence.\n\n"
            f"{prompt}"
        )

    def _build_system_prompt(self) -> str:
        return (
            "You are part of a multi-model consensus panel. Respond with a clear decision, "
            "supporting reasoning, confidence estimate (0-100%), and noted risks."
        )

    def _infer_confidence(self, text: str) -> float:
        if not text:
            return 0.5
        match = re.search(r"confidence(?: level)?\s*[:=-]\s*(\d{1,3})", text, re.IGNORECASE)
        if match:
            value = int(match.group(1))
            return max(0.0, min(1.0, value / 100.0))

        lowered = text.lower()
        positive = any(word in lowered for word in ("approve", "accept", "success", "ready", "pass"))
        negative = any(word in lowered for word in ("reject", "fail", "block", "concern", "risk"))

        if positive and not negative:
            return 0.78
        if negative and not positive:
            return 0.42
        return 0.6

    def _extract_reasoning(self, text: str) -> str:
        if not text:
            return ""
        trimmed = text.strip()
        if len(trimmed) <= 400:
            return trimmed
        return trimmed[:380] + "…"
