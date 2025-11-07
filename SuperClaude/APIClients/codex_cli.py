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
                "Install the Codex CLI or set SUPERCLAUDE_CODEX_CLI."
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
            raise CodexCLIUnavailable(f"Codex CLI binary '{binary}' could not be executed: {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise CodexCLIUnavailable(
                f"Codex CLI timed out after {self.config.timeout_seconds:.0f}s"
            ) from exc

        duration = time.perf_counter() - start

        if completed.returncode != 0:
            stderr = (completed.stderr or "unknown error").strip()
            raise CodexCLIUnavailable(
                f"Codex CLI exited with status {completed.returncode}: {stderr}"
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
        """Parse the first valid JSON object found in ``stdout``."""

        # Try whole output first.
        try:
            return json.loads(stdout)
        except json.JSONDecodeError:
            pass

        # Fall back to scanning lines from the end.
        for line in reversed(stdout.splitlines()):
            candidate = line.strip()
            if not candidate:
                continue
            if candidate.startswith("`") and candidate.endswith("`"):
                candidate = candidate.strip("`")
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

        raise CodexCLIUnavailable("Codex CLI output did not contain valid JSON")

