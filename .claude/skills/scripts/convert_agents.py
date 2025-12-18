#!/usr/bin/env python3
"""
Agent Conversion Script for SuperClaude Skills Migration.

Converts Extended Agent markdown files to Agent Skills SKILL.md format.

Usage:
    python convert_agents.py [--dry-run]
"""

import re
import sys
from pathlib import Path


def parse_agent_frontmatter(content: str) -> dict:
    """Extract YAML frontmatter from agent markdown."""
    frontmatter = {}

    # Match YAML frontmatter
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if not match:
        return frontmatter, content

    yaml_content = match.group(1)
    body = content[match.end() :]

    # Parse simple YAML (name, description, tools)
    for line in yaml_content.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            # Handle quoted strings
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            frontmatter[key] = value

    return frontmatter, body


def extract_first_paragraph(body: str) -> str:
    """Extract the first paragraph as agent summary."""
    # Skip empty lines and headers
    lines = body.strip().split("\n")
    paragraph = []

    for line in lines:
        line = line.strip()
        if not line:
            if paragraph:
                break
            continue
        if line.startswith("#"):
            continue
        if line.startswith("When invoked:"):
            break
        paragraph.append(line)

    return " ".join(paragraph)[:500] if paragraph else ""


def extract_tools(frontmatter: dict) -> list:
    """Extract tools from frontmatter."""
    tools_str = frontmatter.get("tools", "")
    if not tools_str:
        return []

    # Parse comma-separated tools
    tools = [t.strip() for t in tools_str.split(",") if t.strip()]
    return tools


def extract_checklist(body: str) -> list:
    """Extract key checklist items from body."""
    checklist = []
    in_checklist = False

    for line in body.split("\n"):
        line = line.strip()
        if "checklist:" in line.lower():
            in_checklist = True
            continue
        if in_checklist:
            if line.startswith("-"):
                item = line[1:].strip()
                checklist.append(item)
            elif line and not line.startswith("-"):
                in_checklist = False

    return checklist[:8]  # Limit to 8 items


def extract_sections(body: str) -> dict:
    """Extract major sections from body."""
    sections = {}
    current_section = None
    current_content = []

    for line in body.split("\n"):
        if line.startswith("## "):
            if current_section:
                sections[current_section] = "\n".join(current_content)
            current_section = line[3:].strip()
            current_content = []
        elif current_section:
            current_content.append(line)

    if current_section:
        sections[current_section] = "\n".join(current_content)

    return sections


def generate_skill_md(
    name: str,
    description: str,
    tools: list,
    summary: str,
    checklist: list,
    category: str,
) -> str:
    """Generate SKILL.md content from parsed agent data."""

    # Create skill ID from name
    skill_id = f"agent-{name}"

    # Format tools section
    tools_section = ""
    if tools:
        tools_list = ", ".join(tools[:6])  # Limit displayed tools
        tools_section = f"""
## Tools

Primary: {tools_list}
"""

    # Format checklist
    checklist_section = ""
    if checklist:
        items = "\n".join(f"- {item}" for item in checklist[:6])
        checklist_section = f"""
## Key Capabilities

{items}
"""

    # Determine domain from category
    domain_map = {
        "01-core-development": "Core Development",
        "02-language-specialists": "Language Expertise",
        "03-infrastructure": "Infrastructure & DevOps",
        "04-quality-security": "Quality & Security",
        "05-data-ai": "Data & AI",
        "06-developer-experience": "Developer Experience",
        "07-specialized-domains": "Specialized Domains",
        "08-business-product": "Business & Product",
        "09-meta-orchestration": "Meta Orchestration",
        "10-research-analysis": "Research & Analysis",
    }
    domain = domain_map.get(category, "General")

    # Generate SKILL.md
    skill_content = f"""---
name: {skill_id}
description: {description}
---

# {name.replace("-", " ").title()} Agent

{summary}

## Domain

{domain}
{tools_section}{checklist_section}
## Activation

This agent activates for tasks involving:
- {name.replace("-", " ").replace("pro", "professional").replace("expert", "expertise")} related work
- Domain-specific implementation and optimization
- Technical guidance and best practices

## Integration

Works with other agents for:
- Cross-functional collaboration
- Domain expertise sharing
- Quality validation
"""

    return skill_content


def convert_agent_file(
    source_path: Path, target_dir: Path, dry_run: bool = False
) -> bool:
    """Convert a single agent file to SKILL.md format."""
    try:
        # Read source file
        content = source_path.read_text(encoding="utf-8")

        # Parse frontmatter and body
        frontmatter, body = parse_agent_frontmatter(content)

        if not frontmatter.get("name"):
            print(f"  SKIP: No name in {source_path.name}")
            return False

        name = frontmatter["name"]
        description = frontmatter.get("description", f"{name} agent")
        tools = extract_tools(frontmatter)
        summary = extract_first_paragraph(body)
        checklist = extract_checklist(body)
        category = source_path.parent.name

        # Generate SKILL.md content
        skill_content = generate_skill_md(
            name, description, tools, summary, checklist, category
        )

        # Create target directory
        skill_dir = target_dir / f"agent-{name}"

        if dry_run:
            print(f"  DRY-RUN: Would create {skill_dir}/SKILL.md")
            return True

        skill_dir.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text(skill_content, encoding="utf-8")

        print(f"  Created: agent-{name}/SKILL.md")
        return True

    except Exception as e:
        print(f"  ERROR: {source_path.name}: {e}")
        return False


def main():
    """Main entry point."""
    dry_run = "--dry-run" in sys.argv

    # Paths
    project_root = Path(__file__).parent.parent.parent.parent
    source_dir = project_root / "SuperClaude" / "Agents" / "Extended"
    target_dir = project_root / ".claude" / "skills"

    if not source_dir.exists():
        print(f"ERROR: Source directory not found: {source_dir}")
        sys.exit(1)

    print(f"Converting agents from: {source_dir}")
    print(f"Target directory: {target_dir}")
    print(f"Mode: {'DRY-RUN' if dry_run else 'LIVE'}")
    print()

    # Find all agent files
    agent_files = sorted(source_dir.glob("**/*.md"))

    print(f"Found {len(agent_files)} agent files")
    print()

    success_count = 0
    error_count = 0

    # Process by category
    current_category = None
    for agent_file in agent_files:
        category = agent_file.parent.name

        if category != current_category:
            current_category = category
            print(f"\n[{category}]")

        if convert_agent_file(agent_file, target_dir, dry_run):
            success_count += 1
        else:
            error_count += 1

    print()
    print(f"Conversion complete: {success_count} succeeded, {error_count} failed")

    if not dry_run:
        # Count created files
        created = list(target_dir.glob("agent-*/SKILL.md"))
        print(f"Total agent skills created: {len(created)}")


if __name__ == "__main__":
    main()
