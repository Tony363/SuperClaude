"""Tests for SDK hooks."""

from SuperClaude.SDK.hooks import (
    BaseHook,
    CompositeHooks,
    EvidenceHooks,
    ExecutionEvidence,
    FileChangeHooks,
    QualityHooks,
    create_quality_hooks,
)


class TestExecutionEvidence:
    """Tests for ExecutionEvidence dataclass."""

    def test_empty_evidence(self):
        """Test empty evidence state."""
        evidence = ExecutionEvidence()

        assert evidence.has_file_modifications() is False
        assert evidence.has_execution_evidence() is False
        assert evidence.tool_invocations == []

    def test_has_file_modifications_written(self):
        """Test file modifications detection for written files."""
        evidence = ExecutionEvidence(files_written=["test.py"])

        assert evidence.has_file_modifications() is True

    def test_has_file_modifications_edited(self):
        """Test file modifications detection for edited files."""
        evidence = ExecutionEvidence(files_edited=["test.py"])

        assert evidence.has_file_modifications() is True

    def test_has_execution_evidence_commands(self):
        """Test execution evidence from commands."""
        evidence = ExecutionEvidence(commands_run=["pytest"])

        assert evidence.has_execution_evidence() is True

    def test_has_execution_evidence_tests(self):
        """Test execution evidence from tests."""
        evidence = ExecutionEvidence(tests_run=True)

        assert evidence.has_execution_evidence() is True

    def test_to_dict(self):
        """Test conversion to dictionary."""
        evidence = ExecutionEvidence(
            files_read=["a.py", "b.py"],
            files_written=["c.py"],
            tests_run=True,
            test_passed=5,
            session_id="test-session",
        )

        result = evidence.to_dict()

        assert result["files_read"] == 2
        assert result["files_written"] == 1
        assert result["tests_run"] is True
        assert result["test_passed"] == 5
        assert result["session_id"] == "test-session"
        assert result["has_file_modifications"] is True


class TestQualityHooks:
    """Tests for QualityHooks."""

    def test_initialization(self):
        """Test hook initialization."""
        hooks = QualityHooks()

        assert hooks.scorer is None
        assert isinstance(hooks.evidence, ExecutionEvidence)

    def test_reset(self):
        """Test resetting evidence."""
        hooks = QualityHooks()
        hooks.evidence.files_written.append("test.py")

        hooks.reset()

        assert hooks.evidence.files_written == []

    def test_pre_tool_use_allows_all(self):
        """Test pre_tool_use allows all tools."""
        hooks = QualityHooks()

        result = hooks.pre_tool_use("Read", {"file_path": "test.py"})

        assert result is None  # None means proceed

    def test_post_tool_use_tracks_read(self):
        """Test tracking file reads."""
        hooks = QualityHooks()

        hooks.post_tool_use("Read", {"file_path": "test.py"}, "file contents")

        assert "test.py" in hooks.evidence.files_read
        assert len(hooks.evidence.file_changes) == 1
        assert hooks.evidence.file_changes[0].action == "read"

    def test_post_tool_use_tracks_write(self):
        """Test tracking file writes."""
        hooks = QualityHooks()

        hooks.post_tool_use("Write", {"file_path": "new.py", "content": "code"}, None)

        assert "new.py" in hooks.evidence.files_written
        assert len(hooks.evidence.file_changes) == 1
        assert hooks.evidence.file_changes[0].action == "write"

    def test_post_tool_use_tracks_edit(self):
        """Test tracking file edits."""
        hooks = QualityHooks()

        hooks.post_tool_use(
            "Edit",
            {"file_path": "test.py", "old_string": "old", "new_string": "new"},
            None,
        )

        assert "test.py" in hooks.evidence.files_edited
        assert len(hooks.evidence.file_changes) == 1
        assert hooks.evidence.file_changes[0].action == "edit"

    def test_post_tool_use_tracks_bash(self):
        """Test tracking bash commands."""
        hooks = QualityHooks()

        hooks.post_tool_use(
            "Bash",
            {"command": "ls -la"},
            {"stdout": "output", "exit_code": 0},
        )

        assert "ls -la" in hooks.evidence.commands_run
        assert len(hooks.evidence.command_results) == 1

    def test_post_tool_use_tracks_test_execution(self):
        """Test tracking test execution."""
        hooks = QualityHooks()

        hooks.post_tool_use(
            "Bash",
            {"command": "pytest tests/"},
            {"stdout": "5 passed, 1 failed", "exit_code": 1},
        )

        assert hooks.evidence.tests_run is True
        assert hooks.evidence.test_passed == 5
        assert hooks.evidence.test_failed == 1

    def test_post_tool_use_tracks_subagents(self):
        """Test tracking subagent spawns."""
        hooks = QualityHooks()

        hooks.post_tool_use(
            "Task",
            {"description": "review code"},
            None,
        )

        assert hooks.evidence.subagents_spawned == 1
        assert "review code" in hooks.evidence.subagent_names

    def test_session_lifecycle(self):
        """Test session start and end."""
        hooks = QualityHooks()

        hooks.session_start("test-session-123")
        assert hooks.evidence.session_id == "test-session-123"
        assert hooks.evidence.start_time is not None

        hooks.session_end("test-session-123")
        assert hooks.evidence.end_time is not None


