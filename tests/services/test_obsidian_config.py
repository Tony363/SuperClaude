"""Tests for Obsidian configuration service."""

from pathlib import Path

import pytest

from setup.services.obsidian_config import (
    ArtifactConfig,
    ContextConfig,
    ObsidianConfig,
    ObsidianConfigService,
    VaultConfig,
)


class TestVaultConfig:
    """Tests for VaultConfig dataclass."""

    def test_from_dict_defaults(self):
        """Test VaultConfig with minimal data."""
        config = VaultConfig.from_dict({"path": "~/Documents/Obsidian"})
        assert config.path == Path.home() / "Documents" / "Obsidian"
        assert config.read_paths == ["Knowledge/"]
        assert config.output_base == "Claude/"

    def test_from_dict_custom(self):
        """Test VaultConfig with custom values."""
        config = VaultConfig.from_dict(
            {
                "path": "/custom/vault",
                "read_paths": ["Notes/", "Projects/"],
                "output_base": "AI/",
            }
        )
        assert config.path == Path("/custom/vault")
        assert config.read_paths == ["Notes/", "Projects/"]
        assert config.output_base == "AI/"

    def test_path_expansion(self):
        """Test that ~ is expanded in paths."""
        config = VaultConfig.from_dict({"path": "~/test/vault"})
        assert str(config.path).startswith(str(Path.home()))


class TestContextConfig:
    """Tests for ContextConfig dataclass."""

    def test_from_dict_defaults(self):
        """Test ContextConfig with empty data."""
        config = ContextConfig.from_dict({})
        assert config.relevance_filter.type == "project_name"
        assert config.relevance_filter.field == "project"
        assert "summary" in config.extract_fields

    def test_from_dict_custom(self):
        """Test ContextConfig with custom values."""
        config = ContextConfig.from_dict(
            {
                "relevance_filter": {"type": "tags", "field": "topics"},
                "extract_fields": ["title", "status"],
            }
        )
        assert config.relevance_filter.type == "tags"
        assert config.relevance_filter.field == "topics"
        assert config.extract_fields == ["title", "status"]


class TestArtifactConfig:
    """Tests for ArtifactConfig dataclass."""

    def test_from_dict_defaults(self):
        """Test ArtifactConfig with empty data."""
        config = ArtifactConfig.from_dict({})
        assert config.sync_on == "task_completion"
        assert config.types == ["decisions"]
        assert config.backlinks.enabled is True

    def test_from_dict_disabled_sync(self):
        """Test ArtifactConfig with sync disabled."""
        config = ArtifactConfig.from_dict({"sync_on": "never"})
        assert config.sync_on == "never"

    def test_from_dict_backlinks_disabled(self):
        """Test ArtifactConfig with backlinks disabled."""
        config = ArtifactConfig.from_dict({"backlinks": {"enabled": False}})
        assert config.backlinks.enabled is False


class TestObsidianConfig:
    """Tests for ObsidianConfig dataclass."""

    def test_from_dict_minimal(self):
        """Test ObsidianConfig with minimal vault config."""
        config = ObsidianConfig.from_dict({"vault": {"path": "~/Documents/Obsidian"}})
        assert config.vault.path == Path.home() / "Documents" / "Obsidian"
        assert config.context is not None
        assert config.artifacts is not None
        assert config.notes is not None

    def test_from_dict_full(self):
        """Test ObsidianConfig with full configuration."""
        config = ObsidianConfig.from_dict(
            {
                "vault": {
                    "path": "/vault",
                    "read_paths": ["KB/"],
                    "output_base": "Output/",
                },
                "context": {
                    "relevance_filter": {"type": "path", "field": "folder"},
                },
                "artifacts": {
                    "sync_on": "manual",
                    "types": ["decisions", "notes"],
                },
                "notes": {
                    "format": "minimal",
                },
            }
        )
        assert config.vault.read_paths == ["KB/"]
        assert config.context.relevance_filter.type == "path"
        assert config.artifacts.sync_on == "manual"
        assert config.notes.format == "minimal"

    def test_from_dict_missing_vault_raises(self):
        """Test that missing vault raises ValueError."""
        with pytest.raises(ValueError, match="must include 'vault'"):
            ObsidianConfig.from_dict({})

    def test_default_config(self):
        """Test default configuration factory."""
        config = ObsidianConfig.default()
        assert config.vault.path == Path.home() / "Documents" / "Obsidian"
        assert config.artifacts.sync_on == "task_completion"


