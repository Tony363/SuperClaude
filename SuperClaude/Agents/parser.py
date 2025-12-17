"""
Markdown Agent Parser for SuperClaude Framework

This module parses agent definitions from markdown files, extracting
metadata, behavioral mindset, focus areas, and boundaries.

P0 SAFETY: Implements strict schema validation to prevent runtime parsing errors.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:  # Optional dependency used for YAML frontmatter
    import yaml
except ModuleNotFoundError:  # pragma: no cover - depends on optional extras
    yaml = None  # type: ignore


@dataclass
class AgentSchemaError:
    """Represents a schema validation error."""

    field: str
    message: str
    severity: str = "error"  # "error", "warning", "info"
    line_number: int | None = None


@dataclass
class AgentValidationResult:
    """Result of agent schema validation."""

    valid: bool
    errors: list[AgentSchemaError] = field(default_factory=list)
    warnings: list[AgentSchemaError] = field(default_factory=list)
    agent_name: str = ""
    file_path: str = ""

    def add_error(self, field: str, message: str, line: int | None = None) -> None:
        """Add a validation error."""
        self.errors.append(AgentSchemaError(field, message, "error", line))
        self.valid = False

    def add_warning(self, field: str, message: str, line: int | None = None) -> None:
        """Add a validation warning."""
        self.warnings.append(AgentSchemaError(field, message, "warning", line))


class AgentSchema:
    """
    Schema definition for agent markdown files.

    P0 SAFETY: Defines required and optional fields with type validation
    to prevent runtime parsing failures.
    """

    # Required fields in YAML frontmatter
    REQUIRED_FIELDS: set[str] = {"name", "description"}

    # Optional but recommended fields
    RECOMMENDED_FIELDS: set[str] = {"tools", "category"}

    # Valid tool names (from Claude Code)
    VALID_TOOLS: set[str] = {
        "Read",
        "Write",
        "Edit",
        "MultiEdit",
        "Bash",
        "Glob",
        "Grep",
        "Task",
        "TodoWrite",
        "WebFetch",
        "WebSearch",
        "NotebookEdit",
        # MCP tools
        "Docker",
        "docker",
        "database",
        "redis",
        "postgresql",
        "postgres",
        "mcp",
        "Browser",
        "browser",
        "playwright",
    }

    # Valid agent categories
    VALID_CATEGORIES: set[str] = {
        "core-development",
        "language-specialist",
        "infrastructure",
        "quality-security",
        "data-ai",
        "developer-experience",
        "specialized-domain",
        "business-product",
        "meta-orchestration",
        "research-analysis",
    }

    # Maximum lengths
    MAX_NAME_LENGTH = 64
    MAX_DESCRIPTION_LENGTH = 500
    MAX_TOOLS_COUNT = 20


class AgentMarkdownParser:
    """
    Parser for agent markdown files.

    Extracts structured data from markdown files that define agent
    behavior, capabilities, and configuration.
    """

    def __init__(self):
        """Initialize the markdown parser."""
        self.logger = logging.getLogger("agent.parser")

    def parse(self, file_path: Path) -> dict[str, Any] | None:
        """
        Parse an agent markdown file.

        Args:
            file_path: Path to the markdown file

        Returns:
            Dictionary containing parsed agent configuration or None
        """
        try:
            # Try UTF-8 first, then fall back to latin-1
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Fall back to latin-1 which accepts all byte values
                with open(file_path, encoding="latin-1") as f:
                    content = f.read()

            # Parse YAML frontmatter
            config = self._parse_frontmatter(content)

            if not config:
                config = {}

            # Parse markdown sections
            sections = self._parse_sections(content)

            # Extract key information
            config.update(self._extract_agent_info(sections))

            # Ensure required fields
            if "name" not in config and file_path.stem != "__init__":
                config["name"] = file_path.stem

            return config

        except Exception as e:
            self.logger.error(f"Failed to parse {file_path}: {e}")
            return None

    def _parse_frontmatter(self, content: str) -> dict[str, Any]:
        """
        Parse YAML frontmatter from markdown content.

        Args:
            content: Markdown file content

        Returns:
            Dictionary containing frontmatter data
        """
        # Check for YAML frontmatter (between --- markers)
        pattern = r"^---\s*\n(.*?)\n---\s*\n"
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return {}

        if yaml is None:
            self.logger.debug("PyYAML not installed; skipping frontmatter parsing")
            return {}

        try:
            yaml_content = match.group(1)
            data = yaml.safe_load(yaml_content)
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError as e:
            self.logger.warning(f"Failed to parse YAML frontmatter: {e}")
            return {}

    def _parse_sections(self, content: str) -> dict[str, str]:
        """
        Parse markdown sections from content.

        Args:
            content: Markdown file content

        Returns:
            Dictionary mapping section headers to content
        """
        sections = {}

        # Remove frontmatter if present
        content = re.sub(r"^---\s*\n.*?\n---\s*\n", "", content, flags=re.DOTALL)

        # Split by headers (## or ###)
        header_pattern = r"^##\s+(.+)$"
        lines = content.split("\n")

        current_section = None
        current_content = []

        for line in lines:
            header_match = re.match(header_pattern, line)

            if header_match:
                # Save previous section
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()

                # Start new section
                current_section = header_match.group(1).strip()
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _extract_agent_info(self, sections: dict[str, str]) -> dict[str, Any]:
        """
        Extract agent information from parsed sections.

        Args:
            sections: Dictionary of markdown sections

        Returns:
            Dictionary containing extracted agent information
        """
        info = {}

        # Extract triggers
        if "Triggers" in sections:
            info["triggers"] = self._parse_list_section(sections["Triggers"])

        # Extract behavioral mindset
        if "Behavioral Mindset" in sections:
            info["behavioral_mindset"] = sections["Behavioral Mindset"]

        # Extract focus areas
        if "Focus Areas" in sections:
            info["focus_areas"] = self._parse_focus_areas(sections["Focus Areas"])

        # Extract key actions
        if "Key Actions" in sections:
            info["key_actions"] = self._parse_numbered_list(sections["Key Actions"])

        # Extract outputs
        if "Outputs" in sections:
            info["outputs"] = self._parse_list_section(sections["Outputs"])

        # Extract boundaries
        if "Boundaries" in sections:
            info["boundaries"] = self._parse_boundaries(sections["Boundaries"])

        return info

    def _parse_list_section(self, content: str) -> list[str]:
        """
        Parse a section containing a list.

        Args:
            content: Section content

        Returns:
            List of items
        """
        items = []
        lines = content.split("\n")

        for line in lines:
            # Match lines starting with - or *
            match = re.match(r"^[-*]\s+(.+)$", line.strip())
            if match:
                items.append(match.group(1).strip())

        return items

    def _parse_numbered_list(self, content: str) -> list[str]:
        """
        Parse a numbered list section.

        Args:
            content: Section content

        Returns:
            List of items
        """
        items = []
        lines = content.split("\n")
        current_item = []

        for line in lines:
            # Match lines starting with number
            match = re.match(r"^\d+\.\s+(.+)$", line.strip())

            if match:
                # Save previous item
                if current_item:
                    items.append(" ".join(current_item))
                # Start new item
                current_item = [match.group(1).strip()]
            elif line.strip() and current_item:
                # Continuation of current item
                current_item.append(line.strip())

        # Save last item
        if current_item:
            items.append(" ".join(current_item))

        return items

    def _parse_focus_areas(self, content: str) -> dict[str, str]:
        """
        Parse focus areas section.

        Args:
            content: Section content

        Returns:
            Dictionary of focus areas
        """
        areas = {}
        lines = content.split("\n")

        for line in lines:
            # Match lines with bold text followed by colon
            match = re.match(r"^[-*]\s+\*\*(.+?)\*\*:\s+(.+)$", line.strip())
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                areas[key] = value

        return areas

    def _parse_boundaries(self, content: str) -> dict[str, list[str]]:
        """
        Parse boundaries section (Will/Will Not).

        Args:
            content: Section content

        Returns:
            Dictionary with 'will' and 'will_not' lists
        """
        boundaries = {"will": [], "will_not": []}
        current_section = None

        lines = content.split("\n")

        for line in lines:
            # Check for Will: or Will Not: headers
            if line.strip().startswith("**Will:**"):
                current_section = "will"
            elif line.strip().startswith("**Will Not:**"):
                current_section = "will_not"
            elif current_section:
                # Parse list items under current section
                match = re.match(r"^[-*]\s+(.+)$", line.strip())
                if match:
                    boundaries[current_section].append(match.group(1).strip())

        return boundaries

    def validate_agent_config(self, config: dict[str, Any]) -> bool:
        """
        Validate agent configuration (simple boolean check).

        Args:
            config: Agent configuration dictionary

        Returns:
            True if configuration is valid
        """
        result = self.validate_schema(config)
        return result.valid

    def validate_schema(
        self, config: dict[str, Any], file_path: Path | None = None
    ) -> AgentValidationResult:
        """
        Validate agent configuration against schema.

        P0 SAFETY: Comprehensive validation to prevent runtime parsing errors.

        Args:
            config: Agent configuration dictionary
            file_path: Optional path for error reporting

        Returns:
            AgentValidationResult with errors and warnings
        """
        result = AgentValidationResult(
            valid=True,
            agent_name=config.get("name", "unknown"),
            file_path=str(file_path) if file_path else "",
        )

        # Check required fields
        for field_name in AgentSchema.REQUIRED_FIELDS:
            if field_name not in config or not config[field_name]:
                result.add_error(
                    field_name, f"Required field '{field_name}' is missing"
                )

        # Check recommended fields (warnings only)
        for field_name in AgentSchema.RECOMMENDED_FIELDS:
            if field_name not in config:
                result.add_warning(
                    field_name, f"Recommended field '{field_name}' is missing"
                )

        # Validate name format
        if "name" in config:
            name = config["name"]
            if not isinstance(name, str):
                result.add_error("name", "Name must be a string")
            elif len(name) > AgentSchema.MAX_NAME_LENGTH:
                result.add_error(
                    "name",
                    f"Name exceeds maximum length of {AgentSchema.MAX_NAME_LENGTH}",
                )
            elif not re.match(r"^[a-z][a-z0-9-]*$", name):
                result.add_warning(
                    "name",
                    "Name should be lowercase with hyphens (e.g., 'backend-developer')",
                )

        # Validate description
        if "description" in config:
            desc = config["description"]
            if not isinstance(desc, str):
                result.add_error("description", "Description must be a string")
            elif len(desc) > AgentSchema.MAX_DESCRIPTION_LENGTH:
                result.add_warning(
                    "description",
                    f"Description exceeds recommended length of {AgentSchema.MAX_DESCRIPTION_LENGTH}",
                )

        # Validate tools
        if "tools" in config:
            tools = config["tools"]
            if isinstance(tools, str):
                # Parse comma-separated tools
                tool_list = [t.strip() for t in tools.split(",")]
            elif isinstance(tools, list):
                tool_list = tools
            else:
                result.add_error("tools", "Tools must be a string or list")
                tool_list = []

            if len(tool_list) > AgentSchema.MAX_TOOLS_COUNT:
                result.add_warning(
                    "tools",
                    f"Agent has {len(tool_list)} tools, which exceeds recommended max of {AgentSchema.MAX_TOOLS_COUNT}",
                )

            # Check for unknown tools (warning only - new tools may be added)
            for tool in tool_list:
                if tool and tool not in AgentSchema.VALID_TOOLS:
                    # Don't error on unknown tools, just warn
                    result.add_warning(
                        "tools",
                        f"Unknown tool '{tool}' - verify it exists",
                    )

        # Validate category if present
        if "category" in config:
            category = config["category"]
            if isinstance(category, str):
                if category not in AgentSchema.VALID_CATEGORIES:
                    result.add_warning(
                        "category",
                        f"Unknown category '{category}' - valid categories: {', '.join(sorted(AgentSchema.VALID_CATEGORIES))}",
                    )

        return result

    def validate_all_agents(self, agents_dir: Path) -> list[AgentValidationResult]:
        """
        Validate all agent markdown files in a directory.

        P0 SAFETY: Batch validation for CI/CD integration.

        Args:
            agents_dir: Directory containing agent markdown files

        Returns:
            List of validation results for all agents
        """
        results = []

        # Find all markdown files
        md_files = list(agents_dir.rglob("*.md"))

        for md_file in md_files:
            # Skip non-agent files
            if md_file.name.startswith("_") or md_file.name == "README.md":
                continue

            config = self.parse(md_file)
            if config is None:
                result = AgentValidationResult(
                    valid=False,
                    agent_name=md_file.stem,
                    file_path=str(md_file),
                )
                result.add_error("parse", f"Failed to parse markdown file: {md_file}")
            else:
                result = self.validate_schema(config, md_file)

            results.append(result)

        return results

    def get_validation_summary(
        self, results: list[AgentValidationResult]
    ) -> dict[str, Any]:
        """
        Generate a summary of validation results.

        Args:
            results: List of validation results

        Returns:
            Summary dictionary with counts and details
        """
        total = len(results)
        valid = sum(1 for r in results if r.valid)
        invalid = total - valid
        total_errors = sum(len(r.errors) for r in results)
        total_warnings = sum(len(r.warnings) for r in results)

        return {
            "total_agents": total,
            "valid": valid,
            "invalid": invalid,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "pass_rate": valid / total if total > 0 else 0,
            "invalid_agents": [
                {"name": r.agent_name, "path": r.file_path, "errors": len(r.errors)}
                for r in results
                if not r.valid
            ],
        }
