"""Tests for .github/scripts/apply-docstrings.py pure functions."""

import importlib
import json
import sys
from pathlib import Path

scripts_dir = str(Path(__file__).parent.parent.parent / ".github" / "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

mod = importlib.import_module("apply-docstrings")

is_protected = mod.is_protected
find_function_info = mod.find_function_info
find_def_end_line = mod.find_def_end_line
get_body_indent = mod.get_body_indent
format_docstring = mod.format_docstring
apply_docstrings = mod.apply_docstrings


class TestIsProtected:
    """Tests for is_protected."""

    def test_workflow_protected(self):
        assert is_protected(".github/workflows/ci.yml") is True

    def test_agents_protected(self):
        assert is_protected("agents/core/dev.md") is True

    def test_regular_ok(self):
        assert is_protected("src/main.py") is False


class TestFindFunctionInfo:
    """Tests for find_function_info."""

    def test_finds_simple_function(self):
        source = "def foo():\n    pass\n"
        info = find_function_info(source, "foo")
        assert info is not None
        assert info["lineno"] == 1
        assert info["has_docstring"] is False

    def test_finds_function_with_docstring(self):
        source = 'def bar():\n    """Hello."""\n    pass\n'
        info = find_function_info(source, "bar")
        assert info is not None
        assert info["has_docstring"] is True

    def test_finds_async_function(self):
        source = "async def baz():\n    pass\n"
        info = find_function_info(source, "baz")
        assert info is not None
        assert info["lineno"] == 1

    def test_returns_none_for_missing(self):
        source = "def foo():\n    pass\n"
        info = find_function_info(source, "nonexistent")
        assert info is None

    def test_returns_none_for_syntax_error(self):
        source = "def foo(:\n    broken syntax"
        info = find_function_info(source, "foo")
        assert info is None


class TestFindDefEndLine:
    """Tests for find_def_end_line."""

    def test_single_line_def(self):
        lines = ["def foo():\n", "    pass\n"]
        assert find_def_end_line(lines, 0) == 0

    def test_multiline_def(self):
        lines = [
            "def foo(\n",
            "    x,\n",
            "    y,\n",
            "):\n",
            "    pass\n",
        ]
        assert find_def_end_line(lines, 0) == 3


class TestGetBodyIndent:
    """Tests for get_body_indent."""

    def test_standard_indent(self):
        lines = ["def foo():\n", "    pass\n"]
        indent = get_body_indent(lines, 0)
        assert indent == "    "

    def test_nested_indent(self):
        lines = ["class X:\n", "    def foo():\n", "        pass\n"]
        indent = get_body_indent(lines, 1)
        assert indent == "        "


class TestFormatDocstring:
    """Tests for format_docstring."""

    def test_single_line(self):
        result = format_docstring("Short summary.", "    ")
        assert len(result) == 1
        assert result[0] == '    """Short summary."""\n'

    def test_multi_line(self):
        result = format_docstring("Summary.\n\nArgs:\n    x: value", "    ")
        assert result[0] == '    """Summary.\n'
        assert result[-1] == '    """\n'


class TestApplyDocstrings:
    """Tests for apply_docstrings integration."""

    def test_empty_suggestions(self, tmp_path: Path):
        p = tmp_path / "suggestions.json"
        p.write_text(json.dumps({"functions_documented": []}))

        result = apply_docstrings(str(p))
        assert result["files_modified"] == 0
        assert result["docstrings_inserted"] == 0

    def test_applies_docstring_to_file(self, tmp_path: Path):
        # Create target file
        target = tmp_path / "target.py"
        target.write_text("def greet():\n    return 'hello'\n")

        suggestions = {
            "functions_documented": [
                {
                    "file": str(target),
                    "function": "greet",
                    "docstring": "Return a greeting.",
                }
            ]
        }
        p = tmp_path / "suggestions.json"
        p.write_text(json.dumps(suggestions))

        result = apply_docstrings(str(p))
        assert result["docstrings_inserted"] == 1
        assert result["files_modified"] == 1

        modified = target.read_text()
        assert '"""Return a greeting."""' in modified

    def test_skips_existing_docstring(self, tmp_path: Path):
        target = tmp_path / "target.py"
        target.write_text('def greet():\n    """Existing."""\n    return "hello"\n')

        suggestions = {
            "functions_documented": [
                {
                    "file": str(target),
                    "function": "greet",
                    "docstring": "New docstring.",
                }
            ]
        }
        p = tmp_path / "suggestions.json"
        p.write_text(json.dumps(suggestions))

        result = apply_docstrings(str(p))
        assert result["skipped_existing"] == 1
        assert result["docstrings_inserted"] == 0