class TestObsidianConfigService:
    """Tests for ObsidianConfigService."""

    def test_config_path(self, tmp_path):
        """Test config path property."""
        service = ObsidianConfigService(tmp_path)
        assert service.config_path == tmp_path / ".obsidian.yaml"

    def test_config_exists_false(self, tmp_path):
        """Test config_exists when no config file."""
        service = ObsidianConfigService(tmp_path)
        assert service.config_exists() is False

    def test_config_exists_true(self, tmp_path):
        """Test config_exists when config file present."""
        config_file = tmp_path / ".obsidian.yaml"
        config_file.write_text("vault:\n  path: ~/Documents/Obsidian\n")

        service = ObsidianConfigService(tmp_path)
        assert service.config_exists() is True

    def test_load_config_success(self, tmp_path):
        """Test loading valid config file."""
        config_file = tmp_path / ".obsidian.yaml"
        config_file.write_text("""\
vault:
  path: ~/Documents/Obsidian
  read_paths:
    - Knowledge/
artifacts:
  sync_on: task_completion
""")

        service = ObsidianConfigService(tmp_path)
        config = service.load_config()

        assert config is not None
        assert config.vault.path == Path.home() / "Documents" / "Obsidian"
        assert config.artifacts.sync_on == "task_completion"

    def test_load_config_not_found(self, tmp_path):
        """Test loading when no config file exists."""
        service = ObsidianConfigService(tmp_path)
        config = service.load_config()
        assert config is None

    def test_load_config_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML."""
        config_file = tmp_path / ".obsidian.yaml"
        config_file.write_text("vault: {invalid yaml:::")

        service = ObsidianConfigService(tmp_path)
        with pytest.raises(ValueError, match="Invalid YAML"):
            service.load_config()

    def test_load_config_caching(self, tmp_path):
        """Test that config is cached."""
        config_file = tmp_path / ".obsidian.yaml"
        config_file.write_text("vault:\n  path: ~/Documents/Obsidian\n")

        service = ObsidianConfigService(tmp_path)
        config1 = service.load_config()
        config2 = service.load_config()

        assert config1 is config2  # Same instance

    def test_clear_cache(self, tmp_path):
        """Test clearing config cache."""
        config_file = tmp_path / ".obsidian.yaml"
        config_file.write_text("vault:\n  path: ~/Documents/Obsidian\n")

        service = ObsidianConfigService(tmp_path)
        config1 = service.load_config()
        service.clear_cache()
        config2 = service.load_config()

        assert config1 is not config2  # Different instances

    def test_validate_vault_path_exists(self, tmp_path):
        """Test vault path validation when path exists."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        config_file = tmp_path / ".obsidian.yaml"
        config_file.write_text(f"vault:\n  path: {vault_path}\n")

        service = ObsidianConfigService(tmp_path)
        assert service.validate_vault_path() is True

    def test_validate_vault_path_missing(self, tmp_path):
        """Test vault path validation when path missing."""
        config_file = tmp_path / ".obsidian.yaml"
        config_file.write_text("vault:\n  path: /nonexistent/path\n")

        service = ObsidianConfigService(tmp_path)
        assert service.validate_vault_path() is False

    def test_get_read_paths(self, tmp_path):
        """Test getting absolute read paths."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        config_file = tmp_path / ".obsidian.yaml"
        config_file.write_text(f"""\
vault:
  path: {vault_path}
  read_paths:
    - Knowledge/
    - Projects/
""")

        service = ObsidianConfigService(tmp_path)
        paths = service.get_read_paths()

        assert len(paths) == 2
        assert paths[0] == vault_path / "Knowledge/"
        assert paths[1] == vault_path / "Projects/"

    def test_get_output_path(self, tmp_path):
        """Test getting output path for artifact type."""
        vault_path = tmp_path / "vault"
        vault_path.mkdir()

        config_file = tmp_path / ".obsidian.yaml"
        config_file.write_text(f"""\
vault:
  path: {vault_path}
artifacts:
  output_paths:
    decisions: Claude/Decisions/
    notes: Claude/Notes/
""")

        service = ObsidianConfigService(tmp_path)

        assert service.get_output_path("decisions") == vault_path / "Claude/Decisions/"
        assert service.get_output_path("notes") == vault_path / "Claude/Notes/"
        assert service.get_output_path("unknown") is None

    def test_create_default_config(self, tmp_path):
        """Test creating default config file."""
        service = ObsidianConfigService(tmp_path)
        path = service.create_default_config()

        assert path.exists()
        content = path.read_text()
        assert "vault:" in content
        assert "artifacts:" in content
        assert "backlinks:" in content
