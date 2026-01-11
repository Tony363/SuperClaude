#!/usr/bin/env python3
"""
SuperClaude Agent Frontmatter Validator

Validates agent markdown files against the schema for the tiered architecture.
Supports core agents, traits, and extensions.

Usage:
    python scripts/validate_agents.py [--strict] [--verbose]

Exit codes:
    0: All validations passed (or warnings only in non-strict mode)
    1: Validation errors found
    2: Configuration/setup error
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

# =============================================================================
# Configuration
# =============================================================================

# Paths to scan for active agents (relative to repo root)
ACTIVE_PATHS = [
    "agents/core",
    "agents/traits",
    "agents/extensions",
]

# Paths to ignore (deprecated/legacy)
IGNORED_PATHS = [
    "agents/DEPRECATED",
    "agents/extended",  # Legacy, to be moved
]

# Valid tier values
VALID_TIERS = {"core", "trait", "extension"}

# Valid tool names (Claude Code standard tools)
VALID_TOOLS = {
    "Read",
    "Write",
    "Edit",
    "Bash",
    "Glob",
    "Grep",
    "Task",
    "WebFetch",
    "WebSearch",
    "NotebookEdit",
    "AskUserQuestion",
    "TodoWrite",
    "KillShell",
    "TaskOutput",
    "LSP",
    "Skill",
    "EnterPlanMode",
    "ExitPlanMode",
}

# Name pattern: lowercase letters, numbers, hyphens
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*[a-z0-9]$|^[a-z]$")


# =============================================================================
# Frontmatter Parsing
# =============================================================================


def extract_frontmatter(content: str) -> Tuple[Optional[Dict], Optional[str]]:
    """Extract YAML frontmatter from markdown content.

    Returns:
        Tuple of (frontmatter_dict, error_message)
    """
    if not content.startswith("---"):
        return None, "File does not start with YAML frontmatter delimiter '---'"

    # Find the closing delimiter
    end_match = re.search(r"\n---\s*\n", content[3:])
    if not end_match:
        return None, "Could not find closing frontmatter delimiter '---'"

    yaml_content = content[3 : end_match.start() + 3]

    try:
        frontmatter = yaml.safe_load(yaml_content)
        if not isinstance(frontmatter, dict):
            return None, f"Frontmatter is not a dictionary: {type(frontmatter)}"
        return frontmatter, None
    except yaml.YAMLError as e:
        return None, f"YAML parse error: {e}"


# =============================================================================
# Validation Functions
# =============================================================================


class ValidationResult:
    """Holds validation results for a single file."""

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.name: Optional[str] = None
        self.tier: Optional[str] = None
        self.traits: List[str] = []

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


def validate_name(fm: dict, result: ValidationResult) -> None:
    """Validate the 'name' field."""
    name = fm.get("name")

    if not name:
        result.add_error("Missing required field: 'name'")
        return

    if not isinstance(name, str):
        result.add_error(f"'name' must be a string, got {type(name).__name__}")
        return

    # Normalize and validate
    normalized = name.lower().strip()
    if not NAME_PATTERN.match(normalized):
        result.add_error(f"'name' must be lowercase alphanumeric with hyphens, got '{name}'")
        return

    result.name = normalized


def validate_description(fm: dict, result: ValidationResult) -> None:
    """Validate the 'description' field."""
    desc = fm.get("description")

    if not desc:
        result.add_error("Missing required field: 'description'")
        return

    if not isinstance(desc, str):
        result.add_error(f"'description' must be a string, got {type(desc).__name__}")
        return

    if len(desc) > 200:
        result.add_warning(f"'description' exceeds 200 chars ({len(desc)} chars)")


def validate_tier(fm: dict, result: ValidationResult) -> None:
    """Validate the 'tier' field."""
    tier = fm.get("tier")

    if not tier:
        result.add_error("Missing required field: 'tier'")
        return

    if tier not in VALID_TIERS:
        result.add_error(f"'tier' must be one of {VALID_TIERS}, got '{tier}'")
        return

    result.tier = tier


def validate_triggers(fm: dict, result: ValidationResult) -> None:
    """Validate the 'triggers' field (warning-only for now)."""
    triggers = fm.get("triggers")
    tier = result.tier

    # Traits should NOT have triggers (they're composable modifiers)
    if tier == "trait":
        if triggers and len(triggers) > 0:
            result.add_warning(
                "Traits should not define 'triggers' - they are composable modifiers"
            )
        return

    # For core/extension: triggers recommended but not required (Phase 1)
    if not triggers:
        result.add_warning("Missing 'triggers' - recommended for agent discovery")
        return

    if not isinstance(triggers, list):
        result.add_error(f"'triggers' must be a list, got {type(triggers).__name__}")
        return

    if len(triggers) == 0:
        result.add_warning("'triggers' is empty - consider adding discovery keywords")


def validate_tools(fm: dict, result: ValidationResult) -> None:
    """Validate the 'tools' field."""
    tools = fm.get("tools")

    if not tools:
        return  # Optional field

    if not isinstance(tools, list):
        result.add_error(f"'tools' must be a list, got {type(tools).__name__}")
        return

    for tool in tools:
        if tool not in VALID_TOOLS:
            result.add_warning(f"Unknown tool '{tool}' - not in standard tool list")


def validate_priority(fm: dict, result: ValidationResult) -> None:
    """Validate the 'priority' field."""
    priority = fm.get("priority")
    tier = result.tier

    # Traits should NOT have priority
    if tier == "trait" and priority is not None:
        result.add_warning(
            "Traits should not define 'priority' - they don't participate in selection"
        )
        return

    if priority is None:
        return  # Optional field

    if not isinstance(priority, int):
        result.add_error(f"'priority' must be an integer, got {type(priority).__name__}")
        return

    if priority < 1 or priority > 3:
        result.add_warning(f"'priority' should be 1-3, got {priority}")


def validate_traits_field(fm: dict, result: ValidationResult) -> None:
    """Validate the 'traits' field (for agent composition)."""
    traits = fm.get("traits")
    tier = result.tier

    # Traits should NOT reference other traits (avoid complexity)
    if tier == "trait" and traits:
        result.add_warning("Traits should not reference other traits")
        return

    if not traits:
        return  # Optional field

    if not isinstance(traits, list):
        result.add_error(f"'traits' must be a list, got {type(traits).__name__}")
        return

    # Store for cross-file validation
    result.traits = [t for t in traits if isinstance(t, str)]


def validate_category(fm: dict, result: ValidationResult) -> None:
    """Validate the 'category' field (optional, for organization)."""
    category = fm.get("category")

    if not category:
        return  # Optional

    if not isinstance(category, str):
        result.add_warning(f"'category' should be a string, got {type(category).__name__}")


def validate_file(filepath: Path) -> ValidationResult:
    """Validate a single agent markdown file."""
    result = ValidationResult(filepath)

    # Read file
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        result.add_error(f"Failed to read file: {e}")
        return result

    # Extract frontmatter
    fm, error = extract_frontmatter(content)
    if error:
        result.add_error(error)
        return result

    if not fm:
        result.add_error("Empty frontmatter")
        return result

    # Run all validations
    validate_name(fm, result)
    validate_description(fm, result)
    validate_tier(fm, result)
    validate_triggers(fm, result)
    validate_tools(fm, result)
    validate_priority(fm, result)
    validate_traits_field(fm, result)
    validate_category(fm, result)

    return result


# =============================================================================
# Cross-File Validation
# =============================================================================


def validate_uniqueness(results: List[ValidationResult]) -> List[str]:
    """Check for duplicate agent names across all files."""
    errors = []
    names_seen: Dict[str, Path] = {}

    for result in results:
        if result.name:
            if result.name in names_seen:
                errors.append(
                    f"Duplicate agent name '{result.name}': "
                    f"{names_seen[result.name]} and {result.filepath}"
                )
            else:
                names_seen[result.name] = result.filepath

    return errors


def validate_trait_references(results: List[ValidationResult]) -> List[str]:
    """Check that all referenced traits exist."""
    errors = []

    # Collect all trait names
    trait_names = {r.name for r in results if r.tier == "trait" and r.name}

    # Check references
    for result in results:
        for trait_ref in result.traits:
            if trait_ref not in trait_names:
                errors.append(f"{result.filepath}: references unknown trait '{trait_ref}'")

    return errors


def check_for_cycles(results: List[ValidationResult]) -> List[str]:
    """Check for circular trait references (defensive, shouldn't happen)."""
    # With current rules (traits can't reference traits), cycles are impossible
    # But keeping this for future-proofing
    return []


# =============================================================================
# Main Entry Point
# =============================================================================


def find_agent_files(repo_root: Path) -> List[Path]:
    """Find all agent markdown files in active paths."""
    files = []

    for path_str in ACTIVE_PATHS:
        path = repo_root / path_str
        if path.exists() and path.is_dir():
            files.extend(path.glob("*.md"))

    return sorted(files)


def print_results(
    results: List[ValidationResult], cross_errors: List[str], verbose: bool = False
) -> Tuple[int, int]:
    """Print validation results and return counts."""
    total_errors = len(cross_errors)
    total_warnings = 0

    for result in results:
        total_errors += len(result.errors)
        total_warnings += len(result.warnings)

        if result.has_errors or (verbose and result.has_warnings):
            print(f"\n{result.filepath}:")
            for err in result.errors:
                print(f"  ERROR: {err}")
            if verbose:
                for warn in result.warnings:
                    print(f"  WARNING: {warn}")

    if cross_errors:
        print("\nCross-file validation errors:")
        for err in cross_errors:
            print(f"  ERROR: {err}")

    return total_errors, total_warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate SuperClaude agent frontmatter")
    parser.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show warnings even in non-strict mode"
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Repository root (defaults to script parent's parent)",
    )
    args = parser.parse_args()

    # Determine repo root
    if args.repo_root:
        repo_root = args.repo_root.resolve()
    else:
        repo_root = Path(__file__).parent.parent.resolve()

    if not (repo_root / "CLAUDE.md").exists():
        print(f"ERROR: Could not find CLAUDE.md in {repo_root}", file=sys.stderr)
        print("Are you running from the SuperClaude repository?", file=sys.stderr)
        return 2

    # Find agent files
    files = find_agent_files(repo_root)

    if not files:
        print("No agent files found in active paths.")
        print(f"Searched: {', '.join(ACTIVE_PATHS)}")
        print("(This is OK during initial setup)")
        return 0

    print(f"Validating {len(files)} agent file(s)...")

    # Validate each file
    results = [validate_file(f) for f in files]

    # Cross-file validation
    cross_errors = []
    cross_errors.extend(validate_uniqueness(results))
    cross_errors.extend(validate_trait_references(results))
    cross_errors.extend(check_for_cycles(results))

    # Print results
    total_errors, total_warnings = print_results(
        results, cross_errors, verbose=args.verbose or args.strict
    )

    # Summary
    print(f"\n{'=' * 50}")
    print(f"Files validated: {len(files)}")
    print(f"Errors: {total_errors}")
    print(f"Warnings: {total_warnings}")

    if total_errors > 0:
        print("\nValidation FAILED")
        return 1

    if args.strict and total_warnings > 0:
        print("\nValidation FAILED (strict mode, warnings treated as errors)")
        return 1

    print("\nValidation PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
