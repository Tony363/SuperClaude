#!/usr/bin/env python3
"""
Agent Selection Script for SuperClaude Skills.

Deterministic agent selection based on weighted scoring algorithm.
Supports the tiered agent architecture with composable traits.

Usage:
    python select_agent.py '{"task": "build react component", "files": ["*.tsx"]}'
    python select_agent.py '{"task": "secure api", "traits": ["security-first", "test-driven"]}'

Input (JSON):
    {
        "task": "task description",
        "files": ["file1.py", "file2.tsx"],
        "languages": ["python", "typescript"],
        "domains": ["frontend", "api"],
        "keywords": ["react", "component"],
        "imports": ["react", "express"],
        "traits": ["security-first", "performance-first"]  # Optional trait modifiers
    }

Output (JSON):
    {
        "selected_agent": "frontend-architect",
        "confidence": "high",
        "score": 0.75,
        "breakdown": {...},
        "matched_criteria": [...],
        "alternatives": [...],
        "traits_applied": ["security-first"],
        "agent_path": "agents/core/frontend-architect.md",
        "trait_paths": ["agents/traits/security-first.md"]
    }
"""

from __future__ import annotations

import fnmatch
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import yaml

# =============================================================================
# Trait Conflict Detection
# =============================================================================

# Hard conflicts: These traits cannot be combined
TRAIT_CONFLICTS: Dict[str, Set[str]] = {
    # minimal-changes is about conservative, careful modifications
    # rapid-prototype is about speed over polish - direct conflict
    "minimal-changes": {"rapid-prototype"},
    "rapid-prototype": {"minimal-changes"},
}

# Soft conflicts: These traits may have tension, warn but allow
TRAIT_TENSIONS: Dict[str, Set[str]] = {
    # legacy-friendly prioritizes backward compat
    # cloud-native assumes modern infrastructure
    # They can coexist but may pull in different directions
    "legacy-friendly": {"cloud-native"},
    "cloud-native": {"legacy-friendly"},
}


# =============================================================================
# Configuration
# =============================================================================


# Find the SuperClaude root directory (contains CLAUDE.md)
def find_superclaude_root() -> Path:
    """Find SuperClaude root by searching upward for CLAUDE.md."""
    current = Path(__file__).resolve()
    for parent in [current] + list(current.parents):
        if (parent / "CLAUDE.md").exists():
            return parent
    # Fallback to script's great-great-grandparent
    return Path(__file__).parent.parent.parent.parent.parent


SUPERCLAUDE_ROOT = find_superclaude_root()
AGENTS_DIR = SUPERCLAUDE_ROOT / "agents"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class AgentMetadata:
    """Agent metadata from frontmatter."""

    id: str
    name: str
    description: str = ""
    tier: str = "core"
    category: str = ""
    priority: int = 2
    triggers: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    file_path: str = ""

    # Computed fields for scoring
    domains: List[str] = field(default_factory=list)
    languages: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    file_patterns: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)


@dataclass
class TraitMetadata:
    """Trait metadata from frontmatter."""

    id: str
    name: str
    description: str = ""
    tier: str = "trait"
    category: str = ""
    file_path: str = ""


@dataclass
class MatchScore:
    """Match score with detailed breakdown."""

    agent_id: str
    total_score: float
    breakdown: Dict[str, float]
    matched_criteria: List[str]
    confidence: str


# =============================================================================
# Frontmatter Parsing
# =============================================================================


