#!/usr/bin/env python3
"""
JSON Schema Validator for SuperClaude Agent Frontmatter.

Validates agent markdown files against config/schemas/agent.schema.json.
This provides external tooling compatibility alongside the Python validator.

Usage:
    python scripts/validate_schema.py [--verbose]

Exit codes:
    0: All validations passed
    1: Validation errors found
    2: Schema file not found
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

try:
    from jsonschema import Draft202012Validator

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


# Paths
REPO_ROOT = Path(__file__).parent.parent
SCHEMA_PATH = REPO_ROOT / "config" / "schemas" / "agent.schema.json"
AGENTS_DIR = REPO_ROOT / "agents"

# Directories to validate
ACTIVE_PATHS = ["core", "traits", "extensions"]


def extract_frontmatter(content: str) -> Optional[dict[str, Any]]:
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


def validate_file(filepath: Path, validator: Any, verbose: bool = False) -> list[str]:
    """Validate a single agent file against the schema."""
    errors = []

    try:
        content = filepath.read_text(encoding="utf-8")
        frontmatter = extract_frontmatter(content)

        if not frontmatter:
            errors.append(f"{filepath}: No valid frontmatter found")
            return errors

        # Validate against schema
        validation_errors = list(validator.iter_errors(frontmatter))

        for error in validation_errors:
            path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
            errors.append(f"{filepath}: {path}: {error.message}")

        if verbose and not errors:
            print(f"  ✓ {filepath.name}")

    except Exception as e:
        errors.append(f"{filepath}: Failed to read: {e}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate agent frontmatter against JSON Schema")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show successful validations")
    args = parser.parse_args()

    # Check dependencies
    if not HAS_JSONSCHEMA:
        print("WARNING: jsonschema not installed, skipping JSON Schema validation")
        print("Install with: pip install jsonschema")
        return 0  # Non-blocking, Python validator is primary

    # Load schema
    if not SCHEMA_PATH.exists():
        print(f"ERROR: Schema file not found: {SCHEMA_PATH}")
        return 2

    try:
        with open(SCHEMA_PATH) as f:
            schema = json.load(f)
        validator = Draft202012Validator(schema)
    except Exception as e:
        print(f"ERROR: Failed to load schema: {e}")
        return 2

    print(f"Validating agents against {SCHEMA_PATH.name}...")

    # Find and validate all agent files
    all_errors = []
    file_count = 0

    for subdir in ACTIVE_PATHS:
        dir_path = AGENTS_DIR / subdir
        if not dir_path.exists():
            continue

        if args.verbose:
            print(f"\n{subdir}/")

        for md_file in sorted(dir_path.glob("*.md")):
            file_count += 1
            errors = validate_file(md_file, validator, args.verbose)
            all_errors.extend(errors)

    # Report results
    print(f"\n{'=' * 50}")
    print(f"Files validated: {file_count}")
    print(f"Errors: {len(all_errors)}")

    if all_errors:
        print("\nValidation errors:")
        for error in all_errors:
            print(f"  ✗ {error}")
        print("\nJSON Schema validation FAILED")
        return 1

    print("\nJSON Schema validation PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
