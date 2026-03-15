"""
Integration tests for scripts/apply_type_hints.py

Tests protected paths, AST parsing, signature replacement,
and import injection. Uses subprocess-based testing with tempfile fixtures.

Run with: pytest tests/integration/test_apply_type_hints.py -v
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

PYTHON = sys.executable


class TestIsProtected:
    """Tests for protected path detection."""

    def test_protected_paths_blocked(self):
        """SuperClaude protected patterns are blocked."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.apply_type_hints import is_protected
assert is_protected("agents/core/architect.md") is True
assert is_protected("agents/traits/security-first.md") is True
assert is_protected(".claude/skills/sc-test/SKILL.md") is True
assert is_protected("CLAUDE.md") is True
assert is_protected("benchmarks/data.json") is True
assert is_protected(".github/workflows/ci.yml") is True
assert is_protected(".env") is True
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout

    def test_unprotected_paths_allowed(self):
        """Non-protected paths are allowed."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.apply_type_hints import is_protected
assert is_protected("scripts/validate_agents.py") is False
assert is_protected("tests/integration/test_foo.py") is False
assert is_protected("src/utils.py") is False
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout


class TestFindFunctionLine:
    """Tests for AST-based function line lookup."""

    def test_find_simple_function(self):
        """Finds function line number correctly."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.apply_type_hints import find_function_line
source = '''
def hello():
    pass

def world():
    return 42
'''
line = find_function_line(source, "world")
assert line == 5
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout

    def test_find_async_function(self):
        """Finds async function correctly."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.apply_type_hints import find_function_line
source = '''
async def fetch_data():
    pass
'''
line = find_function_line(source, "fetch_data")
assert line == 2
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout

    def test_find_nonexistent_function(self):
        """Returns None for nonexistent function."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.apply_type_hints import find_function_line
source = "def hello(): pass"
line = find_function_line(source, "nonexistent")
assert line is None
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout


class TestApplyTypeHints:
    """Tests for the full type hints application pipeline."""

    def test_apply_simple_type_hint(self):
        """Applies type hint to a simple function."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as py_file:
            py_file.write("def add(a, b):\n    return a + b\n")
            py_file.flush()
            py_path = py_file.name

        suggestions = {
            "functions_annotated": [
                {
                    "file": py_path,
                    "function": "add",
                    "typed_signature": "def add(a: int, b: int) -> int:",
                    "imports_needed": [],
                }
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as json_file:
            json.dump(suggestions, json_file)
            json_file.flush()
            json_path = json_file.name

        result = subprocess.run(
            [
                PYTHON,
                "-c",
                f"""
import sys; sys.path.insert(0, '.')
from scripts.apply_type_hints import apply_type_hints
result = apply_type_hints("{json_path}")
assert result["functions_applied"] == 1
assert result["files_modified"] == 1
assert result["files_reverted"] == 0

content = open("{py_path}").read()
assert "def add(a: int, b: int) -> int:" in content
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        Path(py_path).unlink()
        Path(json_path).unlink()
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "PASS" in result.stdout

    def test_inject_missing_imports(self):
        """Injects missing import statements."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as py_file:
            py_file.write("import os\n\ndef get_items():\n    return []\n")
            py_file.flush()
            py_path = py_file.name

        suggestions = {
            "functions_annotated": [
                {
                    "file": py_path,
                    "function": "get_items",
                    "typed_signature": "def get_items() -> list[str]:",
                    "imports_needed": ["from typing import Optional"],
                }
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as json_file:
            json.dump(suggestions, json_file)
            json_file.flush()
            json_path = json_file.name

        result = subprocess.run(
            [
                PYTHON,
                "-c",
                f"""
import sys; sys.path.insert(0, '.')
from scripts.apply_type_hints import apply_type_hints
result = apply_type_hints("{json_path}")
assert result["functions_applied"] == 1

content = open("{py_path}").read()
assert "from typing import Optional" in content
assert "def get_items() -> list[str]:" in content
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        Path(py_path).unlink()
        Path(json_path).unlink()
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "PASS" in result.stdout

    def test_async_function_preserved(self):
        """Async prefix is preserved when applying type hints."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as py_file:
            py_file.write("async def fetch():\n    return None\n")
            py_file.flush()
            py_path = py_file.name

        suggestions = {
            "functions_annotated": [
                {
                    "file": py_path,
                    "function": "fetch",
                    "typed_signature": "def fetch() -> str:",
                    "imports_needed": [],
                }
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as json_file:
            json.dump(suggestions, json_file)
            json_file.flush()
            json_path = json_file.name

        result = subprocess.run(
            [
                PYTHON,
                "-c",
                f"""
import sys; sys.path.insert(0, '.')
from scripts.apply_type_hints import apply_type_hints
result = apply_type_hints("{json_path}")
assert result["functions_applied"] == 1

content = open("{py_path}").read()
# Should have async prefix even though typed_signature didn't
assert "async def fetch() -> str:" in content
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        Path(py_path).unlink()
        Path(json_path).unlink()
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "PASS" in result.stdout
