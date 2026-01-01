"""Tests for /ask and /ask-multi skills.

TDD tests covering:
- Layer 1: Schema validation (file structure, frontmatter, sections)
- Layer 2: Behavioral tests (argument parsing, constraints)
"""

import re
from pathlib import Path

import pytest

from conftest import parse_skill_frontmatter, parse_skill_sections


# =============================================================================
# Layer 1: Schema Validation Tests - /ask skill
# =============================================================================


class TestAskSkillSchema:
    """Schema validation tests for /ask skill."""

    def test_skill_file_exists(self, ask_skill_path: Path) -> None:
        """Skill file should exist at expected location."""
        assert ask_skill_path.exists(), f"Expected {ask_skill_path} to exist"

    def test_has_yaml_frontmatter(self, ask_skill_path: Path) -> None:
        """Skill should have valid YAML frontmatter."""
        frontmatter = parse_skill_frontmatter(ask_skill_path)
        assert frontmatter, "Frontmatter should not be empty"
        assert "name" in frontmatter, "Frontmatter must have 'name'"
        assert "description" in frontmatter, "Frontmatter must have 'description'"

    def test_frontmatter_name_matches_directory(self, ask_skill_path: Path) -> None:
        """Frontmatter name should match directory name."""
        frontmatter = parse_skill_frontmatter(ask_skill_path)
        dir_name = ask_skill_path.parent.name
        assert frontmatter.get("name") == dir_name, (
            f"Frontmatter name '{frontmatter.get('name')}' "
            f"should match directory '{dir_name}'"
        )

    def test_has_required_sections(self, ask_skill_path: Path) -> None:
        """Skill should have required markdown sections."""
        sections = parse_skill_sections(ask_skill_path)
        required = ["Usage", "Instructions", "Examples"]
        for section in required:
            assert section in sections, f"Missing required section: ## {section}"

    def test_usage_section_not_empty(self, ask_skill_path: Path) -> None:
        """Usage section should contain content."""
        sections = parse_skill_sections(ask_skill_path)
        assert sections.get("Usage", "").strip(), "Usage section should not be empty"

    def test_instructions_section_not_empty(self, ask_skill_path: Path) -> None:
        """Instructions section should contain content."""
        sections = parse_skill_sections(ask_skill_path)
        assert sections.get("Instructions", "").strip(), (
            "Instructions section should not be empty"
        )


# =============================================================================
# Layer 1: Schema Validation Tests - /ask-multi skill
# =============================================================================


class TestAskMultiSkillSchema:
    """Schema validation tests for /ask-multi skill."""

    def test_skill_file_exists(self, ask_multi_skill_path: Path) -> None:
        """Skill file should exist at expected location."""
        assert ask_multi_skill_path.exists(), f"Expected {ask_multi_skill_path} to exist"

    def test_has_yaml_frontmatter(self, ask_multi_skill_path: Path) -> None:
        """Skill should have valid YAML frontmatter."""
        frontmatter = parse_skill_frontmatter(ask_multi_skill_path)
        assert frontmatter, "Frontmatter should not be empty"
        assert "name" in frontmatter, "Frontmatter must have 'name'"
        assert "description" in frontmatter, "Frontmatter must have 'description'"

    def test_frontmatter_name_matches_directory(
        self, ask_multi_skill_path: Path
    ) -> None:
        """Frontmatter name should match directory name."""
        frontmatter = parse_skill_frontmatter(ask_multi_skill_path)
        dir_name = ask_multi_skill_path.parent.name
        assert frontmatter.get("name") == dir_name, (
            f"Frontmatter name '{frontmatter.get('name')}' "
            f"should match directory '{dir_name}'"
        )

    def test_has_required_sections(self, ask_multi_skill_path: Path) -> None:
        """Skill should have required markdown sections."""
        sections = parse_skill_sections(ask_multi_skill_path)
        required = ["Usage", "Instructions", "Examples"]
        for section in required:
            assert section in sections, f"Missing required section: ## {section}"

    def test_description_mentions_multiselect(
        self, ask_multi_skill_path: Path
    ) -> None:
        """Description should mention multi-select capability."""
        frontmatter = parse_skill_frontmatter(ask_multi_skill_path)
        description = frontmatter.get("description", "").lower()
        assert "multi" in description, (
            "Description should mention multi-select capability"
        )


