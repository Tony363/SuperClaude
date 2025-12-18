"""
Skill Adapter for SuperClaude Framework.

Bidirectional adapter between Agent Skills SKILL.md format and
Python CommandMetadata registry. Enables Skills-first runtime
while maintaining backward compatibility with Python orchestration.
"""

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:
    yaml = None  # type: ignore

# Import from Commands module for compatibility
from SuperClaude.Commands.registry import CommandMetadata


def _parse_simple_yaml(content: str) -> dict:
    """
    Simple YAML parser for frontmatter when PyYAML is not available.

    Only handles basic key: value pairs, not nested structures.
    """
    result = {}
    for line in content.strip().split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            # Handle quoted strings
            if (value.startswith('"') and value.endswith('"')) or (
                value.startswith("'") and value.endswith("'")
            ):
                value = value[1:-1]
            # Handle lists (simple format: [item1, item2])
            if value.startswith("[") and value.endswith("]"):
                items = value[1:-1].split(",")
                value = [i.strip().strip('"').strip("'") for i in items if i.strip()]
            result[key] = value
    return result


logger = logging.getLogger(__name__)


@dataclass
class SkillMetadata:
    """
    Metadata for an Agent Skill.

    Follows the Agent Skills specification with progressive loading support.
    """

    # Core identifiers
    skill_id: str
    name: str
    description: str

    # Skill type
    skill_type: str = "command"  # command, agent, mode, reference

    # Domain and categorization
    domain: str = "general"
    category: str = "general"

    # Tool and integration info
    tools: list[str] = field(default_factory=list)
    mcp_servers: list[str] = field(default_factory=list)
    personas: list[str] = field(default_factory=list)

    # Flags and parameters
    flags: list[dict[str, Any]] = field(default_factory=list)

    # File references
    skill_dir: str = ""
    skill_file: str = ""

    # Content (loaded on demand for progressive loading)
    content: str = ""
    resources: dict[str, str] = field(default_factory=dict)

    # Evidence requirements
    requires_evidence: bool = False

    # Aliases
    aliases: list[str] = field(default_factory=list)

    # Bundled scripts
    scripts: list[str] = field(default_factory=list)


