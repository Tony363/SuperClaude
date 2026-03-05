#!/usr/bin/env python3
"""
PAL MCP Consensus Review Integration

Runs multi-model consensus code review on selected files.
Produces structured findings with category, severity, and actionability.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Any


# Finding schema (for validation)
FINDING_SCHEMA = {
    "type": "object",
    "required": ["category", "severity", "file", "line_start", "issue", "suggestion", "confidence", "actionable"],
    "properties": {
        "category": {"enum": ["security", "quality", "performance", "tests"]},
        "severity": {"enum": ["critical", "high", "medium", "low"]},
        "file": {"type": "string"},
        "line_start": {"type": "integer", "minimum": 1},
        "line_end": {"type": "integer", "minimum": 1},
        "issue": {"type": "string"},
        "suggestion": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "actionable": {"type": "boolean"},
    }
}


def load_scope_selection(scope_file: Path) -> Dict[str, Any]:
    """Load scope selection JSON."""
    try:
        with open(scope_file, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"Error loading scope file: {e}", file=sys.stderr)
        sys.exit(1)


def create_review_prompt(files: List[Dict[str, Any]], categories: List[str]) -> str:
    """Create review prompt for PAL MCP consensus."""
    file_list = "\n".join([
        f"- {f['path']} ({f['lines_of_code']} LOC, {f['category']})"
        for f in files
    ])

    categories_str = ", ".join(categories)

    return f"""# Multi-Model Code Review - Nightly Analysis

You are performing a proactive code review on {len(files)} files to identify issues across multiple dimensions: {categories_str}.

## Files to Review

{file_list}

## Review Instructions

For each file, perform a comprehensive analysis focusing on:

1. **Security**: Vulnerabilities, input validation, auth/authz issues, secrets, injection risks
2. **Quality**: Code smells, SOLID violations, complexity, maintainability, readability
3. **Performance**: Algorithmic efficiency, resource usage, N+1 queries, unnecessary operations
4. **Tests**: Missing test coverage, test quality, edge cases, integration test gaps

## Output Format

For each finding, output a JSON object with this EXACT schema:

```json
{{
  "category": "security|quality|performance|tests",
  "severity": "critical|high|medium|low",
  "file": "relative/path/to/file.py",
  "line_start": 42,
  "line_end": 45,
  "issue": "Clear description of the issue",
  "suggestion": "Specific, actionable fix recommendation",
  "confidence": 0.85,
  "actionable": true
}}
```

**CRITICAL**: Output ONLY a JSON array of findings. No markdown, no explanations, no prose.

Example output:
```json
[
  {{
    "category": "security",
    "severity": "high",
    "file": "src/auth.py",
    "line_start": 23,
    "line_end": 25,
    "issue": "Hardcoded secret key in source code",
    "suggestion": "Move secret key to environment variable and load via os.getenv('SECRET_KEY')",
    "confidence": 0.95,
    "actionable": true
  }},
  {{
    "category": "quality",
    "severity": "medium",
    "file": "src/utils.py",
    "line_start": 102,
    "line_end": 102,
    "issue": "Function exceeds 30 lines (KISS violation)",
    "suggestion": "Extract helper function for data validation logic",
    "confidence": 0.80,
    "actionable": true
  }}
]
```

**Severity Guidelines**:
- **critical**: Security vulnerabilities, data loss risks, production-breaking bugs
- **high**: Major design issues, significant performance problems, missing auth checks
- **medium**: Code quality issues, maintainability concerns, minor performance issues
- **low**: Style issues, minor improvements, optional optimizations

**Confidence Guidelines**:
- **0.9-1.0**: Definitely an issue (e.g., SQL injection, hardcoded secrets)
- **0.7-0.9**: Likely an issue (e.g., complex function, missing tests)
- **0.5-0.7**: Possible issue (e.g., potential performance bottleneck)
- **< 0.5**: Don't report (too uncertain)

**Actionability**:
- `true`: Clear, specific fix available
- `false`: Issue identified but fix requires architectural changes or more context

