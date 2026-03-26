"""Tests for .github/scripts/apply-type-hints.py pure functions."""

import importlib
import json
import sys
from pathlib import Path

scripts_dir = str(Path(__file__).parent.parent.parent / ".github" / "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

mod = importlib.import_module("apply-type-hints")

is_protected = mod.is_protected
find_function_line = mod.find_function_line
find_def_end_line = mod.find_def_end_line
get_existing_imports = mod.get_existing_imports
find_last_import_line = mod.find_last_import_line
normalize_import = mod.normalize_import
apply_type_hints = mod.apply_type_hints


class TestIsProtected:
    """Tests for is_protected."""

    def test_github_scripts_protected(self):
        assert is_protected(".github/scripts/helper.py") is True

    def test_claude_dir_protected(self):
        assert is_protected(".claude/rules/test.md") is True

    def test_validate_agents_protected(self):
        assert is_protected("scripts/validate_agents.py") is True

    def test_regular_ok(self):
        assert is_protected("src/service.py") is False


class TestFindFunctionLine:
    """Tests for find_function_line."""

    def test_simple_function(self):
        source = "x = 1\ndef foo():\n    pass\n"
        assert find_function_line(source, "foo") == 2

    def test_async_function(self):
        source = "async def bar():\n    pass\n"
        assert find_function_line(source, "bar") == 1

    def test_not_found(self):
        source = "def foo(): pass\n"
        assert find_function_line(source, "bar") is None

    def test_syntax_error(self):
        source = "def incomplete("
        assert find_function_line(source, "incomplete") is None


class TestFindDefEndLine:
    """Tests for find_def_end_line."""

    def test_single_line(self):
        lines = ["def foo():\n", "    pass\n"]
        assert find_def_end_line(lines, 0) == 0

    def test_multiline_signature(self):
        lines = ["def foo(\n", "    a: int,\n", "    b: str,\n", ") -> None:\n", "    pass\n"]
        assert find_def_end_line(lines, 0) == 3


class TestGetExistingImports:
    """Tests for get_existing_imports."""

    def test_finds_imports(self):
        source = "import os\nfrom pathlib import Path\n\nx = 1"
        imports = get_existing_imports(source)
        assert "import os" in imports
        assert "from pathlib import Path" in imports
        assert len(imports) == 2

    def test_no_imports(self):
        source = "x = 1\ny = 2"
        imports = get_existing_imports(source)
        assert imports == set()


class TestFindLastImportLine:
    """Tests for find_last_import_line."""

    def test_finds_last(self):
        lines = ["import os\n", "from sys import path\n", "\n", "x = 1\n"]
        assert find_last_import_line(lines) == 1

    def test_no_imports(self):
        lines = ["x = 1\n", "y = 2\n"]
        assert find_last_import_line(lines) == -1


class TestNormalizeImport:
    """Tests for normalize_import."""

    def test_strips_whitespace(self):
        result = normalize_import("  from typing import Any  ")
        assert result == ["from typing import Any"]


class TestApplyTypeHints:
    """Tests for apply_type_hints integration."""

    def test_empty_suggestions(self, tmp_path: Path):
        p = tmp_path / "suggestions.json"
        p.write_text(json.dumps({"functions_annotated": []}))

        result = apply_type_hints(str(p))
        assert result["files_modified"] == 0
        assert result["functions_applied"] == 0

    def test_applies_hint_to_file(self, tmp_path: Path):
        target = tmp_path / "target.py"
        target.write_text("def greet(name):\n    return f'hello {name}'\n")

        suggestions = {
            "functions_annotated": [
                {
                    "file": str(target),
                    "function": "greet",
                    "typed_signature": "def greet(name: str) -> str:",
                    "imports_needed": [],
                }
            ]
        }
        p = tmp_path / "suggestions.json"
        p.write_text(json.dumps(suggestions))

        result = apply_type_hints(str(p))
        assert result["functions_applied"] == 1

        modified = target.read_text()
        assert "name: str" in modified
        assert "-> str" in modified
