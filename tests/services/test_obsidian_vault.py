"""Tests for Obsidian vault service."""

from pathlib import Path

import pytest

from setup.services.obsidian_config import ObsidianConfig, VaultConfig
from setup.services.obsidian_vault import ObsidianNote, ObsidianVaultService


class TestObsidianNote:
    """Tests for ObsidianNote dataclass."""

    def test_project_property(self):
        """Test project property from frontmatter."""
        note = ObsidianNote(
            path=Path("/vault/note.md"),
            relative_path="note.md",
            title="Test Note",
            frontmatter={"project": "SuperClaude"},
        )
        assert note.project == "SuperClaude"

    def test_project_property_missing(self):
        """Test project property when not in frontmatter."""
        note = ObsidianNote(
            path=Path("/vault/note.md"),
            relative_path="note.md",
            title="Test Note",
        )
        assert note.project is None

    def test_category_property(self):
        """Test category property from frontmatter."""
        note = ObsidianNote(
            path=Path("/vault/note.md"),
            relative_path="note.md",
            title="Test Note",
            frontmatter={"category": "Architecture"},
        )
        assert note.category == "Architecture"

    def test_summary_from_frontmatter(self):
        """Test summary from frontmatter."""
        note = ObsidianNote(
            path=Path("/vault/note.md"),
            relative_path="note.md",
            title="Test Note",
            frontmatter={"summary": "This is the summary"},
            content="First paragraph of content.",
        )
        assert note.summary == "This is the summary"

    def test_summary_from_content(self):
        """Test summary extracted from first paragraph."""
        note = ObsidianNote(
            path=Path("/vault/note.md"),
            relative_path="note.md",
            title="Test Note",
            content="# Heading\n\nFirst paragraph of content.\n\nSecond paragraph.",
        )
        assert note.summary == "First paragraph of content."

    def test_summary_skips_headings(self):
        """Test summary skips heading lines."""
        note = ObsidianNote(
            path=Path("/vault/note.md"),
            relative_path="note.md",
            title="Test Note",
            content="# Main Heading\n\n## Subheading\n\nActual content here.",
        )
        assert note.summary == "Actual content here."

    def test_matches_project_by_frontmatter(self):
        """Test project matching via frontmatter."""
        note = ObsidianNote(
            path=Path("/vault/note.md"),
            relative_path="note.md",
            title="Test Note",
            frontmatter={"project": "SuperClaude"},
        )
        assert note.matches_project("SuperClaude") is True
        assert note.matches_project("superclaude") is True
        assert note.matches_project("super") is True
        assert note.matches_project("OtherProject") is False

    def test_matches_project_by_tags(self):
        """Test project matching via tags."""
        note = ObsidianNote(
            path=Path("/vault/note.md"),
            relative_path="note.md",
            title="Test Note",
            tags=["superclaude", "architecture"],
        )
        assert note.matches_project("SuperClaude") is True
        assert note.matches_project("architecture") is True
        assert note.matches_project("other") is False

    def test_matches_project_by_path(self):
        """Test project matching via path."""
        note = ObsidianNote(
            path=Path("/vault/SuperClaude/note.md"),
            relative_path="SuperClaude/note.md",
            title="Test Note",
        )
        assert note.matches_project("SuperClaude") is True
        assert note.matches_project("superclaude") is True
        assert note.matches_project("Other") is False


