"""
Artifact management utilities for SuperClaude commands.

Provides deterministic, repository-backed reporting so that command
executions leave verifiable evidence (e.g., markdown summaries) that
can be inspected by downstream guardrails and quality checks.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


def _slugify(value: str) -> str:
    """Create a filesystem-safe slug from the provided value."""
    sanitized = "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in value)
    sanitized = "-".join(part for part in sanitized.split("-") if part)
    return sanitized.lower() or "artifact"


@dataclass
class ArtifactRecord:
    """Metadata describing a generated artifact."""

    command: str
    path: Path
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)


class CommandArtifactManager:
    """
    Handles creation of deterministic command artifacts.

    Artifacts are stored beneath the repository in ``SuperClaude/Generated``
    and are intended to provide lightweight, inspectable evidence that a
    command executed concrete work.
    """

    def __init__(self, base_dir: Path, enabled: bool = True):
        self.base_dir = base_dir
        self.enabled = enabled
        if self.enabled:
            self.base_dir.mkdir(parents=True, exist_ok=True)

    def _ensure_command_dir(self, command_name: str) -> Path:
        command_dir = self.base_dir / _slugify(command_name)
        command_dir.mkdir(parents=True, exist_ok=True)
        return command_dir

    def _make_filename(self, command_name: str, payload: dict[str, Any]) -> str:
        digest_source = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
        digest = hashlib.sha1(digest_source).hexdigest()[:12]
        return f"{_slugify(command_name)}-{digest}.md"

    def record_summary(
        self,
        command_name: str,
        summary: str,
        *,
        operations: Iterable[str] = (),
        artifacts: Iterable[str] = (),
        metadata: dict[str, Any] | None = None,
    ) -> ArtifactRecord | None:
        """
        Persist a markdown report describing command execution.

        Returns:
            ArtifactRecord if artifacts are enabled, otherwise None.
        """
        if not self.enabled:
            return None

        metadata = metadata or {}
        payload = {
            "summary": summary,
            "operations": list(operations),
            "artifacts": list(artifacts),
            "metadata": metadata,
        }

        command_dir = self._ensure_command_dir(command_name)
        filename = self._make_filename(command_name, payload)
        artifact_path = command_dir / filename

        content_lines: list[str] = [
            f"# {command_name} Execution Summary",
            "",
            "## Summary",
            summary.strip() or "No summary provided.",
            "",
        ]

        if operations:
            content_lines.append("## Operations")
            for op in operations:
                content_lines.append(f"- {op}")
            content_lines.append("")

        if artifacts:
            content_lines.append("## Related Artifacts")
            for item in artifacts:
                content_lines.append(f"- {item}")
            content_lines.append("")

        if metadata:
            content_lines.append("## Metadata")
            for key, value in metadata.items():
                content_lines.append(f"- **{key}**: {value}")
            content_lines.append("")

        artifact_path.write_text(
            "\n".join(content_lines).strip() + "\n", encoding="utf-8"
        )

        return ArtifactRecord(
            command=command_name,
            path=artifact_path,
            description="Command execution summary",
            metadata=metadata,
        )
