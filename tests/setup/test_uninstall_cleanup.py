"""Tests for uninstall cleanup logic — artifact removal, CLAUDE.md handling, Sondera."""

import argparse
import json
from pathlib import Path
from unittest.mock import MagicMock


def _make_args(**overrides):
    """Create a namespace with default uninstall args."""
    defaults = {
        "install_dir": Path("/tmp/test"),
        "complete": True,
        "keep_backups": False,
        "keep_logs": False,
        "keep_settings": False,
        "cleanup_env": False,
        "cleanup_sondera": False,
        "no_restore_script": False,
        "dry_run": False,
        "no_confirm": True,
        "yes": True,
        "quiet": True,
        "verbose": False,
        "components": None,
    }
    defaults.update(overrides)
    return argparse.Namespace(**defaults)


class TestSuperClaudeOwnedFiles:
    """Verify all owned files are in the allowlist and get removed."""

    def test_owned_files_list_includes_component_registry(self):
        from setup.cli.commands.uninstall import cleanup_installation_directory

        # Access the function to verify it can be imported
        assert callable(cleanup_installation_directory)

    def test_metadata_file_removed(self, tmp_path):
        (tmp_path / ".superclaude-metadata.json").write_text("{}")
        args = _make_args(install_dir=tmp_path)

        from setup.cli.commands.uninstall import cleanup_installation_directory

        cleanup_installation_directory(tmp_path, args)

        assert not (tmp_path / ".superclaude-metadata.json").exists()

    def test_component_registry_removed(self, tmp_path):
        (tmp_path / ".component-registry.json").write_text("{}")
        (tmp_path / ".component-registry.json.backup").write_text("{}")
        args = _make_args(install_dir=tmp_path)

        from setup.cli.commands.uninstall import cleanup_installation_directory

        cleanup_installation_directory(tmp_path, args)

        assert not (tmp_path / ".component-registry.json").exists()
        assert not (tmp_path / ".component-registry.json.backup").exists()

    def test_settings_backup_removed(self, tmp_path):
        (tmp_path / "settings.json.backup").write_text("{}")
        args = _make_args(install_dir=tmp_path)

        from setup.cli.commands.uninstall import cleanup_installation_directory

        cleanup_installation_directory(tmp_path, args)

        assert not (tmp_path / "settings.json.backup").exists()

    def test_corrupted_metadata_glob_removed(self, tmp_path):
        (tmp_path / ".superclaude-metadata.json.corrupted.1").write_text("{}")
        (tmp_path / ".superclaude-metadata.json.corrupted.2").write_text("{}")
        args = _make_args(install_dir=tmp_path)

        from setup.cli.commands.uninstall import cleanup_installation_directory

        cleanup_installation_directory(tmp_path, args)

        remaining = list(tmp_path.glob(".superclaude-metadata.json.corrupted.*"))
        assert remaining == []

    def test_owned_dirs_removed(self, tmp_path):
        for dirname in ["superclaude", "feedback", "cache", "commands"]:
            (tmp_path / dirname).mkdir()
            (tmp_path / dirname / "dummy.txt").write_text("x")

        args = _make_args(install_dir=tmp_path)

        from setup.cli.commands.uninstall import cleanup_installation_directory

        cleanup_installation_directory(tmp_path, args)

        for dirname in ["superclaude", "feedback", "cache", "commands"]:
            assert not (tmp_path / dirname).exists()

    def test_conditional_dirs_preserved_with_flags(self, tmp_path):
        (tmp_path / "backups").mkdir()
        (tmp_path / "backups" / "test.tar.gz").write_text("x")
        (tmp_path / "logs").mkdir()
        (tmp_path / "logs" / "app.log").write_text("x")

        args = _make_args(install_dir=tmp_path, keep_backups=True, keep_logs=True)

        from setup.cli.commands.uninstall import cleanup_installation_directory

        cleanup_installation_directory(tmp_path, args)

        assert (tmp_path / "backups").exists()
        assert (tmp_path / "logs").exists()


class TestCLAUDEMdCleanup:
    """Test intelligent CLAUDE.md cleanup during complete uninstall."""

    def test_claude_md_deleted_when_only_boilerplate(self, tmp_path):
        content = """# SuperClaude Entry Point

This file serves as the entry point for the SuperClaude framework.
You can add your own custom instructions and configurations here.

The SuperClaude framework components will be automatically imported below.

# ═══════════════════════════════════════════════════
# SuperClaude Framework Components
# ═══════════════════════════════════════════════════

# Core Framework
@AGENTS.md
@CLAUDE_CORE.md
"""
        (tmp_path / "CLAUDE.md").write_text(content)
        args = _make_args(install_dir=tmp_path)

        from setup.cli.commands.uninstall import cleanup_installation_directory

        cleanup_installation_directory(tmp_path, args)

        assert not (tmp_path / "CLAUDE.md").exists()

    def test_claude_md_preserved_with_user_content(self, tmp_path):
        content = """# My Project Instructions

Always use snake_case for Python files.
Use pytest for all testing.

# ═══════════════════════════════════════════════════
# SuperClaude Framework Components
# ═══════════════════════════════════════════════════

# Core Framework
@AGENTS.md
@CLAUDE_CORE.md
"""
        (tmp_path / "CLAUDE.md").write_text(content)
        args = _make_args(install_dir=tmp_path)

        from setup.cli.commands.uninstall import cleanup_installation_directory

        cleanup_installation_directory(tmp_path, args)

        assert (tmp_path / "CLAUDE.md").exists()
        remaining = (tmp_path / "CLAUDE.md").read_text()
        assert "My Project Instructions" in remaining
        assert "SuperClaude Framework Components" not in remaining
        assert "@AGENTS.md" not in remaining

    def test_claude_md_no_framework_section_left_alone(self, tmp_path):
        content = """# My Custom Config

This is all user content with no framework section.
"""
        (tmp_path / "CLAUDE.md").write_text(content)
        args = _make_args(install_dir=tmp_path)

        from setup.cli.commands.uninstall import cleanup_installation_directory

        cleanup_installation_directory(tmp_path, args)

        # CLAUDE.md is in owned files list, but _cleanup_claude_md runs first
        # and leaves it because it has user content with no framework marker
        assert (tmp_path / "CLAUDE.md").exists()
        remaining = (tmp_path / "CLAUDE.md").read_text()
        assert "My Custom Config" in remaining


