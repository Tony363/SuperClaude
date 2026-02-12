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
    """Create a temporary file-based store for testing."""
    skills_dir = tmp_path / "skills" / "learned"
    feedback_dir = tmp_path / "feedback"
    store = SkillStore(skills_dir=skills_dir, feedback_dir=feedback_dir)
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

    def test_init_creates_directories(self, tmp_path):
        """Test that initializing SkillStore creates parent directories."""
        skills_dir = tmp_path / "subdir" / "skills" / "learned"
        feedback_dir = tmp_path / "subdir" / "feedback"
        store = SkillStore(skills_dir=skills_dir, feedback_dir=feedback_dir)
        # Directories should be created on init
        assert skills_dir.exists()
        assert feedback_dir.exists()
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
        skills_dir = tmp_path / "context_test" / "skills" / "learned"
        feedback_dir = tmp_path / "context_test" / "feedback"
        with SkillStore(skills_dir=skills_dir, feedback_dir=feedback_dir) as _store:
            # Directories should be created
            assert skills_dir.exists()
            assert feedback_dir.exists()

    def test_close_method(self, tmp_path):
        """Test explicit close method."""
        skills_dir = tmp_path / "close_test" / "skills" / "learned"
        feedback_dir = tmp_path / "close_test" / "feedback"
        store = SkillStore(skills_dir=skills_dir, feedback_dir=feedback_dir)
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
        # Override the default paths
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_SKILLS_DIR",
            tmp_path / "default_test" / "skills" / "learned",
        )
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_FEEDBACK_DIR",
            tmp_path / "default_test" / "feedback",
        )
        store = get_default_store()
        assert store is not None
        store.close()

    def test_learn_from_session_no_data(self, tmp_path, monkeypatch):
        """Test learn_from_session with no data returns None."""
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_SKILLS_DIR",
            tmp_path / "learn_test" / "skills" / "learned",
        )
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_FEEDBACK_DIR",
            tmp_path / "learn_test" / "feedback",
        )
        result = learn_from_session("nonexistent-session")
        assert result is None

    def test_retrieve_skills_for_task(self, tmp_path, monkeypatch):
        """Test retrieve_skills_for_task works."""
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_SKILLS_DIR",
            tmp_path / "retrieve_test" / "skills" / "learned",
        )
        monkeypatch.setattr(
            "core.skill_persistence.SkillStore.DEFAULT_FEEDBACK_DIR",
            tmp_path / "retrieve_test" / "feedback",
        )
        # Should return empty list when no skills exist
        result = retrieve_skills_for_task("implement auth")
        assert result == []


# --- LearnedSkill Extended Tests ---


class TestLearnedSkillDataclass:
    """Extended tests for LearnedSkill dataclass."""

    def test_to_dict_round_trip(self, sample_skill):
        """to_dict and from_dict should round-trip."""
        d = sample_skill.to_dict()
        restored = LearnedSkill.from_dict(d)
        assert restored.skill_id == sample_skill.skill_id
        assert restored.name == sample_skill.name
        assert restored.patterns == sample_skill.patterns
        assert restored.anti_patterns == sample_skill.anti_patterns
        assert restored.quality_score == sample_skill.quality_score

    def test_to_dict_contains_all_fields(self, sample_skill):
        """to_dict should include all dataclass fields."""
        d = sample_skill.to_dict()
        assert "skill_id" in d
        assert "name" in d
        assert "triggers" in d
        assert "domain" in d
        assert "patterns" in d
        assert "anti_patterns" in d
        assert "promoted" in d
        assert "promotion_reason" in d

    def test_to_skill_md_has_frontmatter(self, sample_skill):
        """SKILL.md should contain YAML frontmatter."""
        md = sample_skill.to_skill_md()
        assert md.startswith("---")
        assert "learned: true" in md

    def test_to_skill_md_has_domain_section(self, sample_skill):
        """SKILL.md should have domain section."""
        md = sample_skill.to_skill_md()
        assert "## Domain" in md
        assert "testing" in md

    def test_to_skill_md_has_triggers(self, sample_skill):
        """SKILL.md should list triggers."""
        md = sample_skill.to_skill_md()
        assert "## Triggers" in md
        assert "test" in md

    def test_to_skill_md_has_anti_patterns(self, sample_skill):
        """SKILL.md should list anti-patterns."""
        md = sample_skill.to_skill_md()
        assert "## Anti-Patterns" in md
        assert "Don't test implementation details" in md

    def test_to_skill_md_provenance(self, sample_skill):
        """SKILL.md should include provenance."""
        md = sample_skill.to_skill_md()
        assert "## Provenance" in md
        assert "session-abc123" in md
        assert "85.0" in md

    def test_default_promoted_false(self, sample_skill):
        """Default promoted should be False."""
        assert sample_skill.promoted is False
        assert sample_skill.promotion_reason == ""


