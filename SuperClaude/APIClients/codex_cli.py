"""Codex CLI client stub for SuperClaude Framework.

This module provides a minimal stub for CodexCLI integration.
The actual CLI must be installed separately.
"""

import os
import shutil


class CodexCLIUnavailable(RuntimeError):
    """Raised when the Codex CLI is not available."""

    pass


class CodexCLIClient:
    """Stub client for Codex CLI integration."""

    DEFAULT_BINARY = "codex"

    @classmethod
    def resolve_binary(cls) -> str:
        """Return the path to the Codex CLI binary."""
        return os.getenv("SUPERCLAUDE_CODEX_CLI", cls.DEFAULT_BINARY)

    @classmethod
    def is_available(cls) -> bool:
        """Check if the Codex CLI is available on PATH."""
        binary = cls.resolve_binary()
        return shutil.which(binary) is not None
