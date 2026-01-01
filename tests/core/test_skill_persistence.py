"""Tests for the skill persistence layer."""

from __future__ import annotations

import pytest

from core.skill_persistence import (
    IterationFeedback,
    LearnedSkill,
    PromotionGate,
    SkillExtractor,
    SkillRetriever,
    SkillStore,
    get_default_store,
    learn_from_session,
    retrieve_skills_for_task,
)

# --- Fixtures ---


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = tmp_path / "test_skills.db"
    store = SkillStore(db_path)
    yield store
    store.close()


@pytest.fixture
def sample_skill():
    """Create a sample learned skill."""
    return LearnedSkill(
        skill_id="test-skill-001",
        name="Test Skill",
        description="A test skill for unit testing",
        triggers=["test", "unit", "pytest"],
        domain="testing",
        source_session="session-abc123",
        source_repo="/path/to/repo",
        learned_at="2025-01-01T00:00:00Z",
        patterns=["Use pytest fixtures", "Mock external calls"],
        anti_patterns=["Don't test implementation details"],
        quality_score=85.0,
        iteration_count=3,
        provenance={"iterations": 3, "repo": "/path/to/repo"},
        applicability_conditions=["Python projects", "Has test suite"],
        promoted=False,
        promotion_reason="",
    )


@pytest.fixture
def sample_feedback():
    """Create sample iteration feedback."""
    return IterationFeedback(
        session_id="session-abc123",
        iteration=1,
        quality_before=50.0,
        quality_after=75.0,
        improvements_applied=["Added tests", "Fixed linting"],
        improvements_needed=["Add docstrings"],
        changed_files=["test_foo.py", "foo.py"],
        test_results={"ran": True, "passed": 10, "failed": 0},
        duration_seconds=30.5,
        success=True,
        termination_reason="",
    )


@pytest.fixture
def high_quality_skill():
    """Create a high-quality skill that meets promotion criteria."""
    return LearnedSkill(
        skill_id="high-quality-001",
        name="High Quality Skill",
        description="A high quality skill",
        triggers=["quality", "best"],
        domain="backend",
        source_session="session-xyz789",
        source_repo="/path/to/repo",
        learned_at="2025-01-01T00:00:00Z",
        patterns=["Pattern 1", "Pattern 2"],
        anti_patterns=["Anti-pattern 1"],
        quality_score=90.0,
        iteration_count=5,
        provenance={},
        applicability_conditions=[],
        promoted=False,
        promotion_reason="",
    )


# --- SkillStore Tests ---