class TestEvidenceHooks:
    """Tests for EvidenceHooks."""

    def test_requires_evidence_flag(self):
        """Test requires_evidence flag."""
        hooks = EvidenceHooks(requires_evidence=True)

        assert hooks.requires_evidence is True

    def test_validate_without_quality_hooks(self):
        """Test validation fails without attached quality hooks."""
        hooks = EvidenceHooks(requires_evidence=True)

        is_valid, issues = hooks.validate_evidence()

        assert is_valid is False
        assert "No evidence collector attached" in issues

    def test_validate_with_empty_evidence(self):
        """Test validation fails with no execution evidence."""
        quality_hooks = QualityHooks()
        evidence_hooks = EvidenceHooks(requires_evidence=True)
        evidence_hooks.attach_quality_hooks(quality_hooks)

        is_valid, issues = evidence_hooks.validate_evidence()

        assert is_valid is False
        assert any("No execution evidence" in issue for issue in issues)

    def test_validate_with_file_changes(self):
        """Test validation passes with file changes."""
        quality_hooks = QualityHooks()
        quality_hooks.evidence.files_written.append("test.py")
        evidence_hooks = EvidenceHooks(requires_evidence=True)
        evidence_hooks.attach_quality_hooks(quality_hooks)

        is_valid, issues = evidence_hooks.validate_evidence()

        assert is_valid is True
        assert len(issues) == 0

    def test_validate_min_file_changes(self):
        """Test minimum file changes requirement."""
        quality_hooks = QualityHooks()
        quality_hooks.evidence.files_written.append("test.py")
        evidence_hooks = EvidenceHooks(requires_evidence=True, min_file_changes=3)
        evidence_hooks.attach_quality_hooks(quality_hooks)

        is_valid, issues = evidence_hooks.validate_evidence()

        assert is_valid is False
        assert any("Insufficient file changes" in issue for issue in issues)

    def test_validate_require_tests(self):
        """Test test execution requirement."""
        quality_hooks = QualityHooks()
        quality_hooks.evidence.files_written.append("test.py")
        evidence_hooks = EvidenceHooks(requires_evidence=True, require_tests=True)
        evidence_hooks.attach_quality_hooks(quality_hooks)

        is_valid, issues = evidence_hooks.validate_evidence()

        assert is_valid is False
        assert any("Tests were not executed" in issue for issue in issues)

    def test_validate_passes_all_requirements(self):
        """Test validation passes when all requirements met."""
        quality_hooks = QualityHooks()
        quality_hooks.evidence.files_written.extend(["a.py", "b.py", "c.py"])
        quality_hooks.evidence.tests_run = True
        evidence_hooks = EvidenceHooks(
            requires_evidence=True,
            min_file_changes=2,
            require_tests=True,
        )
        evidence_hooks.attach_quality_hooks(quality_hooks)

        is_valid, issues = evidence_hooks.validate_evidence()

        assert is_valid is True
        assert len(issues) == 0


class TestFileChangeHooks:
    """Tests for FileChangeHooks."""

    def test_track_read(self):
        """Test tracking file reads."""
        hooks = FileChangeHooks()

        hooks.post_tool_use("Read", {"file_path": "test.py"}, "content")

        assert len(hooks.changes) == 1
        assert hooks.changes[0].action == "read"
        assert hooks.changes[0].path == "test.py"

    def test_track_write_new_file(self):
        """Test tracking new file creation."""
        hooks = FileChangeHooks()

        hooks.post_tool_use(
            "Write",
            {"file_path": "new.py", "content": "line1\nline2\nline3"},
            None,
        )

        assert len(hooks.changes) == 1
        assert hooks.changes[0].action == "create"  # New file
        assert hooks.changes[0].lines_changed == 3

    def test_track_edit(self):
        """Test tracking file edits."""
        hooks = FileChangeHooks()

        hooks.post_tool_use(
            "Edit",
            {
                "file_path": "test.py",
                "old_string": "old",
                "new_string": "new\nlines",
            },
            None,
        )

        assert len(hooks.changes) == 1
        assert hooks.changes[0].action == "edit"

    def test_get_modified_files(self):
        """Test getting list of modified files."""
        hooks = FileChangeHooks()

        # Simulate various operations
        hooks.post_tool_use("Read", {"file_path": "a.py"}, "content")
        hooks.post_tool_use("Write", {"file_path": "b.py", "content": "new"}, None)
        hooks.post_tool_use(
            "Edit",
            {"file_path": "c.py", "old_string": "x", "new_string": "y"},
            None,
        )

        modified = hooks.get_modified_files()

        assert "a.py" not in modified  # Read is not a modification
        assert "b.py" in modified
        assert "c.py" in modified

    def test_reset(self):
        """Test resetting tracked changes."""
        hooks = FileChangeHooks()
        hooks.post_tool_use("Write", {"file_path": "test.py", "content": "x"}, None)

        hooks.reset()

        assert hooks.changes == []