# --- IterationFeedback Tests ---


class TestIterationFeedback:
    """Tests for IterationFeedback dataclass."""

    def test_to_dict(self, sample_feedback):
        """to_dict should serialize all fields."""
        d = sample_feedback.to_dict()
        assert d["session_id"] == "session-abc123"
        assert d["iteration"] == 1
        assert d["quality_before"] == 50.0
        assert d["quality_after"] == 75.0
        assert d["success"] is True

    def test_from_dict_round_trip(self, sample_feedback):
        """from_dict should recreate the object."""
        d = sample_feedback.to_dict()
        restored = IterationFeedback.from_dict(d)
        assert restored.session_id == sample_feedback.session_id
        assert restored.iteration == sample_feedback.iteration
        assert restored.quality_after == sample_feedback.quality_after

    def test_default_timestamp(self):
        """Timestamp should be auto-generated."""
        fb = IterationFeedback(
            session_id="s1",
            iteration=0,
            quality_before=0,
            quality_after=0,
            improvements_applied=[],
            improvements_needed=[],
            changed_files=[],
            test_results={},
            duration_seconds=0,
            success=False,
            termination_reason="",
        )
        assert fb.timestamp  # Non-empty


# --- SkillApplication Tests ---


class TestSkillApplication:
    """Tests for SkillApplication dataclass."""

    def test_to_dict(self):
        """to_dict should serialize correctly."""
        from core.skill_persistence import SkillApplication

        app = SkillApplication(
            skill_id="sk1",
            session_id="s1",
            applied_at="2025-01-01",
            was_helpful=True,
            quality_impact=10.0,
            feedback="good",
        )
        d = app.to_dict()
        assert d["skill_id"] == "sk1"
        assert d["was_helpful"] is True
        assert d["quality_impact"] == 10.0

    def test_from_dict(self):
        """from_dict should recreate the object."""
        from core.skill_persistence import SkillApplication

        data = {
            "skill_id": "sk1",
            "session_id": "s1",
            "applied_at": "2025-01-01",
            "was_helpful": None,
            "quality_impact": None,
            "feedback": "",
        }
        app = SkillApplication.from_dict(data)
        assert app.skill_id == "sk1"
        assert app.was_helpful is None


# --- SkillStore Extended Tests ---


