"""Common helpers for locating SuperClaude metrics directories."""

from __future__ import annotations

import os
from pathlib import Path


def _detect_repo_root() -> Path:
    """Locate the repository root (best-effort)."""

    env_root = os.environ.get("SUPERCLAUDE_REPO_ROOT")
    if env_root:
        try:
            return Path(env_root).expanduser().resolve()
        except Exception:
            return Path(env_root)

    try:
        current = Path.cwd().resolve()
    except Exception:
        current = Path.cwd()

    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate

    return current


def get_metrics_dir() -> Path:
    """Return the directory used for metrics artifacts, creating it if required."""

    env_dir = os.environ.get("SUPERCLAUDE_METRICS_DIR")
    if env_dir:
        base = Path(env_dir).expanduser()
        base.mkdir(parents=True, exist_ok=True)
        return base

    base = _detect_repo_root() / ".superclaude_metrics"
    base.mkdir(parents=True, exist_ok=True)
    return base