class TestCompositeHooks:
    """Tests for CompositeHooks."""

    def test_add_hooks(self):
        """Test adding hooks."""
        composite = CompositeHooks()
        hook1 = BaseHook()
        hook2 = BaseHook()

        composite.add(hook1).add(hook2)

        assert len(composite.hooks) == 2

    def test_extend_hooks(self):
        """Test extending with multiple hooks."""
        composite = CompositeHooks()
        hooks = [BaseHook(), BaseHook()]

        composite.extend(hooks)

        assert len(composite.hooks) == 2

    def test_pre_tool_use_delegates(self):
        """Test pre_tool_use delegates to all hooks."""

        class TrackingHook(BaseHook):
            def __init__(self):
                self.called = False

            def pre_tool_use(self, tool_name, tool_input):
                self.called = True
                return None

        hook1 = TrackingHook()
        hook2 = TrackingHook()
        composite = CompositeHooks([hook1, hook2])

        composite.pre_tool_use("Read", {"file_path": "test.py"})

        assert hook1.called
        assert hook2.called

    def test_pre_tool_use_first_block_wins(self):
        """Test first blocking hook wins."""

        class BlockingHook(BaseHook):
            def pre_tool_use(self, tool_name, tool_input):
                return {"block": True, "reason": "blocked"}

        class PassingHook(BaseHook):
            def pre_tool_use(self, tool_name, tool_input):
                return None

        composite = CompositeHooks([BlockingHook(), PassingHook()])

        result = composite.pre_tool_use("Write", {"file_path": "test.py"})

        assert result is not None
        assert result.get("block") is True

    def test_post_tool_use_delegates_to_all(self):
        """Test post_tool_use delegates to all hooks."""

        class TrackingHook(BaseHook):
            def __init__(self):
                self.post_called = False

            def post_tool_use(self, tool_name, tool_input, tool_output):
                self.post_called = True

        hook1 = TrackingHook()
        hook2 = TrackingHook()
        composite = CompositeHooks([hook1, hook2])

        composite.post_tool_use("Read", {}, "output")

        assert hook1.post_called
        assert hook2.post_called


class TestCreateQualityHooks:
    """Tests for create_quality_hooks factory."""

    def test_creates_composite(self):
        """Test factory creates composite hooks."""
        hooks = create_quality_hooks()

        assert isinstance(hooks, CompositeHooks)

    def test_includes_quality_hooks(self):
        """Test factory includes quality hooks."""
        hooks = create_quality_hooks()

        has_quality = any(isinstance(h, QualityHooks) for h in hooks.hooks)
        assert has_quality

    def test_includes_evidence_hooks(self):
        """Test factory includes evidence hooks."""
        hooks = create_quality_hooks(requires_evidence=True)

        has_evidence = any(isinstance(h, EvidenceHooks) for h in hooks.hooks)
        assert has_evidence

    def test_includes_file_change_hooks(self):
        """Test factory includes file change hooks when requested."""
        hooks = create_quality_hooks(track_file_changes=True)

        has_file_hooks = any(isinstance(h, FileChangeHooks) for h in hooks.hooks)
        assert has_file_hooks

    def test_excludes_file_change_hooks(self):
        """Test factory excludes file change hooks when not requested."""
        hooks = create_quality_hooks(track_file_changes=False)

        has_file_hooks = any(isinstance(h, FileChangeHooks) for h in hooks.hooks)
        assert not has_file_hooks

    def test_evidence_hooks_attached_to_quality(self):
        """Test evidence hooks are attached to quality hooks."""
        composite = create_quality_hooks(requires_evidence=True)

        evidence_hook = next(
            (h for h in composite.hooks if isinstance(h, EvidenceHooks)), None
        )
        assert evidence_hook is not None
        assert evidence_hook._quality_hooks is not None
