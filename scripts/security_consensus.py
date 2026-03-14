#!/usr/bin/env python3
"""
Security Consensus Validator using PAL MCP

Uses Claude Opus 4.6 with extended thinking to validate Bandit security findings.
For each high-severity finding, validates:
1. True positive or false positive?
2. Risk level (critical/high/medium/low)
3. Recommended fix (if true positive)

Cost: $20-35 per consensus run (for 3-20 findings)
"""

import json
import os
import sys
from pathlib import Path
from typing import Any


def load_high_severity_findings(findings_path: Path) -> list[dict[str, Any]]:
    """Load high severity findings from Bandit JSON output."""
    with open(findings_path) as f:
        return json.load(f)


def format_finding_for_prompt(finding: dict[str, Any]) -> str:
    """Format a single Bandit finding for the consensus prompt."""
    return f"""
**Finding {finding.get("test_id", "UNKNOWN")}**
- **File**: `{finding.get("filename", "unknown")}`
- **Line**: {finding.get("line_number", "N/A")}
- **Severity**: {finding.get("issue_severity", "UNKNOWN")}
- **Confidence**: {finding.get("issue_confidence", "UNKNOWN")}
- **Issue**: {finding.get("issue_text", "No description")}

**Code**:
```python
{finding.get("code", "Code not available")}
```
"""


def build_consensus_prompt(findings: list[dict[str, Any]]) -> str:
    """Build the consensus validation prompt for Claude."""
    findings_formatted = "\n".join(
        format_finding_for_prompt(f)
        for f in findings[:20]  # Limit to 20
    )

    return f"""You are a security expert reviewing automated security scan findings from Bandit (a Python security linter).

Your task: Validate each finding and provide actionable recommendations.

## Findings to Review ({len(findings[:20])} total)

{findings_formatted}

## Your Analysis

For each finding, provide:

1. **Validation**: True positive or false positive?
   - True positive: Real security vulnerability
   - False positive: Bandit flagged safe code incorrectly

2. **Risk Level**: If true positive, assess actual risk
   - **Critical**: Exploitable vulnerability with severe impact (data breach, RCE, etc.)
   - **High**: Significant security issue requiring immediate fix
   - **Medium**: Security weakness that should be addressed soon
   - **Low**: Minor issue or edge case

3. **Recommended Fix**: If true positive, suggest specific code change
   - Be concrete: provide code snippets if possible
   - Explain why the fix resolves the vulnerability

4. **Justification**: Explain your reasoning
   - Why is this a true/false positive?
   - What makes this risk level appropriate?
   - Are there mitigating factors?

## Output Format

Respond with a JSON object:

```json
{{
  "findings_validated": [
    {{
      "finding_id": "B123",
      "file": "scripts/example.py",
      "line": 42,
      "is_true_positive": true,
      "risk_level": "high",
      "recommended_fix": "Use parameterized queries instead of string concatenation",
      "justification": "String concatenation in SQL query creates SQL injection vulnerability."
    }}
  ],
  "summary": {{
    "total_reviewed": 5,
    "true_positives": 3,
    "false_positives": 2,
    "critical_count": 0,
    "high_count": 2,
    "medium_count": 1,
    "low_count": 0
  }},
  "overall_recommendation": "Fix 2 high-risk issues immediately. Review medium-risk finding before next release."
}}
```

## Important Considerations

- **Context matters**: Consider the application's security posture
- **False positives are common**: Bandit is conservative, so validate carefully
- **Defense in depth**: Even if one control exists, additional vulnerabilities may still be exploitable
- **Real-world exploitability**: Focus on issues attackable by real adversaries

Begin your analysis."""


def run_consensus(findings: list[dict[str, Any]], api_key: str) -> dict[str, Any]:
    """Run PAL MCP consensus using Claude Opus 4.6 with extended thinking."""
    # LET-IT-CRASH-EXCEPTION: IMPORT_GUARD - anthropic only needed for API calls
    try:
        import anthropic
    except ImportError:
        print("::error::anthropic package not installed", file=sys.stderr)
        print("Install with: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    prompt = build_consensus_prompt(findings)

    # LET-IT-CRASH-EXCEPTION: API_BOUNDARY - Anthropic API call
    response = client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=16000,
        temperature=0,
        thinking={
            "type": "enabled",
            "budget_tokens": 10000,
        },
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = ""
    for block in response.content:
        if block.type == "text":
            response_text += block.text

    # Find JSON in response (handle markdown code blocks)
    json_start = response_text.find("```json")
    if json_start != -1:
        json_start = response_text.find("\n", json_start) + 1
        json_end = response_text.find("```", json_start)
        response_text = response_text[json_start:json_end].strip()
    else:
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            response_text = response_text[json_start:json_end]

    result = json.loads(response_text)

    result["_metadata"] = {
        "model": "claude-opus-4-20250514",
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
        "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
    }

    return result


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate cost based on Claude Opus 4.6 pricing."""
    # Opus 4.6 pricing (as of 2026-03):
    # Input: $15 / 1M tokens
    # Output: $75 / 1M tokens
    input_cost = (input_tokens / 1_000_000) * 15
    output_cost = (output_tokens / 1_000_000) * 75
    return round(input_cost + output_cost, 2)


def main():
    """Main entry point for security consensus validation."""
    findings_path = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/high-severity.json")
    output_path = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/consensus-results.json")

    # Let It Crash: required env var
    api_key = os.environ["ANTHROPIC_API_KEY"]

    print(f"Loading high severity findings from {findings_path}...")
    findings = load_high_severity_findings(findings_path)

    if not findings:
        print("No findings to validate. Skipping consensus.")
        result = {
            "findings_validated": [],
            "summary": {
                "total_reviewed": 0,
                "true_positives": 0,
                "false_positives": 0,
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "low_count": 0,
            },
            "overall_recommendation": "No high severity findings detected.",
            "_metadata": {
                "model": "N/A",
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        }
    else:
        print(f"Running consensus validation on {len(findings)} findings...")
        result = run_consensus(findings, api_key)

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Consensus validation complete. Results saved to {output_path}")

    summary = result.get("summary", {})
    metadata = result.get("_metadata", {})

    print("\n## Consensus Validation Results\n")
    print(f"- **Findings reviewed**: {summary.get('total_reviewed', 0)}")
    print(f"- **True positives**: {summary.get('true_positives', 0)}")
    print(f"- **False positives**: {summary.get('false_positives', 0)}")
    print(f"- **Critical risk**: {summary.get('critical_count', 0)}")
    print(f"- **High risk**: {summary.get('high_count', 0)}")
    print(f"- **Medium risk**: {summary.get('medium_count', 0)}")
    print(f"- **Low risk**: {summary.get('low_count', 0)}")
    print(f"\n**Recommendation**: {result.get('overall_recommendation', 'N/A')}")

    if metadata.get("input_tokens"):
        cost = estimate_cost(metadata["input_tokens"], metadata["output_tokens"])
        print(f"\n**Cost**: ${cost}")
        print(
            f"**Tokens**: {metadata['total_tokens']:,} "
            f"({metadata['input_tokens']:,} in + {metadata['output_tokens']:,} out)"
        )

    if summary.get("critical_count", 0) > 0 or summary.get("high_count", 0) > 0:
        print(
            "\n::warning::Critical or high-risk vulnerabilities detected. Manual review required."
        )


if __name__ == "__main__":
    main()