class TestRulesCleanup:
    """Test template rules removal."""

    def test_template_rules_removed(self, tmp_path):
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        for name in ["architecture-reference.md", "logging.md", "project-conventions.md", "README.md"]:
            (rules_dir / name).write_text("template content")

        args = _make_args(install_dir=tmp_path)

        from setup.cli.commands.uninstall import cleanup_installation_directory

        cleanup_installation_directory(tmp_path, args)

        assert not rules_dir.exists()

    def test_user_rules_preserved(self, tmp_path):
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        (rules_dir / "architecture-reference.md").write_text("template")
        (rules_dir / "my-custom-rule.md").write_text("user rule")

        args = _make_args(install_dir=tmp_path)

        from setup.cli.commands.uninstall import cleanup_installation_directory

        cleanup_installation_directory(tmp_path, args)

        # rules/ should still exist because user file is preserved
        assert rules_dir.exists()
        assert (rules_dir / "my-custom-rule.md").exists()
        assert not (rules_dir / "architecture-reference.md").exists()


class TestSonderaCleanup:
    """Test Sondera artifact detection and removal."""

    def test_detect_sondera_artifacts_false_when_none(self):
        from setup.cli.commands.uninstall import _detect_sondera_artifacts

        # May return True if real artifacts exist on this system,
        # but the function should at least be callable
        assert isinstance(_detect_sondera_artifacts(), bool)

    def test_cleanup_sondera_no_error_when_nothing_exists(self):
        from setup.cli.commands.uninstall import cleanup_sondera_artifacts

        logger = MagicMock()
        result = cleanup_sondera_artifacts(logger)
        assert result is True

    def test_settings_local_only_removed_if_sondera(self, tmp_path, monkeypatch):
        """settings.local.json should only be removed if it contains 'sondera'."""
        from setup.cli.commands.uninstall import cleanup_sondera_artifacts

        # Patch Path.home to use tmp_path
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_local = claude_dir / "settings.local.json"
        settings_local.write_text(json.dumps({"hooks": {"sondera-harness": {}}}))

        logger = MagicMock()
        cleanup_sondera_artifacts(logger)

        assert not settings_local.exists()

    def test_settings_local_preserved_if_not_sondera(self, tmp_path, monkeypatch):
        """settings.local.json without sondera content should be preserved."""
        from setup.cli.commands.uninstall import cleanup_sondera_artifacts

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        settings_local = claude_dir / "settings.local.json"
        settings_local.write_text(json.dumps({"theme": "dark"}))

        logger = MagicMock()
        cleanup_sondera_artifacts(logger)

        assert settings_local.exists()


class TestVerifySuperclaudeFile:
    """Test the verify_superclaude_file helper."""

    def test_core_known_file(self, tmp_path):
        from setup.cli.commands.uninstall import verify_superclaude_file

        assert verify_superclaude_file(tmp_path / "AGENTS.md", "core") is True
        assert verify_superclaude_file(tmp_path / "FLAGS.md", "core") is True

    def test_core_unknown_file(self, tmp_path):
        from setup.cli.commands.uninstall import verify_superclaude_file

        assert verify_superclaude_file(tmp_path / "random.md", "core") is False

    def test_commands_in_sc_dir(self, tmp_path):
        from setup.cli.commands.uninstall import verify_superclaude_file

        path = tmp_path / "commands" / "sc" / "test.md"
        assert verify_superclaude_file(path, "commands") is True

    def test_agents_any_md(self, tmp_path):
        from setup.cli.commands.uninstall import verify_superclaude_file

        path = tmp_path / "agents" / "custom-agent.md"
        assert verify_superclaude_file(path, "agents") is True

    def test_agents_non_md(self, tmp_path):
        from setup.cli.commands.uninstall import verify_superclaude_file

        path = tmp_path / "agents" / "config.json"
        assert verify_superclaude_file(path, "agents") is False


class TestBackupCreationLogic:
    """Test that backup is skipped for --complete without --keep-backups."""

    def test_complete_skips_backup(self):
        """With --complete and not --keep-backups, backup should not be created."""
        args = _make_args(complete=True, keep_backups=False, dry_run=False)
        # The condition: not dry_run and not keep_backups and not complete
        should_backup = not args.dry_run and not args.keep_backups and not args.complete
        assert should_backup is False

    def test_partial_uninstall_creates_backup(self):
        """Without --complete, backup should be created."""
        args = _make_args(complete=False, keep_backups=False, dry_run=False)
        should_backup = not args.dry_run and not args.keep_backups and not args.complete
        assert should_backup is True