# =============================================================================
# Layer 2: Behavioral Tests - /ask skill
# =============================================================================


class TestAskSkillBehavior:
    """Behavioral tests for /ask skill argument parsing."""

    def test_instructions_mention_options_constraint(
        self, ask_skill_path: Path
    ) -> None:
        """Instructions should mention 2-4 options constraint."""
        sections = parse_skill_sections(ask_skill_path)
        instructions = sections.get("Instructions", "")
        constraints = sections.get("Constraints", "")
        combined = instructions + constraints
        
        # Should mention option limits
        assert "2" in combined or "two" in combined.lower(), (
            "Should mention minimum of 2 options"
        )
        assert "4" in combined or "four" in combined.lower(), (
            "Should mention maximum of 4 options"
        )

    def test_instructions_mention_multiselect_false(
        self, ask_skill_path: Path
    ) -> None:
        """Instructions should specify multiSelect: false."""
        sections = parse_skill_sections(ask_skill_path)
        instructions = sections.get("Instructions", "").lower()
        
        # Should mention multiSelect is false
        assert "multiselect" in instructions or "multi" in instructions, (
            "Should mention multiSelect setting"
        )
        assert "false" in instructions, "Should set multiSelect to false"

    def test_examples_show_valid_usage(self, ask_skill_path: Path) -> None:
        """Examples should demonstrate valid skill usage."""
        sections = parse_skill_sections(ask_skill_path)
        examples = sections.get("Examples", "")
        
        # Should have at least one example with /ask
        assert "/ask" in examples, "Examples should show /ask usage"
        
        # Should have quoted strings (question and options)
        assert '"' in examples, "Examples should use quoted arguments"


# =============================================================================
# Layer 2: Behavioral Tests - /ask-multi skill
# =============================================================================


class TestAskMultiSkillBehavior:
    """Behavioral tests for /ask-multi skill."""

    def test_instructions_mention_multiselect_true(
        self, ask_multi_skill_path: Path
    ) -> None:
        """Instructions should specify multiSelect: true."""
        sections = parse_skill_sections(ask_multi_skill_path)
        instructions = sections.get("Instructions", "").lower()
        
        # Should mention multiSelect is true
        assert "multiselect" in instructions or "multi" in instructions, (
            "Should mention multiSelect setting"
        )
        assert "true" in instructions, "Should set multiSelect to true"

    def test_examples_show_valid_usage(self, ask_multi_skill_path: Path) -> None:
        """Examples should demonstrate valid skill usage."""
        sections = parse_skill_sections(ask_multi_skill_path)
        examples = sections.get("Examples", "")
        
        # Should have at least one example with /ask-multi
        assert "/ask-multi" in examples, "Examples should show /ask-multi usage"


# =============================================================================
# Cross-skill consistency tests
# =============================================================================


class TestSkillConsistency:
    """Tests ensuring /ask and /ask-multi are consistent."""

    def test_both_skills_have_same_structure(
        self, ask_skill_path: Path, ask_multi_skill_path: Path
    ) -> None:
        """Both skills should have the same section structure."""
        ask_sections = set(parse_skill_sections(ask_skill_path).keys())
        multi_sections = set(parse_skill_sections(ask_multi_skill_path).keys())
        
        # Core sections should be the same
        core_sections = {"Usage", "Instructions", "Examples"}
        assert core_sections.issubset(ask_sections), "ask missing core sections"
        assert core_sections.issubset(multi_sections), "ask-multi missing core sections"

    def test_usage_syntax_is_parallel(
        self, ask_skill_path: Path, ask_multi_skill_path: Path
    ) -> None:
        """Usage syntax should be parallel between skills."""
        ask_usage = parse_skill_sections(ask_skill_path).get("Usage", "")
        multi_usage = parse_skill_sections(ask_multi_skill_path).get("Usage", "")
        
        # Both should show quoted arguments pattern
        assert '"Question"' in ask_usage or '"' in ask_usage
        assert '"Question"' in multi_usage or '"' in multi_usage
