"""Fixtures for skill testing."""

import re
from pathlib import Path
from typing import Any

import pytest
import yaml


@pytest.fixture
def skill_root() -> Path:
    """Return the path to the skills directory."""
    return Path(__file__).parent.parent.parent / ".claude" / "skills"


@pytest.fixture
def ask_skill_path(skill_root: Path) -> Path:
    """Return path to ask skill."""
    return skill_root / "ask" / "SKILL.md"


@pytest.fixture
def ask_multi_skill_path(skill_root: Path) -> Path:
    """Return path to ask-multi skill."""
    return skill_root / "ask-multi" / "SKILL.md"


def parse_skill_frontmatter(skill_path: Path) -> dict[str, Any]:
    """Parse YAML frontmatter from a skill file.
    
    Args:
        skill_path: Path to the SKILL.md file
        
    Returns:
        Dictionary of frontmatter key-value pairs
    """
    content = skill_path.read_text()
    
    # Match YAML frontmatter between --- delimiters
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}
    
    return yaml.safe_load(match.group(1)) or {}


def parse_skill_sections(skill_path: Path) -> dict[str, str]:
    """Parse markdown sections from a skill file.
    
    Args:
        skill_path: Path to the SKILL.md file
        
    Returns:
        Dictionary mapping section headers to their content
    """
    content = skill_path.read_text()
    
    # Remove frontmatter
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
            # Top-level header (skill title)
            if current_header:
                sections[current_header] = "\n".join(current_content).strip()
            current_header = "_title"
            current_content = [line[2:].strip()]
        elif current_header:
            current_content.append(line)
    
    if current_header:
        sections[current_header] = "\n".join(current_content).strip()
    
    return sections
