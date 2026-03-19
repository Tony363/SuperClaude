"""Tests for environment variable and .env file cleanup during uninstall."""

from pathlib import Path


class TestCleanupEnvFile:
    """Test .env file cleanup logic."""

    def test_removes_superclaude_api_keys_section(self, tmp_path):
        from setup.utils.environment import cleanup_env_file

        env_file = tmp_path / ".env"
        env_file.write_text(
            'DATABASE_URL="postgres://localhost/db"\n'
            "# SuperClaude API Keys\n"
            'TWENTYFIRST_API_KEY="abc123"\n'
            'MORPH_API_KEY="xyz789"\n'
            "\n"
            'OTHER_VAR="keep"\n'
        )

        result = cleanup_env_file(env_file)

        assert result is True
        content = env_file.read_text()
        assert "TWENTYFIRST_API_KEY" not in content
        assert "MORPH_API_KEY" not in content
        assert "SuperClaude" not in content
        assert 'DATABASE_URL="postgres://localhost/db"' in content
        assert 'OTHER_VAR="keep"' in content

    def test_preserves_non_superclaude_vars(self, tmp_path):
        from setup.utils.environment import cleanup_env_file

        env_file = tmp_path / ".env"
        original = 'API_KEY="secret"\nDEBUG=true\n'
        env_file.write_text(original)

        result = cleanup_env_file(env_file)

        assert result is True
        assert env_file.read_text() == original

    def test_noop_when_file_missing(self, tmp_path):
        from setup.utils.environment import cleanup_env_file

        result = cleanup_env_file(tmp_path / ".env")
        assert result is True

    def test_removes_single_api_key_comment(self, tmp_path):
        from setup.utils.environment import cleanup_env_file

        env_file = tmp_path / ".env"
        env_file.write_text(
            "# SuperClaude API Key\n"
            'TWENTYFIRST_API_KEY="abc"\n'
            "\n"
            'KEEP_ME="yes"\n'
        )

        cleanup_env_file(env_file)

        content = env_file.read_text()
        assert "TWENTYFIRST_API_KEY" not in content
        assert 'KEEP_ME="yes"' in content


class TestShellConfigCleanup:
    """Test shell config (zshrc/bashrc) env var removal."""

    def test_remove_env_var_from_shell_config(self, tmp_path):
        from setup.utils.environment import _remove_env_var_from_shell_config

        zshrc = tmp_path / ".zshrc"
        zshrc.write_text(
            "# existing config\n"
            "export PATH=$PATH:/usr/local/bin\n"
            "\n"
            "# SuperClaude API Key\n"
            'export TWENTYFIRST_API_KEY="abc123"\n'
            "\n"
            "# other stuff\n"
            "alias ll='ls -la'\n"
        )

        result = _remove_env_var_from_shell_config(zshrc, "TWENTYFIRST_API_KEY")

        assert result is True
        content = zshrc.read_text()
        assert "TWENTYFIRST_API_KEY" not in content
        assert "SuperClaude API Key" not in content
        assert "export PATH" in content
        assert "alias ll" in content

    def test_remove_nonexistent_var_noop(self, tmp_path):
        from setup.utils.environment import _remove_env_var_from_shell_config

        zshrc = tmp_path / ".zshrc"
        original = "export PATH=$PATH\n"
        zshrc.write_text(original)

        result = _remove_env_var_from_shell_config(zshrc, "NONEXISTENT_VAR")

        assert result is True
        assert zshrc.read_text() == original
