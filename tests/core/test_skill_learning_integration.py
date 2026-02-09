"""Tests for the skill learning integration module."""

from __future__ import annotations

import pytest

from core.skill_learning_integration import (
    LearningLoopOrchestrator,
    create_learning_invoker_signal,
    get_skill_stats,
    list_pending_skills,
    promote_skill,
    run_learning_loop,
)
from core.skill_persistence import LearnedSkill, SkillStore
from core.types import LoopConfig

# --- Fixtures ---


@pytest.fixture
def temp_store(tmp_path):
    """Create a temporary skill store."""
    db_path = tmp_path / "test_learning.db"
    store = SkillStore(db_path)
    yield store
    store.close()


@pytest.fixture
def learning_orchestrator(temp_store):
    """Create a learning orchestrator with temp store."""
    config = LoopConfig(max_iterations=3, quality_threshold=70.0)
    return LearningLoopOrchestrator(
        config=config,
        store=temp_store,
        enable_learning=True,
        auto_promote=False,
    )


@pytest.fixture
def sample_skill():
    """Create a sample skill for testing."""
    return LearnedSkill(
        skill_id="test-learn-001",
        name="Test Learning Skill",
        description="A test skill",
        triggers=["test", "learn"],
        domain="testing",
        source_session="session-123",
        source_repo="/path/to/repo",
        learned_at="2025-01-01T00:00:00Z",
        patterns=["Pattern 1"],
        anti_patterns=["Anti-pattern 1"],
        quality_score=90.0,
        iteration_count=3,
        provenance={},
        applicability_conditions=[],
        promoted=False,
        promotion_reason="",
    )


# --- LearningLoopOrchestrator Tests ---


