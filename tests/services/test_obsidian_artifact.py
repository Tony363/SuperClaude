"""Tests for Obsidian artifact writer."""

from datetime import datetime

import pytest

from setup.services.obsidian_artifact import (
    DecisionRecord,
    ObsidianArtifactWriter,
    extract_decisions_from_evidence,
)
from setup.services.obsidian_config import ArtifactConfig, ObsidianConfig, VaultConfig


class TestDecisionRecord:
    """Tests for DecisionRecord dataclass."""

    def test_to_slug_simple(self):
        """Test slug generation from simple title."""
        record = DecisionRecord(
            title="API Design Decision",
            summary="Summary",
            decision_type="architecture",
            context="",
            rationale="",
        )
        slug = record.to_slug()
        assert slug == "api-design-decision"

    def test_to_slug_special_chars(self):
        """Test slug removes special characters."""
        record = DecisionRecord(
            title="Use @PAL for Consensus!?",
            summary="Summary",
            decision_type="consensus",
            context="",
            rationale="",
        )
        slug = record.to_slug()
        assert slug == "use-pal-for-consensus"

    def test_to_slug_truncation(self):
        """Test slug truncation for long titles."""
        record = DecisionRecord(
            title="A" * 100,
            summary="Summary",
            decision_type="technical",
            context="",
            rationale="",
        )
        slug = record.to_slug()
        assert len(slug) <= 50

    def test_to_filename_format(self):
        """Test filename generation format."""
        record = DecisionRecord(
            title="Test Decision",
            summary="Summary",
            decision_type="architecture",
            context="",
            rationale="",
            created=datetime(2025, 2, 4, 12, 30, 0),
        )
        filename = record.to_filename()

        assert filename.startswith("2025-02-04-")
        assert "test-decision" in filename
        assert filename.endswith(".md")
        # Should have 6-char hash suffix
        parts = filename.replace(".md", "").split("-")
        assert len(parts[-1]) == 6

    def test_to_filename_unique(self):
        """Test that same title at different times gives unique filenames."""
        record1 = DecisionRecord(
            title="Test Decision",
            summary="Summary",
            decision_type="architecture",
            context="",
            rationale="",
            created=datetime(2025, 2, 4, 12, 0, 0),
        )
        record2 = DecisionRecord(
            title="Test Decision",
            summary="Summary",
            decision_type="architecture",
            context="",
            rationale="",
            created=datetime(2025, 2, 4, 12, 0, 1),
        )

        assert record1.to_filename() != record2.to_filename()


