"""Tests for the /sc:cicd-setup command generator."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Add the skills script to path
sys.path.insert(
    0, str(Path(__file__).parent.parent.parent / ".claude/skills/sc-cicd-setup/scripts")
)

from generate_workflows import (
    check_conflicts,
    detect_main_branch,
    detect_project_type,
    get_template_context,
    get_templates_to_generate,
)


class TestDetectProjectType:
    """Unit tests for project type detection."""

    def test_detect_python_pyproject(self, tmp_path: Path) -> None:
        """Detect Python project from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'")
        assert detect_project_type(tmp_path) == "python"

    def test_detect_python_requirements(self, tmp_path: Path) -> None:
        """Detect Python project from requirements.txt."""
        (tmp_path / "requirements.txt").write_text("requests>=2.0")
        assert detect_project_type(tmp_path) == "python"

    def test_detect_python_setup_py(self, tmp_path: Path) -> None:
        """Detect Python project from setup.py."""
        (tmp_path / "setup.py").write_text("from setuptools import setup")
        assert detect_project_type(tmp_path) == "python"

    def test_detect_node(self, tmp_path: Path) -> None:
        """Detect Node.js project from package.json."""
        (tmp_path / "package.json").write_text('{"name": "test"}')
        assert detect_project_type(tmp_path) == "node"

    def test_detect_go(self, tmp_path: Path) -> None:
        """Detect Go project from go.mod."""
        (tmp_path / "go.mod").write_text("module example.com/test\n\ngo 1.21")
        assert detect_project_type(tmp_path) == "go"

    def test_detect_rust(self, tmp_path: Path) -> None:
        """Detect Rust project from Cargo.toml."""
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"')
        assert detect_project_type(tmp_path) == "rust"

    def test_detect_none(self, tmp_path: Path) -> None:
        """Return None for empty directory."""
        assert detect_project_type(tmp_path) is None

    def test_detect_priority_python_over_node(self, tmp_path: Path) -> None:
        """Python takes priority when multiple manifests exist."""
        (tmp_path / "pyproject.toml").write_text("[project]")
        (tmp_path / "package.json").write_text("{}")
        # Python is checked first in the detector order
        assert detect_project_type(tmp_path) == "python"


class TestDetectMainBranch:
    """Unit tests for main branch detection."""

    def test_detect_from_git_head(self, tmp_path: Path) -> None:
        """Detect branch from .git/HEAD file."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/main")
        assert detect_main_branch(tmp_path) == "main"

    def test_detect_master_branch(self, tmp_path: Path) -> None:
        """Detect master branch from .git/HEAD."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/master")
        assert detect_main_branch(tmp_path) == "master"

    def test_detect_custom_branch(self, tmp_path: Path) -> None:
        """Detect custom branch name."""
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        (git_dir / "HEAD").write_text("ref: refs/heads/develop")
        assert detect_main_branch(tmp_path) == "develop"

    def test_default_to_main(self, tmp_path: Path) -> None:
        """Default to 'main' when no git directory."""
        assert detect_main_branch(tmp_path) == "main"


class TestGetTemplatesToGenerate:
    """Unit tests for template selection."""

    def test_default_templates(self) -> None:
        """Default mode generates ci, security, ai-review, pre-commit."""
        templates = get_templates_to_generate("python", minimal=False, full=False)
        output_files = [t[1] for t in templates]
        assert ".github/workflows/ci.yml" in output_files
        assert ".github/workflows/security.yml" in output_files
        assert ".github/workflows/ai-review.yml" in output_files
        assert ".pre-commit-config.yaml" in output_files
        assert ".github/workflows/publish.yml" not in output_files

    def test_minimal_templates(self) -> None:
        """Minimal mode generates only ci workflow."""
        templates = get_templates_to_generate("python", minimal=True, full=False)
        output_files = [t[1] for t in templates]
        assert output_files == [".github/workflows/ci.yml"]

    def test_full_templates(self) -> None:
        """Full mode includes publish workflow."""
        templates = get_templates_to_generate("python", minimal=False, full=True)
        output_files = [t[1] for t in templates]
        assert ".github/workflows/ci.yml" in output_files
        assert ".github/workflows/publish.yml" in output_files


class TestCheckConflicts:
    """Unit tests for conflict detection."""

    def test_no_conflicts(self, tmp_path: Path) -> None:
        """No conflicts in empty directory."""
        conflicts = check_conflicts(tmp_path, [".github/workflows/ci.yml"])
        assert conflicts == []

    def test_detects_existing_file(self, tmp_path: Path) -> None:
        """Detects existing workflow file."""
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("name: CI")

        conflicts = check_conflicts(tmp_path, [".github/workflows/ci.yml"])
        assert ".github/workflows/ci.yml" in conflicts

    def test_multiple_conflicts(self, tmp_path: Path) -> None:
        """Detects multiple conflicts."""
        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yml").write_text("name: CI")
        (workflows / "security.yml").write_text("name: Security")

        conflicts = check_conflicts(
            tmp_path,
            [".github/workflows/ci.yml", ".github/workflows/security.yml", ".github/workflows/ai-review.yml"]
        )
        assert len(conflicts) == 2
        assert ".github/workflows/ci.yml" in conflicts
        assert ".github/workflows/security.yml" in conflicts


class TestGetTemplateContext:
    """Unit tests for context building."""

    def test_python_context_defaults(self, tmp_path: Path) -> None:
        """Python context has correct defaults."""
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'myproject'")
        context = get_template_context(tmp_path, "python")

        assert context["project_name"] == tmp_path.name
        assert context["main_branch"] == "main"
        assert "python_versions" in context
        assert "3.10" in context["python_versions"]

    def test_node_context_defaults(self, tmp_path: Path) -> None:
        """Node.js context has correct defaults."""
        (tmp_path / "package.json").write_text('{"name": "myapp"}')
        context = get_template_context(tmp_path, "node")

        assert "node_versions" in context
        assert context["package_manager"] == "npm"

    def test_node_detects_yarn(self, tmp_path: Path) -> None:
        """Detects yarn from lock file."""
        (tmp_path / "package.json").write_text('{"name": "myapp"}')
        (tmp_path / "yarn.lock").write_text("")
        context = get_template_context(tmp_path, "node")

        assert context["package_manager"] == "yarn"

    def test_node_detects_pnpm(self, tmp_path: Path) -> None:
        """Detects pnpm from lock file."""
        (tmp_path / "package.json").write_text('{"name": "myapp"}')
        (tmp_path / "pnpm-lock.yaml").write_text("")
        context = get_template_context(tmp_path, "node")

        assert context["package_manager"] == "pnpm"
