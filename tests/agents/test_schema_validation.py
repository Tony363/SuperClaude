"""
P0 Safety Tests: Agent Schema Validation

Tests the agent markdown parsing and schema validation to prevent
runtime parsing errors from malformed agent definitions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from SuperClaude.Agents.parser import (
    AgentMarkdownParser,
    AgentSchema,
    AgentSchemaError,
    AgentValidationResult,
)


class TestAgentSchema:
    """Test schema constants and configuration."""

    def test_required_fields_defined(self):
        """Verify required fields are defined."""
        assert "name" in AgentSchema.REQUIRED_FIELDS
        assert "description" in AgentSchema.REQUIRED_FIELDS

    def test_recommended_fields_defined(self):
        """Verify recommended fields are defined."""
        assert "tools" in AgentSchema.RECOMMENDED_FIELDS
        assert "category" in AgentSchema.RECOMMENDED_FIELDS

    def test_valid_tools_include_core(self):
        """Verify core Claude Code tools are included."""
        core_tools = ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "Task"]
        for tool in core_tools:
            assert tool in AgentSchema.VALID_TOOLS

    def test_valid_categories_defined(self):
        """Verify agent categories are defined."""
        expected_categories = [
            "core-development",
            "language-specialist",
            "infrastructure",
            "quality-security",
            "data-ai",
        ]
        for category in expected_categories:
            assert category in AgentSchema.VALID_CATEGORIES

    def test_max_lengths_are_reasonable(self):
        """Verify max lengths prevent unbounded input."""
        assert AgentSchema.MAX_NAME_LENGTH > 0
        assert AgentSchema.MAX_NAME_LENGTH <= 100
        assert AgentSchema.MAX_DESCRIPTION_LENGTH > 0
        assert AgentSchema.MAX_DESCRIPTION_LENGTH <= 1000
        assert AgentSchema.MAX_TOOLS_COUNT > 0
        assert AgentSchema.MAX_TOOLS_COUNT <= 50


class TestAgentSchemaError:
    """Test schema error dataclass."""

    def test_error_creation(self):
        """Test creating a schema error."""
        error = AgentSchemaError(
            field="name",
            message="Name is required",
            severity="error",
            line_number=5,
        )

        assert error.field == "name"
        assert error.message == "Name is required"
        assert error.severity == "error"
        assert error.line_number == 5

    def test_default_severity(self):
        """Test default severity is 'error'."""
        error = AgentSchemaError(field="test", message="test message")
        assert error.severity == "error"


class TestAgentValidationResult:
    """Test validation result dataclass."""

    def test_starts_valid(self):
        """Test that result starts as valid."""
        result = AgentValidationResult(valid=True)
        assert result.valid is True
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_add_error_invalidates(self):
        """Test that adding an error makes result invalid."""
        result = AgentValidationResult(valid=True)
        result.add_error("field", "error message")

        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "field"

    def test_add_warning_keeps_valid(self):
        """Test that warnings don't invalidate result."""
        result = AgentValidationResult(valid=True)
        result.add_warning("field", "warning message")

        assert result.valid is True
        assert len(result.warnings) == 1

    def test_multiple_errors(self):
        """Test accumulating multiple errors."""
        result = AgentValidationResult(valid=True)
        result.add_error("name", "missing")
        result.add_error("description", "too long")

        assert result.valid is False
        assert len(result.errors) == 2


