"""Tests for Obsidian CLAUDE.md integration service."""

import pytest
from pathlib import Path

from setup.services.obsidian_md import ObsidianMdService, setup_obsidian_integration


class TestObsidianMdService:
    """Tests for ObsidianMdService."""

    @pytest.fixture
    def setup_dirs(self, tmp_path):
        """Create test directories."""
        install_dir = tmp_path / "install"
        install_dir.mkdir()

        project_root = tmp_path / "project"
        project_root.mkdir()

        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()
        (vault_dir / "Knowledge").mkdir()

        return {
            "install": install_dir,
            "project": project_root,
            "vault": vault_dir,
        }

    def test_is_configured_false(self, setup_dirs):
        """Test is_configured when no config file."""
        service = ObsidianMdService(
            install_dir=setup_dirs["install"],
            project_root=setup_dirs["project"],
        )
        assert service.is_configured() is False

    def test_is_configured_true(self, setup_dirs):
        """Test is_configured when config exists."""
        config_file = setup_dirs["project"] / ".obsidian.yaml"
        config_file.write_text("vault:\n  path: ~/vault\n")

        service = ObsidianMdService(
            install_dir=setup_dirs["install"],
            project_root=setup_dirs["project"],
        )
        assert service.is_configured() is True

    def test_obsidian_md_path(self, setup_dirs):
        """Test obsidian_md_path property."""
        service = ObsidianMdService(
            install_dir=setup_dirs["install"],
            project_root=setup_dirs["project"],
        )
        assert service.obsidian_md_path == setup_dirs["install"] / "OBSIDIAN.md"

    def test_setup_obsidian_context_not_configured(self, setup_dirs):
        """Test setup when not configured."""
        service = ObsidianMdService(
            install_dir=setup_dirs["install"],
            project_root=setup_dirs["project"],
        )
        result = service.setup_obsidian_context()
        assert result is False

    def test_setup_obsidian_context_vault_missing(self, setup_dirs):
        """Test setup when vault path doesn't exist."""
        config_file = setup_dirs["project"] / ".obsidian.yaml"
        config_file.write_text("vault:\n  path: /nonexistent/path\n")

        service = ObsidianMdService(
            install_dir=setup_dirs["install"],
            project_root=setup_dirs["project"],
        )
        result = service.setup_obsidian_context()
        assert result is False

    def test_setup_obsidian_context_success(self, setup_dirs):
        """Test successful context setup."""
        vault_dir = setup_dirs["vault"]

        # Create config
        config_file = setup_dirs["project"] / ".obsidian.yaml"
        config_file.write_text(f"""\
vault:
  path: {vault_dir}
  read_paths:
    - Knowledge/
""")

        # Create test note
        (vault_dir / "Knowledge" / "note.md").write_text("""\
---
project: TestProject
---
# Test Note
Content here.
""")

        # Create CLAUDE.md first
        claude_md = setup_dirs["install"] / "CLAUDE.md"
        claude_md.write_text("# Entry Point\n")

        service = ObsidianMdService(
            install_dir=setup_dirs["install"],
            project_root=setup_dirs["project"],
            project_name="TestProject",
        )
        result = service.setup_obsidian_context()

        assert result is True

        # Check OBSIDIAN.md was created
        obsidian_md = setup_dirs["install"] / "OBSIDIAN.md"
        assert obsidian_md.exists()
        content = obsidian_md.read_text()
        assert "# Obsidian Knowledge Context" in content
        assert "TestProject" in content

        # Check import was added to CLAUDE.md
        claude_content = claude_md.read_text()
        assert "@OBSIDIAN.md" in claude_content

    def test_refresh_context_no_changes(self, setup_dirs):
        """Test refresh when no changes needed."""
        vault_dir = setup_dirs["vault"]

        config_file = setup_dirs["project"] / ".obsidian.yaml"
        config_file.write_text(f"""\
vault:
  path: {vault_dir}
  read_paths:
    - Knowledge/
""")

        # Create existing OBSIDIAN.md with matching state
        obsidian_md = setup_dirs["install"] / "OBSIDIAN.md"
        obsidian_md.write_text("""\
# Obsidian Knowledge Context

Project: **TestProject**
Generated: 2025-02-04

*0 relevant notes loaded from Obsidian vault*
""")

        service = ObsidianMdService(
            install_dir=setup_dirs["install"],
            project_root=setup_dirs["project"],
            project_name="TestProject",
        )
        result = service.refresh_context()

        # Should return False (no changes)
        assert result is False

    def test_refresh_context_with_changes(self, setup_dirs):
        """Test refresh when vault has changed."""
        vault_dir = setup_dirs["vault"]

        config_file = setup_dirs["project"] / ".obsidian.yaml"
        config_file.write_text(f"""\
vault:
  path: {vault_dir}
  read_paths:
    - Knowledge/
""")

        # Create existing OBSIDIAN.md claiming 0 notes
        obsidian_md = setup_dirs["install"] / "OBSIDIAN.md"
        obsidian_md.write_text("""\
Project: **TestProject**
*0 relevant notes loaded from Obsidian vault*
""")

        # Now add a note
        (vault_dir / "Knowledge" / "note.md").write_text("""\
---
project: TestProject
---
# Note
""")

        service = ObsidianMdService(
            install_dir=setup_dirs["install"],
            project_root=setup_dirs["project"],
            project_name="TestProject",
        )
        result = service.refresh_context()

        # Should return True (changes made)
        assert result is True
        content = obsidian_md.read_text()
        assert "1 relevant notes loaded" in content

    def test_remove_obsidian_context(self, setup_dirs):
        """Test removing Obsidian context."""
        # Create OBSIDIAN.md
        obsidian_md = setup_dirs["install"] / "OBSIDIAN.md"
        obsidian_md.write_text("# Context")

        # Create CLAUDE.md with import
        claude_md = setup_dirs["install"] / "CLAUDE.md"
        claude_md.write_text("""\
# Entry

# ═══════════════════════════════════════════════════
# SuperClaude Framework Components
# ═══════════════════════════════════════════════════

# Obsidian Context
@OBSIDIAN.md
""")

        service = ObsidianMdService(
            install_dir=setup_dirs["install"],
            project_root=setup_dirs["project"],
        )
        result = service.remove_obsidian_context()

        assert result is True
        assert not obsidian_md.exists()

    def test_get_status_not_configured(self, setup_dirs):
        """Test status when not configured."""
        service = ObsidianMdService(
            install_dir=setup_dirs["install"],
            project_root=setup_dirs["project"],
        )
        status = service.get_status()

        assert status["configured"] is False
        assert status["vault_exists"] is False
        assert status["note_count"] == 0

    def test_get_status_configured(self, setup_dirs):
        """Test status when configured."""
        vault_dir = setup_dirs["vault"]

        config_file = setup_dirs["project"] / ".obsidian.yaml"
        config_file.write_text(f"""\
vault:
  path: {vault_dir}
  read_paths:
    - Knowledge/
""")

        (vault_dir / "Knowledge" / "note.md").write_text("""\
---
project: TestProject
category: Architecture
---
# Note
""")

        service = ObsidianMdService(
            install_dir=setup_dirs["install"],
            project_root=setup_dirs["project"],
            project_name="TestProject",
        )
        status = service.get_status()

        assert status["configured"] is True
        assert status["vault_exists"] is True
        assert status["note_count"] == 1
        assert "Architecture" in status["categories"]
        assert str(vault_dir) in status["vault_path"]


