"""
Git and repository operations for the SuperClaude Command Executor.

Provides functions for repository detection, change tracking, diff analysis,
and commit message generation.
"""

import logging
import os
import shutil
import subprocess
from collections.abc import Iterable, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

from .utils import truncate_output

logger = logging.getLogger(__name__)


def normalize_repo_root(
    repo_root: Path | None, detect_fn: callable | None = None
) -> Path | None:
    """Normalize desired repo root, falling back to detected git root."""
    env_root = os.environ.get("SUPERCLAUDE_REPO_ROOT")
    if repo_root is None and env_root:
        repo_root = Path(env_root).expanduser()

    if repo_root is not None:
        try:
            return Path(repo_root).resolve()
        except Exception:
            return Path(repo_root)

    if detect_fn:
        return detect_fn()
    return detect_repo_root()


def detect_repo_root() -> Path | None:
    """Locate the git repository root, if available."""
    try:
        current = Path.cwd().resolve()
    except Exception:
        return None

    for candidate in [current, *current.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def snapshot_repo_changes(repo_root: Path | None) -> set[str]:
    """Capture current git worktree changes for comparison."""
    if not repo_root or not (repo_root / ".git").exists():
        return set()

    snapshot: set[str] = set()
    commands = [
        ["git", "diff", "--name-status"],
        ["git", "diff", "--name-status", "--cached"],
    ]

    for cmd in commands:
        try:
            result = subprocess.run(
                cmd, cwd=repo_root, capture_output=True, text=True, check=False
            )
        except Exception as exc:
            logger.debug(f"Failed to run {' '.join(cmd)}: {exc}")
            return set()

        if result.returncode != 0:
            continue

        for line in result.stdout.splitlines():
            entry = line.strip()
            if entry:
                snapshot.add(entry)

    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                path = line.strip()
                if path:
                    snapshot.add(f"??\t{path}")
    except Exception as exc:
        logger.debug(f"Failed to list untracked files: {exc}")

    return snapshot


def diff_snapshots(before: set[str], after: set[str]) -> list[str]:
    """Return new repo changes detected between snapshots."""
    if not after:
        return []
    if not before:
        return sorted(after)
    return sorted(after - before)


def partition_change_entries(
    entries: Iterable[str],
) -> tuple[list[str], list[str]]:
    """Separate artifact-only changes from potential evidence."""
    artifact_entries: list[str] = []
    evidence_entries: list[str] = []

    for entry in entries:
        if is_artifact_change(entry):
            artifact_entries.append(entry)
        else:
            evidence_entries.append(entry)

    return artifact_entries, evidence_entries


def is_artifact_change(entry: str) -> bool:
    """Heuristically detect whether a change originates from command artifacts."""
    parts = entry.split("\t")
    if len(parts) < 2:
        return False

    # git name-status formats place the path in the last column
    candidate = parts[-1].strip()
    return candidate.startswith("SuperClaude/Generated/") or candidate.startswith(
        ".worktrees/"
    )


def format_change_entry(entry: str) -> str:
    """Convert a git name-status entry into a human readable description."""
    parts = entry.split("\t")
    if not parts:
        return entry

    code = parts[0]
    code_letter = code[0] if code else "?"

    if code.startswith("??") and len(parts) >= 2:
        return f"add {parts[1]}"

    if code_letter == "M" and len(parts) >= 2:
        return f"modify {parts[1]}"

    if code_letter == "A" and len(parts) >= 2:
        return f"add {parts[1]}"

    if code_letter == "D" and len(parts) >= 2:
        return f"delete {parts[1]}"

    if code_letter == "R" and len(parts) >= 3:
        return f"rename {parts[1]} -> {parts[2]}"

    if code_letter == "C" and len(parts) >= 3:
        return f"copy {parts[1]} -> {parts[2]}"

    if len(parts) >= 2:
        return f"{code_letter.lower()} {parts[1]}"

    return entry


def run_command(
    command: Sequence[str],
    *,
    cwd: Path | None = None,
    repo_root: Path | None = None,
    env: dict[str, Any] | None = None,
    timeout: int | None = None,
) -> dict[str, Any]:
    """
    Execute a system command and capture its output.

    Returns:
        Dictionary containing command metadata, stdout, stderr, exit code, duration,
        and an optional error indicator.
    """
    args = [str(part) for part in command]
    working_dir = Path(cwd or repo_root or Path.cwd())
    runtime_env = os.environ.copy()
    runtime_env.setdefault("PYENV_DISABLE_REHASH", "1")
    if env:
        runtime_env.update({str(key): str(value) for key, value in env.items()})

    start = datetime.now()
    try:
        result = subprocess.run(
            args,
            cwd=str(working_dir),
            capture_output=True,
            text=True,
            env=runtime_env,
            timeout=timeout,
            check=False,
        )
        duration = (datetime.now() - start).total_seconds()
        stdout_text = (result.stdout or "").strip()
        stderr_text = (result.stderr or "").strip()
        output = {
            "command": " ".join(args),
            "args": args,
            "cwd": str(working_dir),
            "stdout": stdout_text,
            "stderr": stderr_text,
            "exit_code": result.returncode,
            "duration_s": duration,
        }
        if result.returncode != 0:
            output["error"] = f"exit code {result.returncode}"
        return output
    except subprocess.TimeoutExpired as exc:
        duration = (datetime.now() - start).total_seconds()
        stdout_text = getattr(exc, "stdout", "") or ""
        stderr_text = getattr(exc, "stderr", "") or ""
        return {
            "command": " ".join(args),
            "args": args,
            "cwd": str(working_dir),
            "stdout": stdout_text.strip(),
            "stderr": (stderr_text or "Command timed out").strip(),
            "exit_code": None,
            "duration_s": duration,
            "error": "timeout",
        }
    except Exception as exc:
        duration = (datetime.now() - start).total_seconds()
        return {
            "command": " ".join(args),
            "args": args,
            "cwd": str(working_dir),
            "stdout": "",
            "stderr": str(exc),
            "exit_code": None,
            "duration_s": duration,
            "error": str(exc),
        }


def collect_diff_stats(repo_root: Path | None) -> list[str]:
    """Collect diff statistics for working and staged changes."""
    if not repo_root or not (repo_root / ".git").exists():
        return []

    stats: list[str] = []
    commands = [
        ("working", ["git", "diff", "--stat"]),
        ("staged", ["git", "diff", "--stat", "--cached"]),
    ]

    for label, cmd in commands:
        try:
            result = subprocess.run(
                cmd, cwd=repo_root, capture_output=True, text=True, check=False
            )
        except Exception as exc:
            logger.debug(f"Failed to gather diff stats ({label}): {exc}")
            continue

        output = result.stdout.strip()
        if output:
            stats.append(f"diff --stat ({label}): {truncate_output(output)}")

    return stats


def clean_build_artifacts(repo_root: Path) -> tuple[list[str], list[str]]:
    """Remove common build artifacts when a clean build is requested."""
    removed: list[str] = []
    errors: list[str] = []
    targets = [
        "build",
        "dist",
        "htmlcov",
        ".pytest_cache",
        "SuperClaude.egg-info",
    ]

    for target in targets:
        path = repo_root / target
        if not path.exists():
            continue
        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
            removed.append(str(path.relative_to(repo_root)))
        except Exception as exc:
            errors.append(f"{target}: {exc}")

    return removed, errors


def git_has_modifications(repo_root: Path | None, file_path: Path) -> bool:
    """Check whether git reports pending changes for the path (excluding untracked files)."""
    if not repo_root or not (repo_root / ".git").exists():
        return False

    try:
        rel_path = file_path.relative_to(repo_root)
    except ValueError:
        # File sits outside repo root; treat as unmanaged.
        return False

    try:
        result = subprocess.run(
            ["git", "status", "--short", "--", str(rel_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception:
        return False

    if result.returncode != 0:
        return False

    output = result.stdout.strip()
    if not output:
        return False

    status = output.splitlines()[0][:2]
    if status == "??":
        return False
    return True


def extract_changed_paths(
    repo_root: Path | None,
    repo_entries: list[str],
    applied_changes: list[str],
) -> list[Path]:
    """Derive candidate file paths that were reported as changed."""
    if not repo_root:
        return []

    candidates: list[str] = []

    for entry in repo_entries:
        parts = entry.split("\t")
        if not parts:
            continue
        code = parts[0]
        if code.startswith("??") and len(parts) >= 2:
            candidates.append(parts[1])
        elif (code.startswith("R") or code.startswith("C")) and len(parts) >= 3:
            candidates.append(parts[2])
        elif len(parts) >= 2:
            candidates.append(parts[1])

    for change in applied_changes:
        tokens = change.split()
        if not tokens:
            continue
        verb = tokens[0].lower()
        if (verb in {"add", "modify", "delete"} and len(tokens) >= 2) or (
            verb in {"rename", "copy"} and len(tokens) >= 3
        ):
            candidates.append(tokens[-1])

    seen: set[str] = set()
    paths: list[Path] = []
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate or candidate.startswith("diff"):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        path = (repo_root / candidate).resolve()
        # Ensure we do not escape repo boundaries
        try:
            path.relative_to(repo_root)
        except ValueError:
            continue
        paths.append(path)

    return paths


def generate_commit_message(repo_root: Path) -> str:
    """Generate a conventional commit message based on repository changes."""
    status_result = run_command(["git", "status", "--short"], cwd=repo_root)
    stdout = status_result.get("stdout", "")
    if not stdout.strip():
        return "chore: update workspace"

    scopes: set[str] = set()
    doc_only = True
    test_only = True

    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        if len(parts) < 2:
            continue
        path_fragment = parts[1]
        path = Path(path_fragment)
        if path.parts:
            scopes.add(path.parts[0])
        suffix = path.suffix.lower()
        if suffix not in {".md", ".rst"}:
            doc_only = False
        if "test" not in path.parts and not path.parts[0].startswith("test"):
            test_only = False

    scope_text = "/".join(sorted(scopes)) if scopes else "project"
    if doc_only and not test_only:
        prefix = "docs"
    elif test_only and not doc_only:
        prefix = "test"
    else:
        prefix = "chore"

    return f"{prefix}: update {scope_text}"


def relative_to_repo_path(repo_root: Path | None, path: Path) -> str:
    """Convert absolute path to repo-relative string."""
    if not repo_root:
        return str(path)
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def extract_heading_titles(source_text: str) -> list[str]:
    """Extract top-level headings from a document."""
    titles: list[str] = []
    for line in source_text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue
        level = len(stripped) - len(stripped.lstrip("#"))
        if level > 3:
            continue
        title = stripped.lstrip("#").strip()
        if title:
            titles.append(title)
    return titles[:12]


def extract_feature_list(source_text: str) -> list[str]:
    """Extract feature-like bullet items from a document."""
    features: list[str] = []
    for line in source_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped[0] in {"-", "*"}:
            candidate = stripped[1:].strip(" -*\t")
            if candidate:
                features.append(candidate)
    return features[:12]


def select_feature_owner(description: str) -> str:
    """Choose an agent owner for a workflow item based on keywords."""
    text = description.lower()
    if any(keyword in text for keyword in ("frontend", "ui", "ux", "react", "view")):
        return "frontend-architect"
    if any(keyword in text for keyword in ("backend", "api", "service", "database")):
        return "backend-architect"
    if any(
        keyword in text for keyword in ("security", "auth", "permission", "compliance")
    ):
        return "security-engineer"
    if any(keyword in text for keyword in ("testing", "qa", "quality")):
        return "quality-engineer"
    if any(
        keyword in text for keyword in ("deployment", "infrastructure", "devops", "ci")
    ):
        return "devops-architect"
    return "general-purpose"


__all__ = [
    "clean_build_artifacts",
    "collect_diff_stats",
    "detect_repo_root",
    "diff_snapshots",
    "extract_changed_paths",
    "extract_feature_list",
    "extract_heading_titles",
    "format_change_entry",
    "generate_commit_message",
    "git_has_modifications",
    "is_artifact_change",
    "normalize_repo_root",
    "partition_change_entries",
    "relative_to_repo_path",
    "run_command",
    "select_feature_owner",
    "snapshot_repo_changes",
]