class SkillAdapter:
    """
    Bidirectional adapter between SKILL.md format and CommandMetadata.

    Features:
    - Parse SKILL.md files into SkillMetadata
    - Convert SkillMetadata to CommandMetadata for registry compatibility
    - Export CommandMetadata to SKILL.md format
    - Support progressive loading (metadata → instructions → resources)
    """

    def __init__(self):
        """Initialize skill adapter."""
        self._metadata_cache: dict[str, SkillMetadata] = {}

    def load_skill(self, skill_path: Path) -> SkillMetadata | None:
        """
        Load skill from SKILL.md file.

        Args:
            skill_path: Path to SKILL.md file or skill directory

        Returns:
            SkillMetadata or None if loading fails
        """
        # Note: We can now parse without PyYAML using _parse_simple_yaml

        # Handle both file and directory paths
        if skill_path.is_dir():
            skill_file = skill_path / "SKILL.md"
        else:
            skill_file = skill_path
            skill_path = skill_file.parent

        if not skill_file.exists():
            logger.warning(f"SKILL.md not found: {skill_file}")
            return None

        try:
            content = skill_file.read_text(encoding="utf-8")
            return self._parse_skill_md(content, skill_path, skill_file)
        except Exception as e:
            logger.error(f"Error loading skill from {skill_file}: {e}")
            return None

    def _parse_skill_md(
        self, content: str, skill_dir: Path, skill_file: Path
    ) -> SkillMetadata | None:
        """
        Parse SKILL.md content into SkillMetadata.

        Args:
            content: Raw SKILL.md content
            skill_dir: Directory containing the skill
            skill_file: Path to SKILL.md file

        Returns:
            SkillMetadata or None if parsing fails
        """
        # Extract YAML frontmatter
        frontmatter_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
        if not frontmatter_match:
            logger.warning(f"No frontmatter in {skill_file}")
            return None

        try:
            if yaml is not None:
                frontmatter = yaml.safe_load(frontmatter_match.group(1))
            else:
                # Fallback to simple parser
                frontmatter = _parse_simple_yaml(frontmatter_match.group(1))
        except Exception as e:
            logger.error(f"Invalid YAML frontmatter in {skill_file}: {e}")
            return None

        # Extract skill body
        body = content[frontmatter_match.end() :]

        # Determine skill type from directory name
        dir_name = skill_dir.name
        if dir_name.startswith("sc-"):
            skill_type = "command"
        elif dir_name.startswith("agent-"):
            skill_type = "agent"
        elif dir_name.startswith("mode-"):
            skill_type = "mode"
        else:
            skill_type = "reference"

        # Extract skill ID from name or directory
        skill_id = frontmatter.get("name", dir_name)

        # Parse tools from frontmatter or body
        tools = self._extract_tools(frontmatter, body)

        # Parse MCP servers
        mcp_servers = frontmatter.get("mcp-servers", []) or []
        if isinstance(mcp_servers, str):
            mcp_servers = [s.strip() for s in mcp_servers.split(",")]

        # Parse personas
        personas = frontmatter.get("personas", []) or []
        if isinstance(personas, str):
            personas = [p.strip() for p in personas.split(",")]

        # Parse flags
        flags = self._extract_flags(frontmatter, body)

        # Extract domain from body
        domain = self._extract_domain(body)

        # Determine category
        category = frontmatter.get(
            "category", self._infer_category(skill_type, dir_name)
        )

        # Check for evidence requirements
        requires_evidence = self._check_evidence_requirement(body)

        # Find bundled scripts
        scripts = self._find_scripts(skill_dir)

        # Parse aliases
        aliases = frontmatter.get("aliases", []) or []

        # Load resources (progressive loading - just paths for now)
        resources = self._discover_resources(skill_dir)

        return SkillMetadata(
            skill_id=skill_id,
            name=frontmatter.get("name", skill_id),
            description=frontmatter.get("description", ""),
            skill_type=skill_type,
            domain=domain,
            category=category,
            tools=tools,
            mcp_servers=mcp_servers,
            personas=personas,
            flags=flags,
            skill_dir=str(skill_dir),
            skill_file=str(skill_file),
            content=body,
            resources=resources,
            requires_evidence=requires_evidence,
            aliases=aliases,
            scripts=scripts,
        )

    def _extract_tools(self, frontmatter: dict, body: str) -> list[str]:
        """Extract tools from frontmatter or body."""
        tools = frontmatter.get("tools", [])
        if isinstance(tools, str):
            tools = [t.strip() for t in tools.split(",")]

        # Also check for Tools section in body
        tools_match = re.search(r"##\s*Tools\s*\n(.*?)(?=\n##|\Z)", body, re.DOTALL)
        if tools_match:
            tools_section = tools_match.group(1)
            # Extract tool names from bullet points or Primary: line
            primary_match = re.search(r"Primary:\s*(.+)", tools_section)
            if primary_match:
                tools.extend([t.strip() for t in primary_match.group(1).split(",")])
            bullet_tools = re.findall(r"[-*]\s*\*\*(\w+)\*\*", tools_section)
            tools.extend(bullet_tools)

        return list(set(tools))  # Deduplicate

    def _extract_flags(self, frontmatter: dict, body: str) -> list[dict[str, Any]]:
        """Extract flags from frontmatter or body."""
        flags = frontmatter.get("flags", []) or []

        # Also parse flag table from body
        flags_match = re.search(r"##\s*Flags\s*\n(.*?)(?=\n##|\Z)", body, re.DOTALL)
        if flags_match:
            table_content = flags_match.group(1)
            # Parse markdown table rows
            rows = re.findall(
                r"\|\s*`--(\w+)`\s*\|\s*(\w+)\s*\|\s*([^|]*)\s*\|\s*([^|]*)\s*\|",
                table_content,
            )
            for row in rows:
                flag_name, flag_type, default, description = row
                flag = {
                    "name": flag_name,
                    "type": flag_type.strip(),
                    "default": default.strip(),
                    "description": description.strip(),
                }
                # Check if flag already exists
                if not any(f.get("name") == flag_name for f in flags):
                    flags.append(flag)

        return flags

    def _extract_domain(self, body: str) -> str:
        """Extract domain from body content."""
        domain_match = re.search(r"##\s*Domain\s*\n\s*(\w+(?:\s+\w+)*)", body)
        if domain_match:
            return domain_match.group(1).strip()
        return "general"

    def _check_evidence_requirement(self, body: str) -> bool:
        """Check if skill requires evidence."""
        evidence_patterns = [
            r"requires evidence",
            r"evidence required",
            r"you must.*show.*output",
            r"you must.*provide.*proof",
        ]
        body_lower = body.lower()
        return any(re.search(p, body_lower) for p in evidence_patterns)

    def _find_scripts(self, skill_dir: Path) -> list[str]:
        """Find bundled scripts in skill directory."""
        scripts_dir = skill_dir / "scripts"
        if not scripts_dir.exists():
            return []

        scripts = []
        for script_file in scripts_dir.glob("*.py"):
            scripts.append(str(script_file))

        return scripts

    def _discover_resources(self, skill_dir: Path) -> dict[str, str]:
        """Discover additional resources in skill directory."""
        resources = {}

        # Look for common resource files
        resource_patterns = ["PERSONAS.md", "EXAMPLES.md", "REFERENCE.md", "README.md"]
        for pattern in resource_patterns:
            resource_file = skill_dir / pattern
            if resource_file.exists():
                resources[pattern] = str(resource_file)

        return resources

    def _infer_category(self, skill_type: str, dir_name: str) -> str:
        """Infer category from skill type and directory name."""
        if skill_type == "command":
            return "command"
        elif skill_type == "agent":
            # Try to extract category from agent directory structure
            if "core-development" in dir_name:
                return "core-development"
            elif "language" in dir_name:
                return "language-specialists"
            elif "infrastructure" in dir_name:
                return "infrastructure"
            elif "quality" in dir_name or "security" in dir_name:
                return "quality-security"
            elif "data" in dir_name or "ai" in dir_name:
                return "data-ai"
            return "agent"
        return "general"

    def to_command_metadata(self, skill: SkillMetadata) -> CommandMetadata:
        """
        Convert SkillMetadata to CommandMetadata for registry compatibility.

        Args:
            skill: SkillMetadata to convert

        Returns:
            CommandMetadata compatible with CommandRegistry
        """
        # Map skill complexity
        complexity = "standard"
        if "advanced" in skill.description.lower():
            complexity = "advanced"
        elif "basic" in skill.description.lower():
            complexity = "basic"

        return CommandMetadata(
            name=skill.name,
            description=skill.description,
            category=skill.category,
            complexity=complexity,
            mcp_servers=skill.mcp_servers,
            personas=skill.personas,
            triggers=[],  # Skills don't have explicit triggers
            flags=skill.flags,
            parameters={},  # Extract from flags if needed
            file_path=skill.skill_file,
            content=skill.content,
            requires_evidence=skill.requires_evidence,
            aliases=skill.aliases,
        )

    def from_command_metadata(self, command: CommandMetadata) -> SkillMetadata:
        """
        Convert CommandMetadata to SkillMetadata for export.

        Args:
            command: CommandMetadata to convert

        Returns:
            SkillMetadata for SKILL.md export
        """
        # Determine skill type from command name
        if command.name.startswith("agent-"):
            skill_type = "agent"
        elif command.name.startswith("mode-"):
            skill_type = "mode"
        else:
            skill_type = "command"

        skill_id = f"sc-{command.name}" if skill_type == "command" else command.name

        return SkillMetadata(
            skill_id=skill_id,
            name=command.name,
            description=command.description,
            skill_type=skill_type,
            domain="general",
            category=command.category,
            tools=[],  # Would need to extract from content
            mcp_servers=command.mcp_servers,
            personas=command.personas,
            flags=command.flags,
            skill_dir="",
            skill_file=command.file_path,
            content=command.content,
            requires_evidence=command.requires_evidence,
            aliases=command.aliases,
        )

    def export_to_skill_md(self, skill: SkillMetadata) -> str:
        """
        Export SkillMetadata to SKILL.md format.

        Args:
            skill: SkillMetadata to export

        Returns:
            SKILL.md content string
        """
        # Build YAML frontmatter
        frontmatter = {
            "name": skill.name,
            "description": skill.description,
        }

        if yaml is None:
            # Fallback to simple string formatting
            yaml_str = f"name: {skill.name}\ndescription: {skill.description}"
        else:
            yaml_str = yaml.dump(frontmatter, default_flow_style=False).strip()

        # Build body
        body_parts = [
            f"# {skill.name.replace('-', ' ').title()}",
            "",
            skill.description,
            "",
        ]

        if skill.domain:
            body_parts.extend(["## Domain", "", skill.domain, ""])

        if skill.tools:
            tools_list = ", ".join(skill.tools[:6])
            body_parts.extend(["## Tools", "", f"Primary: {tools_list}", ""])

        if skill.mcp_servers:
            servers = ", ".join(skill.mcp_servers)
            body_parts.extend(["## MCP Integration", "", f"Servers: {servers}", ""])

        body_parts.extend(
            ["## Activation", "", f"Use for {skill.name} related tasks.", ""]
        )

        body = "\n".join(body_parts)

        return f"---\n{yaml_str}\n---\n\n{body}"

    def get_cached_skill(self, skill_id: str) -> SkillMetadata | None:
        """Get skill from cache by ID."""
        return self._metadata_cache.get(skill_id)

    def cache_skill(self, skill: SkillMetadata) -> None:
        """Add skill to cache."""
        self._metadata_cache[skill.skill_id] = skill

    def clear_cache(self) -> None:
        """Clear skill cache."""
        self._metadata_cache.clear()