class TestSkillStoreCache:
    """Tests for SkillStore caching behavior."""

    def test_cache_populated_on_first_load(self, temp_db, sample_skill):
        """Cache should be None initially, populated after load."""
        assert temp_db._skills_cache is None
        temp_db.save_skill(sample_skill)
        temp_db.get_skill(sample_skill.skill_id)
        assert temp_db._skills_cache is not None

    def test_invalidate_cache(self, temp_db, sample_skill):
        """_invalidate_cache should clear the cache."""
        temp_db.save_skill(sample_skill)
        temp_db.get_skill(sample_skill.skill_id)  # Populate cache
        assert temp_db._skills_cache is not None
        temp_db._invalidate_cache()
        assert temp_db._skills_cache is None

    def test_save_invalidates_cache(self, temp_db, sample_skill):
        """Saving a skill should invalidate cache."""
        temp_db.save_skill(sample_skill)
        temp_db.get_skill(sample_skill.skill_id)  # Populate
        assert temp_db._skills_cache is not None
        sample_skill.quality_score = 99.0
        temp_db.save_skill(sample_skill)
        assert temp_db._skills_cache is None  # Invalidated

    def test_json_fallback_loading(self, temp_db, sample_skill):
        """Should load from metadata.json if .yaml not found."""
        import json

        skill_dir = temp_db.skills_dir / sample_skill.skill_id
        skill_dir.mkdir(parents=True, exist_ok=True)
        json_path = skill_dir / "metadata.json"
        json_path.write_text(json.dumps(sample_skill.to_dict()))

        temp_db._invalidate_cache()
        loaded = temp_db.get_skill(sample_skill.skill_id)
        assert loaded is not None
        assert loaded.skill_id == sample_skill.skill_id


class TestSkillStoreEdgeCases:
    """Edge case tests for SkillStore."""

    def test_read_jsonl_nonexistent_file(self, temp_db):
        """Reading nonexistent JSONL should return empty list."""
        from pathlib import Path

        result = temp_db._read_jsonl(Path("/nonexistent/path.jsonl"))
        assert result == []

    def test_read_jsonl_with_corrupt_lines(self, temp_db, tmp_path):
        """Corrupt JSONL lines should be skipped."""
        jsonl_path = tmp_path / "corrupt.jsonl"
        jsonl_path.write_text('{"good": 1}\nnot json at all\n{"also_good": 2}\n')
        result = temp_db._read_jsonl(jsonl_path)
        assert len(result) == 2
        assert result[0]["good"] == 1

    def test_read_jsonl_empty_lines_skipped(self, temp_db, tmp_path):
        """Empty lines in JSONL should be skipped."""
        jsonl_path = tmp_path / "sparse.jsonl"
        jsonl_path.write_text('{"a": 1}\n\n\n{"b": 2}\n\n')
        result = temp_db._read_jsonl(jsonl_path)
        assert len(result) == 2

    def test_get_session_feedback_invalid_records(self, temp_db, tmp_path):
        """Invalid feedback records should be skipped gracefully."""
        feedback_path = temp_db.feedback_dir / "bad-session.jsonl"
        feedback_path.write_text('{"bad": "record"}\n')
        result = temp_db.get_session_feedback("bad-session")
        assert result == []

    def test_get_skill_effectiveness_no_applications(self, temp_db, sample_skill):
        """Effectiveness with no applications should have zero counts."""
        temp_db.save_skill(sample_skill)
        eff = temp_db.get_skill_effectiveness(sample_skill.skill_id)
        assert eff["applications"] == 0
        assert eff["helpful_count"] == 0
        assert eff["success_rate"] == 0.0
        assert eff["avg_quality_impact"] == 0.0

    def test_get_skill_effectiveness_mixed(self, temp_db, sample_skill):
        """Effectiveness should correctly calculate from mixed feedback."""
        temp_db.save_skill(sample_skill)
        temp_db.record_skill_application(
            sample_skill.skill_id, "s1", was_helpful=True, quality_impact=10.0
        )
        temp_db.record_skill_application(
            sample_skill.skill_id, "s2", was_helpful=True, quality_impact=20.0
        )
        temp_db.record_skill_application(
            sample_skill.skill_id, "s3", was_helpful=False, quality_impact=-5.0
        )
        temp_db.record_skill_application(
            sample_skill.skill_id, "s4", was_helpful=None
        )  # No opinion

        eff = temp_db.get_skill_effectiveness(sample_skill.skill_id)
        assert eff["applications"] == 4
        assert eff["helpful_count"] == 2
        assert eff["unhelpful_count"] == 1
        assert eff["success_rate"] == 0.5  # 2/4
        # avg_quality_impact = (10 + 20 + -5) / 3 = 8.33...
        assert abs(eff["avg_quality_impact"] - 8.333) < 0.01

    def test_get_bulk_effectiveness_empty_list(self, temp_db):
        """Bulk effectiveness with empty list should return empty dict."""
        result = temp_db.get_bulk_skill_effectiveness([])
        assert result == {}

    def test_search_min_quality_filter(self, temp_db, sample_skill):
        """Search should filter by min_quality."""
        sample_skill.quality_score = 60.0
        temp_db.save_skill(sample_skill)
        results = temp_db.search_skills("test", min_quality=70.0)
        assert len(results) == 0
        results = temp_db.search_skills("test", min_quality=50.0)
        assert len(results) == 1

    def test_search_no_trigger_match(self, temp_db, sample_skill):
        """Search with non-matching query should return empty."""
        temp_db.save_skill(sample_skill)
        results = temp_db.search_skills("completely unrelated query")
        assert len(results) == 0

    def test_get_promoted_empty(self, temp_db, sample_skill):
        """get_promoted_skills with no promoted skills returns empty."""
        temp_db.save_skill(sample_skill)
        assert temp_db.get_promoted_skills() == []

    def test_get_skills_by_domain_no_match(self, temp_db, sample_skill):
        """get_skills_by_domain with wrong domain returns empty."""
        temp_db.save_skill(sample_skill)
        assert temp_db.get_skills_by_domain("nonexistent") == []

    def test_load_skills_skips_non_directories(self, temp_db):
        """_load_skills should skip non-directory entries."""
        # Create a file (not a directory) in skills_dir
        fake_file = temp_db.skills_dir / "not-a-directory.txt"
        fake_file.write_text("just a file")
        temp_db._invalidate_cache()
        skills = temp_db._load_skills()
        assert "not-a-directory.txt" not in skills

    def test_load_skills_skips_dir_without_metadata(self, temp_db):
        """_load_skills should skip dirs without metadata files."""
        empty_dir = temp_db.skills_dir / "empty-skill"
        empty_dir.mkdir(parents=True, exist_ok=True)
        temp_db._invalidate_cache()
        skills = temp_db._load_skills()
        assert "empty-skill" not in skills