class TestObsidianVaultService:
    """Tests for ObsidianVaultService."""

    @pytest.fixture
    def vault_dir(self, tmp_path):
        """Create a test vault directory."""
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "Knowledge").mkdir()
        return vault

    @pytest.fixture
    def config(self, vault_dir):
        """Create test config."""
        return ObsidianConfig(
            vault=VaultConfig(path=vault_dir, read_paths=["Knowledge/"]),
        )

    def test_scan_empty_folder(self, config):
        """Test scanning empty knowledge folder."""
        service = ObsidianVaultService(config=config)
        notes = service.scan_knowledge_folder()
        assert notes == []

    def test_scan_with_notes(self, vault_dir, config):
        """Test scanning folder with markdown files."""
        # Create test notes
        (vault_dir / "Knowledge" / "note1.md").write_text("# Note 1\n\nContent here.")
        (vault_dir / "Knowledge" / "note2.md").write_text("# Note 2\n\nMore content.")

        service = ObsidianVaultService(config=config)
        notes = service.scan_knowledge_folder()

        assert len(notes) == 2
        titles = {n.title for n in notes}
        assert "Note 1" in titles
        assert "Note 2" in titles

    def test_scan_nested_folders(self, vault_dir, config):
        """Test scanning nested folders."""
        subfolder = vault_dir / "Knowledge" / "SubFolder"
        subfolder.mkdir()
        (subfolder / "nested.md").write_text("# Nested Note\n\nNested content.")

        service = ObsidianVaultService(config=config)
        notes = service.scan_knowledge_folder()

        assert len(notes) == 1
        assert notes[0].title == "Nested Note"
        assert "SubFolder" in notes[0].relative_path

    def test_parse_frontmatter(self, vault_dir, config):
        """Test parsing YAML frontmatter."""
        (vault_dir / "Knowledge" / "note.md").write_text("""\
---
title: Custom Title
project: TestProject
tags:
  - tag1
  - tag2
category: Architecture
---

# Body Heading

Body content here.
""")

        service = ObsidianVaultService(config=config)
        notes = service.scan_knowledge_folder()

        assert len(notes) == 1
        note = notes[0]
        assert note.title == "Custom Title"
        assert note.frontmatter["project"] == "TestProject"
        assert note.frontmatter["category"] == "Architecture"
        assert "tag1" in note.tags
        assert "tag2" in note.tags

    def test_parse_inline_tags(self, vault_dir, config):
        """Test parsing inline #tags from content."""
        (vault_dir / "Knowledge" / "note.md").write_text("""\
# Note with Tags

This note has #inline and #tags in the content.
Also #nested/tag works.
""")

        service = ObsidianVaultService(config=config)
        notes = service.scan_knowledge_folder()

        assert len(notes) == 1
        note = notes[0]
        assert "inline" in note.tags
        assert "tags" in note.tags
        assert "nested/tag" in note.tags

    def test_title_from_filename(self, vault_dir, config):
        """Test title extraction from filename when no heading."""
        (vault_dir / "Knowledge" / "my-note-file.md").write_text("Just content, no heading.")

        service = ObsidianVaultService(config=config)
        notes = service.scan_knowledge_folder()

        assert len(notes) == 1
        assert notes[0].title == "my-note-file"

    def test_filter_by_project(self, vault_dir, config):
        """Test filtering notes by project."""
        (vault_dir / "Knowledge" / "project.md").write_text("""\
---
project: SuperClaude
---
# Project Note
""")
        (vault_dir / "Knowledge" / "other.md").write_text("""\
---
project: OtherProject
---
# Other Note
""")

        service = ObsidianVaultService(config=config)
        all_notes = service.scan_knowledge_folder()
        filtered = service.filter_by_project(all_notes, "SuperClaude")

        assert len(filtered) == 1
        assert filtered[0].title == "Project Note"

    def test_get_note_by_path(self, vault_dir, config):
        """Test getting specific note by path."""
        (vault_dir / "Knowledge" / "specific.md").write_text("# Specific Note")

        service = ObsidianVaultService(config=config)
        note = service.get_note_by_path("Knowledge/specific.md")

        assert note is not None
        assert note.title == "Specific Note"

    def test_get_note_by_path_not_found(self, config):
        """Test getting note that doesn't exist."""
        service = ObsidianVaultService(config=config)
        note = service.get_note_by_path("nonexistent.md")
        assert note is None

    def test_get_relevant_notes(self, vault_dir, config):
        """Test convenience method for getting relevant notes."""
        (vault_dir / "Knowledge" / "relevant.md").write_text("""\
---
project: TestProject
---
# Relevant
""")
        (vault_dir / "Knowledge" / "unrelated.md").write_text("# Unrelated")

        service = ObsidianVaultService(config=config)
        notes = service.get_relevant_notes("TestProject")

        assert len(notes) == 1
        assert notes[0].title == "Relevant"

    def test_note_exists(self, vault_dir, config):
        """Test checking if note exists."""
        (vault_dir / "Knowledge" / "exists.md").write_text("# Exists")

        service = ObsidianVaultService(config=config)

        assert service.note_exists("Knowledge/exists.md") is True
        assert service.note_exists("Knowledge/missing.md") is False

    def test_get_notes_by_tag(self, vault_dir, config):
        """Test getting notes by tag."""
        (vault_dir / "Knowledge" / "tagged.md").write_text("""\
---
tags: [architecture, design]
---
# Tagged Note
""")
        (vault_dir / "Knowledge" / "other.md").write_text("# Other Note")

        service = ObsidianVaultService(config=config)
        notes = service.get_notes_by_tag("architecture")

        assert len(notes) == 1
        assert notes[0].title == "Tagged Note"

    def test_get_notes_by_category(self, vault_dir, config):
        """Test getting notes by category."""
        (vault_dir / "Knowledge" / "arch.md").write_text("""\
---
category: Architecture
---
# Architecture Note
""")
        (vault_dir / "Knowledge" / "impl.md").write_text("""\
---
category: Implementation
---
# Implementation Note
""")

        service = ObsidianVaultService(config=config)
        notes = service.get_notes_by_category("Architecture")

        assert len(notes) == 1
        assert notes[0].title == "Architecture Note"

    def test_nonexistent_vault_path(self, tmp_path):
        """Test handling nonexistent vault path."""
        config = ObsidianConfig(
            vault=VaultConfig(path=tmp_path / "nonexistent"),
        )
        service = ObsidianVaultService(config=config)
        notes = service.scan_knowledge_folder()
        assert notes == []

    def test_invalid_frontmatter_graceful(self, vault_dir, config):
        """Test graceful handling of invalid frontmatter."""
        (vault_dir / "Knowledge" / "bad.md").write_text("""\
---
invalid: yaml: {broken
---
# Still parses content
""")

        service = ObsidianVaultService(config=config)
        notes = service.scan_knowledge_folder()

        # Should still parse the note, just without frontmatter
        assert len(notes) == 1
        assert notes[0].title == "Still parses content"
        assert notes[0].frontmatter == {}
