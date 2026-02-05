"""Tests for Obsidian context generator."""

import pytest
from pathlib import Path
from datetime import datetime

from setup.services.obsidian_config import ObsidianConfig, VaultConfig, ContextConfig
from setup.services.obsidian_vault import ObsidianNote, ObsidianVaultService
from setup.services.obsidian_context import ObsidianContextGenerator, generate_obsidian_context


class TestObsidianContextGenerator:
    """Tests for ObsidianContextGenerator."""

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

    def test_generate_empty_context(self, config):
        """Test generating context with no notes."""
        generator = ObsidianContextGenerator(
            project_name="TestProject",
            config=config,
        )
        content = generator.generate_context()

        assert "# Obsidian Knowledge Context" in content
        assert "Project: **TestProject**" in content
        assert "No relevant notes found" in content

    def test_generate_context_with_notes(self, vault_dir, config):
        """Test generating context with notes."""
        (vault_dir / "Knowledge" / "note1.md").write_text("""\
---
project: TestProject
category: Architecture
tags: [design, api]
---
# API Design

This is the summary of the API design document.

More details here.
""")

        generator = ObsidianContextGenerator(
            project_name="TestProject",
            config=config,
        )
        content = generator.generate_context()

        assert "# Obsidian Knowledge Context" in content
        assert "Project: **TestProject**" in content
        assert "## Architecture" in content
        assert "### API Design" in content
        assert "design, api" in content
        assert "This is the summary" in content
        assert "[[Knowledge/note1.md]]" in content
        assert "1 relevant notes loaded" in content

    def test_generate_context_multiple_categories(self, vault_dir, config):
        """Test context with multiple categories."""
        (vault_dir / "Knowledge" / "arch.md").write_text("""\
---
project: TestProject
category: Architecture
---
# Arch Note
Summary of arch.
""")
        (vault_dir / "Knowledge" / "impl.md").write_text("""\
---
project: TestProject
category: Implementation
---
# Impl Note
Summary of impl.
""")

        generator = ObsidianContextGenerator(
            project_name="TestProject",
            config=config,
        )
        content = generator.generate_context()

        assert "## Architecture" in content
        assert "## Implementation" in content
        assert "2 relevant notes loaded" in content

    def test_generate_context_uncategorized(self, vault_dir, config):
        """Test context with uncategorized notes."""
        (vault_dir / "Knowledge" / "note.md").write_text("""\
---
project: TestProject
---
# No Category Note
Just content.
""")

        generator = ObsidianContextGenerator(
            project_name="TestProject",
            config=config,
        )
        content = generator.generate_context()

        assert "## Uncategorized" in content
        assert "### No Category Note" in content

    def test_generate_context_filters_by_project(self, vault_dir, config):
        """Test that context only includes relevant notes."""
        (vault_dir / "Knowledge" / "relevant.md").write_text("""\
---
project: TestProject
---
# Relevant Note
Content.
""")
        (vault_dir / "Knowledge" / "unrelated.md").write_text("""\
---
project: OtherProject
---
# Unrelated Note
Content.
""")

        generator = ObsidianContextGenerator(
            project_name="TestProject",
            config=config,
        )
        content = generator.generate_context()

        assert "Relevant Note" in content
        assert "Unrelated Note" not in content
        assert "1 relevant notes loaded" in content

    def test_should_regenerate_empty_content(self, config):
        """Test should_regenerate with empty content."""
        generator = ObsidianContextGenerator(
            project_name="TestProject",
            config=config,
        )
        assert generator.should_regenerate("") is True

    def test_should_regenerate_different_project(self, config):
        """Test should_regenerate when project changed."""
        generator = ObsidianContextGenerator(
            project_name="NewProject",
            config=config,
        )
        existing = "Project: **OldProject**\n*0 relevant notes loaded*"
        assert generator.should_regenerate(existing) is True

    def test_should_regenerate_count_changed(self, vault_dir, config):
        """Test should_regenerate when note count changed."""
        # Create a note
        (vault_dir / "Knowledge" / "note.md").write_text("""\
---
project: TestProject
---
# Note
""")

        generator = ObsidianContextGenerator(
            project_name="TestProject",
            config=config,
        )
        # Existing content says 0 notes
        existing = "Project: **TestProject**\n*0 relevant notes loaded*"
        assert generator.should_regenerate(existing) is True

    def test_should_regenerate_same_state(self, vault_dir, config):
        """Test should_regenerate when state unchanged."""
        (vault_dir / "Knowledge" / "note.md").write_text("""\
---
project: TestProject
---
# Note
""")

        generator = ObsidianContextGenerator(
            project_name="TestProject",
            config=config,
        )
        # Existing content matches current state
        existing = "Project: **TestProject**\n*1 relevant notes loaded*"
        assert generator.should_regenerate(existing) is False

    def test_get_note_count(self, vault_dir, config):
        """Test getting note count."""
        (vault_dir / "Knowledge" / "note.md").write_text("""\
---
project: TestProject
---
# Note
""")

        generator = ObsidianContextGenerator(
            project_name="TestProject",
            config=config,
        )
        assert generator.get_note_count() == 1

    def test_get_categories(self, vault_dir, config):
        """Test getting categories list."""
        (vault_dir / "Knowledge" / "arch.md").write_text("""\
---
project: TestProject
category: Architecture
---
# Arch
""")
        (vault_dir / "Knowledge" / "impl.md").write_text("""\
---
project: TestProject
category: Implementation
---
# Impl
""")

        generator = ObsidianContextGenerator(
            project_name="TestProject",
            config=config,
        )
        categories = generator.get_categories()

        assert "Architecture" in categories
        assert "Implementation" in categories
        assert categories == sorted(categories)  # Should be sorted

    def test_summary_truncation(self, vault_dir, config):
        """Test that long summaries are truncated."""
        long_content = "A" * 600
        (vault_dir / "Knowledge" / "note.md").write_text(f"""\
---
project: TestProject
---
# Note

{long_content}
""")

        generator = ObsidianContextGenerator(
            project_name="TestProject",
            config=config,
        )
        content = generator.generate_context()

        # Summary should be truncated
        assert "..." in content
        assert long_content not in content

    def test_no_config_returns_empty(self):
        """Test that missing config returns empty string."""
        generator = ObsidianContextGenerator(
            project_name="TestProject",
            config=None,
        )
        content = generator.generate_context()
        assert content == ""


class TestGenerateObsidianContext:
    """Tests for convenience function."""

    def test_generate_obsidian_context_no_config(self, tmp_path):
        """Test function when no config exists."""
        content = generate_obsidian_context(
            project_name="TestProject",
            project_root=tmp_path,
        )
        # Should return empty when no config
        assert content == ""

    def test_generate_obsidian_context_with_config(self, tmp_path):
        """Test function with valid config."""
        # Create vault
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "Knowledge").mkdir()
        (vault / "Knowledge" / "note.md").write_text("""\
---
project: TestProject
---
# Test Note
Summary content.
""")

        # Create config
        config_file = tmp_path / ".obsidian.yaml"
        config_file.write_text(f"""\
vault:
  path: {vault}
  read_paths:
    - Knowledge/
""")

        content = generate_obsidian_context(
            project_name="TestProject",
            project_root=tmp_path,
        )

        assert "# Obsidian Knowledge Context" in content
        assert "Test Note" in content
