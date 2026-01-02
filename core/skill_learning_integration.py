"""
Skill Learning Integration for SuperClaude Loop Orchestrator.

This module integrates the skill persistence layer with the loop orchestrator,
enabling cross-session learning by:

1. Recording iteration feedback after each iteration
2. Extracting learned skills from successful sessions
3. Retrieving and injecting relevant skills at loop start
4. Tracking skill application effectiveness

Usage:
    from core.skill_learning_integration import LearningLoopOrchestrator

    orchestrator = LearningLoopOrchestrator(config)
    result = orchestrator.run(context, skill_invoker)
    # Skills are automatically learned and retrieved
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .loop_orchestrator import LoopOrchestrator, create_skill_invoker_signal
from .metrics import MetricsEmitter
from .skill_persistence import (
    IterationFeedback,
    LearnedSkill,
    PromotionGate,
    SkillExtractor,
    SkillRetriever,
    SkillStore,
)
from .types import (
    LoopConfig,
    LoopResult,
    TerminationReason,
)


class LearningLoopOrchestrator(LoopOrchestrator):
    """
    Extended loop orchestrator with learning capabilities.

    Wraps the standard LoopOrchestrator to add:
    - Feedback persistence after each iteration
    - Skill extraction from successful sessions
    - Relevant skill retrieval at loop start
    - Application tracking for skill effectiveness

    Observability:
        Inherits all logging and metrics from LoopOrchestrator, plus:

        - Logger: Uses the same logger as parent, with additional
          `session_id` context for learning-specific events.
        - Metrics: Emits learning-specific metrics via the same callback.

        Additional metrics emitted:
            - learning.skills.applied.count: Skills injected at loop start
            - learning.skills.extracted.count: Skills extracted from success
              (with domain and success tags)
            - learning.skills.promoted.count: Skills auto-promoted
              (with reason tag)

    Usage:
        from core.skill_learning_integration import LearningLoopOrchestrator
        from core.metrics import InMemoryMetricsCollector

        collector = InMemoryMetricsCollector()
        orchestrator = LearningLoopOrchestrator(
            config=config,
            metrics_emitter=collector,
        )
        result = orchestrator.run(context, skill_invoker)

        # Check metrics
        print(f"Skills applied: {collector.get('learning.skills.applied.count')}")
    """

    def __init__(
        self,
        config: Optional[LoopConfig] = None,
        store: Optional[SkillStore] = None,
        enable_learning: bool = True,
        auto_promote: bool = False,
        logger: Optional[logging.Logger] = None,
        metrics_emitter: Optional[MetricsEmitter] = None,
    ):
        """
        Initialize the learning-enabled orchestrator.

        Args:
            config: Loop configuration
            store: Skill store instance (uses default if None)
            enable_learning: Whether to record feedback and extract skills
            auto_promote: Whether to automatically promote high-quality skills
            logger: A logger instance. If not provided, a default will be used.
            metrics_emitter: A callable for emitting operational metrics.
        """
        super().__init__(config, logger=logger, metrics_emitter=metrics_emitter)

        self.enable_learning = enable_learning
        self.auto_promote = auto_promote
        self.store = store or SkillStore()
        self.extractor = SkillExtractor(self.store)
        self.retriever = SkillRetriever(self.store)
        self.promotion_gate = PromotionGate(self.store)

        # Session tracking
        self.session_id = str(uuid.uuid4())[:12]
        self.repo_path = self._detect_repo_path()
        self.domain = "general"

        # Track applied skills for effectiveness measurement
        self._applied_skills: List[LearnedSkill] = []
        self._initial_quality: float = 0.0

    def _detect_repo_path(self) -> str:
        """Detect the current repository path."""
        cwd = Path.cwd()

        # Walk up to find .git directory
        for parent in [cwd] + list(cwd.parents):
            if (parent / ".git").exists():
                return str(parent)

        return str(cwd)

    def run(
        self,
        initial_context: Dict[str, Any],
        skill_invoker: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> LoopResult:
        """
        Execute the agentic loop with learning.

        Args:
            initial_context: Initial task context
            skill_invoker: Function that invokes Skills

        Returns:
            LoopResult with final output and learning metadata
        """
        log_context = {"loop_id": self.loop_id, "session_id": self.session_id}
        self.logger.info("Running loop with learning enabled.", extra=log_context)

        # Detect domain from context
        self.domain = self._detect_domain(initial_context)

        # Retrieve and inject relevant skills
        if self.enable_learning:
            initial_context = self._inject_relevant_skills(initial_context)
            self.metrics_emitter(
                "learning.skills.applied.count", len(self._applied_skills)
            )
            if self._applied_skills:
                self.logger.info(
                    f"Injected {len(self._applied_skills)} relevant skills.",
                    extra={
                        **log_context,
                        "skill_ids": [s.skill_id for s in self._applied_skills],
                    },
                )

        # Run the standard loop
        result = super().run(initial_context, skill_invoker)

        # Record all iteration feedback
        if self.enable_learning:
            self._record_all_feedback(result)
            self.logger.debug(
                "Recorded feedback for all iterations.",
                extra={**log_context, "iterations": len(result.iteration_history)},
            )

        # Extract skill if successful
        if self.enable_learning and result.termination_reason == TerminationReason.QUALITY_MET:
            learned_skill = self._extract_and_save_skill(result)
            self.metrics_emitter(
                "learning.skills.extracted.count",
                1,
                {"domain": self.domain, "success": str(learned_skill is not None).lower()},
            )
            if learned_skill:
                self.logger.info(
                    "Successfully extracted and saved new skill.",
                    extra={
                        **log_context,
                        "skill_id": learned_skill.skill_id,
                        "skill_name": learned_skill.name,
                    },
                )
            else:
                self.logger.info(
                    "Loop successful, but no new skill was extracted.",
                    extra=log_context,
                )

        # Track skill application effectiveness
        if self.enable_learning and self._applied_skills:
            self._record_skill_effectiveness(result)
            self.logger.debug(
                "Recorded effectiveness for applied skills.",
                extra={
                    **log_context,
                    "applied_skill_count": len(self._applied_skills),
                },
            )

        return result

    def _detect_domain(self, context: Dict[str, Any]) -> str:
        """Detect domain from task context."""
        task = context.get("task", "").lower()
        files = context.get("changed_files", [])

        # Check task keywords
        domain_keywords = {
            "backend": ["api", "server", "database", "endpoint", "rest", "graphql"],
            "frontend": ["ui", "component", "react", "vue", "css", "html", "form"],
            "infrastructure": ["deploy", "docker", "kubernetes", "ci", "cd", "terraform"],
            "testing": ["test", "spec", "coverage", "mock", "fixture"],
            "security": ["auth", "security", "encrypt", "permission", "access"],
            "data": ["data", "pipeline", "etl", "analytics", "ml", "model"],
        }

        for domain, keywords in domain_keywords.items():
            if any(kw in task for kw in keywords):
                return domain

        # Check file extensions
        extensions = set()
        for f in files:
            ext = Path(f).suffix.lstrip(".")
            if ext:
                extensions.add(ext)

        ext_domains = {
            "py": "backend",
            "ts": "frontend",
            "tsx": "frontend",
            "jsx": "frontend",
            "go": "backend",
            "rs": "backend",
            "tf": "infrastructure",
            "yaml": "infrastructure",
            "sql": "data",
        }

        for ext in extensions:
            if ext in ext_domains:
                return ext_domains[ext]

        return "general"

    def _inject_relevant_skills(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve and inject relevant learned skills into context."""
        task = context.get("task", "")
        files = context.get("changed_files", [])

        # Retrieve relevant skills
        skill_results = self.retriever.retrieve(
            task_description=task,
            file_paths=files,
            domain=self.domain,
            max_skills=3,
            promoted_only=False,  # Include pending skills for now
        )

        if not skill_results:
            return context

        # Track applied skills (effectiveness will be recorded at end of session)
        self._applied_skills = [skill for skill, _score in skill_results]

        # Build skill injection
        skill_context = []
        for skill, score in skill_results:
            skill_info = {
                "name": skill.name,
                "relevance": f"{score:.0%}",
                "patterns": skill.patterns[:3],  # Top 3 patterns
                "anti_patterns": skill.anti_patterns[:2],  # Top 2 anti-patterns
                "conditions": skill.applicability_conditions,
            }
            skill_context.append(skill_info)
            # NOTE: Application recording moved to _record_skill_effectiveness()
            # to avoid double-counting and include outcome data

        # Inject into context
        context = context.copy()
        context["learned_skills"] = skill_context
        context["learning_context"] = (
            f"Found {len(skill_context)} relevant learned skills. "
            "Consider applying their patterns and avoiding their anti-patterns."
        )

        return context

    def _record_all_feedback(self, result: LoopResult) -> None:
        """Record all iteration feedback to the store."""
        for iter_result in result.iteration_history:
            feedback = IterationFeedback(
                session_id=self.session_id,
                iteration=iter_result.iteration,
                quality_before=iter_result.input_quality,
                quality_after=iter_result.output_quality,
                improvements_applied=iter_result.improvements_applied,
                improvements_needed=[],  # Already applied
                changed_files=iter_result.changed_files,
                test_results={},  # Would need to extract from output
                duration_seconds=iter_result.time_taken,
                success=iter_result.success,
                termination_reason=iter_result.termination_reason,
            )
            self.store.save_feedback(feedback)

    def _extract_and_save_skill(self, result: LoopResult) -> Optional[LearnedSkill]:
        """Extract a learned skill from a successful session."""
        skill = self.extractor.extract_from_session(
            session_id=self.session_id,
            repo_path=self.repo_path,
            domain=self.domain,
        )

        if skill is None:
            return None

        # Save the skill
        self.store.save_skill(skill)

        # Auto-promote if enabled and meets criteria
        if self.auto_promote:
            should_promote, reason = self.promotion_gate.evaluate(skill)
            if should_promote:
                self.metrics_emitter(
                    "learning.skills.promoted.count", 1, {"reason": "auto"}
                )
                self.logger.info(
                    "Auto-promoting skill.",
                    extra={
                        "loop_id": self.loop_id,
                        "session_id": self.session_id,
                        "skill_id": skill.skill_id,
                        "reason": reason,
                    },
                )
                self.promotion_gate.promote(skill, reason)

        return skill

    def _record_skill_effectiveness(self, result: LoopResult) -> None:
        """Record how effective the applied skills were."""
        final_quality = result.final_assessment.overall_score
        # Get initial quality from first iteration, or use 0 if no iterations
        initial_quality = (
            result.iteration_history[0].input_quality if result.iteration_history else 0.0
        )
        quality_impact = final_quality - initial_quality
        was_helpful = result.termination_reason == TerminationReason.QUALITY_MET

        for skill in self._applied_skills:
            self.store.record_skill_application(
                skill_id=skill.skill_id,
                session_id=self.session_id,
                was_helpful=was_helpful,
                quality_impact=quality_impact,
                feedback=f"Final quality: {final_quality:.1f}, Termination: {result.termination_reason.value}",
            )