class TestObsidianArtifactWriter:
    """Tests for ObsidianArtifactWriter."""

    @pytest.fixture
    def vault_dir(self, tmp_path):
        """Create test vault directory."""
        vault = tmp_path / "vault"
        vault.mkdir()
        return vault

    @pytest.fixture
    def config(self, vault_dir):
        """Create test config."""
        return ObsidianConfig(
            vault=VaultConfig(path=vault_dir),
            artifacts=ArtifactConfig(
                types=["decisions"],
                output_paths={"decisions": "Claude/Decisions/"},
            ),
        )

    @pytest.fixture
    def decision(self):
        """Create test decision record."""
        return DecisionRecord(
            title="Use Microservices Architecture",
            summary="Decided to use microservices for scalability.",
            decision_type="architecture",
            context="Team needed to scale the application.",
            rationale="Microservices allow independent scaling.",
            source_notes=["Knowledge/architecture.md"],
            session_id="test-session-123",
            project="TestProject",
            created=datetime(2025, 2, 4, 12, 0, 0),
        )

    def test_write_decision_creates_file(self, vault_dir, config, decision):
        """Test that write_decision creates a file."""
        writer = ObsidianArtifactWriter(config=config)
        path = writer.write_decision(decision)

        assert path is not None
        assert path.exists()
        assert path.parent == vault_dir / "Claude" / "Decisions"

    def test_write_decision_content_format(self, vault_dir, config, decision):
        """Test decision file content format."""
        writer = ObsidianArtifactWriter(config=config)
        path = writer.write_decision(decision)

        content = path.read_text()

        # Check frontmatter
        assert "---" in content
        assert "title: Use Microservices Architecture" in content
        assert "type: decision" in content
        assert "decision_type: architecture" in content
        assert "project: TestProject" in content
        assert "session_id: test-session-123" in content

        # Check body sections
        assert "# Use Microservices Architecture" in content
        assert "## Summary" in content
        assert "Decided to use microservices" in content
        assert "## Context" in content
        assert "Team needed to scale" in content
        assert "## Rationale" in content
        assert "Microservices allow independent" in content

        # Check related notes
        assert "## Related Notes" in content
        assert "[[Knowledge/architecture.md]]" in content

    def test_write_decision_disabled_type(self, vault_dir):
        """Test that disabled artifact types are not written."""
        config = ObsidianConfig(
            vault=VaultConfig(path=vault_dir),
            artifacts=ArtifactConfig(
                types=[],  # No types enabled
                output_paths={"decisions": "Claude/Decisions/"},
            ),
        )

        writer = ObsidianArtifactWriter(config=config)
        decision = DecisionRecord(
            title="Test",
            summary="Summary",
            decision_type="architecture",
            context="",
            rationale="",
        )

        path = writer.write_decision(decision)
        assert path is None

    def test_write_decision_no_config(self):
        """Test write_decision with no config."""
        writer = ObsidianArtifactWriter(config=None)
        decision = DecisionRecord(
            title="Test",
            summary="Summary",
            decision_type="architecture",
            context="",
            rationale="",
        )

        path = writer.write_decision(decision)
        assert path is None

    def test_write_decision_creates_output_dir(self, vault_dir, config, decision):
        """Test that output directory is created if needed."""
        # Ensure dir doesn't exist
        output_dir = vault_dir / "Claude" / "Decisions"
        assert not output_dir.exists()

        writer = ObsidianArtifactWriter(config=config)
        path = writer.write_decision(decision)

        assert output_dir.exists()
        assert path.parent == output_dir

    def test_backlinks_injection(self, vault_dir, config, decision):
        """Test backlink injection into source notes."""
        # Create source note
        knowledge_dir = vault_dir / "Knowledge"
        knowledge_dir.mkdir()
        source_note = knowledge_dir / "architecture.md"
        source_note.write_text("# Architecture\n\nOriginal content.")

        writer = ObsidianArtifactWriter(config=config)
        writer.write_decision(decision)

        # Check backlink was added
        content = source_note.read_text()
        assert "## Claude References" in content
        assert "Use Microservices Architecture" in content
        assert "2025-02-04" in content

    def test_backlinks_appends_to_existing_section(self, vault_dir, config, decision):
        """Test backlinks append to existing section."""
        # Create source note with existing backlinks section
        knowledge_dir = vault_dir / "Knowledge"
        knowledge_dir.mkdir()
        source_note = knowledge_dir / "architecture.md"
        source_note.write_text("""\
# Architecture

Content.

## Claude References

- [[existing-decision.md]] - 2025-01-01
""")

        writer = ObsidianArtifactWriter(config=config)
        writer.write_decision(decision)

        content = source_note.read_text()
        # Should have both links
        assert "existing-decision.md" in content
        assert "Use Microservices Architecture" in content

    def test_backlinks_disabled(self, vault_dir):
        """Test backlinks not injected when disabled."""
        config = ObsidianConfig(
            vault=VaultConfig(path=vault_dir),
            artifacts=ArtifactConfig(
                types=["decisions"],
                output_paths={"decisions": "Claude/Decisions/"},
                backlinks={"enabled": False, "section": "## Claude References"},
            ),
        )

        # Create source note
        knowledge_dir = vault_dir / "Knowledge"
        knowledge_dir.mkdir()
        source_note = knowledge_dir / "architecture.md"
        source_note.write_text("# Architecture\n\nContent.")

        decision = DecisionRecord(
            title="Test Decision",
            summary="Summary",
            decision_type="architecture",
            context="",
            rationale="",
            source_notes=["Knowledge/architecture.md"],
        )

        writer = ObsidianArtifactWriter(config=config)
        writer.write_decision(decision)

        # Source note should be unchanged
        content = source_note.read_text()
        assert "## Claude References" not in content

    def test_should_sync(self, config):
        """Test should_sync returns config setting."""
        writer = ObsidianArtifactWriter(config=config)
        assert writer.should_sync() is True

    def test_should_sync_disabled(self, vault_dir):
        """Test should_sync when disabled."""
        config = ObsidianConfig(
            vault=VaultConfig(path=vault_dir),
            artifacts=ArtifactConfig(sync_on="never"),
        )
        writer = ObsidianArtifactWriter(config=config)
        assert writer.should_sync() is False

    def test_get_output_dir(self, vault_dir, config):
        """Test getting output directory."""
        writer = ObsidianArtifactWriter(config=config)
        output_dir = writer.get_output_dir("decisions")
        assert output_dir == vault_dir / "Claude/Decisions/"


