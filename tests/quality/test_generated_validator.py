"""Tests for the generated implementation validator."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from SuperClaude.Quality.generated_validator import (
    GeneratedDocValidation,
    GeneratedValidator,
    ValidationIssue,
)


@pytest.fixture
def temp_generated_dir():
    """Create a temporary Generated directory structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        gen_dir = Path(tmpdir) / "Generated"
        gen_dir.mkdir()

        # Create subdirectories matching real structure
        (gen_dir / "implement").mkdir()
        (gen_dir / "workflow").mkdir()
        (gen_dir / "quality-assessment").mkdir()
        (gen_dir / "test-tests").mkdir()

        yield gen_dir


@pytest.fixture
def validator(temp_generated_dir):
    """Create a validator instance."""
    return GeneratedValidator(generated_dir=temp_generated_dir)


class TestGeneratedValidator:
    """Test the validator initialization and basic operations."""

    def test_init_with_path(self, temp_generated_dir):
        """Can initialize with explicit path."""
        validator = GeneratedValidator(generated_dir=temp_generated_dir)
        assert validator.generated_dir == temp_generated_dir

    def test_init_default_path(self):
        """Uses default path when none specified."""
        validator = GeneratedValidator()
        assert "Generated" in str(validator.generated_dir)

    def test_validate_all_empty_dir(self, validator, temp_generated_dir):
        """Empty directory returns empty report."""
        report = validator.validate_all()
        assert report.total_files == 0
        assert report.valid_files == 0
        assert report.success_rate == 100.0

    def test_validate_all_nonexistent_dir(self):
        """Non-existent directory handled gracefully."""
        validator = GeneratedValidator(generated_dir="/nonexistent/path")
        report = validator.validate_all()
        assert report.total_files == 0


class TestDocumentValidation:
    """Test individual document validation."""

    def test_valid_implement_doc(self, validator, temp_generated_dir):
        """Valid implementation document passes."""
        doc = temp_generated_dir / "implement" / "test-doc.md"
        doc.write_text(
            """# implement Execution Summary

## Summary
Implementation request for: add feature X
Mode: normal
Agents engaged: python-expert

## Agent Insights
- python-expert: Analysis shows...

## Recommendations
1. Add proper error handling
2. Update tests
"""
        )

        result = validator.validate_document(doc)
        assert result.valid
        assert result.doc_type == "implement"
        assert result.error_count == 0

    def test_valid_quality_assessment(self, validator, temp_generated_dir):
        """Valid quality assessment document passes."""
        doc = temp_generated_dir / "quality-assessment" / "test-qa.md"
        doc.write_text(
            """# quality-assessment Execution Summary

## Summary
Overall: 85.0 (threshold 70.0)
Passed: yes

## Dimensions
- correctness: 90.0
- completeness: 80.0
- security: 85.0
"""
        )

        result = validator.validate_document(doc)
        assert result.valid
        assert result.doc_type == "quality-assessment"

    def test_missing_summary_section(self, validator, temp_generated_dir):
        """Missing required section generates warning."""
        doc = temp_generated_dir / "implement" / "no-summary.md"
        doc.write_text(
            """# Some Other Title

Content without proper summary section.
"""
        )

        result = validator.validate_document(doc)
        # Still valid (warning, not error)
        assert result.valid
        assert result.warning_count > 0
        assert any(i.code == "MISSING_SECTION" for i in result.issues)

    def test_incomplete_markers_detected(self, validator, temp_generated_dir):
        """TODO and FIXME markers generate warnings."""
        doc = temp_generated_dir / "implement" / "with-todo.md"
        doc.write_text(
            """# implement Execution Summary

## Summary
TODO: Complete this summary
FIXME: Add more details
"""
        )

        result = validator.validate_document(doc)
        assert result.warning_count >= 2
        assert any(i.code == "INCOMPLETE_MARKER" for i in result.issues)

    def test_minimal_content_warning(self, validator, temp_generated_dir):
        """Very short documents get warning."""
        doc = temp_generated_dir / "implement" / "short.md"
        doc.write_text("# Short\n\nToo short.")

        result = validator.validate_document(doc)
        assert any(i.code == "MINIMAL_CONTENT" for i in result.issues)

    def test_unreadable_file(self, validator, temp_generated_dir):
        """Unreadable file generates error."""
        doc = temp_generated_dir / "implement" / "bad.md"
        doc.write_bytes(b"\x80\x81\x82")  # Invalid UTF-8

        result = validator.validate_document(doc)
        assert not result.valid
        assert result.error_count == 1
        assert any(i.code == "READ_ERROR" for i in result.issues)