def create_learning_invoker_signal(
    context: Dict[str, Any],
    learned_skills: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Create a signal for Claude Code with learned skill context.

    Extends create_skill_invoker_signal with learned skill information.

    Args:
        context: Context for skill execution
        learned_skills: List of learned skill info dicts

    Returns:
        Signal dict for Claude Code
    """
    signal = create_skill_invoker_signal(context)

    if learned_skills:
        signal["learned_context"] = {
            "skills_applied": len(learned_skills),
            "patterns_to_follow": [
                pattern for skill in learned_skills for pattern in skill.get("patterns", [])
            ],
            "patterns_to_avoid": [
                pattern for skill in learned_skills for pattern in skill.get("anti_patterns", [])
            ],
        }

    return signal


# --- CLI Entry Point ---


def run_learning_loop(
    task: str,
    max_iterations: int = 3,
    quality_threshold: float = 70.0,
    enable_learning: bool = True,
    auto_promote: bool = False,
) -> Dict[str, Any]:
    """
    Run an agentic loop with learning enabled.

    This is the main entry point for --loop with learning.

    Args:
        task: Task description
        max_iterations: Maximum iterations
        quality_threshold: Quality threshold to meet
        enable_learning: Whether to enable learning
        auto_promote: Whether to auto-promote skills

    Returns:
        Result dict with loop outcome and learning metadata
    """
    config = LoopConfig(
        max_iterations=max_iterations,
        quality_threshold=quality_threshold,
    )

    orchestrator = LearningLoopOrchestrator(
        config=config,
        enable_learning=enable_learning,
        auto_promote=auto_promote,
    )

    # Create initial context
    initial_context = {
        "task": task,
        "improvements_needed": [],
        "changed_files": [],
    }

    # Placeholder skill invoker (Claude Code would provide this)
    def placeholder_invoker(ctx: dict[str, Any]) -> dict[str, Any]:
        """Placeholder - Claude Code provides actual invoker."""
        return {
            "changes": [],
            "tests": {"ran": False},
            "lint": {"ran": False},
            "changed_files": [],
        }

    result = orchestrator.run(initial_context, placeholder_invoker)

    return {
        "success": result.termination_reason == TerminationReason.QUALITY_MET,
        "termination_reason": result.termination_reason.value,
        "iterations": result.total_iterations,
        "final_score": result.final_assessment.overall_score,
        "session_id": orchestrator.session_id,
        "skills_applied": len(orchestrator._applied_skills),
        "learning_enabled": enable_learning,
    }


# --- Utility Functions ---


def list_pending_skills() -> List[Dict[str, Any]]:
    """List skills pending promotion review."""
    store = SkillStore()
    gate = PromotionGate(store)
    pending = gate.list_pending()

    return [
        {
            "skill_id": skill.skill_id,
            "name": skill.name,
            "quality_score": skill.quality_score,
            "source_session": skill.source_session,
            "learned_at": skill.learned_at,
            "patterns": len(skill.patterns),
        }
        for skill in pending
    ]


def promote_skill(skill_id: str, reason: str = "") -> bool:
    """Manually promote a skill."""
    store = SkillStore()
    gate = PromotionGate(store)

    skill = store.get_skill(skill_id)
    if skill is None:
        return False

    path = gate.promote(skill, reason)
    return path is not None


def get_skill_stats() -> Dict[str, Any]:
    """Get overall skill learning statistics."""
    store = SkillStore()
    conn = store._get_connection()

    # Count skills
    skill_counts = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN promoted = 1 THEN 1 ELSE 0 END) as promoted,
            AVG(quality_score) as avg_quality
        FROM learned_skills
    """).fetchone()

    # Count feedback
    feedback_count = conn.execute("SELECT COUNT(*) FROM iteration_feedback").fetchone()[0]

    # Count applications
    app_stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN was_helpful = 1 THEN 1 ELSE 0 END) as helpful
        FROM skill_applications
    """).fetchone()

    return {
        "total_skills": skill_counts["total"] or 0,
        "promoted_skills": skill_counts["promoted"] or 0,
        "avg_quality": skill_counts["avg_quality"] or 0.0,
        "total_feedback_records": feedback_count or 0,
        "total_applications": app_stats["total"] or 0,
        "helpful_applications": app_stats["helpful"] or 0,
        "success_rate": (
            (app_stats["helpful"] or 0) / app_stats["total"] if app_stats["total"] else 0
        ),
    }
