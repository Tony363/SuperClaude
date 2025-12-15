"""
Zen MCP Integration

Local implementation that fronts the ModelRouter consensus engine. This
module now also provides a lightweight `--zen-review` facade used by the
executor's agentic loop.
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..ModelRouter.consensus import VoteType
from ..ModelRouter.facade import ModelRouterFacade


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
            votes.append(
                {
                    "model": entry.get("model"),
                    "vote": entry.get("response"),
                    "confidence": entry.get("confidence"),
                    "weight": next(
                        (
                            m.weight
                            for m in (models or [])
                            if m.name == entry.get("model")
                        ),
                        1.0,
                    ),
                    "metadata": entry.get("metadata"),
                }
            )

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

    async def review_code(
        self,
        diff: str,
        *,
        files: Optional[List[str]] = None,
        model: str = "gpt-5",
        severity_filter: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        max_issues: int = 10,
    ) -> Dict[str, Any]:
        """Run a GPT-5 code review over a diff block via Zen consensus."""
        if not diff or not diff.strip():
            raise ValueError("diff payload required for zen-review")

        prompt = self._build_review_prompt(
            diff, files or [], severity_filter, max_issues
        )
        models = [ModelConfig(name=model, weight=1.0)]
        review_context = {
            "mode": "zen-review",
            "files": files or [],
            "metadata": metadata or {},
            "severity_filter": severity_filter,
        }

        consensus = await self.consensus(
            prompt,
            models=models,
            vote=ConsensusType.majority,
            thinking=ThinkingMode.high,
            context=review_context,
        )

        parsed = self._parse_review_response(consensus.final_decision)
        parsed.setdefault("model", model)
        parsed.setdefault("created_at", datetime.now().isoformat())
        parsed.setdefault("raw", consensus.final_decision)
        parsed.setdefault("agreement_score", consensus.agreement_score)
        parsed.setdefault("consensus", consensus.consensus_reached)
        parsed.setdefault("tokens_used", consensus.total_tokens)
        parsed.setdefault("files", files or [])
        return parsed

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
    def _resolve_quorum(
        vote: ConsensusType, models: Optional[List[ModelConfig]]
    ) -> int:
        if vote != ConsensusType.quorum or not models:
            return 2
        return max(1, (len(models) // 2) + 1)

    @staticmethod
    def _build_review_prompt(
        diff: str,
        files: List[str],
        severity_filter: Optional[str],
        max_issues: int,
    ) -> str:
        file_text = ", ".join(files) if files else "(files inferred from diff)"
        severity_text = severity_filter or "critical"
        schema = (
            '{"overall_score": number 0-100, "summary": string, '
            '"critical_issues": integer, "dimensions": {'
            '"correctness": {"score": number, "issues": [string], "suggestions": [string]}, '
            '"completeness": {"score": number, "issues": [string], "suggestions": [string]}, '
            '"maintainability": {"score": number}, "security": {"score": number}, '
            '"performance": {"score": number}, "scalability": {"score": number}, '
            '"testability": {"score": number}, "usability": {"score": number}}, '
            '"improvements": [string], "issues": [{"severity": "critical|warning|nit", '
            '"title": string, "details": string, "files": [string], "recommendation": string}], '
            '"recommendations": [string]}'
        )
        return (
            "You are GPT-5 performing a production code review for Claude Code's agentic loop. "
            "Evaluate the diff below for logical, security, and quality issues. "
            "Report ONLY JSON matching this schema: " + schema + ". "
            "Highlight up to "
            + str(max_issues)
            + " issues prioritising severity >= "
            + severity_text
            + ".\n"
            f"Files: {file_text}\n"
            "Diff to review:\n" + diff.strip()
        )

    def _parse_review_response(self, payload: Any) -> Dict[str, Any]:
        if isinstance(payload, dict):
            return self._normalize_review_payload(payload)
        if isinstance(payload, str):
            json_blob = self._extract_json_blob(payload)
            if json_blob:
                try:
                    data = json.loads(json_blob)
                    return self._normalize_review_payload(data)
                except json.JSONDecodeError:
                    pass
            return {
                "score": 0.0,
                "summary": payload.strip(),
                "critical_issues": 0,
                "warnings": 0,
                "issues": [],
                "recommendations": [],
            }
        return {
            "score": 0.0,
            "summary": "zen-review returned no structured payload",
            "critical_issues": 0,
            "warnings": 0,
            "issues": [],
            "recommendations": [],
        }

    @staticmethod
    def _normalize_review_payload(data: Dict[str, Any]) -> Dict[str, Any]:
        issues = data.get("issues") or []
        normalized_issues: List[Dict[str, Any]] = []
        for issue in issues:
            if not isinstance(issue, dict):
                continue
            normalized_issues.append(
                {
                    "severity": str(issue.get("severity", "warning")),
                    "title": issue.get("title") or issue.get("summary") or "Unnamed",
                    "details": issue.get("details") or issue.get("description") or "",
                    "files": issue.get("files") or [],
                    "recommendation": issue.get("recommendation")
                    or issue.get("fix")
                    or "",
                }
            )

        normalized_dimensions: Dict[str, Dict[str, Any]] = {}
        raw_dimensions = data.get("dimensions") or {}
        if isinstance(raw_dimensions, dict):
            for key, payload in raw_dimensions.items():
                if not isinstance(payload, dict):
                    continue
                normalized_dimensions[key] = {
                    "score": float(payload.get("score", 0.0)),
                    "issues": payload.get("issues") or [],
                    "suggestions": payload.get("suggestions") or [],
                }

        return {
            "score": float(data.get("overall_score", data.get("score", 0.0))),
            "summary": str(data.get("summary", "")),
            "critical_issues": int(data.get("critical_issues", 0)),
            "warnings": int(data.get("warnings", 0)),
            "issues": normalized_issues,
            "recommendations": data.get("recommendations") or [],
            "dimensions": normalized_dimensions,
            "improvements": data.get("improvements") or [],
        }

    @staticmethod
    def _extract_json_blob(text: str) -> Optional[str]:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        return match.group(0) if match else None
