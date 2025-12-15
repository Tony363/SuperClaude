"""Codex CLI transport for fast-codex workflows.

This module shells out to the `codex` command-line interface so /sc:implement
can rely on the same automation surfaced in the Codex desktop client. The
client expects the CLI to emit JSON describing the changes it intends to apply
and raises :class:`CodexCLIUnavailable` when the binary is missing or produces
unexpected output.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


class CodexCLIUnavailable(RuntimeError):
    """Raised when the Codex CLI cannot be invoked successfully."""

    def __init__(self, message: str, *, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.details: Dict[str, Any] = details or {}


@dataclass
class CodexCLIConfig:
    """Configuration for invoking the Codex CLI."""

    binary: str = field(default_factory=lambda: os.getenv("SUPERCLAUDE_CODEX_CLI", "codex"))
    timeout_seconds: float = float(os.getenv("SUPERCLAUDE_CODEX_TIMEOUT", "120"))
    extra_args: List[str] = field(default_factory=lambda: shlex.split(os.getenv("SUPERCLAUDE_CODEX_ARGS", "--full-auto --json")))
    env: Dict[str, str] = field(default_factory=dict)


@dataclass
class CodexCLIResult:
    """Structured result from a Codex CLI invocation."""

    payload: Dict[str, Any]
    stdout: str
    stderr: str
    duration_s: float
    returncode: int
    command: List[str]


class CodexCLIClient:
    """Shells out to ``codex exec`` and parses the JSON response."""

    def __init__(self, config: Optional[CodexCLIConfig] = None) -> None:
        self.config = config or CodexCLIConfig()

    # ------------------------------------------------------------------
    # Availability helpers
    # ------------------------------------------------------------------
    @classmethod
    def resolve_binary(cls) -> str:
        """Return the binary path respecting configuration overrides."""

        return os.getenv("SUPERCLAUDE_CODEX_CLI", "codex")

    @classmethod
    def is_available(cls) -> bool:
        """Return ``True`` when the Codex CLI binary is reachable."""

        binary = cls.resolve_binary()
        return shutil.which(binary) is not None

    # ------------------------------------------------------------------
    # Invocation
    # ------------------------------------------------------------------
    def run(self, prompt: str, *, workdir: Optional[Path] = None, extra_args: Optional[Iterable[str]] = None) -> CodexCLIResult:
        """Execute ``codex exec`` and parse the JSON payload."""

        binary = self.config.binary
        if shutil.which(binary) is None:
            raise CodexCLIUnavailable(
                f"Codex CLI binary '{binary}' is not available on PATH. "
                "Install the Codex CLI or set SUPERCLAUDE_CODEX_CLI.",
                details={
                    "binary": binary,
                    "path": shutil.which(binary) or "not found",
                }
            )

        args: List[str] = [binary, "exec", prompt]
        cli_args = list(extra_args) if extra_args is not None else list(self.config.extra_args)
        args.extend(cli_args)

        command_env = os.environ.copy()
        command_env.update(self.config.env)

        cwd = str(workdir) if workdir else None
        start = time.perf_counter()
        try:
            completed = subprocess.run(
                args,
                cwd=cwd,
                env=command_env,
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                check=False,
            )
        except FileNotFoundError as exc:
            raise CodexCLIUnavailable(
                f"Codex CLI binary '{binary}' could not be executed: {exc}",
                details={
                    "binary": binary,
                    "command": args,
                    "cwd": cwd,
                }
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise CodexCLIUnavailable(
                f"Codex CLI timed out after {self.config.timeout_seconds:.0f}s",
                details={
                    "binary": binary,
                    "command": args,
                    "cwd": cwd,
                    "timeout_seconds": self.config.timeout_seconds,
                }
            ) from exc

        duration = time.perf_counter() - start

        if completed.returncode != 0:
            stderr = (completed.stderr or "unknown error").strip()
            raise CodexCLIUnavailable(
                f"Codex CLI exited with status {completed.returncode}: {stderr}",
                details={
                    "binary": binary,
                    "command": args,
                    "cwd": cwd,
                    "returncode": completed.returncode,
                    "stdout": self._truncate_log(completed.stdout),
                    "stderr": self._truncate_log(completed.stderr),
                }
            )

        stdout = completed.stdout.strip()
        if not stdout:
            raise CodexCLIUnavailable("Codex CLI produced no output")

        payload = self._extract_json(stdout)

        return CodexCLIResult(
            payload=payload,
            stdout=stdout,
            stderr=(completed.stderr or "").strip(),
            duration_s=duration,
            returncode=completed.returncode,
            command=args,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_json(stdout: str) -> Dict[str, Any]:
        """Parse Codex CLI JSONL output and return the change payload."""

        # Some Codex builds still emit a single JSON blob – keep the fast path.
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            parsed = CodexCLIClient._parse_payload_from_record(payload)
            if parsed:
                return parsed

        parsed_lines = []
        for line in stdout.splitlines():
            candidate = line.strip()
            if not candidate:
                continue
            record = CodexCLIClient._safe_json_loads(candidate)
            if record is None:
                continue
            parsed_lines.append(record)
            payload = CodexCLIClient._parse_payload_from_record(record)
            if payload:
                return payload

        # Re-check parsed entries in reverse to catch nested payloads surfaced late.
        for record in reversed(parsed_lines):
            payload = CodexCLIClient._parse_payload_from_record(record)
            if payload:
                return payload

        raise CodexCLIUnavailable(
            "Codex CLI output did not contain valid JSON",
            details={"stdout": CodexCLIClient._truncate_log(stdout)}
        )

    @staticmethod
    def _parse_payload_from_record(record: Any) -> Optional[Dict[str, Any]]:
        """Return the Codex diff payload from a decoded JSON object, if present."""

        if not isinstance(record, dict):
            return None

        if "summary" in record and "changes" in record:
            return record

        text_candidates = []
        for key in ("text", "message", "content"):
            value = record.get(key)
            if isinstance(value, str):
                text_candidates.append(value)

        for text in text_candidates:
            nested = CodexCLIClient._safe_json_loads(text)
            if isinstance(nested, dict):
                payload = CodexCLIClient._parse_payload_from_record(nested)
                if payload:
                    return payload

        for key in ("item", "payload", "data"):
            nested = record.get(key)
            if isinstance(nested, dict):
                payload = CodexCLIClient._parse_payload_from_record(nested)
                if payload:
                    return payload

        return None

    @staticmethod
    def _safe_json_loads(blob: str) -> Optional[Any]:
        """Best-effort JSON parsing that tolerates code fences and whitespace."""

        snippet = blob.strip()
        if not snippet:
            return None
        if snippet.startswith("`") and snippet.endswith("`"):
            snippet = snippet.strip("`").strip()
        if snippet.startswith("```"):
            snippet = snippet.lstrip("`").strip()
        if "\n" in snippet:
            first_line, rest = snippet.split("\n", 1)
            if first_line.strip().lower() in {"json", "jsonc"}:
                snippet = rest.strip()
            else:
                snippet = f"{first_line}\n{rest}".strip()
        try:
            return json.loads(snippet)
        except json.JSONDecodeError:
            return None

    @staticmethod
    def _truncate_log(payload: Optional[str], limit: int = 2000) -> str:
        """Return the tail of a log string to avoid flooding diagnostics."""

        if not payload:
            return ""
        text = payload.strip()
        if len(text) <= limit:
            return text
        return text[-limit:]
