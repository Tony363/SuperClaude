#!/usr/bin/env python3
"""
Strict JSON Schema Validation for Review Findings

Validates review-findings.json against the expected schema.
Returns exit code 0 if valid, 1 if invalid.
Writes sanitized (valid-only) findings to output file.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from finding_utils import validate_finding


def validate_findings_file(findings_path: Path) -> tuple[bool, str, dict | None]:
    """Validate a findings JSON file against the schema.

    Returns (is_valid, message, sanitized_data).
    """
    if not findings_path.exists():
        return (False, f"File not found: {findings_path}", None)

    try:
        with open(findings_path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return (False, f"Invalid JSON: {e}", None)

    if not isinstance(data, dict):
        return (False, "Root must be a JSON object", None)

    if "findings" not in data:
        return (False, "Missing 'findings' key", None)

    if not isinstance(data["findings"], list):
        return (False, "'findings' must be an array", None)

    valid_findings = []
    invalid_count = 0

    for i, finding in enumerate(data["findings"]):
        if validate_finding(finding):
            valid_findings.append(finding)
        else:
            invalid_count += 1
            print(f"Warning: Finding {i} failed validation, skipping", file=sys.stderr)

    sanitized = {
        "findings": valid_findings,
        "summary": data.get(
            "summary",
            {"total": len(valid_findings), "by_category": {}},
        ),
    }
    sanitized["summary"]["total"] = len(valid_findings)

    msg = f"Validated: {len(valid_findings)} valid, {invalid_count} rejected"
    return (len(valid_findings) > 0 or invalid_count == 0, msg, sanitized)


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: validate_findings_schema.py <findings.json> [output.json]",
            file=sys.stderr,
        )
        sys.exit(1)

    findings_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    is_valid, message, sanitized = validate_findings_file(findings_path)
    print(message, file=sys.stderr)

    if sanitized and output_path:
        with open(output_path, "w") as f:
            json.dump(sanitized, f, indent=2)
        print(f"Sanitized output written to: {output_path}", file=sys.stderr)
    elif sanitized:
        json.dump(sanitized, sys.stdout, indent=2)

    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