# --- SkillExtractor Extended Tests ---


class TestSkillExtractorPatterns:
    """Tests for SkillExtractor pattern extraction methods."""

    def _make_feedback(
        self,
        session_id,
        iteration,
        q_before,
        q_after,
        improvements=None,
        needed=None,
        files=None,
        tests=None,
        success=True,
        reason="",
    ):
        return IterationFeedback(
            session_id=session_id,
            iteration=iteration,
            quality_before=q_before,
            quality_after=q_after,
            improvements_applied=improvements or [],
            improvements_needed=needed or [],
            changed_files=files or [],
            test_results=tests or {},
            duration_seconds=10.0,
            success=success,
            termination_reason=reason,
        )

    def test_extract_patterns_quality_improvement(self, temp_db):
        """Patterns should be extracted from iterations where quality improved."""
        extractor = SkillExtractor(temp_db)
        feedbacks = [
            self._make_feedback("s1", 1, 50.0, 70.0, improvements=["Added tests"]),
            self._make_feedback("s1", 2, 70.0, 85.0, improvements=["Fixed linting"]),
        ]
        patterns = extractor._extract_patterns(feedbacks)
        assert len(patterns) == 2
        assert any("Added tests" in p for p in patterns)
        assert any("Fixed linting" in p for p in patterns)

    def test_extract_patterns_deduplication(self, temp_db):
        """Duplicate patterns should be deduplicated."""
        extractor = SkillExtractor(temp_db)
        feedbacks = [
            self._make_feedback("s1", 1, 50.0, 70.0, improvements=["Added tests"]),
            self._make_feedback("s1", 2, 70.0, 85.0, improvements=["Added tests"]),
        ]
        patterns = extractor._extract_patterns(feedbacks)
        # Normalized "added tests" should appear only once
        assert len(patterns) == 1

    def test_extract_patterns_limited_to_10(self, temp_db):
        """Patterns should be limited to 10."""
        extractor = SkillExtractor(temp_db)
        feedbacks = [
            self._make_feedback(
                "s1", i, float(50 + i), float(51 + i), improvements=[f"improvement_{i}"]
            )
            for i in range(15)
        ]
        patterns = extractor._extract_patterns(feedbacks)
        assert len(patterns) <= 10

    def test_extract_patterns_no_improvement_skipped(self, temp_db):
        """Iterations without quality improvement should not contribute patterns."""
        extractor = SkillExtractor(temp_db)
        feedbacks = [
            self._make_feedback("s1", 1, 70.0, 65.0, improvements=["Bad change"]),
        ]
        patterns = extractor._extract_patterns(feedbacks)
        assert len(patterns) == 0

    def test_extract_anti_patterns(self, temp_db):
        """Anti-patterns should come from failed/stalled iterations."""
        extractor = SkillExtractor(temp_db)
        feedbacks = [
            self._make_feedback("s1", 1, 70.0, 65.0, improvements=["Bad change"]),
            self._make_feedback("s1", 2, 65.0, 60.0, needed=["Fix imports"], success=False),
        ]
        anti = extractor._extract_anti_patterns(feedbacks)
        assert any("Bad change" in a for a in anti)
        assert any("Fix imports" in a for a in anti)

    def test_extract_anti_patterns_limited_to_5(self, temp_db):
        """Anti-patterns should be limited to 5."""
        extractor = SkillExtractor(temp_db)
        feedbacks = [
            self._make_feedback(
                "s1", i, 70.0, 60.0, improvements=[f"bad_{i}"], needed=[f"need_{i}"], success=False
            )
            for i in range(10)
        ]
        anti = extractor._extract_anti_patterns(feedbacks)
        assert len(anti) <= 5

    def test_extract_triggers_from_files(self, temp_db):
        """Triggers should be extracted from file paths."""
        extractor = SkillExtractor(temp_db)
        feedbacks = [
            self._make_feedback("s1", 1, 50.0, 70.0, files=["auth/login.py", "auth/utils.py"]),
        ]
        triggers = extractor._extract_triggers(feedbacks)
        assert "auth" in triggers
        assert "py" in triggers

    def test_extract_triggers_filters_stopwords(self, temp_db):
        """Stopwords should be filtered from triggers."""
        extractor = SkillExtractor(temp_db)
        feedbacks = [
            self._make_feedback(
                "s1", 1, 50.0, 70.0, improvements=["Fixed the implementation with better handling"]
            ),
        ]
        triggers = extractor._extract_triggers(feedbacks)
        assert "the" not in triggers
        assert "with" not in triggers

    def test_extract_triggers_filters_common_dirs(self, temp_db):
        """Common directory names like 'src' should be filtered."""
        extractor = SkillExtractor(temp_db)
        feedbacks = [
            self._make_feedback("s1", 1, 50.0, 70.0, files=["src/auth/login.py"]),
        ]
        triggers = extractor._extract_triggers(feedbacks)
        assert "src" not in triggers
        assert "auth" in triggers

    def test_extract_triggers_limited_to_15(self, temp_db):
        """Triggers should be limited to 15."""
        extractor = SkillExtractor(temp_db)
        # Lots of unique file paths
        files = [f"module_{i}/handler_{i}.py" for i in range(20)]
        feedbacks = [self._make_feedback("s1", 1, 50.0, 70.0, files=files)]
        triggers = extractor._extract_triggers(feedbacks)
        assert len(triggers) <= 15

    def test_extract_conditions_file_types(self, temp_db):
        """Conditions should include file type info."""
        extractor = SkillExtractor(temp_db)
        feedbacks = [
            self._make_feedback("s1", 1, 50.0, 70.0, files=["main.py", "style.css"]),
        ]
        conditions = extractor._extract_conditions(feedbacks)
        assert any(".py" in c and ".css" in c for c in conditions)

    def test_extract_conditions_test_presence(self, temp_db):
        """Conditions should note test suite presence."""
        extractor = SkillExtractor(temp_db)
        feedbacks = [
            self._make_feedback("s1", 1, 50.0, 70.0, tests={"ran": True}),
        ]
        conditions = extractor._extract_conditions(feedbacks)
        assert any("test suite" in c.lower() for c in conditions)

    def test_extract_conditions_multiple_iterations(self, temp_db):
        """3+ iterations should note complex task."""
        extractor = SkillExtractor(temp_db)
        feedbacks = [self._make_feedback("s1", i, 50.0 + i * 10, 60.0 + i * 10) for i in range(3)]
        conditions = extractor._extract_conditions(feedbacks)
        assert any("multiple iterations" in c.lower() for c in conditions)

    def test_generate_skill_id_deterministic(self, temp_db):
        """Same inputs should generate same skill ID."""
        extractor = SkillExtractor(temp_db)
        id1 = extractor._generate_skill_id("session1", ["pattern1"])
        id2 = extractor._generate_skill_id("session1", ["pattern1"])
        assert id1 == id2
        assert id1.startswith("learned-")

    def test_generate_skill_id_different_inputs(self, temp_db):
        """Different inputs should generate different IDs."""
        extractor = SkillExtractor(temp_db)
        id1 = extractor._generate_skill_id("session1", ["pattern1"])
        id2 = extractor._generate_skill_id("session2", ["pattern2"])
        assert id1 != id2

    def test_generate_skill_name_from_patterns(self, temp_db):
        """Name should derive from first pattern."""
        extractor = SkillExtractor(temp_db)
        name = extractor._generate_skill_name(["[Iter 1] Added test coverage"], "backend")
        assert "backend" in name
        assert "learned" in name

    def test_generate_skill_name_no_patterns(self, temp_db):
        """No patterns should use domain fallback."""
        extractor = SkillExtractor(temp_db)
        name = extractor._generate_skill_name([], "frontend")
        assert name == "learned-frontend-skill"

    def test_extract_single_iteration_returns_none(self, temp_db):
        """Sessions with < 2 iterations should return None."""
        extractor = SkillExtractor(temp_db)
        fb = self._make_feedback("s1", 1, 50.0, 85.0, success=True, reason="quality_met")
        temp_db.save_feedback(fb)
        result = extractor.extract_from_session("s1")
        assert result is None

    def test_extract_failed_session_returns_none(self, temp_db):
        """Failed sessions should return None."""
        extractor = SkillExtractor(temp_db)
        fb1 = self._make_feedback("fail-s", 1, 50.0, 55.0, success=True)
        fb2 = self._make_feedback("fail-s", 2, 55.0, 60.0, success=False)
        temp_db.save_feedback(fb1)
        temp_db.save_feedback(fb2)
        result = extractor.extract_from_session("fail-s")
        assert result is None

    def test_extract_low_quality_returns_none(self, temp_db):
        """Sessions ending below 70 quality should return None."""
        extractor = SkillExtractor(temp_db)
        fb1 = self._make_feedback("low-s", 1, 30.0, 40.0, success=True)
        fb2 = self._make_feedback("low-s", 2, 40.0, 60.0, success=True)
        temp_db.save_feedback(fb1)
        temp_db.save_feedback(fb2)
        result = extractor.extract_from_session("low-s")
        assert result is None

    def test_extract_successful_has_provenance(self, temp_db):
        """Extracted skill should have full provenance."""
        extractor = SkillExtractor(temp_db)
        fb1 = self._make_feedback(
            "prov-s", 1, 50.0, 70.0, improvements=["Fix A"], files=["a.py"], success=True
        )
        fb2 = self._make_feedback(
            "prov-s",
            2,
            70.0,
            85.0,
            improvements=["Fix B"],
            files=["b.py"],
            success=True,
            reason="quality_met",
        )
        temp_db.save_feedback(fb1)
        temp_db.save_feedback(fb2)
        skill = extractor.extract_from_session("prov-s", repo_path="/repo", domain="backend")
        assert skill is not None
        assert skill.provenance["session_id"] == "prov-s"
        assert skill.provenance["repo_path"] == "/repo"
        assert skill.provenance["iterations"] == 2
        assert len(skill.provenance["quality_progression"]) == 2
        assert skill.provenance["total_duration"] == 20.0


