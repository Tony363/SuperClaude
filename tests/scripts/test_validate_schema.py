"""Tests for scripts/validate_schema.py."""

from pathlib import Path

from scripts.validate_schema import extract_frontmatter


class TestExtractFrontmatter:
    """Tests for extract_frontmatter."""

    def test_valid_frontmatter(self):
        content = "---\nname: test-agent\ntier: core\n---\n\n# Body"
        result = extract_frontmatter(content)
        assert result is not None
        assert result["name"] == "test-agent"
        assert result["tier"] == "core"

    def test_no_frontmatter(self):
        content = "# Just a heading\n\nSome text."
        result = extract_frontmatter(content)
        assert result is None

    def test_missing_closing_delimiter(self):
        content = "---\nname: test\n# No closing delimiter"
        result = extract_frontmatter(content)
        assert result is None

    def test_empty_frontmatter(self):
        content = "---\n---\n\nBody"
        result = extract_frontmatter(content)
        assert result is None

    def test_complex_frontmatter(self):
        content = "---\nname: my-agent\ndescription: A test agent\ntier: extension\ntriggers:\n  - keyword1\n  - keyword2\n---\n\n# Agent"
        result = extract_frontmatter(content)
        assert result["name"] == "my-agent"
        assert result["triggers"] == ["keyword1", "keyword2"]

    def test_invalid_yaml(self):
        content = "---\n: invalid: yaml: {[\n---\n\nBody"
        result = extract_frontmatter(content)
        assert result is None


# --- New tests for validate_file and main ---

from unittest.mock import MagicMock  # noqa: E402

from scripts.validate_schema import validate_file  # noqa: E402


class TestValidateFile:
    """Tests for validate_file."""

    def test_valid_file(self, tmp_path: Path):
        f = tmp_path / "agent.md"
        f.write_text("---\nname: test\ntier: core\n---\n\n# Body")

        # Create a mock validator that yields no errors
        mock_validator = MagicMock()
        mock_validator.iter_errors.return_value = []

        errors = validate_file(f, mock_validator)
        assert errors == []

    def test_no_frontmatter(self, tmp_path: Path):
        f = tmp_path / "bad.md"
        f.write_text("# No frontmatter here")

        mock_validator = MagicMock()
        errors = validate_file(f, mock_validator)
        assert len(errors) == 1
        assert "No valid frontmatter" in errors[0]

    def test_schema_validation_error(self, tmp_path: Path):
        f = tmp_path / "agent.md"
        f.write_text("---\nname: test\n---\n\n# Body")

        mock_error = MagicMock()
        mock_error.absolute_path = ["tier"]
        mock_error.message = "'tier' is a required property"

        mock_validator = MagicMock()
        mock_validator.iter_errors.return_value = [mock_error]

        errors = validate_file(f, mock_validator)
        assert len(errors) == 1
        assert "tier" in errors[0]

    def test_schema_error_at_root(self, tmp_path: Path):
        f = tmp_path / "agent.md"
        f.write_text("---\nname: test\n---\n\n# Body")

        mock_error = MagicMock()
        mock_error.absolute_path = []
        mock_error.message = "Some root error"

        mock_validator = MagicMock()
        mock_validator.iter_errors.return_value = [mock_error]

        errors = validate_file(f, mock_validator)
        assert len(errors) == 1
        assert "root" in errors[0]

    def test_unreadable_file(self, tmp_path: Path):
        f = tmp_path / "missing.md"  # doesn't exist

        mock_validator = MagicMock()
        errors = validate_file(f, mock_validator)
        assert len(errors) == 1
        assert "Failed to read" in errors[0]

    def test_verbose_prints_success(self, tmp_path: Path, capsys):
        f = tmp_path / "ok.md"
        f.write_text("---\nname: ok\n---\n\n# Body")

        mock_validator = MagicMock()
        mock_validator.iter_errors.return_value = []

        errors = validate_file(f, mock_validator, verbose=True)
        assert errors == []
        captured = capsys.readouterr()
        assert "ok.md" in captured.out


class TestValidateSchemaMain:
    """Tests for main() function."""

    def test_no_jsonschema_returns_zero(self, monkeypatch):
        monkeypatch.setattr("scripts.validate_schema.HAS_JSONSCHEMA", False)
        monkeypatch.setattr("sys.argv", ["validate_schema.py"])

        from scripts.validate_schema import main

        result = main()
        assert result == 0

    def test_missing_schema_file(self, monkeypatch, tmp_path: Path):
        monkeypatch.setattr("scripts.validate_schema.HAS_JSONSCHEMA", True)
        monkeypatch.setattr("scripts.validate_schema.SCHEMA_PATH", tmp_path / "missing.json")
        monkeypatch.setattr("sys.argv", ["validate_schema.py"])

        from scripts.validate_schema import main

        result = main()
        assert result == 2

    def test_invalid_schema_json(self, monkeypatch, tmp_path: Path):
        schema_file = tmp_path / "bad.json"
        schema_file.write_text("not json")

        monkeypatch.setattr("scripts.validate_schema.HAS_JSONSCHEMA", True)
        monkeypatch.setattr("scripts.validate_schema.SCHEMA_PATH", schema_file)
        monkeypatch.setattr("sys.argv", ["validate_schema.py"])

        from scripts.validate_schema import main

        result = main()
        assert result == 2

    def test_success_with_valid_agents(self, monkeypatch, tmp_path: Path):
        # Create a minimal schema
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        schema_file = tmp_path / "schema.json"
        schema_file.write_text(__import__("json").dumps(schema))

        # Create agent directory with a valid file
        agents_dir = tmp_path / "agents"
        core_dir = agents_dir / "core"
        core_dir.mkdir(parents=True)
        (core_dir / "test.md").write_text("---\nname: test\n---\n\n# Body")

        monkeypatch.setattr("scripts.validate_schema.HAS_JSONSCHEMA", True)
        monkeypatch.setattr("scripts.validate_schema.SCHEMA_PATH", schema_file)
        monkeypatch.setattr("scripts.validate_schema.AGENTS_DIR", agents_dir)
        monkeypatch.setattr("sys.argv", ["validate_schema.py"])

        # Need jsonschema installed for this test
        try:
            from jsonschema import Draft202012Validator  # noqa: F401

            from scripts.validate_schema import main

            result = main()
            assert result == 0
        except ImportError:
            pass  # Skip if jsonschema not installed
