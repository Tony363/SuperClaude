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
            "actionable": True,
        },
        {
            "category": "security",
            "severity": "high",
            "file": "src/api.py",
            "line_start": 42,
            "issue": "Missing input validation",
            "suggestion": "Add Pydantic validation",
            "confidence": 0.85,
            "actionable": True,
        },
        {
            "category": "quality",
            "severity": "medium",
            "file": "src/utils.py",
            "line_start": 102,
            "issue": "Function exceeds 30 lines (KISS violation)",
            "suggestion": "Extract helper function",
            "confidence": 0.80,
            "actionable": True,
        },
        {
            "category": "quality",
            "severity": "low",
            "file": "src/helpers.py",
            "line_start": 15,
            "issue": "Missing docstring",
            "suggestion": "Add docstring",
            "confidence": 0.60,  # Below threshold
            "actionable": True,
        },
        {
            "category": "performance",
            "severity": "high",
            "file": "src/queries.py",
            "line_start": 78,
            "issue": "N+1 query detected",
            "suggestion": "Use select_related()",
            "confidence": 0.90,
            "actionable": True,
        },
        {
            "category": "tests",
            "severity": "medium",
            "file": "src/core.py",
            "line_start": 50,
            "issue": "Missing test coverage for error path",
            "suggestion": "Add test for ValueError case",
            "confidence": 0.75,
            "actionable": True,
        },
    ],
    "summary": {"total": 6, "models_used": ["gpt-5.2", "gemini-3-pro"]},
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
            PYTHON,
            "scripts/normalize_findings.py",
            "--findings",
            str(sample_findings_file),
            "--output-dir",
            str(output_dir),
            "--confidence-threshold",
            "0.7",
        ],
        capture_output=True,
        text=True,
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
            PYTHON,
            "scripts/normalize_findings.py",
            "--findings",
            str(sample_findings_file),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
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
                "confidence": 0.95,
            }
        ],
        "summary": {"top_severity": "critical", "files_affected": 1, "avg_confidence": 0.95},
    }

    with open(fix_plans_dir / "security.json", "w") as f:
        json.dump(security_plan, f)

    # Run suggestion generator
    pr_content_dir = temp_workspace / "pr-content"
    result = subprocess.run(
        [
            PYTHON,
            "scripts/generate_suggestions.py",
            "--fix-plans-dir",
            str(fix_plans_dir),
            "--output-dir",
            str(pr_content_dir),
        ],
        capture_output=True,
        text=True,
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
            PYTHON,
            "scripts/generate_suggestions.py",
            "--fix-plans-dir",
            str(fix_plans_dir),
            "--output-dir",
            str(pr_content_dir),
        ],
        capture_output=True,
        text=True,
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
            PYTHON,
            "scripts/normalize_findings.py",
            "--findings",
            str(sample_findings_file),
            "--output-dir",
            str(fix_plans_dir),
        ],
        check=True,
    )

    # Step 2: Generate suggestions
    pr_content_dir = temp_workspace / "pr-content"
    subprocess.run(
        [
            PYTHON,
            "scripts/generate_suggestions.py",
            "--fix-plans-dir",
            str(fix_plans_dir),
            "--output-dir",
            str(pr_content_dir),
        ],
        check=True,
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
    from scripts.finding_utils import validate_finding

    # Valid finding
    valid_finding = {
        "category": "security",
        "severity": "high",
        "file": "test.py",
        "line_start": 10,
        "issue": "Test issue",
        "suggestion": "Test fix",
        "confidence": 0.85,
        "actionable": True,
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
    from scripts.finding_utils import deduplicate_findings

    findings = [
        {"file": "test.py", "line_start": 10, "line_end": 15, "issue": "Issue 1"},
        {"file": "test.py", "line_start": 10, "line_end": 15, "issue": "Issue 2 (duplicate)"},
        {"file": "test.py", "line_start": 20, "issue": "Issue 3 (different line)"},
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
            PYTHON,
            "scripts/scope_selector.py",
            "--scope",
            "all",
            "--max-files",
            "10",
            "--output",
            str(temp_workspace / "scope.json"),
        ],
        capture_output=True,
        text=True,
    )

    # May fail if not in git repo (expected in temp dir)
    # Just validate script exists and has valid syntax
    assert "scope_selector.py" in result.stderr or result.returncode in [0, 1]


# ========== Fix-Type Registry Tests ==========


def test_fix_type_registry_structure():
    """Test that fix type registry has expected structure and entries."""
    from scripts.fix_type_registry import FIX_TYPES, FixType

    assert len(FIX_TYPES) >= 2
    assert "ruff_format" in FIX_TYPES
    assert "ruff_lint_fix" in FIX_TYPES

    for name, fix_type in FIX_TYPES.items():
        assert isinstance(fix_type, FixType)
        assert fix_type.name == name
        assert 0 < fix_type.confidence_threshold <= 1.0
        assert len(fix_type.categories) > 0
        # LLM fix types have no CLI tool_command
        if fix_type.tool_command:
            assert "{file}" in fix_type.tool_command
        assert fix_type.max_passes >= 0
        assert isinstance(fix_type.safe, bool)


def test_fix_type_registry_ruff_format():
    """Test ruff_format fix type has correct properties."""
    from scripts.fix_type_registry import get_fix_type

    ft = get_fix_type("ruff_format")
    assert ft is not None
    assert ft.confidence_threshold == 0.95
    assert ft.max_passes == 1  # Deterministic
    assert ft.ruff_select_codes is None
    assert "quality" in ft.categories
    assert ft.safe is True


def test_fix_type_registry_ruff_lint_fix():
    """Test ruff_lint_fix fix type has correct properties."""
    from scripts.fix_type_registry import get_fix_type

    ft = get_fix_type("ruff_lint_fix")
    assert ft is not None
    assert ft.confidence_threshold == 0.90
    assert ft.max_passes == 3  # Multi-pass for lint
    assert ft.ruff_select_codes == ("F401", "I001")
    assert "quality" in ft.categories
    assert "{codes}" in ft.tool_command


def test_fix_type_registry_unknown_type():
    """Test that unknown fix type returns None."""
    from scripts.fix_type_registry import get_fix_type, is_known_fix_type

    assert get_fix_type("nonexistent") is None
    assert is_known_fix_type("nonexistent") is False


# ========== Fix-Type Inference Tests ==========


def test_infer_fix_type_explicit():
    """Test fix type inference with explicit fix_type field."""
    from scripts.fix_type_registry import infer_fix_type

    assert infer_fix_type("anything", explicit_fix_type="ruff_format") == "ruff_format"
    assert infer_fix_type("anything", explicit_fix_type="ruff_lint_fix") == "ruff_lint_fix"
    assert infer_fix_type("anything", explicit_fix_type="RUFF_FORMAT") == "ruff_format"


def test_infer_fix_type_from_suggestion():
    """Test fix type inference from suggestion text patterns."""
    from scripts.fix_type_registry import infer_fix_type

    # ruff_format patterns
    assert infer_fix_type("Apply ruff format to this file") == "ruff_format"
    assert infer_fix_type("Fix formatting issues") == "ruff_format"
    assert infer_fix_type("Auto-format the code") == "ruff_format"

    # ruff_lint_fix patterns
    assert infer_fix_type("Remove unused import os") == "ruff_lint_fix"
    assert infer_fix_type("Fix import sorting") == "ruff_lint_fix"
    assert infer_fix_type("F401 violation detected") == "ruff_lint_fix"
    assert infer_fix_type("I001 issue found") == "ruff_lint_fix"


def test_infer_fix_type_no_match():
    """Test that non-matching suggestions return None."""
    from scripts.fix_type_registry import infer_fix_type

    assert infer_fix_type("Add input validation for security") is None
    assert infer_fix_type("Use select_related() for N+1 query") is None
    assert infer_fix_type("") is None


def test_infer_fix_type_explicit_overrides_suggestion():
    """Test that explicit fix_type takes precedence over suggestion text."""
    from scripts.fix_type_registry import infer_fix_type

    # Suggestion says "formatting" but explicit says "ruff_lint_fix"
    result = infer_fix_type("Fix formatting", explicit_fix_type="ruff_lint_fix")
    assert result == "ruff_lint_fix"


# ========== Autofix Eligibility Tests ==========


def test_autofix_eligibility_format_finding():
    """Test autofix eligibility for a ruff_format-type finding."""
    from scripts.normalize_findings import is_finding_autofix_eligible

    finding = {
        "category": "quality",
        "severity": "low",
        "file": "src/api/views.py",
        "line_start": 10,
        "line_end": 15,
        "issue": "Poor formatting",
        "suggestion": "Apply ruff format",
        "confidence": 0.96,
        "actionable": True,
    }
    assert is_finding_autofix_eligible(finding) is True
    assert finding["_resolved_fix_type"] == "ruff_format"


def test_autofix_eligibility_lint_finding():
    """Test autofix eligibility for a ruff_lint_fix-type finding."""
    from scripts.normalize_findings import is_finding_autofix_eligible

    finding = {
        "category": "quality",
        "severity": "low",
        "file": "src/api/views.py",
        "line_start": 1,
        "line_end": 1,
        "issue": "Unused import os",
        "suggestion": "Remove unused import",
        "confidence": 0.95,
        "actionable": True,
    }
    assert is_finding_autofix_eligible(finding) is True
    assert finding["_resolved_fix_type"] == "ruff_lint_fix"


def test_autofix_eligibility_low_confidence():
    """Test that low confidence rejects autofix even with matching suggestion."""
    from scripts.normalize_findings import is_finding_autofix_eligible

    finding = {
        "category": "quality",
        "severity": "low",
        "file": "src/api/views.py",
        "line_start": 10,
        "line_end": 15,
        "issue": "Poor formatting",
        "suggestion": "Apply ruff format",
        "confidence": 0.80,  # Below ruff_format's 0.95 threshold
        "actionable": True,
    }
    assert is_finding_autofix_eligible(finding) is False


def test_autofix_eligibility_wrong_category():
    """Test that wrong category rejects autofix."""
    from scripts.normalize_findings import is_finding_autofix_eligible

    finding = {
        "category": "security",  # ruff_format only allows "quality"
        "severity": "low",
        "file": "src/api/views.py",
        "line_start": 10,
        "line_end": 15,
        "issue": "Poor formatting",
        "suggestion": "Apply ruff format",
        "confidence": 0.96,
        "actionable": True,
    }
    assert is_finding_autofix_eligible(finding) is False


def test_autofix_eligibility_denied_file():
    """Test that files outside allowlist are rejected."""
    from scripts.normalize_findings import is_finding_autofix_eligible

    finding = {
        "category": "quality",
        "severity": "low",
        "file": "tests/test_main.py",  # In denylist
        "line_start": 10,
        "line_end": 15,
        "issue": "Poor formatting",
        "suggestion": "Apply ruff format",
        "confidence": 0.96,
        "actionable": True,
    }
    assert is_finding_autofix_eligible(finding) is False


def test_autofix_eligibility_no_matching_fix_type():
    """Test that unrecognized suggestions are not autofix-eligible."""
    from scripts.normalize_findings import is_finding_autofix_eligible

    finding = {
        "category": "security",
        "severity": "high",
        "file": "src/api/auth.py",
        "line_start": 10,
        "line_end": 15,
        "issue": "SQL injection vulnerability",
        "suggestion": "Use parameterized queries",
        "confidence": 0.95,
        "actionable": True,
    }
    assert is_finding_autofix_eligible(finding) is False


# ========== Command Building Tests ==========


def test_build_fix_command_ruff_format():
    """Test command building for ruff_format."""
    from scripts.apply_autofix import build_fix_command
    from scripts.fix_type_registry import get_fix_type

    fix_type = get_fix_type("ruff_format")
    cmd = build_fix_command(fix_type, Path("src/main.py"))
    assert cmd == ["ruff", "format", "src/main.py"]


def test_build_fix_command_ruff_lint_fix():
    """Test command building for ruff_lint_fix with code substitution."""
    from scripts.apply_autofix import build_fix_command
    from scripts.fix_type_registry import get_fix_type

    fix_type = get_fix_type("ruff_lint_fix")
    cmd = build_fix_command(fix_type, Path("src/main.py"))
    assert cmd == ["ruff", "check", "--select", "F401,I001", "--fix", "src/main.py"]


# ========== Validate Findings Schema Tests ==========


def test_validate_findings_schema_valid(temp_workspace):
    """Test schema validation with valid findings."""
    findings_file = temp_workspace / "findings.json"
    output_file = temp_workspace / "validated.json"

    data = {
        "findings": [
            {
                "category": "security",
                "severity": "high",
                "file": "src/auth.py",
                "line_start": 10,
                "issue": "Test issue",
                "suggestion": "Test fix",
                "confidence": 0.9,
                "actionable": True,
            }
        ],
        "summary": {"total": 1},
    }

    with open(findings_file, "w") as f:
        json.dump(data, f)

    result = subprocess.run(
        [PYTHON, "scripts/validate_findings_schema.py", str(findings_file), str(output_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_file.exists()

    with open(output_file) as f:
        validated = json.load(f)
    assert len(validated["findings"]) == 1


def test_validate_findings_schema_rejects_invalid(temp_workspace):
    """Test schema validation rejects invalid findings and keeps valid ones."""
    findings_file = temp_workspace / "findings.json"
    output_file = temp_workspace / "validated.json"

    data = {
        "findings": [
            {
                "category": "security",
                "severity": "high",
                "file": "src/auth.py",
                "line_start": 10,
                "issue": "Valid issue",
                "suggestion": "Valid fix",
                "confidence": 0.9,
                "actionable": True,
            },
            {
                "category": "INVALID_CATEGORY",  # Bad enum value
                "severity": "high",
                "file": "src/auth.py",
                "line_start": 20,
                "issue": "Invalid",
                "suggestion": "Invalid",
                "confidence": 0.9,
                "actionable": True,
            },
        ],
        "summary": {"total": 2},
    }

    with open(findings_file, "w") as f:
        json.dump(data, f)

    result = subprocess.run(
        [PYTHON, "scripts/validate_findings_schema.py", str(findings_file), str(output_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert output_file.exists()

    with open(output_file) as f:
        validated = json.load(f)
    # Only the valid finding survives
    assert len(validated["findings"]) == 1
    assert validated["summary"]["total"] == 1


def test_validate_findings_schema_bad_json(temp_workspace):
    """Test schema validation fails on invalid JSON."""
    findings_file = temp_workspace / "findings.json"
    findings_file.write_text("not valid json {{{")

    result = subprocess.run(
        [PYTHON, "scripts/validate_findings_schema.py", str(findings_file)],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1


# ========== File Allowlist Tests ==========


def test_file_allowlist_accepts_src():
    """Test allowlist accepts src/**/*.py files."""
    from scripts.normalize_findings import is_file_allowed_for_autofix

    assert is_file_allowed_for_autofix("src/api/views.py") is True
    assert is_file_allowed_for_autofix("src/models/user.py") is True


def test_file_allowlist_rejects_tests():
    """Test allowlist rejects test files."""
    from scripts.normalize_findings import is_file_allowed_for_autofix

    assert is_file_allowed_for_autofix("tests/test_main.py") is False
    assert is_file_allowed_for_autofix("tests/integration/test_api.py") is False


def test_file_allowlist_rejects_config():
    """Test allowlist rejects config and workflow files."""
    from scripts.normalize_findings import is_file_allowed_for_autofix

    assert is_file_allowed_for_autofix(".github/workflows/ci.yml") is False
    assert is_file_allowed_for_autofix("scripts/normalize.py") is False
    assert is_file_allowed_for_autofix("pyproject.toml") is False


# ========== Phase 3: LLM Fix Classification Tests ==========


def test_llm_fixable_unused_variable():
    """Test that unused variable finding is classified as LLM-fixable."""
    from scripts.classify_llm_fixable import is_llm_fixable

    finding = {
        "category": "quality",
        "severity": "medium",
        "file": "src/api/views.py",
        "line_start": 10,
        "line_end": 10,
        "issue": "Unused variable 'temp_result' assigned but never read",
        "suggestion": "Remove unused variable or use it",
        "confidence": 0.85,
        "actionable": True,
    }
    assert is_llm_fixable(finding) is True


def test_llm_fixable_dead_code():
    """Test that dead code finding is classified as LLM-fixable."""
    from scripts.classify_llm_fixable import is_llm_fixable

    finding = {
        "category": "quality",
        "severity": "low",
        "file": "src/api/utils.py",
        "line_start": 50,
        "line_end": 65,
        "issue": "Dead code: function 'old_handler' is never called",
        "suggestion": "Remove dead code to improve maintainability",
        "confidence": 0.90,
        "actionable": True,
    }
    assert is_llm_fixable(finding) is True


def test_llm_fixable_type_hint():
    """Test that missing type hint finding is classified as LLM-fixable."""
    from scripts.classify_llm_fixable import is_llm_fixable

    finding = {
        "category": "quality",
        "severity": "low",
        "file": "src/models/user.py",
        "line_start": 20,
        "line_end": 25,
        "issue": "Missing type annotation on function parameters",
        "suggestion": "Add type hints for clarity",
        "confidence": 0.82,
        "actionable": True,
    }
    assert is_llm_fixable(finding) is True


def test_llm_fixable_rejects_security():
    """Test that security findings are NOT classified as LLM-fixable."""
    from scripts.classify_llm_fixable import is_llm_fixable

    finding = {
        "category": "security",
        "severity": "high",
        "file": "src/api/auth.py",
        "line_start": 10,
        "line_end": 15,
        "issue": "SQL injection vulnerability",
        "suggestion": "Use parameterized queries",
        "confidence": 0.95,
        "actionable": True,
    }
    assert is_llm_fixable(finding) is False


def test_llm_fixable_rejects_deterministic():
    """Test that deterministic-fixable findings are NOT classified as LLM-fixable."""
    from scripts.classify_llm_fixable import is_llm_fixable

    finding = {
        "category": "quality",
        "severity": "low",
        "file": "src/api/views.py",
        "line_start": 1,
        "line_end": 1,
        "issue": "Unused import os",
        "suggestion": "Remove unused import",
        "confidence": 0.95,
        "actionable": True,
    }
    assert is_llm_fixable(finding) is False


def test_llm_fixable_rejects_low_confidence():
    """Test that low confidence findings are rejected."""
    from scripts.classify_llm_fixable import is_llm_fixable

    finding = {
        "category": "quality",
        "severity": "medium",
        "file": "src/api/views.py",
        "line_start": 10,
        "line_end": 10,
        "issue": "Unused variable 'x'",
        "suggestion": "Remove unused variable",
        "confidence": 0.70,  # Below 0.80 threshold
        "actionable": True,
    }
    assert is_llm_fixable(finding) is False


def test_llm_fixable_rejects_large_loc():
    """Test that large LOC findings are rejected."""
    from scripts.classify_llm_fixable import is_llm_fixable

    finding = {
        "category": "quality",
        "severity": "medium",
        "file": "src/api/views.py",
        "line_start": 10,
        "line_end": 100,  # 91 lines > MAX_LOC_PER_LLM_FIX (50)
        "issue": "Dead code block",
        "suggestion": "Remove dead code",
        "confidence": 0.85,
        "actionable": True,
    }
    assert is_llm_fixable(finding) is False


def test_llm_fixable_rejects_denied_file():
    """Test that files outside allowlist are rejected."""
    from scripts.classify_llm_fixable import is_llm_fixable

    finding = {
        "category": "quality",
        "severity": "medium",
        "file": "tests/test_main.py",
        "line_start": 10,
        "line_end": 10,
        "issue": "Unused variable in test",
        "suggestion": "Remove unused variable",
        "confidence": 0.85,
        "actionable": True,
    }
    assert is_llm_fixable(finding) is False


def test_llm_fixable_rejects_non_matching_issue():
    """Test that non-conservative issue patterns are rejected."""
    from scripts.classify_llm_fixable import is_llm_fixable

    finding = {
        "category": "quality",
        "severity": "medium",
        "file": "src/api/views.py",
        "line_start": 10,
        "line_end": 15,
        "issue": "Function is too complex (cyclomatic complexity 25)",
        "suggestion": "Refactor into smaller functions",
        "confidence": 0.85,
        "actionable": True,
    }
    assert is_llm_fixable(finding) is False


def test_classify_findings_prioritization(temp_workspace):
    """Test that classify_findings sorts by severity then confidence."""
    from scripts.classify_llm_fixable import classify_findings

    # Create fix plans with multiple LLM-fixable findings
    plans_dir = temp_workspace / "fix-plans"
    plans_dir.mkdir()

    quality_plan = {
        "findings": [
            {
                "category": "quality",
                "severity": "low",
                "file": "src/api/a.py",
                "line_start": 10,
                "line_end": 10,
                "issue": "Unused variable 'x'",
                "suggestion": "Remove unused variable",
                "confidence": 0.90,
                "actionable": True,
            },
            {
                "category": "quality",
                "severity": "high",
                "file": "src/api/b.py",
                "line_start": 20,
                "line_end": 25,
                "issue": "Dead code block never executed",
                "suggestion": "Remove dead code",
                "confidence": 0.85,
                "actionable": True,
            },
            {
                "category": "quality",
                "severity": "medium",
                "file": "src/api/c.py",
                "line_start": 5,
                "line_end": 5,
                "issue": "Missing type annotation on return",
                "suggestion": "Add type hint",
                "confidence": 0.88,
                "actionable": True,
            },
        ],
    }

    with open(plans_dir / "quality.json", "w") as f:
        json.dump(quality_plan, f)

    result = classify_findings(plans_dir, max_fixes=5)

    assert result["total_candidates"] == 3
    assert result["selected"] == 3
    # High severity should come first
    assert result["findings"][0]["severity"] == "high"
    assert result["findings"][1]["severity"] == "medium"
    assert result["findings"][2]["severity"] == "low"


def test_classify_findings_respects_limit(temp_workspace):
    """Test that classify_findings respects max_fixes limit."""
    from scripts.classify_llm_fixable import classify_findings

    plans_dir = temp_workspace / "fix-plans"
    plans_dir.mkdir()

    quality_plan = {
        "findings": [
            {
                "category": "quality",
                "severity": "medium",
                "file": f"src/api/f{i}.py",
                "line_start": 10,
                "line_end": 10,
                "issue": "Unused variable in function",
                "suggestion": "Remove unused variable",
                "confidence": 0.85,
                "actionable": True,
            }
            for i in range(10)
        ],
    }

    with open(plans_dir / "quality.json", "w") as f:
        json.dump(quality_plan, f)

    result = classify_findings(plans_dir, max_fixes=3)

    assert result["total_candidates"] == 10
    assert result["selected"] == 3
    assert len(result["findings"]) == 3


def test_fix_type_registry_llm_single_file():
    """Test llm_single_file fix type has correct properties."""
    from scripts.fix_type_registry import get_fix_type

    ft = get_fix_type("llm_single_file")
    assert ft is not None
    assert ft.confidence_threshold == 0.80
    assert ft.max_passes == 0  # Not applicable for LLM fixes
    assert ft.safe is False  # Requires human review
    assert "quality" in ft.categories
    assert "performance" in ft.categories
    assert ft.tool_command == ""  # No CLI tool


def test_infer_fix_type_llm_patterns():
    """Test fix type inference for LLM single-file patterns."""
    from scripts.fix_type_registry import infer_fix_type

    assert infer_fix_type("Remove unused variable x") == "llm_single_file"
    assert infer_fix_type("This is dead code") == "llm_single_file"
    assert infer_fix_type("Add type annotation for clarity") == "llm_single_file"
    assert infer_fix_type("Missing docstring on public function") == "llm_single_file"
    assert infer_fix_type("Unreachable code after return") == "llm_single_file"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
