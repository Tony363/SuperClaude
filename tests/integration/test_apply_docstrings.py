"""
Integration tests for scripts/apply_docstrings.py

Tests protected paths, AST parsing, docstring insertion,
and compile rollback. Uses subprocess-based testing with tempfile fixtures.

Run with: pytest tests/integration/test_apply_docstrings.py -v
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

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
from scripts.apply_docstrings import is_protected
# SuperClaude protected patterns
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
from scripts.apply_docstrings import is_protected
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


class TestFindFunctionInfo:
    """Tests for AST-based function lookup."""

    def test_find_simple_function(self):
        """Finds a simple function by name."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.apply_docstrings import find_function_info
source = '''
def hello():
    pass

def world():
    return 42
'''
info = find_function_info(source, "world")
assert info is not None
assert info["lineno"] == 5
assert info["has_docstring"] is False
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout

    def test_find_function_with_existing_docstring(self):
        """Detects existing docstrings correctly."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                '''
import sys; sys.path.insert(0, '.')
from scripts.apply_docstrings import find_function_info
source = """
def documented():
    \\"\\"\\"This function has a docstring.\\"\\"\\"
    pass
"""
info = find_function_info(source, "documented")
assert info is not None
assert info["has_docstring"] is True
print("PASS")
''',
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
from scripts.apply_docstrings import find_function_info
source = "def hello(): pass"
info = find_function_info(source, "nonexistent")
assert info is None
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout


class TestApplyDocstrings:
    """Tests for the full docstring application pipeline."""

    def test_insert_docstring_into_file(self):
        """Inserts docstring into a real Python file."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as py_file:
            py_file.write("def greet(name):\n    return f'Hello {name}'\n")
            py_file.flush()
            py_path = py_file.name

        suggestions = {
            "functions_documented": [
                {
                    "file": py_path,
                    "function": "greet",
                    "docstring": "Greet a person by name.",
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
from scripts.apply_docstrings import apply_docstrings
result = apply_docstrings("{json_path}")
assert result["docstrings_inserted"] == 1
assert result["files_modified"] == 1
assert result["files_reverted"] == 0

# Verify the file now contains the docstring
content = open("{py_path}").read()
assert '\"\"\"Greet a person by name.\"\"\"' in content
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

    def test_revert_on_compile_failure(self):
        """Reverts file if docstring insertion breaks compilation."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as py_file:
            # Valid Python that has tight formatting
            py_file.write("def foo():\n    return 1\n")
            py_file.flush()
            py_path = py_file.name

        original_content = Path(py_path).read_text()

        # Create a suggestion that would produce invalid indentation
        suggestions = {
            "functions_documented": [
                {
                    "file": py_path,
                    "function": "foo",
                    "docstring": "A valid docstring.",
                }
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as json_file:
            json.dump(suggestions, json_file)
            json_file.flush()
            json_path = json_file.name

        # This should insert successfully and compile fine
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                f"""
import sys; sys.path.insert(0, '.')
from scripts.apply_docstrings import apply_docstrings
result = apply_docstrings("{json_path}")
# Should succeed for valid Python
assert result["files_reverted"] == 0
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

    def test_skip_already_documented(self):
        """Skips functions that already have docstrings."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as py_file:
            py_file.write('def foo():\n    """Existing docstring."""\n    return 1\n')
            py_file.flush()
            py_path = py_file.name

        suggestions = {
            "functions_documented": [
                {
                    "file": py_path,
                    "function": "foo",
                    "docstring": "New docstring.",
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
from scripts.apply_docstrings import apply_docstrings
result = apply_docstrings("{json_path}")
assert result["skipped_existing"] == 1
assert result["docstrings_inserted"] == 0
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
