"""
Artifact recording service for SuperClaude Commands.

Handles artifact creation, registration, and management.
"""

import logging
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ..artifact_manager import CommandArtifactManager
from .context import CommandContext

logger = logging.getLogger(__name__)


class ArtifactsService:
    """
    Service for managing command artifacts.

    Handles:
    - Artifact creation and persistence
    - Quality artifact recording
    - Test artifact recording
    - Context registration
    """

    def __init__(
        self,
        artifact_manager: CommandArtifactManager,
        repo_root: Path | None = None,
    ):
        """
        Initialize artifacts service.

        Args:
            artifact_manager: CommandArtifactManager instance
            repo_root: Repository root for relative paths
        """
        self.artifact_manager = artifact_manager
        self.repo_root = repo_root or Path.cwd()

    def record_artifact(
        self,
        context: CommandContext,
        command_name: str,
        summary: str,
        operations: Iterable[str],
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Persist an artifact and register it with the context.

        Args:
            context: Command execution context
            command_name: Name of command creating artifact
            summary: Summary content
            operations: List of operations
            metadata: Additional metadata

        Returns:
            Relative path to artifact or None
        """
        record = self.artifact_manager.record_summary(
            command_name, summary, operations=operations, metadata=metadata or {}
        )

        if not record:
            return None

        rel_path = self._relative_to_repo_path(record.path)
        context.results.setdefault("artifacts", []).append(rel_path)
        context.results.setdefault("executed_operations", []).append(
            f"artifact created: {rel_path}"
        )
        context.artifact_records.append(
            {
                "path": rel_path,
                "metadata": record.metadata,
            }
        )
        return rel_path

    def record_quality_artifact(
        self,
        context: CommandContext,
        assessment: Any,
    ) -> str | None:
        """
        Record a quality assessment artifact.

        Args:
            context: Command execution context
            assessment: QualityAssessment instance

        Returns:
            Relative path to artifact or None
        """
        if not assessment:
            return None

        metadata = {
            "overall_score": assessment.overall_score,
            "passed": assessment.passed,
            "threshold": assessment.threshold,
            "dimensions": dict(assessment.dimension_scores.items()),
        }

        summary_lines = [
            f"Quality Assessment for /sc:{context.command.name}",
            f"Overall Score: {assessment.overall_score:.1f}",
            f"Threshold: {assessment.threshold:.1f}",
            f"Passed: {assessment.passed}",
            "",
            "Dimension Scores:",
        ]
        for dim, score in sorted(assessment.dimension_scores.items()):
            summary_lines.append(f"  {dim}: {score:.1f}")

        if assessment.notes:
            summary_lines.append("")
            summary_lines.append("Notes:")
            summary_lines.extend(f"  - {note}" for note in assessment.notes)

        return self.record_artifact(
            context,
            f"{context.command.name}-quality",
            "\n".join(summary_lines),
            [f"quality assessment score={assessment.overall_score:.1f}"],
            metadata=metadata,
        )

    def record_test_artifact(
        self,
        context: CommandContext,
        parsed_command: Any,
        test_results: dict[str, Any],
    ) -> str | None:
        """
        Record a test execution artifact.

        Args:
            context: Command execution context
            parsed_command: ParsedCommand instance
            test_results: Test execution results

        Returns:
            Relative path to artifact or None
        """
        if not test_results:
            return None

        summary_lines = [
            f"Test Results for /sc:{parsed_command.name}",
            f"Command: {test_results.get('command', 'unknown')}",
            f"Passed: {test_results.get('passed', False)}",
            f"Pass Rate: {test_results.get('pass_rate', 0.0):.1%}",
            f"Duration: {test_results.get('duration_s', 0.0):.2f}s",
            "",
        ]

        summary_lines.extend(
            [
                f"Tests Collected: {test_results.get('tests_collected', 0)}",
                f"Tests Passed: {test_results.get('tests_passed', 0)}",
                f"Tests Failed: {test_results.get('tests_failed', 0)}",
                f"Tests Errored: {test_results.get('tests_errored', 0)}",
                f"Tests Skipped: {test_results.get('tests_skipped', 0)}",
            ]
        )

        if test_results.get("summary"):
            summary_lines.append("")
            summary_lines.append(f"Summary: {test_results['summary']}")

        metadata = {
            "passed": test_results.get("passed", False),
            "pass_rate": test_results.get("pass_rate", 0.0),
            "duration_s": test_results.get("duration_s", 0.0),
            "exit_code": test_results.get("exit_code", -1),
            "tests_collected": test_results.get("tests_collected", 0),
            "tests_passed": test_results.get("tests_passed", 0),
            "tests_failed": test_results.get("tests_failed", 0),
        }

        return self.record_artifact(
            context,
            f"{parsed_command.name}-tests",
            "\n".join(summary_lines),
            [f"test run passed={test_results.get('passed', False)}"],
            metadata=metadata,
        )

    def _relative_to_repo_path(self, path: Path | str) -> str:
        """Convert path to relative path from repo root."""
        path = Path(path)
        try:
            return str(path.relative_to(self.repo_root))
        except ValueError:
            return str(path)