# --- SkillRetriever Extended Tests ---


class TestSkillRetrieverScoring:
    """Tests for SkillRetriever scoring and search term extraction."""

    def test_extract_search_terms_from_description(self, temp_db):
        """Should extract words > 3 chars from description."""
        retriever = SkillRetriever(temp_db)
        terms = retriever._extract_search_terms("implement authentication flow", None)
        assert "implement" in terms
        assert "authentication" in terms
        assert "flow" in terms

    def test_extract_search_terms_from_file_paths(self, temp_db):
        """Should extract from file paths."""
        retriever = SkillRetriever(temp_db)
        terms = retriever._extract_search_terms("task", ["auth/login.py"])
        assert "auth" in terms
        assert "py" in terms

    def test_extract_search_terms_short_words_filtered(self, temp_db):
        """Words <= 3 chars should be filtered."""
        retriever = SkillRetriever(temp_db)
        terms = retriever._extract_search_terms("fix the bug in api", None)
        assert "the" not in terms
        assert "bug" not in terms
        assert "api" not in terms

    def test_score_relevance_promoted_bonus(self, temp_db, sample_skill):
        """Promoted skills should get bonus score."""
        retriever = SkillRetriever(temp_db)
        sample_skill.promoted = False
        score_unpromoted = retriever._score_relevance(sample_skill, {"test"}, None)
        sample_skill.promoted = True
        score_promoted = retriever._score_relevance(sample_skill, {"test"}, None)
        assert score_promoted > score_unpromoted

    def test_score_relevance_quality_component(self, temp_db, sample_skill, high_quality_skill):
        """Higher quality should contribute to higher score."""
        retriever = SkillRetriever(temp_db)
        score_85 = retriever._score_relevance(sample_skill, set(), None)
        score_90 = retriever._score_relevance(high_quality_skill, set(), None)
        # quality_score difference: 90 vs 85 -> 0.3*(90/100) vs 0.3*(85/100)
        assert score_90 > score_85

    def test_score_relevance_effectiveness_history(self, temp_db, sample_skill):
        """Effectiveness history should boost score."""
        retriever = SkillRetriever(temp_db)
        no_eff = retriever._score_relevance(sample_skill, set(), None, effectiveness={})
        with_eff = retriever._score_relevance(
            sample_skill,
            set(),
            None,
            effectiveness={"applications": 5, "success_rate": 0.8},
        )
        assert with_eff > no_eff

    def test_retrieve_max_skills_limit(self, temp_db):
        """Should respect max_skills limit."""
        for i in range(5):
            skill = LearnedSkill(
                skill_id=f"skill-{i}",
                name=f"Skill {i}",
                description="test",
                triggers=["common"],
                domain="testing",
                source_session=f"s{i}",
                source_repo="",
                learned_at="2025-01-01",
                patterns=[],
                anti_patterns=[],
                quality_score=80.0,
                iteration_count=2,
                provenance={},
                applicability_conditions=[],
            )
            temp_db.save_skill(skill)

        retriever = SkillRetriever(temp_db)
        results = retriever.retrieve("common trigger", max_skills=2, promoted_only=False)
        assert len(results) <= 2