Begin review now. Output JSON array only.
"""


def simulate_pal_consensus_review(prompt: str, models: List[str]) -> List[Dict[str, Any]]:
    """
    Simulate PAL MCP consensus review.

    In production, this would call:
    mcp__pal__consensus(prompt=prompt, models=models)

    For now, this is a placeholder that returns empty findings.
    The workflow will need to be updated to call the actual MCP tool.
    """
    # TODO: Replace with actual PAL MCP call
    # This requires the workflow to use Claude Code Action with MCP enabled
    # Similar to how .github/workflows/ai-review.yml does it

    print(f"[PLACEHOLDER] Would call PAL MCP consensus with models: {models}", file=sys.stderr)
    print(f"[PLACEHOLDER] Prompt length: {len(prompt)} chars", file=sys.stderr)

    # Return empty findings for now
    # In production, parse PAL MCP response and validate against FINDING_SCHEMA
    return []


def validate_finding(finding: Dict[str, Any]) -> bool:
    """Validate finding against schema."""
    try:
        # Check required fields
        required = ["category", "severity", "file", "line_start", "issue", "suggestion", "confidence", "actionable"]
        for field in required:
            if field not in finding:
                return False

        # Check enum values
        if finding["category"] not in ["security", "quality", "performance", "tests"]:
            return False
        if finding["severity"] not in ["critical", "high", "medium", "low"]:
            return False

        # Check types
        if not isinstance(finding["line_start"], int) or finding["line_start"] < 1:
            return False
        if not isinstance(finding["confidence"], (int, float)) or not (0 <= finding["confidence"] <= 1):
            return False
        if not isinstance(finding["actionable"], bool):
            return False

        return True
    except (KeyError, TypeError):
        return False


def deduplicate_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove overlapping findings (same file + line range)."""
    seen = set()
    deduplicated = []

    for finding in findings:
        # Create unique key: file + line_start + line_end (or line_start if no line_end)
        line_end = finding.get("line_end", finding["line_start"])
        key = (finding["file"], finding["line_start"], line_end)

        if key not in seen:
            seen.add(key)
            deduplicated.append(finding)

    return deduplicated


def main():
    parser = argparse.ArgumentParser(
        description="Run PAL MCP consensus code review"
    )
    parser.add_argument(
        "--scope-file",
        type=Path,
        required=True,
        help="Scope selection JSON file"
    )
    parser.add_argument(
        "--models",
        type=str,
        default="gpt-5.2,gemini-3-pro",
        help="Comma-separated model names"
    )
    parser.add_argument(
        "--categories",
        type=str,
        default="security,quality,performance,tests",
        help="Comma-separated review categories"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("review-findings.json"),
        help="Output JSON file"
    )

    args = parser.parse_args()

    # Load scope selection
    scope_data = load_scope_selection(args.scope_file)
    files = scope_data["files"]

    if not files:
        print("No files to review", file=sys.stderr)
        # Write empty findings
        with open(args.output, "w") as f:
            json.dump({"findings": [], "summary": {"total": 0}}, f, indent=2)
        sys.exit(0)

    # Parse models and categories
    models = [m.strip() for m in args.models.split(",")]
    categories = [c.strip() for c in args.categories.split(",")]

    # Create review prompt
    prompt = create_review_prompt(files, categories)

    # Run PAL MCP consensus review
    print(f"Running consensus review with models: {models}")
    raw_findings = simulate_pal_consensus_review(prompt, models)

    # Validate findings
    valid_findings = [f for f in raw_findings if validate_finding(f)]

    invalid_count = len(raw_findings) - len(valid_findings)
    if invalid_count > 0:
        print(f"Warning: {invalid_count} findings failed validation", file=sys.stderr)

    # Deduplicate
    deduplicated = deduplicate_findings(valid_findings)

    duplicate_count = len(valid_findings) - len(deduplicated)
    if duplicate_count > 0:
        print(f"Removed {duplicate_count} duplicate findings")

    # Group by category for summary
    by_category = {}
    for finding in deduplicated:
        cat = finding["category"]
        by_category[cat] = by_category.get(cat, 0) + 1

    # Output result
    output_data = {
        "findings": deduplicated,
        "summary": {
            "total": len(deduplicated),
            "by_category": by_category,
            "models_used": models,
            "categories_requested": categories,
        }
    }

    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"Review complete: {len(deduplicated)} findings")
    print(f"Output written to: {args.output}")


if __name__ == "__main__":
    main()