class TestSchemaValidation:
    """Test the validate_schema method."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return AgentMarkdownParser()

    def test_valid_minimal_config(self, parser):
        """Test validation of minimal valid config."""
        config = {
            "name": "test-agent",
            "description": "A test agent for validation",
        }

        result = parser.validate_schema(config)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_valid_full_config(self, parser):
        """Test validation of full valid config."""
        config = {
            "name": "backend-developer",
            "description": "Senior backend engineer",
            "tools": "Read, Write, Bash, Edit",
            "category": "core-development",
        }

        result = parser.validate_schema(config)

        assert result.valid is True
        # May have warnings for unknown tools, but should be valid

    def test_missing_required_field_name(self, parser):
        """Test error on missing name."""
        config = {
            "description": "A description without name",
        }

        result = parser.validate_schema(config)

        assert result.valid is False
        assert any(e.field == "name" for e in result.errors)

    def test_missing_required_field_description(self, parser):
        """Test error on missing description."""
        config = {
            "name": "test-agent",
        }

        result = parser.validate_schema(config)

        assert result.valid is False
        assert any(e.field == "description" for e in result.errors)

    def test_name_too_long(self, parser):
        """Test error on name exceeding max length."""
        config = {
            "name": "a" * (AgentSchema.MAX_NAME_LENGTH + 10),
            "description": "Test description",
        }

        result = parser.validate_schema(config)

        assert result.valid is False
        assert any("length" in e.message.lower() for e in result.errors)

    def test_name_format_warning(self, parser):
        """Test warning on invalid name format."""
        config = {
            "name": "TestAgent_Invalid",  # Should be lowercase-with-hyphens
            "description": "Test description",
        }

        result = parser.validate_schema(config)

        # Should warn but not error (name is technically valid)
        assert any("lowercase" in w.message.lower() for w in result.warnings)

    def test_tools_as_string(self, parser):
        """Test parsing tools from comma-separated string."""
        config = {
            "name": "test-agent",
            "description": "Test description",
            "tools": "Read, Write, Bash",
        }

        result = parser.validate_schema(config)

        # Should parse successfully
        assert result.valid is True

    def test_tools_as_list(self, parser):
        """Test parsing tools from list."""
        config = {
            "name": "test-agent",
            "description": "Test description",
            "tools": ["Read", "Write", "Bash"],
        }

        result = parser.validate_schema(config)

        assert result.valid is True

    def test_unknown_tool_warning(self, parser):
        """Test warning for unknown tools."""
        config = {
            "name": "test-agent",
            "description": "Test description",
            "tools": "Read, UnknownMagicTool",
        }

        result = parser.validate_schema(config)

        # Should be valid but with warning
        assert result.valid is True
        assert any("unknown tool" in w.message.lower() for w in result.warnings)

    def test_unknown_category_warning(self, parser):
        """Test warning for unknown category."""
        config = {
            "name": "test-agent",
            "description": "Test description",
            "category": "invalid-category-name",
        }

        result = parser.validate_schema(config)

        # Should be valid but with warning
        assert result.valid is True
        assert any("unknown category" in w.message.lower() for w in result.warnings)

    def test_missing_recommended_fields_warning(self, parser):
        """Test warnings for missing recommended fields."""
        config = {
            "name": "test-agent",
            "description": "Test description",
            # Missing tools and category
        }

        result = parser.validate_schema(config)

        assert result.valid is True
        assert len(result.warnings) >= 2  # tools and category warnings


class TestValidateAgentConfig:
    """Test the simple boolean validate_agent_config method."""

    @pytest.fixture
    def parser(self):
        return AgentMarkdownParser()

    def test_returns_true_for_valid(self, parser):
        """Test returns True for valid config."""
        config = {
            "name": "test-agent",
            "description": "A valid test agent",
        }

        assert parser.validate_agent_config(config) is True

    def test_returns_false_for_invalid(self, parser):
        """Test returns False for invalid config."""
        config = {
            # Missing required fields
        }

        assert parser.validate_agent_config(config) is False


class TestValidationSummary:
    """Test the validation summary generation."""

    @pytest.fixture
    def parser(self):
        return AgentMarkdownParser()

    def test_summary_with_all_valid(self, parser):
        """Test summary when all agents are valid."""
        results = [
            AgentValidationResult(valid=True, agent_name="agent1"),
            AgentValidationResult(valid=True, agent_name="agent2"),
        ]

        summary = parser.get_validation_summary(results)

        assert summary["total_agents"] == 2
        assert summary["valid"] == 2
        assert summary["invalid"] == 0
        assert summary["pass_rate"] == 1.0

    def test_summary_with_invalid(self, parser):
        """Test summary when some agents are invalid."""
        valid_result = AgentValidationResult(valid=True, agent_name="good-agent")
        invalid_result = AgentValidationResult(
            valid=False,
            agent_name="bad-agent",
            file_path="/path/to/bad-agent.md",
        )
        invalid_result.add_error("name", "missing")

        results = [valid_result, invalid_result]

        summary = parser.get_validation_summary(results)

        assert summary["total_agents"] == 2
        assert summary["valid"] == 1
        assert summary["invalid"] == 1
        assert summary["pass_rate"] == 0.5
        assert len(summary["invalid_agents"]) == 1
        assert summary["invalid_agents"][0]["name"] == "bad-agent"

    def test_summary_counts_errors_and_warnings(self, parser):
        """Test that summary counts all errors and warnings."""
        result1 = AgentValidationResult(valid=True, agent_name="agent1")
        result1.add_warning("tools", "unknown tool")

        result2 = AgentValidationResult(valid=True, agent_name="agent2")
        result2.add_warning("category", "unknown category")
        result2.add_warning("tools", "too many tools")

        results = [result1, result2]

        summary = parser.get_validation_summary(results)

        assert summary["total_warnings"] == 3
        assert summary["total_errors"] == 0


class TestMarkdownParsing:
    """Test parsing actual markdown content."""

    @pytest.fixture
    def parser(self):
        return AgentMarkdownParser()

    def test_parse_valid_frontmatter(self, parser, tmp_path):
        """Test parsing valid YAML frontmatter."""
        content = """---
name: test-agent
description: A test agent for validation testing
tools: Read, Write, Bash
---

You are a test agent.
"""
        md_file = tmp_path / "test-agent.md"
        md_file.write_text(content)

        config = parser.parse(md_file)

        assert config is not None
        assert config["name"] == "test-agent"
        assert config["description"] == "A test agent for validation testing"
        assert "tools" in config

    def test_parse_missing_frontmatter(self, parser, tmp_path):
        """Test parsing file without frontmatter."""
        content = """# Agent Without Frontmatter

This agent has no YAML frontmatter.
"""
        md_file = tmp_path / "no-frontmatter.md"
        md_file.write_text(content)

        config = parser.parse(md_file)

        assert config is not None
        # Name should be derived from filename
        assert config["name"] == "no-frontmatter"

    def test_parse_malformed_yaml(self, parser, tmp_path):
        """Test graceful handling of malformed YAML."""
        content = """---
name: test-agent
description: [invalid yaml
  - broken indentation
---

Content here.
"""
        md_file = tmp_path / "malformed.md"
        md_file.write_text(content)

        # Should not raise, may return empty or partial config
        config = parser.parse(md_file)

        # Parser should handle gracefully (either None or empty dict)
        # The key is no exception is raised