# --- PromotionGate Extended Tests ---


class TestPromotionGateEdgeCases:
    """Edge case tests for PromotionGate."""

    def test_evaluate_low_success_rate(self, temp_db, high_quality_skill):
        """Should reject skills with low success rate despite enough applications."""
        temp_db.save_skill(high_quality_skill)
        # Add applications with low success
        for i in range(5):
            temp_db.record_skill_application(
                high_quality_skill.skill_id,
                f"s{i}",
                was_helpful=(i < 1),  # Only 1/5 helpful = 20%
            )
        gate = PromotionGate(temp_db)
        can_promote, reason = gate.evaluate(high_quality_skill)
        assert can_promote is False
        assert "success rate" in reason.lower()

    def test_promote_does_not_promote_failing_evaluation(self, temp_db, sample_skill):
        """promote() should return None if evaluation fails."""
        sample_skill.quality_score = 50.0  # Too low
        temp_db.save_skill(sample_skill)
        gate = PromotionGate(temp_db)
        result = gate.promote(sample_skill)
        assert result is None
        assert sample_skill.promoted is False  # Should not modify

    def test_list_pending_filters_by_quality(self, temp_db):
        """list_pending should only include skills near threshold."""
        low_skill = LearnedSkill(
            skill_id="low-sk",
            name="Low",
            description="low",
            triggers=["x"],
            domain="testing",
            source_session="s1",
            source_repo="",
            learned_at="2025-01-01",
            patterns=[],
            anti_patterns=[],
            quality_score=50.0,
            iteration_count=2,
            provenance={},
            applicability_conditions=[],
        )
        near_skill = LearnedSkill(
            skill_id="near-sk",
            name="Near",
            description="near",
            triggers=["x"],
            domain="testing",
            source_session="s2",
            source_repo="",
            learned_at="2025-01-01",
            patterns=[],
            anti_patterns=[],
            quality_score=78.0,
            iteration_count=2,
            provenance={},
            applicability_conditions=[],
        )
        temp_db.save_skill(low_skill)
        temp_db.save_skill(near_skill)
        gate = PromotionGate(temp_db)
        pending = gate.list_pending()
        ids = [s.skill_id for s in pending]
        assert "near-sk" in ids
        assert "low-sk" not in ids  # 50 < MIN_QUALITY_SCORE - 10 (75)

    def test_list_pending_excludes_promoted(self, temp_db, high_quality_skill):
        """list_pending should exclude already promoted skills."""
        high_quality_skill.promoted = True
        temp_db.save_skill(high_quality_skill)
        gate = PromotionGate(temp_db)
        pending = gate.list_pending()
        ids = [s.skill_id for s in pending]
        assert high_quality_skill.skill_id not in ids

    def test_promote_creates_skill_md(self, temp_db, high_quality_skill, tmp_path):
        """Promotion should create SKILL.md with correct content."""
        temp_db.save_skill(high_quality_skill)
        for i in range(3):
            temp_db.record_skill_application(
                high_quality_skill.skill_id,
                f"s{i}",
                was_helpful=True,
            )
        gate = PromotionGate(temp_db, skills_dir=tmp_path)
        path = gate.promote(high_quality_skill, "Test reason")
        assert path is not None
        content = path.read_text()
        assert "High Quality Skill" in content
        assert high_quality_skill.promoted is True
        assert high_quality_skill.promotion_reason == "Test reason"

    def test_promote_sorted_by_quality(self, temp_db):
        """list_pending should be sorted by quality score descending."""
        for i, q in enumerate([78.0, 82.0, 76.0, 80.0]):
            skill = LearnedSkill(
                skill_id=f"sort-{i}",
                name=f"S{i}",
                description="",
                triggers=["x"],
                domain="d",
                source_session=f"s{i}",
                source_repo="",
                learned_at="2025-01-01",
                patterns=[],
                anti_patterns=[],
                quality_score=q,
                iteration_count=2,
                provenance={},
                applicability_conditions=[],
            )
            temp_db.save_skill(skill)
        gate = PromotionGate(temp_db)
        pending = gate.list_pending()
        scores = [s.quality_score for s in pending]
        assert scores == sorted(scores, reverse=True)
