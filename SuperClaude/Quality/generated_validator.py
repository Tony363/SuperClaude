"""
Validator for generated implementation documents.

Ensures generated outputs meet minimum quality standards
and can be used for evidence/audit trails.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ValidationIssue:
    """A single validation issue."""

    severity: str  # 'error', 'warning', 'info'
    message: str
    location: str  # file path or section
    code: str  # machine-readable issue code


@dataclass
class GeneratedDocValidation:
    """Validation result for a single generated document."""

    file_path: Path
    valid: bool
    doc_type: str  # 'implement', 'workflow', 'quality-assessment', etc.
    issues: list[ValidationIssue] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")


@dataclass
class ValidationReport:
    """Aggregate validation report for all generated documents."""

    documents: list[GeneratedDocValidation]
    total_files: int
    valid_files: int
    invalid_files: int
    total_errors: int
    total_warnings: int

    @property
    def success_rate(self) -> float:
        if self.total_files == 0:
            return 100.0
        return (self.valid_files / self.total_files) * 100


class GeneratedValidator:
    """
    Validator for SuperClaude generated implementation documents.

    Validates:
    - Document structure (required sections)
    - Metadata completeness
    - Content quality signals
    - Cross-reference integrity
    """

    # Required sections by document type
    REQUIRED_SECTIONS: dict[str, list[str]] = {
        "implement": ["Summary", "Agent"],
        "workflow": ["Summary"],
        "quality-assessment": ["Summary", "Dimensions"],
        "test-tests": ["Summary"],
        "git": ["Summary"],
        "implement-tests": ["Summary"],
    }

    # Patterns that indicate incomplete content
    INCOMPLETE_PATTERNS = [
        r"TODO",
        r"FIXME",
        r"XXX",
        r"\[placeholder\]",
        r"\[insert\s+\w+\s+here\]",
        r"<placeholder>",
        r"not\s+implemented",
    ]

    def __init__(self, generated_dir: Path | str | None = None):
        """
        Initialize validator.

        Args:
            generated_dir: Path to Generated directory
        """
        if generated_dir:
            self.generated_dir = Path(generated_dir)
        else:
            # Default to SuperClaude/Generated
            self.generated_dir = Path(__file__).parent.parent / "Generated"

    def validate_all(self) -> ValidationReport:
        """
        Validate all generated documents.

        Returns:
            ValidationReport with aggregate results
        """
        if not self.generated_dir.exists():
            logger.warning(f"Generated directory not found: {self.generated_dir}")
            return ValidationReport(
                documents=[],
                total_files=0,
                valid_files=0,
                invalid_files=0,
                total_errors=0,
                total_warnings=0,
            )

        documents = []
        for md_file in self.generated_dir.rglob("*.md"):
            result = self.validate_document(md_file)
            documents.append(result)

        valid_files = sum(1 for d in documents if d.valid)
        total_errors = sum(d.error_count for d in documents)
        total_warnings = sum(d.warning_count for d in documents)

        return ValidationReport(
            documents=documents,
            total_files=len(documents),
            valid_files=valid_files,
            invalid_files=len(documents) - valid_files,
            total_errors=total_errors,
            total_warnings=total_warnings,
        )

    def validate_document(self, file_path: Path) -> GeneratedDocValidation:
        """
        Validate a single generated document.

        Args:
            file_path: Path to markdown file

        Returns:
            GeneratedDocValidation result
        """
        issues: list[ValidationIssue] = []
        metadata: dict[str, Any] = {}

        # Determine document type from parent directory
        doc_type = file_path.parent.name

        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            issues.append(
                ValidationIssue(
                    severity="error",
                    message=f"Failed to read file: {e}",
                    location=str(file_path),
                    code="READ_ERROR",
                )
            )
            return GeneratedDocValidation(
                file_path=file_path,
                valid=False,
                doc_type=doc_type,
                issues=issues,
                metadata=metadata,
            )

        # Validate structure
        structure_issues = self._validate_structure(content, doc_type, file_path)
        issues.extend(structure_issues)

        # Validate content quality
        content_issues = self._validate_content(content, file_path)
        issues.extend(content_issues)

        # Extract and validate metadata
        meta_issues, extracted_meta = self._validate_metadata(content, doc_type, file_path)
        issues.extend(meta_issues)
        metadata.update(extracted_meta)

        # Check for minimal content
        if len(content.strip()) < 100:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    message="Document has minimal content (< 100 chars)",
                    location=str(file_path),
                    code="MINIMAL_CONTENT",
                )
            )

        # Document is valid if no errors (warnings are OK)
        has_errors = any(i.severity == "error" for i in issues)

        return GeneratedDocValidation(
            file_path=file_path,
            valid=not has_errors,
            doc_type=doc_type,
            issues=issues,
            metadata=metadata,
        )

    def _validate_structure(
        self, content: str, doc_type: str, file_path: Path
    ) -> list[ValidationIssue]:
        """Check for required sections."""
        issues = []

        required = self.REQUIRED_SECTIONS.get(doc_type, ["Summary"])

        for section in required:
            # Look for markdown headers with this section name
            pattern = rf"^#+\s*{re.escape(section)}"
            if not re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        message=f"Missing required section: {section}",
                        location=str(file_path),
                        code="MISSING_SECTION",
                    )
                )

        return issues

    def _validate_content(
        self, content: str, file_path: Path
    ) -> list[ValidationIssue]:
        """Check for incomplete content markers."""
        issues = []

        for pattern in self.INCOMPLETE_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        message=f"Found incomplete marker: {matches[0]}",
                        location=str(file_path),
                        code="INCOMPLETE_MARKER",
                    )
                )

        return issues

    def _validate_metadata(
        self, content: str, doc_type: str, file_path: Path
    ) -> tuple[list[ValidationIssue], dict[str, Any]]:
        """Extract and validate document metadata."""
        issues = []
        metadata: dict[str, Any] = {}

        # Extract key-value pairs from content
        # Look for patterns like "Mode: normal" or "**Threshold**: 90.0"
        kv_pattern = r"(?:\*\*)?(\w+)(?:\*\*)?:\s*(.+)"
        for match in re.finditer(kv_pattern, content):
            key = match.group(1).lower()
            value = match.group(2).strip()
            metadata[key] = value

        # Check for quality-specific metadata
        if doc_type == "quality-assessment":
            if "threshold" not in metadata and "overall" not in content.lower():
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        message="Quality assessment missing threshold or overall score",
                        location=str(file_path),
                        code="MISSING_QUALITY_DATA",
                    )
                )

        # Check for execution metadata
        if doc_type == "implement":
            if "mode" not in metadata:
                issues.append(
                    ValidationIssue(
                        severity="info",
                        message="Implementation missing execution mode",
                        location=str(file_path),
                        code="MISSING_MODE",
                    )
                )

        return issues, metadata

    def to_json(self, report: ValidationReport) -> str:
        """Convert validation report to JSON."""
        return json.dumps(
            {
                "total_files": report.total_files,
                "valid_files": report.valid_files,
                "invalid_files": report.invalid_files,
                "success_rate": report.success_rate,
                "total_errors": report.total_errors,
                "total_warnings": report.total_warnings,
                "documents": [
                    {
                        "file": str(doc.file_path),
                        "valid": doc.valid,
                        "type": doc.doc_type,
                        "errors": doc.error_count,
                        "warnings": doc.warning_count,
                        "issues": [
                            {
                                "severity": i.severity,
                                "message": i.message,
                                "code": i.code,
                            }
                            for i in doc.issues
                        ],
                    }
                    for doc in report.documents
                ],
            },
            indent=2,
        )


def main():
    """CLI entry point for generated validation."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Validate generated implementations")
    parser.add_argument(
        "--dir",
        type=Path,
        help="Path to Generated directory",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )
    parser.add_argument(
        "--fail-on-errors",
        action="store_true",
        help="Exit with code 1 if any errors found",
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Exit with code 1 if any warnings found",
    )

    args = parser.parse_args()

    validator = GeneratedValidator(generated_dir=args.dir)
    report = validator.validate_all()

    if args.json:
        print(validator.to_json(report))
    else:
        print("Generated Implementation Validation Report")
        print("=" * 50)
        print(f"Total files:     {report.total_files}")
        print(f"Valid files:     {report.valid_files}")
        print(f"Invalid files:   {report.invalid_files}")
        print(f"Success rate:    {report.success_rate:.1f}%")
        print(f"Total errors:    {report.total_errors}")
        print(f"Total warnings:  {report.total_warnings}")
        print()

        if report.total_errors > 0 or report.total_warnings > 0:
            print("Issues:")
            for doc in report.documents:
                if doc.issues:
                    print(f"\n  {doc.file_path.name} ({doc.doc_type}):")
                    for issue in doc.issues:
                        icon = "❌" if issue.severity == "error" else "⚠️"
                        print(f"    {icon} [{issue.code}] {issue.message}")

    # Determine exit code
    if args.fail_on_errors and report.total_errors > 0:
        sys.exit(1)
    if args.fail_on_warnings and (report.total_errors > 0 or report.total_warnings > 0):
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
