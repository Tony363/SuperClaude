"""Tests for scripts/validate_agents.py - Agent frontmatter validator.

Covers:
- extract_frontmatter: YAML parsing from markdown content
- ValidationResult: result accumulator class
- validate_name: name field validation
- validate_description: description field validation
- validate_tier: tier field validation
- validate_triggers: triggers field validation
- validate_tools: tools field validation
- validate_priority: priority field validation
- validate_traits_field: traits field validation
- validate_category: category field validation
- validate_file: single-file validation orchestrator
- validate_uniqueness: cross-file duplicate name detection
- validate_trait_references: cross-file trait reference validation
- find_agent_files: agent file discovery
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.validate_agents import (
    VALID_TIERS,
    VALID_TOOLS,
    ValidationResult,
    extract_frontmatter,
    find_agent_files,
    validate_category,
    validate_description,
    validate_file,
    validate_name,
    validate_priority,
    validate_tier,
    validate_tools,
    validate_trait_references,
    validate_traits_field,
    validate_triggers,
    validate_uniqueness,
)

# =============================================================================
# Helpers
# =============================================================================


def _make_result(tier: str | None = None, name: str | None = None) -> ValidationResult:
    """Create a ValidationResult with optional pre-set tier and name."""
    result = ValidationResult(Path("test.md"))
    result.tier = tier
    result.name = name
    return result


def _wrap_frontmatter(yaml_body: str) -> str:
    """Wrap YAML content in markdown frontmatter delimiters."""
    return f"---\n{yaml_body}\n---\n\nBody content here.\n"


# =============================================================================
# extract_frontmatter
# =============================================================================


class TestExtractFrontmatter:
    """Tests for extract_frontmatter()."""

    def test_valid_frontmatter_returns_dict(self):
        # Arrange
        content = _wrap_frontmatter("name: architect\ntier: core")

        # Act
        fm, error = extract_frontmatter(content)

        # Assert
        assert fm == {"name": "architect", "tier": "core"}
        assert error is None

    def test_valid_frontmatter_with_list_field(self):
        # Arrange
        content = _wrap_frontmatter("name: dev\ntriggers:\n  - build\n  - create")

        # Act
        fm, error = extract_frontmatter(content)

        # Assert
        assert fm["triggers"] == ["build", "create"]
        assert error is None

    def test_no_opening_delimiter_returns_error(self):
        # Arrange
        content = "name: architect\ntier: core\n---\n\nBody.\n"

        # Act
        fm, error = extract_frontmatter(content)

        # Assert
        assert fm is None
        assert "does not start with" in error

    def test_no_closing_delimiter_returns_error(self):
        # Arrange
        content = "---\nname: architect\ntier: core\nno closing"

        # Act
        fm, error = extract_frontmatter(content)

        # Assert
        assert fm is None
        assert "closing" in error.lower()

    def test_invalid_yaml_returns_error(self):
        # Arrange
        content = "---\n[invalid: yaml: : :\n---\n\nBody.\n"

        # Act
        fm, error = extract_frontmatter(content)

        # Assert
        assert fm is None
        assert "YAML parse error" in error

    def test_non_dict_frontmatter_returns_error(self):
        # Arrange -- YAML list instead of dict
        content = "---\n- item1\n- item2\n---\n\nBody.\n"

        # Act
        fm, error = extract_frontmatter(content)

        # Assert
        assert fm is None
        assert "not a dictionary" in error

    def test_empty_frontmatter_block(self):
        # Arrange -- empty YAML between delimiters yields None from safe_load
        content = "---\n\n---\n\nBody.\n"

        # Act
        fm, error = extract_frontmatter(content)

        # Assert
        # safe_load("") returns None, which is not a dict
        assert fm is None
        assert "not a dictionary" in error

    def test_frontmatter_with_complex_types(self):
        # Arrange
        yaml_body = "name: test\nnested:\n  key1: val1\n  key2: val2\ncount: 42"
        content = _wrap_frontmatter(yaml_body)

        # Act
        fm, error = extract_frontmatter(content)

        # Assert
        assert error is None
        assert fm["nested"] == {"key1": "val1", "key2": "val2"}
        assert fm["count"] == 42

    def test_frontmatter_with_trailing_whitespace_on_closing(self):
        # Arrange -- closing --- with trailing spaces
        content = "---\nname: test\n---   \n\nBody.\n"

        # Act
        fm, error = extract_frontmatter(content)

        # Assert
        assert error is None
        assert fm["name"] == "test"

    def test_string_only_frontmatter(self):
        # Arrange -- bare string YAML
        content = "---\njust a string\n---\n\nBody.\n"

        # Act
        fm, error = extract_frontmatter(content)

        # Assert
        assert fm is None
        assert "not a dictionary" in error


# =============================================================================
# ValidationResult
# =============================================================================


class TestValidationResult:
    """Tests for the ValidationResult class."""

    def test_init_defaults(self):
        # Arrange / Act
        result = ValidationResult(Path("agents/core/architect.md"))

        # Assert
        assert result.filepath == Path("agents/core/architect.md")
        assert result.errors == []
        assert result.warnings == []
        assert result.name is None
        assert result.tier is None
        assert result.traits == []

    def test_add_error(self):
        # Arrange
        result = ValidationResult(Path("test.md"))

        # Act
        result.add_error("something broke")

        # Assert
        assert result.errors == ["something broke"]
        assert result.has_errors is True

    def test_add_warning(self):
        # Arrange
        result = ValidationResult(Path("test.md"))

        # Act
        result.add_warning("heads up")

        # Assert
        assert result.warnings == ["heads up"]
        assert result.has_warnings is True

    def test_has_errors_false_when_empty(self):
        result = ValidationResult(Path("test.md"))
        assert result.has_errors is False

    def test_has_warnings_false_when_empty(self):
        result = ValidationResult(Path("test.md"))
        assert result.has_warnings is False

    def test_multiple_errors_and_warnings(self):
        # Arrange
        result = ValidationResult(Path("test.md"))

        # Act
        result.add_error("err1")
        result.add_error("err2")
        result.add_warning("warn1")

        # Assert
        assert len(result.errors) == 2
        assert len(result.warnings) == 1
        assert result.has_errors is True
        assert result.has_warnings is True


# =============================================================================
# validate_name
# =============================================================================


class TestValidateName:
    """Tests for validate_name()."""

    def test_valid_simple_name(self):
        # Arrange
        fm = {"name": "architect"}
        result = _make_result()

        # Act
        validate_name(fm, result)

        # Assert
        assert result.name == "architect"
        assert not result.has_errors

    def test_valid_hyphenated_name(self):
        fm = {"name": "typescript-react-expert"}
        result = _make_result()

        validate_name(fm, result)

        assert result.name == "typescript-react-expert"
        assert not result.has_errors

    def test_valid_name_with_numbers(self):
        fm = {"name": "agent2"}
        result = _make_result()

        validate_name(fm, result)

        assert result.name == "agent2"
        assert not result.has_errors

    def test_valid_single_char_name(self):
        # Arrange -- NAME_PATTERN allows single char via |^[a-z]$
        fm = {"name": "a"}
        result = _make_result()

        # Act
        validate_name(fm, result)

        # Assert
        assert result.name == "a"
        assert not result.has_errors

    def test_missing_name_is_error(self):
        fm = {}
        result = _make_result()

        validate_name(fm, result)

        assert result.has_errors
        assert "Missing required field" in result.errors[0]
        assert result.name is None

    def test_empty_string_name_is_error(self):
        fm = {"name": ""}
        result = _make_result()

        validate_name(fm, result)

        assert result.has_errors
        assert "Missing required field" in result.errors[0]

    def test_none_name_is_error(self):
        fm = {"name": None}
        result = _make_result()

        validate_name(fm, result)

        assert result.has_errors

    def test_non_string_name_is_error(self):
        fm = {"name": 42}
        result = _make_result()

        validate_name(fm, result)

        assert result.has_errors
        assert "must be a string" in result.errors[0]

    def test_uppercase_name_gets_normalized(self):
        fm = {"name": "MyAgent"}
        result = _make_result()

        validate_name(fm, result)

        # The regex requires lowercase after normalization
        # "myagent" should match the pattern
        assert result.name == "myagent"
        assert not result.has_errors

    def test_name_with_leading_spaces_gets_stripped(self):
        fm = {"name": "  architect  "}
        result = _make_result()

        validate_name(fm, result)

        assert result.name == "architect"
        assert not result.has_errors

    def test_name_starting_with_hyphen_is_error(self):
        fm = {"name": "-bad-name"}
        result = _make_result()

        validate_name(fm, result)

        assert result.has_errors
        assert "lowercase alphanumeric" in result.errors[0]

    def test_name_ending_with_hyphen_is_error(self):
        fm = {"name": "bad-name-"}
        result = _make_result()

        validate_name(fm, result)

        assert result.has_errors

    def test_name_with_underscores_is_error(self):
        fm = {"name": "bad_name"}
        result = _make_result()

        validate_name(fm, result)

        assert result.has_errors

    def test_name_with_special_chars_is_error(self):
        fm = {"name": "bad@name!"}
        result = _make_result()

        validate_name(fm, result)

        assert result.has_errors

    def test_name_starting_with_number_is_error(self):
        fm = {"name": "1agent"}
        result = _make_result()

        validate_name(fm, result)

        assert result.has_errors


# =============================================================================
# validate_description
# =============================================================================


class TestValidateDescription:
    """Tests for validate_description()."""

    def test_valid_description(self):
        fm = {"description": "A helpful agent for code review"}
        result = _make_result()

        validate_description(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_missing_description_is_error(self):
        fm = {}
        result = _make_result()

        validate_description(fm, result)

        assert result.has_errors
        assert "Missing required field" in result.errors[0]

    def test_empty_description_is_error(self):
        fm = {"description": ""}
        result = _make_result()

        validate_description(fm, result)

        assert result.has_errors

    def test_none_description_is_error(self):
        fm = {"description": None}
        result = _make_result()

        validate_description(fm, result)

        assert result.has_errors

    def test_non_string_description_is_error(self):
        fm = {"description": 123}
        result = _make_result()

        validate_description(fm, result)

        assert result.has_errors
        assert "must be a string" in result.errors[0]

    def test_description_over_200_chars_is_warning(self):
        fm = {"description": "x" * 201}
        result = _make_result()

        validate_description(fm, result)

        assert not result.has_errors
        assert result.has_warnings
        assert "exceeds 200 chars" in result.warnings[0]

    def test_description_exactly_200_chars_no_warning(self):
        fm = {"description": "x" * 200}
        result = _make_result()

        validate_description(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_description_at_199_chars_no_warning(self):
        fm = {"description": "y" * 199}
        result = _make_result()

        validate_description(fm, result)

        assert not result.has_warnings


# =============================================================================
# validate_tier
# =============================================================================


class TestValidateTier:
    """Tests for validate_tier()."""

    @pytest.mark.parametrize("tier", sorted(VALID_TIERS))
    def test_valid_tiers(self, tier):
        fm = {"tier": tier}
        result = _make_result()

        validate_tier(fm, result)

        assert result.tier == tier
        assert not result.has_errors

    def test_missing_tier_is_error(self):
        fm = {}
        result = _make_result()

        validate_tier(fm, result)

        assert result.has_errors
        assert "Missing required field" in result.errors[0]

    def test_empty_tier_is_error(self):
        fm = {"tier": ""}
        result = _make_result()

        validate_tier(fm, result)

        assert result.has_errors

    def test_none_tier_is_error(self):
        fm = {"tier": None}
        result = _make_result()

        validate_tier(fm, result)

        assert result.has_errors

    def test_invalid_tier_value_is_error(self):
        fm = {"tier": "premium"}
        result = _make_result()

        validate_tier(fm, result)

        assert result.has_errors
        assert "premium" in result.errors[0]

    def test_invalid_tier_includes_valid_options(self):
        fm = {"tier": "invalid"}
        result = _make_result()

        validate_tier(fm, result)

        # The error message should mention the valid set
        assert result.has_errors
        for valid in VALID_TIERS:
            assert valid in result.errors[0]

    def test_tier_case_sensitive(self):
        # "Core" with capital C is not in VALID_TIERS
        fm = {"tier": "Core"}
        result = _make_result()

        validate_tier(fm, result)

        assert result.has_errors


# =============================================================================
# validate_triggers
# =============================================================================


class TestValidateTriggers:
    """Tests for validate_triggers()."""

    def test_valid_triggers_for_core(self):
        fm = {"triggers": ["build", "create", "implement"]}
        result = _make_result(tier="core")

        validate_triggers(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_valid_triggers_for_extension(self):
        fm = {"triggers": ["python", "django"]}
        result = _make_result(tier="extension")

        validate_triggers(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_missing_triggers_for_core_is_warning(self):
        fm = {}
        result = _make_result(tier="core")

        validate_triggers(fm, result)

        assert not result.has_errors
        assert result.has_warnings
        assert "recommended" in result.warnings[0]

    def test_empty_triggers_list_is_warning(self):
        fm = {"triggers": []}
        result = _make_result(tier="core")

        validate_triggers(fm, result)

        assert not result.has_errors
        assert result.has_warnings
        assert "triggers" in result.warnings[0].lower()

    def test_triggers_not_a_list_is_error(self):
        fm = {"triggers": "build"}
        result = _make_result(tier="core")

        validate_triggers(fm, result)

        assert result.has_errors
        assert "must be a list" in result.errors[0]

    def test_trait_with_triggers_is_warning(self):
        fm = {"triggers": ["something"]}
        result = _make_result(tier="trait")

        validate_triggers(fm, result)

        assert not result.has_errors
        assert result.has_warnings
        assert "should not define" in result.warnings[0]

    def test_trait_without_triggers_is_clean(self):
        fm = {}
        result = _make_result(tier="trait")

        validate_triggers(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_trait_with_empty_triggers_no_warning(self):
        # Empty list has len 0, so the `if triggers and len(triggers) > 0` is False
        fm = {"triggers": []}
        result = _make_result(tier="trait")

        validate_triggers(fm, result)

        assert not result.has_warnings

    def test_none_triggers_for_core_is_warning(self):
        fm = {"triggers": None}
        result = _make_result(tier="core")

        validate_triggers(fm, result)

        assert not result.has_errors
        assert result.has_warnings


# =============================================================================
# validate_tools
# =============================================================================


class TestValidateTools:
    """Tests for validate_tools()."""

    def test_valid_tools(self):
        fm = {"tools": ["Read", "Write", "Bash"]}
        result = _make_result()

        validate_tools(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_all_valid_tools_accepted(self):
        fm = {"tools": list(VALID_TOOLS)}
        result = _make_result()

        validate_tools(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_missing_tools_is_ok(self):
        fm = {}
        result = _make_result()

        validate_tools(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_none_tools_is_ok(self):
        fm = {"tools": None}
        result = _make_result()

        validate_tools(fm, result)

        assert not result.has_errors

    def test_empty_tools_list_is_ok(self):
        # Empty list is falsy, so function returns early
        fm = {"tools": []}
        result = _make_result()

        validate_tools(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_tools_not_a_list_is_error(self):
        fm = {"tools": "Read"}
        result = _make_result()

        validate_tools(fm, result)

        assert result.has_errors
        assert "must be a list" in result.errors[0]

    def test_unknown_tool_is_warning(self):
        fm = {"tools": ["Read", "MagicTool"]}
        result = _make_result()

        validate_tools(fm, result)

        assert not result.has_errors
        assert result.has_warnings
        assert "MagicTool" in result.warnings[0]

    def test_multiple_unknown_tools_multiple_warnings(self):
        fm = {"tools": ["FakeTool1", "FakeTool2"]}
        result = _make_result()

        validate_tools(fm, result)

        assert len(result.warnings) == 2


# =============================================================================
# validate_priority
# =============================================================================


class TestValidatePriority:
    """Tests for validate_priority()."""

    @pytest.mark.parametrize("priority", [1, 2, 3])
    def test_valid_priority_values(self, priority):
        fm = {"priority": priority}
        result = _make_result(tier="core")

        validate_priority(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_missing_priority_is_ok(self):
        fm = {}
        result = _make_result(tier="core")

        validate_priority(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_none_priority_is_ok(self):
        fm = {"priority": None}
        result = _make_result(tier="core")

        validate_priority(fm, result)

        assert not result.has_errors

    def test_non_integer_priority_is_error(self):
        fm = {"priority": "high"}
        result = _make_result(tier="core")

        validate_priority(fm, result)

        assert result.has_errors
        assert "must be an integer" in result.errors[0]

    def test_float_priority_is_error(self):
        fm = {"priority": 1.5}
        result = _make_result(tier="core")

        validate_priority(fm, result)

        assert result.has_errors
        assert "must be an integer" in result.errors[0]

    def test_priority_zero_is_warning(self):
        fm = {"priority": 0}
        result = _make_result(tier="core")

        validate_priority(fm, result)

        assert not result.has_errors
        assert result.has_warnings
        assert "should be 1-3" in result.warnings[0]

    def test_priority_four_is_warning(self):
        fm = {"priority": 4}
        result = _make_result(tier="core")

        validate_priority(fm, result)

        assert not result.has_errors
        assert result.has_warnings

    def test_negative_priority_is_warning(self):
        fm = {"priority": -1}
        result = _make_result(tier="core")

        validate_priority(fm, result)

        assert result.has_warnings

    def test_trait_with_priority_is_warning(self):
        fm = {"priority": 1}
        result = _make_result(tier="trait")

        validate_priority(fm, result)

        assert not result.has_errors
        assert result.has_warnings
        assert "should not define" in result.warnings[0]

    def test_trait_without_priority_is_clean(self):
        fm = {}
        result = _make_result(tier="trait")

        validate_priority(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_trait_with_none_priority_is_clean(self):
        fm = {"priority": None}
        result = _make_result(tier="trait")

        validate_priority(fm, result)

        # tier == "trait" and priority is not None => False, so falls through
        # priority is None => returns early
        assert not result.has_errors
        assert not result.has_warnings


# =============================================================================
# validate_traits_field
# =============================================================================


class TestValidateTraitsField:
    """Tests for validate_traits_field()."""

    def test_valid_traits_list(self):
        fm = {"traits": ["security-first", "test-driven"]}
        result = _make_result(tier="core")

        validate_traits_field(fm, result)

        assert not result.has_errors
        assert result.traits == ["security-first", "test-driven"]

    def test_missing_traits_is_ok(self):
        fm = {}
        result = _make_result(tier="core")

        validate_traits_field(fm, result)

        assert not result.has_errors
        assert result.traits == []

    def test_none_traits_is_ok(self):
        fm = {"traits": None}
        result = _make_result(tier="core")

        validate_traits_field(fm, result)

        assert not result.has_errors

    def test_empty_traits_is_ok(self):
        # Empty list is falsy, returns early
        fm = {"traits": []}
        result = _make_result(tier="core")

        validate_traits_field(fm, result)

        assert not result.has_errors

    def test_traits_not_a_list_is_error(self):
        fm = {"traits": "security-first"}
        result = _make_result(tier="core")

        validate_traits_field(fm, result)

        assert result.has_errors
        assert "must be a list" in result.errors[0]

    def test_trait_referencing_other_traits_is_warning(self):
        fm = {"traits": ["other-trait"]}
        result = _make_result(tier="trait")

        validate_traits_field(fm, result)

        assert not result.has_errors
        assert result.has_warnings
        assert "should not reference" in result.warnings[0]

    def test_trait_without_traits_is_clean(self):
        fm = {}
        result = _make_result(tier="trait")

        validate_traits_field(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_non_string_traits_filtered_from_result(self):
        fm = {"traits": ["valid-trait", 42, None, "another-trait"]}
        result = _make_result(tier="core")

        validate_traits_field(fm, result)

        assert result.traits == ["valid-trait", "another-trait"]


# =============================================================================
# validate_category
# =============================================================================


class TestValidateCategory:
    """Tests for validate_category()."""

    def test_valid_category(self):
        fm = {"category": "development"}
        result = _make_result()

        validate_category(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_missing_category_is_ok(self):
        fm = {}
        result = _make_result()

        validate_category(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_none_category_is_ok(self):
        fm = {"category": None}
        result = _make_result()

        validate_category(fm, result)

        assert not result.has_errors

    def test_empty_category_is_ok(self):
        # Empty string is falsy, returns early
        fm = {"category": ""}
        result = _make_result()

        validate_category(fm, result)

        assert not result.has_errors
        assert not result.has_warnings

    def test_non_string_category_is_warning(self):
        fm = {"category": 42}
        result = _make_result()

        validate_category(fm, result)

        assert not result.has_errors
        assert result.has_warnings
        assert "should be a string" in result.warnings[0]

    def test_list_category_is_warning(self):
        fm = {"category": ["dev", "ops"]}
        result = _make_result()

        validate_category(fm, result)

        assert result.has_warnings


# =============================================================================
# validate_file (integration of all validators)
# =============================================================================


class TestValidateFile:
    """Tests for validate_file() -- orchestrates all per-file validation."""

    def test_fully_valid_core_agent(self, tmp_path):
        # Arrange
        agent_file = tmp_path / "architect.md"
        agent_file.write_text(
            _wrap_frontmatter(
                "name: architect\n"
                "description: System design and architecture\n"
                "tier: core\n"
                "triggers:\n  - design\n  - architecture\n"
                "tools:\n  - Read\n  - Write\n"
                "priority: 1\n"
                "category: development"
            )
        )

        # Act
        result = validate_file(agent_file)

        # Assert
        assert not result.has_errors
        assert result.name == "architect"
        assert result.tier == "core"

    def test_fully_valid_trait(self, tmp_path):
        # Arrange
        trait_file = tmp_path / "security-first.md"
        trait_file.write_text(
            _wrap_frontmatter(
                "name: security-first\ndescription: Adds security considerations\ntier: trait"
            )
        )

        # Act
        result = validate_file(trait_file)

        # Assert
        assert not result.has_errors
        assert result.name == "security-first"
        assert result.tier == "trait"

    def test_fully_valid_extension(self, tmp_path):
        # Arrange
        ext_file = tmp_path / "python-expert.md"
        ext_file.write_text(
            _wrap_frontmatter(
                "name: python-expert\n"
                "description: Python and Django specialist\n"
                "tier: extension\n"
                "triggers:\n  - python\n  - django"
            )
        )

        # Act
        result = validate_file(ext_file)

        # Assert
        assert not result.has_errors

    def test_minimal_valid_file(self, tmp_path):
        # Arrange -- only required fields
        agent_file = tmp_path / "minimal.md"
        agent_file.write_text(
            _wrap_frontmatter("name: minimal\ndescription: A minimal agent\ntier: core")
        )

        # Act
        result = validate_file(agent_file)

        # Assert
        assert not result.has_errors

    def test_no_frontmatter_is_error(self, tmp_path):
        # Arrange
        agent_file = tmp_path / "plain.md"
        agent_file.write_text("# Just a regular markdown file\n\nNo frontmatter here.\n")

        # Act
        result = validate_file(agent_file)

        # Assert
        assert result.has_errors

    def test_missing_required_fields_accumulates_errors(self, tmp_path):
        # Arrange -- has frontmatter but missing name, description, tier
        agent_file = tmp_path / "empty-fm.md"
        agent_file.write_text(_wrap_frontmatter("category: test"))

        # Act
        result = validate_file(agent_file)

        # Assert
        assert result.has_errors
        assert len(result.errors) >= 3  # name, description, tier

    def test_nonexistent_file_is_error(self, tmp_path):
        # Arrange
        missing_file = tmp_path / "ghost.md"

        # Act
        result = validate_file(missing_file)

        # Assert
        assert result.has_errors
        assert "Failed to read file" in result.errors[0]

    def test_invalid_yaml_in_file_is_error(self, tmp_path):
        # Arrange
        bad_file = tmp_path / "bad.md"
        bad_file.write_text("---\n[bad: yaml: :\n---\n\nBody.\n")

        # Act
        result = validate_file(bad_file)

        # Assert
        assert result.has_errors

    def test_multiple_validation_issues_collected(self, tmp_path):
        # Arrange -- invalid name + invalid tier + non-string description
        agent_file = tmp_path / "multi-bad.md"
        agent_file.write_text(
            _wrap_frontmatter("name: 123-bad!\ndescription: 42\ntier: invalid\ntools: not-a-list")
        )

        # Act
        result = validate_file(agent_file)

        # Assert
        assert result.has_errors
        assert len(result.errors) >= 3


# =============================================================================
# validate_uniqueness (cross-file)
# =============================================================================


class TestValidateUniqueness:
    """Tests for validate_uniqueness()."""

    def test_no_duplicates_returns_empty(self):
        # Arrange
        r1 = _make_result(name="architect")
        r2 = _make_result(name="developer")
        r3 = _make_result(name="optimizer")

        # Act
        errors = validate_uniqueness([r1, r2, r3])

        # Assert
        assert errors == []

    def test_duplicate_names_returns_errors(self):
        # Arrange
        r1 = _make_result(name="architect")
        r1.filepath = Path("agents/core/architect.md")
        r2 = _make_result(name="architect")
        r2.filepath = Path("agents/extensions/architect.md")

        # Act
        errors = validate_uniqueness([r1, r2])

        # Assert
        assert len(errors) == 1
        assert "Duplicate" in errors[0]
        assert "architect" in errors[0]

    def test_none_names_are_skipped(self):
        # Arrange -- results without names (failed earlier validation)
        r1 = _make_result(name=None)
        r2 = _make_result(name="architect")

        # Act
        errors = validate_uniqueness([r1, r2])

        # Assert
        assert errors == []

    def test_empty_list_returns_empty(self):
        errors = validate_uniqueness([])
        assert errors == []

    def test_all_none_names_returns_empty(self):
        r1 = _make_result(name=None)
        r2 = _make_result(name=None)

        errors = validate_uniqueness([r1, r2])

        assert errors == []

    def test_three_way_duplicate(self):
        # Arrange
        results = []
        for i in range(3):
            r = _make_result(name="dup")
            r.filepath = Path(f"agents/file{i}.md")
            results.append(r)

        # Act
        errors = validate_uniqueness(results)

        # Assert
        # Second and third occurrence each produce an error
        assert len(errors) == 2


# =============================================================================
# validate_trait_references (cross-file)
# =============================================================================


class TestValidateTraitReferences:
    """Tests for validate_trait_references()."""

    def test_valid_references_returns_empty(self):
        # Arrange
        trait = _make_result(tier="trait", name="security-first")
        agent = _make_result(tier="core", name="architect")
        agent.traits = ["security-first"]

        # Act
        errors = validate_trait_references([trait, agent])

        # Assert
        assert errors == []

    def test_unknown_trait_reference_returns_error(self):
        # Arrange
        agent = _make_result(tier="core", name="architect")
        agent.filepath = Path("agents/core/architect.md")
        agent.traits = ["nonexistent-trait"]

        # Act
        errors = validate_trait_references([agent])

        # Assert
        assert len(errors) == 1
        assert "nonexistent-trait" in errors[0]
        assert "architect.md" in errors[0]

    def test_no_traits_referenced_returns_empty(self):
        # Arrange
        r1 = _make_result(tier="core", name="dev")
        r1.traits = []

        # Act
        errors = validate_trait_references([r1])

        # Assert
        assert errors == []

    def test_empty_list_returns_empty(self):
        errors = validate_trait_references([])
        assert errors == []

    def test_multiple_valid_and_invalid_refs(self):
        # Arrange
        trait1 = _make_result(tier="trait", name="security-first")
        trait2 = _make_result(tier="trait", name="test-driven")

        agent = _make_result(tier="core", name="architect")
        agent.filepath = Path("agents/core/architect.md")
        agent.traits = ["security-first", "test-driven", "missing-trait"]

        # Act
        errors = validate_trait_references([trait1, trait2, agent])

        # Assert
        assert len(errors) == 1
        assert "missing-trait" in errors[0]

    def test_trait_tier_without_name_is_excluded_from_known_set(self):
        # Arrange -- trait with None name should not be in known set
        broken_trait = _make_result(tier="trait", name=None)
        agent = _make_result(tier="core", name="dev")
        agent.filepath = Path("agents/core/dev.md")
        agent.traits = ["anything"]

        # Act
        errors = validate_trait_references([broken_trait, agent])

        # Assert
        assert len(errors) == 1


# =============================================================================
# find_agent_files
# =============================================================================


class TestFindAgentFiles:
    """Tests for find_agent_files()."""

    def test_finds_files_in_core(self, tmp_path):
        # Arrange
        core_dir = tmp_path / "agents" / "core"
        core_dir.mkdir(parents=True)
        (core_dir / "architect.md").write_text("---\nname: architect\n---\n")
        (core_dir / "developer.md").write_text("---\nname: developer\n---\n")

        # Act
        files = find_agent_files(tmp_path)

        # Assert
        assert len(files) == 2
        filenames = {f.name for f in files}
        assert "architect.md" in filenames
        assert "developer.md" in filenames

    def test_finds_files_in_traits(self, tmp_path):
        # Arrange
        traits_dir = tmp_path / "agents" / "traits"
        traits_dir.mkdir(parents=True)
        (traits_dir / "security-first.md").write_text("---\nname: sf\n---\n")

        # Act
        files = find_agent_files(tmp_path)

        # Assert
        assert len(files) == 1
        assert files[0].name == "security-first.md"

    def test_finds_files_in_extensions(self, tmp_path):
        # Arrange
        ext_dir = tmp_path / "agents" / "extensions"
        ext_dir.mkdir(parents=True)
        (ext_dir / "python-expert.md").write_text("---\nname: pe\n---\n")

        # Act
        files = find_agent_files(tmp_path)

        # Assert
        assert len(files) == 1

    def test_finds_files_across_all_tiers(self, tmp_path):
        # Arrange
        for subdir in ["core", "traits", "extensions"]:
            d = tmp_path / "agents" / subdir
            d.mkdir(parents=True)
            (d / f"{subdir}-agent.md").write_text(f"---\nname: {subdir}\n---\n")

        # Act
        files = find_agent_files(tmp_path)

        # Assert
        assert len(files) == 3

    def test_returns_empty_for_missing_dirs(self, tmp_path):
        # Arrange -- no agents/ directory at all

        # Act
        files = find_agent_files(tmp_path)

        # Assert
        assert files == []

    def test_returns_sorted_files(self, tmp_path):
        # Arrange
        core_dir = tmp_path / "agents" / "core"
        core_dir.mkdir(parents=True)
        for name in ["zebra.md", "alpha.md", "middle.md"]:
            (core_dir / name).write_text(f"---\nname: {name}\n---\n")

        # Act
        files = find_agent_files(tmp_path)

        # Assert
        assert files == sorted(files)

    def test_ignores_non_md_files(self, tmp_path):
        # Arrange
        core_dir = tmp_path / "agents" / "core"
        core_dir.mkdir(parents=True)
        (core_dir / "agent.md").write_text("---\nname: a\n---\n")
        (core_dir / "readme.txt").write_text("not markdown")
        (core_dir / "config.yaml").write_text("key: val")

        # Act
        files = find_agent_files(tmp_path)

        # Assert
        assert len(files) == 1
        assert files[0].name == "agent.md"

    def test_does_not_scan_deprecated(self, tmp_path):
        # Arrange -- DEPRECATED is an ignored path
        deprecated_dir = tmp_path / "agents" / "DEPRECATED"
        deprecated_dir.mkdir(parents=True)
        (deprecated_dir / "old-agent.md").write_text("---\nname: old\n---\n")

        # Act
        files = find_agent_files(tmp_path)

        # Assert
        assert files == []

    def test_does_not_recurse_into_subdirectories(self, tmp_path):
        # Arrange -- nested subdir inside core
        core_dir = tmp_path / "agents" / "core"
        core_dir.mkdir(parents=True)
        (core_dir / "top-level.md").write_text("---\nname: top\n---\n")
        nested = core_dir / "subdir"
        nested.mkdir()
        (nested / "nested.md").write_text("---\nname: nested\n---\n")

        # Act
        files = find_agent_files(tmp_path)

        # Assert
        # glob("*.md") does not recurse
        assert len(files) == 1
        assert files[0].name == "top-level.md"

    def test_handles_empty_directories(self, tmp_path):
        # Arrange
        (tmp_path / "agents" / "core").mkdir(parents=True)
        (tmp_path / "agents" / "traits").mkdir(parents=True)

        # Act
        files = find_agent_files(tmp_path)

        # Assert
        assert files == []


# =============================================================================
# print_results
# =============================================================================

from scripts.validate_agents import print_results  # noqa: E402


class TestPrintResults:
    """Tests for print_results()."""

    def test_no_errors_no_warnings(self, capsys):
        results = [_make_result(name="ok")]
        total_errors, total_warnings = print_results(results, [])
        assert total_errors == 0
        assert total_warnings == 0

    def test_counts_errors_from_results(self):
        r = _make_result(name="bad")
        r.add_error("Error 1")
        r.add_error("Error 2")

        total_errors, total_warnings = print_results([r], [])
        assert total_errors == 2
        assert total_warnings == 0

    def test_counts_cross_errors(self):
        total_errors, total_warnings = print_results([], ["Cross error 1", "Cross error 2"])
        assert total_errors == 2

    def test_counts_warnings(self):
        r = _make_result(name="warn")
        r.add_warning("Warning 1")

        total_errors, total_warnings = print_results([r], [])
        assert total_errors == 0
        assert total_warnings == 1

    def test_prints_errors(self, capsys):
        r = _make_result(name="bad")
        r.filepath = Path("agents/core/bad.md")
        r.add_error("Something went wrong")

        print_results([r], [])
        captured = capsys.readouterr()
        assert "ERROR: Something went wrong" in captured.out

    def test_prints_cross_errors(self, capsys):
        print_results([], ["Duplicate name found"])
        captured = capsys.readouterr()
        assert "Duplicate name found" in captured.out

    def test_verbose_prints_warnings(self, capsys):
        r = _make_result(name="warn")
        r.filepath = Path("agents/core/warn.md")
        r.add_warning("Some warning")

        print_results([r], [], verbose=True)
        captured = capsys.readouterr()
        assert "WARNING: Some warning" in captured.out


# =============================================================================
# main
# =============================================================================

from scripts.validate_agents import main as validate_agents_main  # noqa: E402


class TestValidateAgentsMain:
    """Tests for main()."""

    def test_invalid_repo_root(self, tmp_path: Path, monkeypatch):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        monkeypatch.setattr("sys.argv", ["prog", "--repo-root", str(empty_dir)])

        result = validate_agents_main()
        assert result == 2

    def test_no_agent_files(self, tmp_path: Path, monkeypatch, capsys):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        monkeypatch.setattr("sys.argv", ["prog", "--repo-root", str(tmp_path)])

        result = validate_agents_main()
        assert result == 0
        captured = capsys.readouterr()
        assert "No agent files" in captured.out

    def test_valid_agents_pass(self, tmp_path: Path, monkeypatch, capsys):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        core = tmp_path / "agents" / "core"
        core.mkdir(parents=True)
        (core / "architect.md").write_text(
            "---\nname: architect\ndescription: System design\ntier: core\n---\n\n# Architect"
        )

        monkeypatch.setattr("sys.argv", ["prog", "--repo-root", str(tmp_path)])

        result = validate_agents_main()
        assert result == 0
        captured = capsys.readouterr()
        assert "PASSED" in captured.out

    def test_invalid_agents_fail(self, tmp_path: Path, monkeypatch, capsys):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        core = tmp_path / "agents" / "core"
        core.mkdir(parents=True)
        (core / "bad.md").write_text("---\ntier: invalid\n---\n\n# Bad")

        monkeypatch.setattr("sys.argv", ["prog", "--repo-root", str(tmp_path)])

        result = validate_agents_main()
        assert result == 1
        captured = capsys.readouterr()
        assert "FAILED" in captured.out

    def test_strict_mode_fails_on_warnings(self, tmp_path: Path, monkeypatch, capsys):
        (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
        core = tmp_path / "agents" / "core"
        core.mkdir(parents=True)
        # Valid agent but missing triggers (warning)
        (core / "dev.md").write_text(
            "---\nname: dev\ndescription: Developer\ntier: core\n---\n\n# Dev"
        )

        monkeypatch.setattr("sys.argv", ["prog", "--repo-root", str(tmp_path), "--strict"])

        result = validate_agents_main()
        assert result == 1
        captured = capsys.readouterr()
        assert "strict mode" in captured.out.lower() or "FAILED" in captured.out