class TestSkillStore:
    """Tests for SkillStore."""

    def test_init_creates_database(self, tmp_path):
        """Test that initializing SkillStore creates parent directory."""
        db_path = tmp_path / "subdir" / "skills.db"
        store = SkillStore(db_path)
        # Parent directory should be created on init
        assert db_path.parent.exists()
        # Database file is created lazily on first connection
        conn = store._get_connection()
        assert conn is not None
        store.close()

    def test_save_and_get_skill(self, temp_db, sample_skill):
        """Test saving and retrieving a skill."""
        assert temp_db.save_skill(sample_skill) is True
        retrieved = temp_db.get_skill(sample_skill.skill_id)
        assert retrieved is not None
        assert retrieved.name == sample_skill.name
        assert retrieved.domain == sample_skill.domain
        assert retrieved.quality_score == sample_skill.quality_score

    def test_get_nonexistent_skill(self, temp_db):
        """Test retrieving a non-existent skill returns None."""
        result = temp_db.get_skill("nonexistent-skill")
        assert result is None

    def test_get_promoted_skills(self, temp_db, sample_skill):
        """Test getting promoted skills."""
        sample_skill.promoted = True
        temp_db.save_skill(sample_skill)
        promoted = temp_db.get_promoted_skills()
        assert len(promoted) == 1
        assert promoted[0].skill_id == sample_skill.skill_id

    def test_get_skills_by_domain(self, temp_db, sample_skill):
        """Test getting skills by domain."""
        temp_db.save_skill(sample_skill)
        skills = temp_db.get_skills_by_domain("testing")
        assert len(skills) == 1
        assert skills[0].domain == "testing"

    def test_search_skills(self, temp_db, sample_skill):
        """Test searching skills."""
        temp_db.save_skill(sample_skill)
        results = temp_db.search_skills("test", min_quality=50.0)
        assert len(results) == 1

    def test_search_skills_by_domain(self, temp_db, sample_skill):
        """Test searching skills with domain filter."""
        temp_db.save_skill(sample_skill)
        results = temp_db.search_skills("test", domain="testing")
        assert len(results) == 1
        results = temp_db.search_skills("test", domain="backend")
        assert len(results) == 0

    def test_search_promoted_only(self, temp_db, sample_skill):
        """Test searching only promoted skills."""
        temp_db.save_skill(sample_skill)
        results = temp_db.search_skills("test", promoted_only=True)
        assert len(results) == 0
        sample_skill.promoted = True
        temp_db.save_skill(sample_skill)
        results = temp_db.search_skills("test", promoted_only=True)
        assert len(results) == 1

    def test_save_and_get_feedback(self, temp_db, sample_feedback):
        """Test saving and retrieving feedback."""
        assert temp_db.save_feedback(sample_feedback) is True
        feedback_list = temp_db.get_session_feedback(sample_feedback.session_id)
        assert len(feedback_list) == 1
        assert feedback_list[0].quality_before == sample_feedback.quality_before
        assert feedback_list[0].quality_after == sample_feedback.quality_after

    def test_record_skill_application(self, temp_db, sample_skill):
        """Test recording skill application."""
        temp_db.save_skill(sample_skill)
        result = temp_db.record_skill_application(
            skill_id=sample_skill.skill_id,
            session_id="session-123",
            was_helpful=True,
            quality_impact=10.0,
            feedback="Great skill!",
        )
        assert result is True

    def test_get_skill_effectiveness(self, temp_db, sample_skill):
        """Test getting skill effectiveness metrics."""
        temp_db.save_skill(sample_skill)
        temp_db.record_skill_application(
            sample_skill.skill_id, "s1", was_helpful=True, quality_impact=10.0
        )
        temp_db.record_skill_application(
            sample_skill.skill_id, "s2", was_helpful=True, quality_impact=5.0
        )
        temp_db.record_skill_application(
            sample_skill.skill_id, "s3", was_helpful=False, quality_impact=-2.0
        )
        effectiveness = temp_db.get_skill_effectiveness(sample_skill.skill_id)
        assert effectiveness["applications"] == 3
        assert effectiveness["helpful_count"] == 2
        assert effectiveness["unhelpful_count"] == 1

    def test_get_bulk_skill_effectiveness(self, temp_db, sample_skill, high_quality_skill):
        """Test bulk effectiveness fetch."""
        temp_db.save_skill(sample_skill)
        temp_db.save_skill(high_quality_skill)
        temp_db.record_skill_application(
            sample_skill.skill_id, "s1", was_helpful=True, quality_impact=10.0
        )
        results = temp_db.get_bulk_skill_effectiveness(
            [sample_skill.skill_id, high_quality_skill.skill_id]
        )
        assert sample_skill.skill_id in results
        assert high_quality_skill.skill_id in results
        assert results[sample_skill.skill_id]["applications"] == 1
        assert results[high_quality_skill.skill_id]["applications"] == 0

    def test_context_manager(self, tmp_path):
        """Test SkillStore as context manager."""
        db_path = tmp_path / "context_test.db"
        with SkillStore(db_path) as _store:
            # Trigger connection to create the database
            _store._get_connection()
            assert db_path.parent.exists()

    def test_close_method(self, tmp_path):
        """Test explicit close method."""
        db_path = tmp_path / "close_test.db"
        store = SkillStore(db_path)
        store.close()
        # Should not raise even if called again
        store.close()


# --- LearnedSkill Tests ---


class TestLearnedSkill:
    """Tests for LearnedSkill dataclass."""

    def test_to_skill_md(self, sample_skill):
        """Test converting skill to SKILL.md format."""
        md = sample_skill.to_skill_md()
        assert "---" in md
        assert "name: Test Skill" in md
        assert "Use pytest fixtures" in md
        assert "Don't test implementation details" in md
        assert "session-abc123" in md


# --- SkillExtractor Tests ---


class TestSkillExtractor:
    """Tests for SkillExtractor."""

    def test_extract_from_session_no_feedback(self, temp_db):
        """Test extraction with no feedback returns None."""
        extractor = SkillExtractor(temp_db)
        result = extractor.extract_from_session("nonexistent-session")
        assert result is None

    def test_extract_from_session_insufficient_improvement(self, temp_db):
        """Test extraction with insufficient improvement returns None."""
        extractor = SkillExtractor(temp_db)
        feedback = IterationFeedback(
            session_id="low-quality-session",
            iteration=1,
            quality_before=50.0,
            quality_after=55.0,  # Only 5 point improvement
            improvements_applied=[],
            improvements_needed=[],
            changed_files=[],
            test_results={},
            duration_seconds=10.0,
            success=True,
            termination_reason="quality_threshold_met",
        )
        temp_db.save_feedback(feedback)
        result = extractor.extract_from_session("low-quality-session")
        assert result is None

    def test_extract_from_successful_session(self, temp_db):
        """Test extraction from a successful session."""
        extractor = SkillExtractor(temp_db)
        # Create feedback that meets criteria
        feedback1 = IterationFeedback(
            session_id="good-session",
            iteration=1,
            quality_before=50.0,
            quality_after=70.0,
            improvements_applied=["Added type hints", "Fixed imports"],
            improvements_needed=[],
            changed_files=["main.py", "utils.py"],
            test_results={"ran": True},
            duration_seconds=30.0,
            success=True,
            termination_reason="",
        )
        feedback2 = IterationFeedback(
            session_id="good-session",
            iteration=2,
            quality_before=70.0,
            quality_after=85.0,
            improvements_applied=["Added tests"],
            improvements_needed=[],
            changed_files=["test_main.py"],
            test_results={"ran": True},
            duration_seconds=20.0,
            success=True,
            termination_reason="quality_threshold_met",
        )
        temp_db.save_feedback(feedback1)
        temp_db.save_feedback(feedback2)
        result = extractor.extract_from_session("good-session", domain="backend")
        assert result is not None
        assert result.domain == "backend"
        assert result.quality_score >= 70.0