class TestMetadataExtraction:
    """Test metadata extraction from documents."""

    def test_extracts_mode(self, validator, temp_generated_dir):
        """Extracts mode from content."""
        doc = temp_generated_dir / "implement" / "with-mode.md"
        doc.write_text(
            """# implement Execution Summary

## Summary
Mode: task_management
"""
        )

        result = validator.validate_document(doc)
        assert "mode" in result.metadata
        assert result.metadata["mode"] == "task_management"

    def test_extracts_bold_metadata(self, validator, temp_generated_dir):
        """Extracts **key**: value patterns."""
        doc = temp_generated_dir / "quality-assessment" / "with-bold.md"
        doc.write_text(
            """# quality-assessment Execution Summary

## Summary
Overall: 75.0

## Dimensions
- **Threshold**: 70.0
- **Passed**: True
"""
        )

        result = validator.validate_document(doc)
        assert "threshold" in result.metadata


class TestValidationReport:
    """Test aggregate validation reports."""

    def test_report_aggregation(self, validator, temp_generated_dir):
        """Report correctly aggregates results."""
        # Create valid doc
        valid_doc = temp_generated_dir / "implement" / "valid.md"
        valid_doc.write_text(
            """# implement Execution Summary

## Summary
Mode: normal
"""
        )

        # Create doc with warnings
        warn_doc = temp_generated_dir / "workflow" / "with-warnings.md"
        warn_doc.write_text(
            """# workflow Execution Summary

## Summary
TODO: Complete this
"""
        )

        report = validator.validate_all()
        assert report.total_files == 2
        assert report.valid_files == 2  # Warnings don't invalidate
        assert report.total_warnings >= 1

    def test_success_rate_calculation(self, validator, temp_generated_dir):
        """Success rate calculated correctly."""
        # Create 3 valid docs
        for i in range(3):
            doc = temp_generated_dir / "implement" / f"doc{i}.md"
            doc.write_text(f"# implement {i}\n\n## Summary\nContent here is sufficient.")

        # Create 1 invalid doc (unreadable)
        bad_doc = temp_generated_dir / "implement" / "bad.md"
        bad_doc.write_bytes(b"\x80\x81")

        report = validator.validate_all()
        assert report.total_files == 4
        assert report.valid_files == 3
        assert report.invalid_files == 1
        assert report.success_rate == 75.0


class TestJSONOutput:
    """Test JSON serialization."""

    def test_to_json(self, validator, temp_generated_dir):
        """Can serialize report to JSON."""
        import json

        doc = temp_generated_dir / "implement" / "test.md"
        doc.write_text("# implement\n\n## Summary\nTest content here.")

        report = validator.validate_all()
        json_str = validator.to_json(report)

        # Should be valid JSON
        data = json.loads(json_str)
        assert "total_files" in data
        assert "documents" in data
        assert len(data["documents"]) == 1


class TestValidationIssue:
    """Test ValidationIssue dataclass."""

    def test_issue_creation(self):
        """Can create validation issue."""
        issue = ValidationIssue(
            severity="error",
            message="Test error",
            location="/path/to/file.md",
            code="TEST_ERROR",
        )
        assert issue.severity == "error"
        assert issue.code == "TEST_ERROR"


class TestGeneratedDocValidation:
    """Test GeneratedDocValidation dataclass."""

    def test_error_count(self):
        """Error count calculated correctly."""
        validation = GeneratedDocValidation(
            file_path=Path("/test.md"),
            valid=False,
            doc_type="implement",
            issues=[
                ValidationIssue("error", "Error 1", "/test.md", "E1"),
                ValidationIssue("error", "Error 2", "/test.md", "E2"),
                ValidationIssue("warning", "Warning 1", "/test.md", "W1"),
            ],
        )
        assert validation.error_count == 2
        assert validation.warning_count == 1
