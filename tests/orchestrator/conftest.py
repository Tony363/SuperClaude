"""Test fixtures for Orchestrator tests."""

import pytest
from datetime import datetime

from SuperClaude.Orchestrator.evidence import EvidenceCollector, TestResult


@pytest.fixture
def empty_evidence():
    """Create empty EvidenceCollector."""
    return EvidenceCollector()


@pytest.fixture
def evidence_with_files():
    """Create EvidenceCollector with file changes."""
    evidence = EvidenceCollector()
    evidence.record_file_write("src/auth.py", lines_changed=50)
    evidence.record_file_edit("src/config.py", lines_changed=10)
    evidence.record_file_read("README.md")
    return evidence


@pytest.fixture
def evidence_with_passing_tests():
    """Create EvidenceCollector with passing test results."""
    evidence = EvidenceCollector()
    evidence.record_file_write("src/feature.py", lines_changed=100)
    evidence.record_command(
        command="pytest tests/",
        output="===== 10 passed in 2.5s =====",
        exit_code=0,
    )
    return evidence


@pytest.fixture
def evidence_with_failing_tests():
    """Create EvidenceCollector with failing test results."""
    evidence = EvidenceCollector()
    evidence.record_file_write("src/buggy.py", lines_changed=20)
    evidence.record_command(
        command="pytest tests/",
        output="===== 5 passed, 3 failed in 1.5s =====",
        exit_code=1,
    )
    return evidence


@pytest.fixture
def evidence_complete():
    """Create EvidenceCollector with comprehensive evidence."""
    evidence = EvidenceCollector()

    # Multiple file changes
    evidence.record_file_write("src/auth.py", lines_changed=100)
    evidence.record_file_write("src/models.py", lines_changed=50)
    evidence.record_file_edit("src/config.py", lines_changed=10)
    evidence.record_file_read("requirements.txt")

    # Passing tests
    evidence.record_command(
        command="pytest tests/ --cov=src",
        output="===== 15 passed in 3.0s =====\nCoverage: 85%",
        exit_code=0,
    )

    return evidence