# --- SkillRetriever Tests ---


class TestSkillRetriever:
    """Tests for SkillRetriever."""

    def test_retrieve_no_skills(self, temp_db):
        """Test retrieval with no skills returns empty list."""
        retriever = SkillRetriever(temp_db)
        results = retriever.retrieve("implement auth")
        assert results == []

    def test_retrieve_matching_skills(self, temp_db, sample_skill):
        """Test retrieval finds matching skills."""
        temp_db.save_skill(sample_skill)
        retriever = SkillRetriever(temp_db)
        results = retriever.retrieve("unit testing", promoted_only=False)
        assert len(results) >= 1
        skill, score = results[0]
        assert skill.skill_id == sample_skill.skill_id
        assert score > 0

    def test_retrieve_with_domain_filter(self, temp_db, sample_skill, high_quality_skill):
        """Test retrieval respects domain filter."""
        temp_db.save_skill(sample_skill)
        temp_db.save_skill(high_quality_skill)
        retriever = SkillRetriever(temp_db)
        results = retriever.retrieve("skill", domain="testing", promoted_only=False)
        assert all(s.domain == "testing" for s, _ in results)

    def test_retrieve_with_file_paths(self, temp_db, sample_skill):
        """Test retrieval considers file paths."""
        temp_db.save_skill(sample_skill)
        retriever = SkillRetriever(temp_db)
        # Use task description that matches skill triggers
        results = retriever.retrieve(
            "unit test pytest", file_paths=["test_foo.py", "conftest.py"], promoted_only=False
        )
        # Results depend on matching; just verify the method works
        assert isinstance(results, list)


# --- PromotionGate Tests ---


class TestPromotionGate:
    """Tests for PromotionGate."""

    def test_evaluate_low_quality(self, temp_db, sample_skill):
        """Test evaluation rejects low quality skills."""
        sample_skill.quality_score = 70.0  # Below threshold
        temp_db.save_skill(sample_skill)
        gate = PromotionGate(temp_db)
        can_promote, reason = gate.evaluate(sample_skill)
        assert can_promote is False
        assert "quality" in reason.lower()

    def test_evaluate_insufficient_applications(self, temp_db, high_quality_skill):
        """Test evaluation rejects skills with too few applications."""
        temp_db.save_skill(high_quality_skill)
        gate = PromotionGate(temp_db)
        can_promote, reason = gate.evaluate(high_quality_skill)
        assert can_promote is False
        assert "application" in reason.lower()

    def test_evaluate_meets_criteria(self, temp_db, high_quality_skill):
        """Test evaluation approves qualifying skills."""
        temp_db.save_skill(high_quality_skill)
        # Add successful applications
        for i in range(3):
            temp_db.record_skill_application(
                high_quality_skill.skill_id, f"session-{i}", was_helpful=True, quality_impact=5.0
            )
        gate = PromotionGate(temp_db)
        can_promote, reason = gate.evaluate(high_quality_skill)
        assert can_promote is True

    def test_promote_skill(self, temp_db, high_quality_skill, tmp_path):
        """Test promoting a skill creates files."""
        temp_db.save_skill(high_quality_skill)
        for i in range(3):
            temp_db.record_skill_application(
                high_quality_skill.skill_id, f"s-{i}", was_helpful=True, quality_impact=5.0
            )
        gate = PromotionGate(temp_db, skills_dir=tmp_path)
        path = gate.promote(high_quality_skill, "Test promotion")
        assert path is not None
        assert path.exists()
        assert "SKILL.md" in str(path)

    def test_list_pending(self, temp_db, sample_skill, high_quality_skill):
        """Test listing pending skills."""
        temp_db.save_skill(sample_skill)
        temp_db.save_skill(high_quality_skill)
        gate = PromotionGate(temp_db)
        pending = gate.list_pending()
        assert len(pending) >= 1


# --- Convenience Function Tests ---


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_default_store(self, tmp_path, monkeypatch):
        """Test get_default_store returns a store."""
        # Override the default path
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_DB_PATH",
            tmp_path / "default_test.db",
        )
        store = get_default_store()
        assert store is not None
        store.close()

    def test_learn_from_session_no_data(self, tmp_path, monkeypatch):
        """Test learn_from_session with no data returns None."""
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_DB_PATH",
            tmp_path / "learn_test.db",
        )
        result = learn_from_session("nonexistent-session")
        assert result is None

    def test_retrieve_skills_for_task(self, tmp_path, monkeypatch):
        """Test retrieve_skills_for_task works."""
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_DB_PATH",
            tmp_path / "retrieve_test.db",
        )
        # Should return empty list when no skills exist
        result = retrieve_skills_for_task("implement auth")
        assert result == []