class TestExtractDecisionsFromEvidence:
    """Tests for extract_decisions_from_evidence function."""

    def test_extract_consensus_decision(self):
        """Test extracting decision from consensus tool."""
        tool_invocations = [
            {
                "tool_name": "mcp__pal__consensus",
                "tool_input": {"question": "Should we use microservices or monolith?"},
                "tool_output": "Consensus: Use microservices for scalability...",
            }
        ]

        decisions = extract_decisions_from_evidence(
            tool_invocations=tool_invocations,
            project_name="TestProject",
            session_id="session-123",
        )

        assert len(decisions) == 1
        assert "Consensus:" in decisions[0].title
        assert decisions[0].decision_type == "consensus"
        assert decisions[0].project == "TestProject"
        assert decisions[0].session_id == "session-123"

    def test_extract_thinkdeep_decision(self):
        """Test extracting decision from thinkdeep tool."""
        tool_invocations = [
            {
                "tool_name": "mcp__pal__thinkdeep",
                "tool_input": {"topic": "Database scaling strategies"},
                "tool_output": "Analysis: Consider horizontal scaling...",
            }
        ]

        decisions = extract_decisions_from_evidence(
            tool_invocations=tool_invocations,
            project_name="TestProject",
            session_id="",
        )

        assert len(decisions) == 1
        assert "Analysis:" in decisions[0].title
        assert decisions[0].decision_type == "technical"

    def test_extract_architecture_decision(self):
        """Test extracting architecture decisions from tool output."""
        tool_invocations = [
            {
                "tool_name": "Bash",
                "tool_input": {"command": "echo 'architecture review'"},
                "tool_output": "architecture decisions...",
            }
        ]

        decisions = extract_decisions_from_evidence(
            tool_invocations=tool_invocations,
            project_name="TestProject",
            session_id="",
        )

        assert len(decisions) == 1
        assert decisions[0].decision_type == "architecture"

    def test_extract_no_decisions(self):
        """Test no decisions from irrelevant tools."""
        tool_invocations = [
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "/test/file.py"},
                "tool_output": "file contents",
            }
        ]

        decisions = extract_decisions_from_evidence(
            tool_invocations=tool_invocations,
            project_name="TestProject",
            session_id="",
        )

        assert len(decisions) == 0

    def test_extract_multiple_decisions(self):
        """Test extracting multiple decisions."""
        tool_invocations = [
            {
                "tool_name": "mcp__pal__consensus",
                "tool_input": {"question": "Question 1"},
                "tool_output": "Answer 1",
            },
            {
                "tool_name": "mcp__pal__thinkdeep",
                "tool_input": {"topic": "Topic 2"},
                "tool_output": "Analysis 2",
            },
        ]

        decisions = extract_decisions_from_evidence(
            tool_invocations=tool_invocations,
            project_name="TestProject",
            session_id="",
        )

        assert len(decisions) == 2
        assert decisions[0].decision_type == "consensus"
        assert decisions[1].decision_type == "technical"

    def test_extract_handles_missing_fields(self):
        """Test extraction handles missing tool input fields."""
        tool_invocations = [
            {
                "tool_name": "mcp__pal__consensus",
                "tool_input": {},  # Missing question
                "tool_output": "",
            }
        ]

        decisions = extract_decisions_from_evidence(
            tool_invocations=tool_invocations,
            project_name="TestProject",
            session_id="",
        )

        # Should not create decision without question
        assert len(decisions) == 0
