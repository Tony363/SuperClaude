"""Tests for the sc-worktree skill."""

import re
from pathlib import Path
from typing import Any

import pytest


def parse_skill_frontmatter(skill_path: Path) -> dict[str, Any]:
    """Parse YAML frontmatter from a skill file (simplified, no yaml dependency)."""
    content = skill_path.read_text()
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}

    # Simple key: value parsing without yaml library
    frontmatter = {}
    for line in match.group(1).strip().split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()
    return frontmatter


def parse_skill_sections(skill_path: Path) -> dict[str, str]:
    """Parse markdown sections from a skill file."""
    content = skill_path.read_text()
    content = re.sub(r"^---\n.*?\n---\n", "", content, flags=re.DOTALL)

    sections = {}
    current_header = None
    current_content = []

    for line in content.split("\n"):
        if line.startswith("## "):
            if current_header:
                sections[current_header] = "\n".join(current_content).strip()
            current_header = line[3:].strip()
            current_content = []
        elif line.startswith("# "):
            if current_header:
                sections[current_header] = "\n".join(current_content).strip()
            current_header = "_title"
            current_content = [line[2:].strip()]
        elif current_header:
            current_content.append(line)

    if current_header:
        sections[current_header] = "\n".join(current_content).strip()

    return sections


@pytest.fixture
def skill_root() -> Path:
    """Return the path to the skills directory."""
    return Path(__file__).parent.parent.parent / ".claude" / "skills"


@pytest.fixture
def worktree_skill_path(skill_root: Path) -> Path:
    """Return path to sc-worktree skill."""
    return skill_root / "sc-worktree" / "SKILL.md"


class TestWorktreeSkillStructure:
    """Test that sc-worktree skill has required structure."""

    def test_skill_file_exists(self, worktree_skill_path: Path):
        """Verify SKILL.md exists."""
        assert worktree_skill_path.exists(), f"SKILL.md not found at {worktree_skill_path}"

    def test_frontmatter_has_required_fields(self, worktree_skill_path: Path):
        """Verify frontmatter has name and description."""
        frontmatter = parse_skill_frontmatter(worktree_skill_path)

        assert "name" in frontmatter, "Missing 'name' in frontmatter"
        assert frontmatter["name"] == "sc-worktree", f"Expected name 'sc-worktree', got '{frontmatter['name']}'"

        assert "description" in frontmatter, "Missing 'description' in frontmatter"
        assert len(frontmatter["description"]) > 20, "Description too short"

    def test_has_required_sections(self, worktree_skill_path: Path):
        """Verify skill has all required sections."""
        sections = parse_skill_sections(worktree_skill_path)

        required_sections = [
            "Quick Start",
            "Behavioral Flow",
            "Commands",
            "Flags",
            "Examples",
        ]

        for section in required_sections:
            assert section in sections, f"Missing required section: {section}"

    def test_quick_start_has_commands(self, worktree_skill_path: Path):
        """Verify Quick Start section shows example commands."""
        # Read full content since code blocks with # comments confuse section parser
        content = worktree_skill_path.read_text()

        # Check that Quick Start exists and has the expected commands
        assert "## Quick Start" in content, "Should have Quick Start section"
        assert "/sc:worktree create" in content, "Quick Start should show create command"
        assert "/sc:worktree list" in content, "Quick Start should show list command"
        assert "/sc:worktree cleanup" in content, "Quick Start should show cleanup command"


class TestWorktreeCommands:
    """Test that worktree commands are properly documented."""

    def test_create_command_documented(self, worktree_skill_path: Path):
        """Verify create command is documented."""
        content = worktree_skill_path.read_text()

        assert "create <task-id>" in content.lower() or "create `<task-id>`" in content.lower(), \
            "Create command should be documented"
        assert "git worktree add" in content, "Create should mention git worktree add"

    def test_cleanup_command_documented(self, worktree_skill_path: Path):
        """Verify cleanup command is documented."""
        content = worktree_skill_path.read_text()

        assert "cleanup" in content.lower(), "Cleanup command should be documented"
        assert "git worktree remove" in content or "git worktree prune" in content, \
            "Cleanup should mention git worktree remove/prune"

    def test_propose_command_documented(self, worktree_skill_path: Path):
        """Verify propose command is documented."""
        content = worktree_skill_path.read_text()

        assert "propose" in content.lower(), "Propose command should be documented"
        assert "pr" in content.lower() or "pull request" in content.lower(), \
            "Propose should mention PR creation"


class TestWorktreeNamingConvention:
    """Test that naming convention is properly documented."""

    def test_worktree_path_convention(self, worktree_skill_path: Path):
        """Verify worktree path naming convention is documented."""
        content = worktree_skill_path.read_text()

        # Should document the path convention
        assert ".worktrees/" in content, "Should document .worktrees/ directory"

    def test_branch_naming_convention(self, worktree_skill_path: Path):
        """Verify branch naming convention is documented."""
        content = worktree_skill_path.read_text()

        # Should document the wt/ prefix for branches
        assert "wt/" in content, "Should document wt/ branch prefix"


class TestWorktreeSafetyGuarantees:
    """Test that safety guarantees are documented."""

    def test_no_auto_merge_documented(self, worktree_skill_path: Path):
        """Verify no auto-merge policy is documented."""
        content = worktree_skill_path.read_text().lower()

        # Should explicitly mention no auto-merge
        assert "no auto-merge" in content or "human review" in content, \
            "Should document no auto-merge / human review policy"

    def test_isolation_documented(self, worktree_skill_path: Path):
        """Verify isolation is documented."""
        content = worktree_skill_path.read_text().lower()

        assert "isolation" in content or "isolated" in content, \
            "Should document worktree isolation"


class TestWorktreeMCPIntegration:
    """Test that MCP integration is documented."""

    def test_pal_mcp_documented(self, worktree_skill_path: Path):
        """Verify PAL MCP integration is documented."""
        content = worktree_skill_path.read_text()

        assert "PAL MCP" in content or "mcp__pal" in content, \
            "Should document PAL MCP integration"

    def test_rube_mcp_documented(self, worktree_skill_path: Path):
        """Verify Rube MCP integration is documented."""
        content = worktree_skill_path.read_text()

        assert "Rube MCP" in content or "mcp__rube" in content, \
            "Should document Rube MCP integration"
