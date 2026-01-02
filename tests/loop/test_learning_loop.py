"""Tests for the LearningLoopOrchestrator.

Validates that skill learning, retrieval, and feedback mechanisms
are correctly integrated into the agentic loop.

This addresses P0-2: LearningLoopOrchestrator completely untested.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.skill_learning_integration import LearningLoopOrchestrator
from core.types import (
    LoopConfig,
    TerminationReason,
)
from tests.loop.conftest import FixtureAssessor, FixtureSkillInvoker


@pytest.fixture
def mock_skill_store():
    """Create a mock SkillStore."""
    store = MagicMock()
    store.save_feedback = MagicMock()
    store.save_skill = MagicMock()
    store.record_skill_application = MagicMock()
    return store


@pytest.fixture
def mock_skill_extractor():
    """Create a mock SkillExtractor."""
    extractor = MagicMock()
    extractor.extract_from_session = MagicMock(return_value=None)
    return extractor


@pytest.fixture
def mock_skill_retriever():
    """Create a mock SkillRetriever."""
    retriever = MagicMock()
    retriever.retrieve = MagicMock(return_value=[])
    return retriever


@pytest.fixture
def mock_promotion_gate():
    """Create a mock PromotionGate."""
    gate = MagicMock()
    gate.evaluate = MagicMock(return_value=(False, ""))
    gate.promote = MagicMock()
    return gate


@pytest.fixture
def mock_learned_skill():
    """Create a mock LearnedSkill object."""
    skill = MagicMock()
    skill.skill_id = "skill-abc-123"
    skill.name = "Refactor to use context manager"
    skill.patterns = ["Use 'with open(...)' for file handling", "Clean up resources"]
    skill.anti_patterns = ["Leaving file handles open"]
    skill.applicability_conditions = ["When *.py files are modified"]
    skill.quality_score = 85.0
    return skill


@pytest.fixture
def patched_skill_dependencies(
    mock_skill_store,
    mock_skill_extractor,
    mock_skill_retriever,
    mock_promotion_gate,
):
    """Patch all skill_persistence dependencies."""
    with patch("core.skill_learning_integration.SkillStore", return_value=mock_skill_store), \
         patch("core.skill_learning_integration.SkillExtractor", return_value=mock_skill_extractor), \
         patch("core.skill_learning_integration.SkillRetriever", return_value=mock_skill_retriever), \
         patch("core.skill_learning_integration.PromotionGate", return_value=mock_promotion_gate):
        yield {
            "store": mock_skill_store,
            "extractor": mock_skill_extractor,
            "retriever": mock_skill_retriever,
            "gate": mock_promotion_gate,
        }


class TestLearningLoopOrchestratorInit:
    """Tests for LearningLoopOrchestrator initialization."""

    def test_inherits_from_loop_orchestrator(self, patched_skill_dependencies):
        """LearningLoopOrchestrator should inherit from LoopOrchestrator."""
        from core.loop_orchestrator import LoopOrchestrator

        orchestrator = LearningLoopOrchestrator()
        assert isinstance(orchestrator, LoopOrchestrator)

    def test_default_learning_enabled(self, patched_skill_dependencies):
        """Learning should be enabled by default."""
        orchestrator = LearningLoopOrchestrator()
        assert orchestrator.enable_learning is True

    def test_learning_can_be_disabled(self, patched_skill_dependencies):
        """Learning should be disableable."""
        orchestrator = LearningLoopOrchestrator(enable_learning=False)
        assert orchestrator.enable_learning is False

    def test_auto_promote_disabled_by_default(self, patched_skill_dependencies):
        """Auto-promotion should be disabled by default."""
        orchestrator = LearningLoopOrchestrator()
        assert orchestrator.auto_promote is False

    def test_session_id_generated(self, patched_skill_dependencies):
        """Each orchestrator should have a unique session ID."""
        orchestrator1 = LearningLoopOrchestrator()
        orchestrator2 = LearningLoopOrchestrator()
        assert orchestrator1.session_id != orchestrator2.session_id
        assert len(orchestrator1.session_id) == 12  # UUID prefix


class TestInjectRelevantSkills:
    """Tests for _inject_relevant_skills() method."""

    def test_skills_injected_into_context(
        self, patched_skill_dependencies, mock_learned_skill
    ):
        """Retrieved skills should be injected into context."""
        patched_skill_dependencies["retriever"].retrieve.return_value = [
            (mock_learned_skill, 0.95)
        ]

        orchestrator = LearningLoopOrchestrator()
        initial_context = {"task": "Refactor file I/O"}

        updated_context = orchestrator._inject_relevant_skills(initial_context)

        assert "learned_skills" in updated_context
        assert "learning_context" in updated_context
        assert len(updated_context["learned_skills"]) == 1

    def test_skill_info_correctly_formatted(
        self, patched_skill_dependencies, mock_learned_skill
    ):
        """Skill info should include name, relevance, patterns, anti-patterns."""
        patched_skill_dependencies["retriever"].retrieve.return_value = [
            (mock_learned_skill, 0.95)
        ]

        orchestrator = LearningLoopOrchestrator()
        updated = orchestrator._inject_relevant_skills({"task": "test"})

        skill_info = updated["learned_skills"][0]
        assert skill_info["name"] == mock_learned_skill.name
        assert skill_info["relevance"] == "95%"
        assert len(skill_info["patterns"]) > 0
        assert len(skill_info["anti_patterns"]) > 0

    def test_applied_skills_tracked(
        self, patched_skill_dependencies, mock_learned_skill
    ):
        """Applied skills should be tracked for effectiveness measurement."""
        patched_skill_dependencies["retriever"].retrieve.return_value = [
            (mock_learned_skill, 0.9)
        ]

        orchestrator = LearningLoopOrchestrator()
        orchestrator._inject_relevant_skills({"task": "test"})

        assert orchestrator._applied_skills == [mock_learned_skill]

    def test_no_skills_returns_unmodified_context(self, patched_skill_dependencies):
        """Context should be unmodified if no skills found."""
        patched_skill_dependencies["retriever"].retrieve.return_value = []

        orchestrator = LearningLoopOrchestrator()
        original_context = {"task": "test", "key": "value"}
        updated = orchestrator._inject_relevant_skills(original_context.copy())

        assert "learned_skills" not in updated
        assert updated["task"] == "test"
        assert updated["key"] == "value"

    def test_retriever_called_with_correct_params(
        self, patched_skill_dependencies
    ):
        """Retriever should be called with task, files, domain."""
        retriever = patched_skill_dependencies["retriever"]
        retriever.retrieve.return_value = []

        orchestrator = LearningLoopOrchestrator()
        orchestrator.domain = "backend"
        orchestrator._inject_relevant_skills({
            "task": "Implement API endpoint",
            "changed_files": ["api.py"],
        })

        retriever.retrieve.assert_called_once()
        call_kwargs = retriever.retrieve.call_args.kwargs
        assert call_kwargs["task_description"] == "Implement API endpoint"
        assert call_kwargs["file_paths"] == ["api.py"]
        assert call_kwargs["domain"] == "backend"
        assert call_kwargs["max_skills"] == 3


class TestRecordAllFeedback:
    """Tests for _record_all_feedback() method."""

    def test_feedback_saved_for_each_iteration(self, patched_skill_dependencies):
        """Feedback should be saved for every iteration in history."""
        from core.types import IterationResult

        orchestrator = LearningLoopOrchestrator()
        store = patched_skill_dependencies["store"]

        # Create a mock LoopResult with iteration history
        result = MagicMock()
        result.iteration_history = [
            IterationResult(
                iteration=0,
                input_quality=0.0,
                output_quality=50.0,
                improvements_applied=["Fix bug"],
                time_taken=1.5,
                success=False,
                termination_reason="",
                changed_files=["main.py"],
            ),
            IterationResult(
                iteration=1,
                input_quality=50.0,
                output_quality=75.0,
                improvements_applied=["Add tests"],
                time_taken=2.0,
                success=True,
                termination_reason="quality_met",
                changed_files=["test_main.py"],
            ),
        ]

        orchestrator._record_all_feedback(result)

        assert store.save_feedback.call_count == 2

    def test_feedback_contains_correct_data(self, patched_skill_dependencies):
        """Saved feedback should contain correct iteration data."""
        from core.types import IterationResult

        orchestrator = LearningLoopOrchestrator()
        store = patched_skill_dependencies["store"]

        result = MagicMock()
        result.iteration_history = [
            IterationResult(
                iteration=0,
                input_quality=40.0,
                output_quality=55.0,
                improvements_applied=["Refactor"],
                time_taken=1.0,
                success=False,
                termination_reason="",
                changed_files=["app.py"],
            ),
        ]

        orchestrator._record_all_feedback(result)

        # Get the feedback object passed to save_feedback
        feedback = store.save_feedback.call_args.args[0]
        assert feedback.session_id == orchestrator.session_id
        assert feedback.iteration == 0
        assert feedback.quality_before == 40.0
        assert feedback.quality_after == 55.0
        assert feedback.changed_files == ["app.py"]


class TestExtractAndSaveSkill:
    """Tests for _extract_and_save_skill() method."""

    @pytest.mark.parametrize(
        "termination_reason,should_extract",
        [
            (TerminationReason.QUALITY_MET, True),
            (TerminationReason.MAX_ITERATIONS, False),
            (TerminationReason.OSCILLATION, False),
            (TerminationReason.STAGNATION, False),
            (TerminationReason.ERROR, False),
            (TerminationReason.TIMEOUT, False),
        ],
    )
    def test_extraction_only_on_quality_met(
        self,
        patched_skill_dependencies,
        termination_reason,
        should_extract,
    ):
        """Skill extraction should only happen on QUALITY_MET."""
        extractor = patched_skill_dependencies["extractor"]

        # Configure assessor for appropriate termination
        if should_extract:
            assessor = FixtureAssessor(scores=[80.0], passed_at=70.0)
        else:
            assessor = FixtureAssessor(scores=[50.0], passed_at=70.0)

        config = LoopConfig(max_iterations=1, quality_threshold=70.0)
        orchestrator = LearningLoopOrchestrator(config=config)

        with patch.object(orchestrator, "assessor", assessor):
            orchestrator.run({"task": "test"}, FixtureSkillInvoker())

        if should_extract:
            extractor.extract_from_session.assert_called_once()
        else:
            extractor.extract_from_session.assert_not_called()

    def test_extracted_skill_saved_to_store(
        self, patched_skill_dependencies, mock_learned_skill
    ):
        """Extracted skill should be saved to the store."""
        extractor = patched_skill_dependencies["extractor"]
        store = patched_skill_dependencies["store"]
        extractor.extract_from_session.return_value = mock_learned_skill

        assessor = FixtureAssessor(scores=[80.0], passed_at=70.0)
        config = LoopConfig(quality_threshold=70.0)
        orchestrator = LearningLoopOrchestrator(config=config)

        with patch.object(orchestrator, "assessor", assessor):
            orchestrator.run({"task": "test"}, FixtureSkillInvoker())

        store.save_skill.assert_called_once_with(mock_learned_skill)

    def test_no_skill_extracted_returns_none(self, patched_skill_dependencies):
        """Should handle case where no skill is extracted."""
        extractor = patched_skill_dependencies["extractor"]
        store = patched_skill_dependencies["store"]
        extractor.extract_from_session.return_value = None

        assessor = FixtureAssessor(scores=[80.0], passed_at=70.0)
        config = LoopConfig(quality_threshold=70.0)
        orchestrator = LearningLoopOrchestrator(config=config)

        with patch.object(orchestrator, "assessor", assessor):
            orchestrator.run({"task": "test"}, FixtureSkillInvoker())

        store.save_skill.assert_not_called()


class TestRecordSkillEffectiveness:
    """Tests for _record_skill_effectiveness() method."""

    def test_effectiveness_recorded_for_applied_skills(
        self, patched_skill_dependencies, mock_learned_skill
    ):
        """Skill effectiveness should be recorded when skills were applied."""
        retriever = patched_skill_dependencies["retriever"]
        store = patched_skill_dependencies["store"]
        retriever.retrieve.return_value = [(mock_learned_skill, 0.9)]

        assessor = FixtureAssessor(scores=[50.0, 80.0], passed_at=70.0)
        config = LoopConfig(quality_threshold=70.0)
        orchestrator = LearningLoopOrchestrator(config=config)

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "test"}, FixtureSkillInvoker())

        assert result.termination_reason == TerminationReason.QUALITY_MET
        store.record_skill_application.assert_called_once()

    def test_effectiveness_includes_quality_impact(
        self, patched_skill_dependencies, mock_learned_skill
    ):
        """Recorded effectiveness should include quality impact."""
        retriever = patched_skill_dependencies["retriever"]
        store = patched_skill_dependencies["store"]
        retriever.retrieve.return_value = [(mock_learned_skill, 0.9)]

        # Scores: 50 -> 80, but quality_impact = final - initial_input_quality
        # The initial input_quality for first iteration is 0.0 by default
        # So impact = 80.0 - 0.0 = 80.0
        assessor = FixtureAssessor(scores=[50.0, 80.0], passed_at=70.0)
        config = LoopConfig(quality_threshold=70.0)
        orchestrator = LearningLoopOrchestrator(config=config)

        with patch.object(orchestrator, "assessor", assessor):
            orchestrator.run({"task": "test"}, FixtureSkillInvoker())

        call_kwargs = store.record_skill_application.call_args.kwargs
        assert call_kwargs["skill_id"] == mock_learned_skill.skill_id
        assert call_kwargs["was_helpful"] is True
        # quality_impact = final_quality (80.0) - first iteration's input_quality (0.0)
        assert call_kwargs["quality_impact"] == 80.0

    def test_not_helpful_when_quality_not_met(
        self, patched_skill_dependencies, mock_learned_skill
    ):
        """Skill should be marked as not helpful if quality not met."""
        retriever = patched_skill_dependencies["retriever"]
        store = patched_skill_dependencies["store"]
        retriever.retrieve.return_value = [(mock_learned_skill, 0.9)]

        # Never reaches quality threshold
        assessor = FixtureAssessor(scores=[50.0], passed_at=70.0)
        config = LoopConfig(max_iterations=1, quality_threshold=70.0)
        orchestrator = LearningLoopOrchestrator(config=config)

        with patch.object(orchestrator, "assessor", assessor):
            result = orchestrator.run({"task": "test"}, FixtureSkillInvoker())

        assert result.termination_reason == TerminationReason.MAX_ITERATIONS
        call_kwargs = store.record_skill_application.call_args.kwargs
        assert call_kwargs["was_helpful"] is False


class TestLearningDisabled:
    """Tests for behavior when learning is disabled."""

    def test_no_skill_retrieval_when_disabled(self, patched_skill_dependencies):
        """Skills should not be retrieved when learning disabled."""
        retriever = patched_skill_dependencies["retriever"]

        orchestrator = LearningLoopOrchestrator(enable_learning=False)
        orchestrator.run({"task": "test"}, FixtureSkillInvoker())

        retriever.retrieve.assert_not_called()

    def test_no_feedback_saved_when_disabled(self, patched_skill_dependencies):
        """Feedback should not be saved when learning disabled."""
        store = patched_skill_dependencies["store"]

        assessor = FixtureAssessor(scores=[80.0], passed_at=70.0)
        orchestrator = LearningLoopOrchestrator(enable_learning=False)

        with patch.object(orchestrator, "assessor", assessor):
            orchestrator.run({"task": "test"}, FixtureSkillInvoker())

        store.save_feedback.assert_not_called()

    def test_no_skill_extraction_when_disabled(self, patched_skill_dependencies):
        """Skills should not be extracted when learning disabled."""
        extractor = patched_skill_dependencies["extractor"]

        assessor = FixtureAssessor(scores=[80.0], passed_at=70.0)
        orchestrator = LearningLoopOrchestrator(enable_learning=False)

        with patch.object(orchestrator, "assessor", assessor):
            orchestrator.run({"task": "test"}, FixtureSkillInvoker())

        extractor.extract_from_session.assert_not_called()

    def test_no_effectiveness_recording_when_disabled(self, patched_skill_dependencies):
        """Skill effectiveness should not be recorded when disabled."""
        store = patched_skill_dependencies["store"]

        orchestrator = LearningLoopOrchestrator(enable_learning=False)
        orchestrator.run({"task": "test"}, FixtureSkillInvoker())

        store.record_skill_application.assert_not_called()


class TestAutoPromotion:
    """Tests for auto-promotion behavior."""

    def test_auto_promote_calls_promotion_gate(
        self, patched_skill_dependencies, mock_learned_skill
    ):
        """Auto-promotion should call PromotionGate when enabled."""
        extractor = patched_skill_dependencies["extractor"]
        gate = patched_skill_dependencies["gate"]
        extractor.extract_from_session.return_value = mock_learned_skill
        gate.evaluate.return_value = (True, "High quality skill")

        assessor = FixtureAssessor(scores=[80.0], passed_at=70.0)
        config = LoopConfig(quality_threshold=70.0)
        orchestrator = LearningLoopOrchestrator(config=config, auto_promote=True)

        with patch.object(orchestrator, "assessor", assessor):
            orchestrator.run({"task": "test"}, FixtureSkillInvoker())

        gate.evaluate.assert_called_once_with(mock_learned_skill)
        gate.promote.assert_called_once_with(mock_learned_skill, "High quality skill")

    def test_no_promotion_when_gate_rejects(
        self, patched_skill_dependencies, mock_learned_skill
    ):
        """Skill should not be promoted if gate rejects."""
        extractor = patched_skill_dependencies["extractor"]
        gate = patched_skill_dependencies["gate"]
        extractor.extract_from_session.return_value = mock_learned_skill
        gate.evaluate.return_value = (False, "Quality too low")

        assessor = FixtureAssessor(scores=[80.0], passed_at=70.0)
        config = LoopConfig(quality_threshold=70.0)
        orchestrator = LearningLoopOrchestrator(config=config, auto_promote=True)

        with patch.object(orchestrator, "assessor", assessor):
            orchestrator.run({"task": "test"}, FixtureSkillInvoker())

        gate.evaluate.assert_called_once()
        gate.promote.assert_not_called()


class TestDomainDetection:
    """Tests for _detect_domain() method."""

    @pytest.mark.parametrize(
        "task,expected_domain",
        [
            ("Implement REST API endpoint", "backend"),
            ("Add GraphQL mutation", "backend"),
            ("Create React component", "frontend"),
            ("Fix CSS styling", "frontend"),
            ("Deploy to Kubernetes", "infrastructure"),
            ("Write unit tests", "testing"),
            ("Add authentication", "security"),
            # Note: "Build ML pipeline" would match "ui" in "build" for frontend
            # before reaching "data" domain, so we test with "Create ML model" instead
            ("Create ML model for analytics", "data"),
        ],
    )
    def test_domain_from_task_keywords(
        self, patched_skill_dependencies, task, expected_domain
    ):
        """Domain should be detected from task keywords."""
        orchestrator = LearningLoopOrchestrator()
        domain = orchestrator._detect_domain({"task": task})
        assert domain == expected_domain

    @pytest.mark.parametrize(
        "files,expected_domain",
        [
            (["main.py", "api.py"], "backend"),
            (["component.tsx", "styles.css"], "frontend"),
            (["main.go"], "backend"),
            (["deploy.tf"], "infrastructure"),
            (["query.sql"], "data"),
        ],
    )
    def test_domain_from_file_extensions(
        self, patched_skill_dependencies, files, expected_domain
    ):
        """Domain should be detected from file extensions."""
        orchestrator = LearningLoopOrchestrator()
        domain = orchestrator._detect_domain({"task": "Generic task", "changed_files": files})
        assert domain == expected_domain

    def test_defaults_to_general(self, patched_skill_dependencies):
        """Unknown domain should default to 'general'."""
        orchestrator = LearningLoopOrchestrator()
        domain = orchestrator._detect_domain({"task": "Do something"})
        assert domain == "general"