def extract_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    """Extract YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return None

    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return None

    yaml_content = content[3 : end_match.start() + 3]

    try:
        return yaml.safe_load(yaml_content)
    except yaml.YAMLError:
        return None


def load_agent_from_file(filepath: Path) -> Optional[AgentMetadata]:
    """Load agent metadata from a markdown file."""
    try:
        content = filepath.read_text(encoding="utf-8")
        fm = extract_frontmatter(content)
        if not fm:
            return None

        # Extract triggers as keywords for scoring
        triggers = fm.get("triggers", [])

        # Determine priority based on tier
        tier = fm.get("tier", "core")
        if tier == "core":
            priority = 1
        elif tier == "extension":
            priority = 2
        else:
            priority = 3

        return AgentMetadata(
            id=fm.get("name", filepath.stem),
            name=fm.get("name", filepath.stem),
            description=fm.get("description", ""),
            tier=tier,
            category=fm.get("category", ""),
            priority=priority,
            triggers=triggers,
            tools=fm.get("tools", []),
            file_path=str(filepath.relative_to(SUPERCLAUDE_ROOT)),
            # Use triggers as keywords for scoring
            keywords=triggers,
            domains=[fm.get("category", "")] if fm.get("category") else [],
        )
    except Exception:
        return None


def load_trait_from_file(filepath: Path) -> Optional[TraitMetadata]:
    """Load trait metadata from a markdown file."""
    try:
        content = filepath.read_text(encoding="utf-8")
        fm = extract_frontmatter(content)
        if not fm:
            return None

        return TraitMetadata(
            id=fm.get("name", filepath.stem),
            name=fm.get("name", filepath.stem),
            description=fm.get("description", ""),
            tier=fm.get("tier", "trait"),
            category=fm.get("category", ""),
            file_path=str(filepath.relative_to(SUPERCLAUDE_ROOT)),
        )
    except Exception:
        return None


# =============================================================================
# Agent Loading
# =============================================================================


def load_all_agents() -> List[AgentMetadata]:
    """Load all agents from core and extensions directories."""
    agents = []

    # Load core agents
    core_dir = AGENTS_DIR / "core"
    if core_dir.exists():
        for filepath in core_dir.glob("*.md"):
            agent = load_agent_from_file(filepath)
            if agent:
                agents.append(agent)

    # Load extension agents
    extensions_dir = AGENTS_DIR / "extensions"
    if extensions_dir.exists():
        for filepath in extensions_dir.glob("*.md"):
            agent = load_agent_from_file(filepath)
            if agent:
                agents.append(agent)

    return agents


def load_all_traits() -> Dict[str, TraitMetadata]:
    """Load all traits from traits directory."""
    traits = {}

    traits_dir = AGENTS_DIR / "traits"
    if traits_dir.exists():
        for filepath in traits_dir.glob("*.md"):
            trait = load_trait_from_file(filepath)
            if trait:
                traits[trait.id] = trait

    return traits


# =============================================================================
# Scoring Algorithm
# =============================================================================


def calculate_match_score(context: Dict[str, Any], metadata: AgentMetadata) -> MatchScore:
    """
    Calculate detailed match score for an agent.

    Scoring components:
    - Keywords/Triggers: 35% weight
    - Domains/Category: 25% weight
    - Task text match: 20% weight
    - File patterns: 10% weight
    - Priority bonus: 10% weight
    """
    score = 0.0
    breakdown = {}
    matched_criteria = []

    # Extract context data
    task_text = context.get("task", "").lower()
    files = [f.lower() for f in context.get("files", [])]
    domains = [d.lower() for d in context.get("domains", [])]
    keywords = [k.lower() for k in context.get("keywords", [])]

    # 1. Keyword/Trigger matching (35% weight)
    keyword_score = 0.0
    if metadata.keywords:
        matched_keywords = []
        for keyword in metadata.keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in task_text:
                keyword_score += 1.0
                matched_keywords.append(keyword)
            elif keyword_lower in keywords:
                keyword_score += 0.8
                matched_keywords.append(keyword)
            elif any(kw in keyword_lower or keyword_lower in kw for kw in keywords):
                keyword_score += 0.3

        keyword_score = min(keyword_score / max(len(metadata.keywords), 1), 1.0)
        if matched_keywords:
            matched_criteria.append(f"triggers: {', '.join(matched_keywords[:3])}")

    breakdown["keywords"] = keyword_score * 0.35
    score += breakdown["keywords"]

    # 2. Domain/Category matching (25% weight)
    domain_score = 0.0
    if metadata.category:
        category_lower = metadata.category.lower()
        if category_lower in task_text or category_lower in domains:
            domain_score = 1.0
            matched_criteria.append(f"category: {metadata.category}")
        elif any(d in category_lower or category_lower in d for d in domains):
            domain_score = 0.5

    breakdown["domains"] = domain_score * 0.25
    score += breakdown["domains"]

    # 3. Task text matching (20% weight)
    task_score = 0.0
    agent_name_parts = metadata.id.replace("-", " ").split()
    for part in agent_name_parts:
        if len(part) > 2 and part.lower() in task_text:
            task_score += 0.5
    task_score = min(task_score, 1.0)
    if task_score > 0:
        matched_criteria.append(f"name match: {metadata.id}")

    breakdown["task_match"] = task_score * 0.20
    score += breakdown["task_match"]

    # 4. File pattern matching (10% weight)
    file_pattern_score = 0.0
    if metadata.file_patterns and files:
        for pattern in metadata.file_patterns:
            pattern_lower = pattern.lower()
            for file in files:
                if pattern_lower in file or fnmatch.fnmatch(file, pattern_lower):
                    file_pattern_score = 1.0
                    matched_criteria.append(f"file: {pattern}")
                    break
            if file_pattern_score > 0:
                break

    breakdown["file_patterns"] = file_pattern_score * 0.10
    score += breakdown["file_patterns"]

    # 5. Priority bonus (10% weight)
    priority_bonus = (4 - metadata.priority) / 3 * 0.10
    breakdown["priority"] = priority_bonus
    score += priority_bonus

    # Determine confidence level
    if score >= 0.7:
        confidence = "excellent"
    elif score >= 0.5:
        confidence = "high"
    elif score >= 0.3:
        confidence = "medium"
    else:
        confidence = "low"

    return MatchScore(
        agent_id=metadata.id,
        total_score=score,
        breakdown=breakdown,
        matched_criteria=matched_criteria,
        confidence=confidence,
    )


# =============================================================================
# Main Selection Logic
# =============================================================================


def validate_traits(
    requested_traits: List[str], available_traits: Dict[str, TraitMetadata]
) -> tuple[List[str], List[str]]:
    """Validate requested traits and return valid/invalid lists."""
    valid = []
    invalid = []

    for trait_name in requested_traits:
        if trait_name in available_traits:
            valid.append(trait_name)
        else:
            invalid.append(trait_name)

    return valid, invalid


def detect_trait_conflicts(
    traits: List[str],
) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
    """
    Detect conflicts and tensions between requested traits.

    Returns:
        Tuple of (hard_conflicts, soft_tensions)
        Each is a list of (trait1, trait2) pairs that conflict/have tension.
    """
    hard_conflicts = []
    soft_tensions = []

    # Check each pair of traits
    for i, trait1 in enumerate(traits):
        for trait2 in traits[i + 1 :]:
            # Check hard conflicts
            if trait1 in TRAIT_CONFLICTS and trait2 in TRAIT_CONFLICTS[trait1]:
                hard_conflicts.append((trait1, trait2))
            # Check soft tensions
            elif trait1 in TRAIT_TENSIONS and trait2 in TRAIT_TENSIONS[trait1]:
                soft_tensions.append((trait1, trait2))

    return hard_conflicts, soft_tensions


def select_agent(context: Dict[str, Any], top_n: int = 3) -> Dict[str, Any]:
    """
    Select the best agent(s) for a given context.

    Args:
        context: Task context with task, files, languages, traits, etc.
        top_n: Number of top alternatives to return

    Returns:
        Selection result with primary agent, alternatives, and applied traits
    """
    # Load agents and traits
    agents = load_all_agents()
    available_traits = load_all_traits()

    # Fallback if no agents found (use hardcoded general-purpose)
    if not agents:
        return {
            "selected_agent": "general-purpose",
            "confidence": "low",
            "score": 0.0,
            "breakdown": {},
            "matched_criteria": [],
            "alternatives": [],
            "traits_applied": [],
            "agent_path": "agents/core/general-purpose.md",
            "trait_paths": [],
            "warning": "No agents found in agents/ directory",
        }

    # Calculate scores for all agents
    scores = []
    agent_map = {}

    for agent in agents:
        match_score = calculate_match_score(context, agent)
        scores.append(match_score)
        agent_map[agent.id] = agent

    # Sort by total score
    scores.sort(key=lambda x: x.total_score, reverse=True)

    # Primary selection
    primary = scores[0]
    primary_agent = agent_map[primary.agent_id]

    # Build alternatives list
    alternatives = []
    for s in scores[1:top_n]:
        alt_agent = agent_map[s.agent_id]
        alternatives.append(
            {
                "agent_id": s.agent_id,
                "total_score": round(s.total_score, 4),
                "confidence": s.confidence,
                "agent_path": alt_agent.file_path,
            }
        )

    # Process traits
    requested_traits = context.get("traits", [])
    valid_traits, invalid_traits = validate_traits(requested_traits, available_traits)

    # Detect trait conflicts
    hard_conflicts, soft_tensions = detect_trait_conflicts(valid_traits)

    trait_paths = []
    for trait_name in valid_traits:
        trait = available_traits[trait_name]
        trait_paths.append(trait.file_path)

    result = {
        "selected_agent": primary.agent_id,
        "confidence": primary.confidence,
        "score": round(primary.total_score, 4),
        "breakdown": {k: round(v, 4) for k, v in primary.breakdown.items()},
        "matched_criteria": primary.matched_criteria,
        "alternatives": alternatives,
        "traits_applied": valid_traits,
        "agent_path": primary_agent.file_path,
        "trait_paths": trait_paths,
    }

    if invalid_traits:
        result["invalid_traits"] = invalid_traits
        result["available_traits"] = list(available_traits.keys())

    # Include conflict information
    if hard_conflicts:
        result["trait_conflicts"] = [
            {"trait1": t1, "trait2": t2, "severity": "error"} for t1, t2 in hard_conflicts
        ]
        result["conflict_warning"] = (
            f"Conflicting traits detected: {hard_conflicts}. "
            "These traits cannot be combined effectively."
        )

    if soft_tensions:
        result["trait_tensions"] = [
            {"trait1": t1, "trait2": t2, "severity": "warning"} for t1, t2 in soft_tensions
        ]
        if "conflict_warning" not in result:
            result["tension_note"] = (
                f"Trait tensions detected: {soft_tensions}. "
                "These traits may pull in different directions but can coexist."
            )

    return result


def main():
    """Main entry point for script execution."""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No context provided. Pass JSON as first argument."}))
        sys.exit(1)

    try:
        context = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        sys.exit(1)

    result = select_agent(context)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