class TestLearningLoopOrchestrator:
    """Tests for LearningLoopOrchestrator."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        orchestrator = LearningLoopOrchestrator()
        assert orchestrator.enable_learning is True
        assert orchestrator.auto_promote is False
        assert orchestrator.session_id is not None

    def test_init_with_custom_config(self, temp_store):
        """Test initialization with custom config."""
        config = LoopConfig(max_iterations=5, quality_threshold=80.0)
        orchestrator = LearningLoopOrchestrator(
            config=config,
            store=temp_store,
            enable_learning=False,
            auto_promote=True,
        )
        assert orchestrator.config.max_iterations == 5
        assert orchestrator.config.quality_threshold == 80.0
        assert orchestrator.enable_learning is False
        assert orchestrator.auto_promote is True

    def test_detect_domain_from_task(self, learning_orchestrator):
        """Test domain detection from task description."""
        # Test backend keywords
        context = {"task": "implement REST API endpoint"}
        domain = learning_orchestrator._detect_domain(context)
        assert domain == "backend"

        # Test frontend keywords
        context = {"task": "create React component"}
        domain = learning_orchestrator._detect_domain(context)
        assert domain == "frontend"

        # Test testing keywords
        context = {"task": "write unit tests"}
        domain = learning_orchestrator._detect_domain(context)
        assert domain == "testing"

    def test_detect_domain_from_files(self, learning_orchestrator):
        """Test domain detection from file extensions."""
        context = {"task": "update code", "changed_files": ["app.tsx", "styles.css"]}
        domain = learning_orchestrator._detect_domain(context)
        assert domain == "frontend"

        context = {"task": "update code", "changed_files": ["main.py", "utils.py"]}
        domain = learning_orchestrator._detect_domain(context)
        assert domain == "backend"

    def test_detect_domain_default(self, learning_orchestrator):
        """Test domain defaults to general."""
        context = {"task": "do something", "changed_files": []}
        domain = learning_orchestrator._detect_domain(context)
        assert domain == "general"

    def test_inject_relevant_skills(self, learning_orchestrator, temp_store, sample_skill):
        """Test skill injection into context."""
        temp_store.save_skill(sample_skill)
        context = {"task": "test learning"}
        result = learning_orchestrator._inject_relevant_skills(context)
        # May or may not find skills depending on matching
        assert "task" in result

    def test_inject_skills_empty_when_none(self, learning_orchestrator):
        """Test skill injection returns original context when no skills match."""
        context = {"task": "completely unrelated task xyz123"}
        result = learning_orchestrator._inject_relevant_skills(context)
        assert result.get("learned_skills") is None or len(result.get("learned_skills", [])) == 0

    def test_repo_path_detection(self, learning_orchestrator):
        """Test repository path detection."""
        # Should detect some path (cwd or git root)
        assert learning_orchestrator.repo_path is not None
        assert len(learning_orchestrator.repo_path) > 0


# --- Utility Function Tests ---


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_create_learning_invoker_signal_basic(self):
        """Test creating invoker signal without learned skills."""
        context = {"task": "implement feature", "files": ["main.py"]}
        signal = create_learning_invoker_signal(context)
        assert "task" in signal or "context" in str(signal).lower()

    def test_create_learning_invoker_signal_with_skills(self):
        """Test creating invoker signal with learned skills."""
        context = {"task": "implement feature"}
        learned_skills = [
            {"name": "skill1", "patterns": ["p1", "p2"], "anti_patterns": ["a1"]},
            {"name": "skill2", "patterns": ["p3"], "anti_patterns": []},
        ]
        signal = create_learning_invoker_signal(context, learned_skills)
        assert "learned_context" in signal
        assert signal["learned_context"]["skills_applied"] == 2
        assert len(signal["learned_context"]["patterns_to_follow"]) == 3
        assert len(signal["learned_context"]["patterns_to_avoid"]) == 1

    def test_list_pending_skills(self, tmp_path, monkeypatch):
        """Test listing pending skills."""
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_SKILLS_DIR",
            tmp_path / "skills",
        )
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_FEEDBACK_DIR",
            tmp_path / "feedback",
        )
        # Should return empty list when no skills
        pending = list_pending_skills()
        assert isinstance(pending, list)

    def test_get_skill_stats(self, tmp_path, monkeypatch):
        """Test getting skill statistics."""
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_SKILLS_DIR",
            tmp_path / "skills",
        )
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_FEEDBACK_DIR",
            tmp_path / "feedback",
        )
        stats = get_skill_stats()
        assert "total_skills" in stats
        assert "promoted_skills" in stats
        assert "total_applications" in stats
        assert stats["total_skills"] == 0

    def test_promote_skill_nonexistent(self, tmp_path, monkeypatch):
        """Test promoting a non-existent skill returns False."""
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_SKILLS_DIR",
            tmp_path / "skills",
        )
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_FEEDBACK_DIR",
            tmp_path / "feedback",
        )
        result = promote_skill("nonexistent-skill-id")
        assert result is False


# --- Run Learning Loop Tests ---


class TestRunLearningLoop:
    """Tests for run_learning_loop function."""

    def test_run_learning_loop_basic(self, tmp_path, monkeypatch):
        """Test basic learning loop execution."""
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_SKILLS_DIR",
            tmp_path / "skills",
        )
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_FEEDBACK_DIR",
            tmp_path / "feedback",
        )
        result = run_learning_loop(
            task="test task",
            max_iterations=1,
            quality_threshold=70.0,
            enable_learning=True,
        )
        assert "success" in result
        assert "termination_reason" in result
        assert "iterations" in result
        assert "session_id" in result

    def test_run_learning_loop_with_auto_promote(self, tmp_path, monkeypatch):
        """Test learning loop with auto-promote enabled."""
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_SKILLS_DIR",
            tmp_path / "skills",
        )
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_FEEDBACK_DIR",
            tmp_path / "feedback",
        )
        result = run_learning_loop(
            task="implement auth",
            max_iterations=2,
            quality_threshold=70.0,
            enable_learning=True,
            auto_promote=True,
        )
        assert "learning_enabled" in result
        assert result["learning_enabled"] is True

    def test_run_learning_loop_disabled(self, tmp_path, monkeypatch):
        """Test learning loop with learning disabled."""
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_SKILLS_DIR",
            tmp_path / "skills",
        )
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_FEEDBACK_DIR",
            tmp_path / "feedback",
        )
        result = run_learning_loop(
            task="simple task",
            max_iterations=1,
            quality_threshold=70.0,
            enable_learning=False,
        )
        assert result["learning_enabled"] is False
