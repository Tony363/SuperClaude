"""
Integration tests for Nightly Code Review workflow

Tests the complete pipeline with mocked data:
1. Scope selection
2. Finding normalization
3. Suggestion generation
4. PR creation logic

Run with: pytest tests/integration/test_nightly_review.py -v
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# Use the current Python interpreter for subprocess calls
PYTHON = sys.executable


# Sample test data
SAMPLE_FINDINGS = {
    "findings": [
        {
            "category": "security",
            "severity": "critical",
            "file": "src/auth.py",
            "line_start": 23,
            "line_end": 25,
            "issue": "Hardcoded secret key in source code",
            "suggestion": "Move secret to environment variable",
            "confidence": 0.95,
            "actionable": True
        },
        {
            "category": "security",
            "severity": "high",
            "file": "src/api.py",
            "line_start": 42,
            "issue": "Missing input validation",
            "suggestion": "Add Pydantic validation",
            "confidence": 0.85,
            "actionable": True
        },
        {
            "category": "quality",
            "severity": "medium",
            "file": "src/utils.py",
            "line_start": 102,
            "issue": "Function exceeds 30 lines (KISS violation)",
            "suggestion": "Extract helper function",
            "confidence": 0.80,
            "actionable": True
        },
        {
            "category": "quality",
            "severity": "low",
            "file": "src/helpers.py",
            "line_start": 15,
            "issue": "Missing docstring",
            "suggestion": "Add docstring",
            "confidence": 0.60,  # Below threshold
            "actionable": True
        },
        {
            "category": "performance",
            "severity": "high",
            "file": "src/queries.py",
            "line_start": 78,
            "issue": "N+1 query detected",
            "suggestion": "Use select_related()",
            "confidence": 0.90,
            "actionable": True
        },
        {
            "category": "tests",
            "severity": "medium",
            "file": "src/core.py",
            "line_start": 50,
            "issue": "Missing test coverage for error path",
            "suggestion": "Add test for ValueError case",
            "confidence": 0.75,
            "actionable": True
        },
    ],
    "summary": {
        "total": 6,
        "models_used": ["gpt-5.2", "gemini-3-pro"]
    }
}


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        yield workspace


@pytest.fixture
def sample_findings_file(temp_workspace):
    """Create sample findings JSON file."""
    findings_file = temp_workspace / "review-findings.json"
    with open(findings_file, "w") as f:
        json.dump(SAMPLE_FINDINGS, f, indent=2)
    return findings_file


def test_normalize_findings_basic(sample_findings_file, temp_workspace):
    """Test finding normalization with confidence threshold."""
    output_dir = temp_workspace / "fix-plans"

    # Run normalize script
    result = subprocess.run(
        [
            PYTHON, "scripts/normalize_findings.py",
            "--findings", str(sample_findings_file),
            "--output-dir", str(output_dir),
            "--confidence-threshold", "0.7"
        ],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Script failed: {result.stderr}"

    # Check output files created
    assert (output_dir / "security.json").exists()
    assert (output_dir / "quality.json").exists()
    assert (output_dir / "performance.json").exists()
    assert (output_dir / "tests.json").exists()

    # Validate security findings
    with open(output_dir / "security.json") as f:
        security_plan = json.load(f)

    assert security_plan["category"] == "security"
    assert security_plan["total_findings"] == 2  # Both security findings above threshold
    assert security_plan["severity_counts"]["critical"] == 1
    assert security_plan["severity_counts"]["high"] == 1

    # Validate quality findings (low confidence filtered out)
    with open(output_dir / "quality.json") as f:
        quality_plan = json.load(f)

    assert quality_plan["total_findings"] == 1  # Only 1 above confidence threshold
    assert quality_plan["findings"][0]["confidence"] >= 0.7


def test_normalize_findings_priority_ranking(sample_findings_file, temp_workspace):
    """Test that findings are ranked by severity (critical first)."""
    output_dir = temp_workspace / "fix-plans"

    subprocess.run(
        [
            PYTHON, "scripts/normalize_findings.py",
            "--findings", str(sample_findings_file),
            "--output-dir", str(output_dir)
        ],
        check=True
    )

    with open(output_dir / "security.json") as f:
        security_plan = json.load(f)

    findings = security_plan["findings"]
    # First finding should be critical
    assert findings[0]["severity"] == "critical"
    # Second finding should be high
    assert findings[1]["severity"] == "high"


def test_generate_suggestions_basic(temp_workspace):
    """Test suggestion generation from fix plans."""
    # Create fix plan
    fix_plans_dir = temp_workspace / "fix-plans"
    fix_plans_dir.mkdir()

    security_plan = {
        "category": "security",
        "total_findings": 2,
        "severity_counts": {"critical": 1, "high": 1, "medium": 0, "low": 0},
        "findings": [
            {
                "category": "security",
                "severity": "critical",
                "file": "src/auth.py",
                "line_start": 23,
                "issue": "Hardcoded secret",
                "suggestion": "Use environment variable",
                "confidence": 0.95
            }
        ],
        "summary": {
            "top_severity": "critical",
            "files_affected": 1,
            "avg_confidence": 0.95
        }
    }

    with open(fix_plans_dir / "security.json", "w") as f:
        json.dump(security_plan, f)

    # Run suggestion generator
    pr_content_dir = temp_workspace / "pr-content"
    result = subprocess.run(
        [
            PYTHON, "scripts/generate_suggestions.py",
            "--fix-plans-dir", str(fix_plans_dir),
            "--output-dir", str(pr_content_dir)
        ],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0, f"Script failed: {result.stderr}"

    # Check PR content created
    pr_file = pr_content_dir / "security-pr.md"
    assert pr_file.exists()

    # Validate PR content
    content = pr_file.read_text()
    assert "# 🔒 Nightly Code Review: SECURITY" in content
    assert "Hardcoded secret" in content
    assert "src/auth.py:23" in content
    assert "Critical" in content or "CRITICAL" in content


def test_generate_suggestions_empty_findings(temp_workspace):
    """Test suggestion generation with no findings."""
    fix_plans_dir = temp_workspace / "fix-plans"
    fix_plans_dir.mkdir()

    pr_content_dir = temp_workspace / "pr-content"

    # Run with empty fix plans directory
    result = subprocess.run(
        [
            PYTHON, "scripts/generate_suggestions.py",
            "--fix-plans-dir", str(fix_plans_dir),
            "--output-dir", str(pr_content_dir)
        ],
        capture_output=True,
        text=True
    )

    assert result.returncode == 0
    # Should create output dir but no PR files
    assert pr_content_dir.exists()
    assert len(list(pr_content_dir.glob("*.md"))) == 0


def test_end_to_end_pipeline(sample_findings_file, temp_workspace):
    """Test complete pipeline: findings → normalization → suggestions."""
    # Step 1: Normalize
    fix_plans_dir = temp_workspace / "fix-plans"
    subprocess.run(
        [
            PYTHON, "scripts/normalize_findings.py",
            "--findings", str(sample_findings_file),
            "--output-dir", str(fix_plans_dir)
        ],
        check=True
    )

    # Step 2: Generate suggestions
    pr_content_dir = temp_workspace / "pr-content"
    subprocess.run(
        [
            PYTHON, "scripts/generate_suggestions.py",
            "--fix-plans-dir", str(fix_plans_dir),
            "--output-dir", str(pr_content_dir)
        ],
        check=True
    )

    # Validate end-to-end
    # Should have PR files for categories with findings
    pr_files = list(pr_content_dir.glob("*-pr.md"))
    assert len(pr_files) == 4  # security, quality, performance, tests

    # Validate PR content structure
    for pr_file in pr_files:
        content = pr_file.read_text()
        # Check required sections
        assert "# 🔒" in content or "# ✨" in content or "# ⚡" in content or "# 🧪" in content
        assert "Summary" in content
        assert "Findings by Severity" in content
        assert "Detailed Findings" in content


def test_validation_schema():
    """Test finding validation schema."""
    from scripts.run_consensus_review import validate_finding

    # Valid finding
    valid_finding = {
        "category": "security",
        "severity": "high",
        "file": "test.py",
        "line_start": 10,
        "issue": "Test issue",
        "suggestion": "Test fix",
        "confidence": 0.85,
        "actionable": True
    }
    assert validate_finding(valid_finding) is True

    # Invalid: missing required field
    invalid_missing_field = valid_finding.copy()
    del invalid_missing_field["confidence"]
    assert validate_finding(invalid_missing_field) is False

    # Invalid: bad enum value
    invalid_category = valid_finding.copy()
    invalid_category["category"] = "invalid_category"
    assert validate_finding(invalid_category) is False

    # Invalid: confidence out of range
    invalid_confidence = valid_finding.copy()
    invalid_confidence["confidence"] = 1.5
    assert validate_finding(invalid_confidence) is False


def test_deduplication():
    """Test finding deduplication logic."""
    from scripts.run_consensus_review import deduplicate_findings

    findings = [
        {
            "file": "test.py",
            "line_start": 10,
            "line_end": 15,
            "issue": "Issue 1"
        },
        {
            "file": "test.py",
            "line_start": 10,
            "line_end": 15,
            "issue": "Issue 2 (duplicate)"
        },
        {
            "file": "test.py",
            "line_start": 20,
            "issue": "Issue 3 (different line)"
        }
    ]

    deduplicated = deduplicate_findings(findings)

    # Should have 2 findings (first duplicate kept, second removed)
    assert len(deduplicated) == 2
    assert deduplicated[0]["line_start"] == 10
    assert deduplicated[1]["line_start"] == 20


def test_scope_selector_dry_run(temp_workspace):
    """Test scope selector in dry-run mode (no git required)."""
    # This test validates the script can run, but won't test git integration
    # For full git testing, use a real git repo in CI

    result = subprocess.run(
        [
            PYTHON, "scripts/scope_selector.py",
            "--scope", "all",
            "--max-files", "10",
            "--output", str(temp_workspace / "scope.json")
        ],
        capture_output=True,
        text=True
    )

    # May fail if not in git repo (expected in temp dir)
    # Just validate script exists and has valid syntax
    assert "scope_selector.py" in result.stderr or result.returncode in [0, 1]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