class TestSetupObsidianIntegration:
    """Tests for convenience function."""

    def test_setup_obsidian_integration_no_config(self, tmp_path):
        """Test function when not configured."""
        result = setup_obsidian_integration(
            install_dir=tmp_path / "install",
            project_root=tmp_path / "project",
        )
        assert result is False

    def test_setup_obsidian_integration_success(self, tmp_path):
        """Test successful integration setup."""
        install_dir = tmp_path / "install"
        install_dir.mkdir()
        project_root = tmp_path / "project"
        project_root.mkdir()
        vault_dir = tmp_path / "vault"
        vault_dir.mkdir()
        (vault_dir / "Knowledge").mkdir()

        # Create config
        config_file = project_root / ".obsidian.yaml"
        config_file.write_text(f"""\
vault:
  path: {vault_dir}
  read_paths:
    - Knowledge/
""")

        # Create note
        (vault_dir / "Knowledge" / "note.md").write_text("""\
---
project: TestProject
---
# Note
""")

        # Create CLAUDE.md
        (install_dir / "CLAUDE.md").write_text("# Entry\n")

        result = setup_obsidian_integration(
            install_dir=install_dir,
            project_root=project_root,
            project_name="TestProject",
        )

        assert result is True
        assert (install_dir / "OBSIDIAN.md").exists()
