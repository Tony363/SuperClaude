#!/usr/bin/env python3
"""
Scope Selector for Nightly Code Review

Determines which files to scan based on scope strategy:
- last-24h: Files changed in last 24 hours
- high-risk-dirs: Security-sensitive directories
- all: All source files (with budget limits)

Enforces budget guardrails to control costs and context limits.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any


# Configuration
HIGH_RISK_DIRS = [
    "src/auth/",
    "src/api/",
    "src/security/",
    "scripts/",
    ".github/workflows/",
]

ALLOWLIST_PATTERNS = [
    "*.py",
    "*.js",
    "*.ts",
    "*.tsx",
    "*.go",
    "*.rs",
    "*.java",
]

DENYLIST_PATTERNS = [
    "tests/fixtures/",
    "tests/data/",
    "**/node_modules/",
    "**/__pycache__/",
    "**/.venv/",
    "**/venv/",
    "**/.git/",
    "**/dist/",
    "**/build/",
    "**/.next/",
    "**/coverage/",
]


def get_git_files_changed_last_24h() -> List[Path]:
    """Get files changed in last 24 hours via git log."""
    since_time = datetime.now() - timedelta(hours=24)
    since_str = since_time.strftime("%Y-%m-%d %H:%M:%S")

    try:
        result = subprocess.run(
            ["git", "log", "--since", since_str, "--name-only", "--pretty=format:", "--diff-filter=ACMR"],
            capture_output=True,
            text=True,
            check=True
        )
        files = [
            Path(line.strip())
            for line in result.stdout.strip().split("\n")
            if line.strip()
        ]
        return list(set(files))  # Deduplicate
    except subprocess.CalledProcessError as e:
        print(f"Error getting git files: {e}", file=sys.stderr)
        return []


def get_high_risk_files(repo_root: Path) -> List[Path]:
    """Get all files in high-risk directories."""
    files = []
    for dir_pattern in HIGH_RISK_DIRS:
        dir_path = repo_root / dir_pattern
        if dir_path.exists() and dir_path.is_dir():
            files.extend(dir_path.rglob("*"))
    return [f for f in files if f.is_file()]


def get_all_source_files(repo_root: Path) -> List[Path]:
    """Get all source files matching allowlist patterns."""
    files = []
    for pattern in ALLOWLIST_PATTERNS:
        files.extend(repo_root.rglob(pattern))
    return [f for f in files if f.is_file()]


def matches_denylist(file_path: Path) -> bool:
    """Check if file matches any denylist pattern."""
    file_str = str(file_path)
    for pattern in DENYLIST_PATTERNS:
        # Simple pattern matching (can be enhanced with fnmatch)
        if pattern.strip("*") in file_str:
            return True
    return False


def count_lines_of_code(file_path: Path) -> int:
    """Count lines of code in a file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return sum(1 for line in f if line.strip())
    except (UnicodeDecodeError, OSError):
        return 0


def get_file_metadata(file_path: Path, repo_root: Path) -> Dict[str, Any]:
    """Get metadata for a file."""
    relative_path = file_path.relative_to(repo_root)
    loc = count_lines_of_code(file_path)

    # Get last modified time from git
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci", str(relative_path)],
            capture_output=True,
            text=True,
            check=True
        )
        last_modified = result.stdout.strip()
    except subprocess.CalledProcessError:
        last_modified = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()

    # Categorize by directory
    category = "general"
    for risk_dir in HIGH_RISK_DIRS:
        if str(relative_path).startswith(risk_dir):
            category = "high-risk"
            break

    return {
        "path": str(relative_path),
        "absolute_path": str(file_path),
        "lines_of_code": loc,
        "last_modified": last_modified,
        "category": category,
        "extension": file_path.suffix,
    }


def select_files(
    scope: str,
    repo_root: Path,
    max_files: int,
    max_loc: int
) -> List[Dict[str, Any]]:
    """Select files based on scope and budget constraints."""
    # Get candidate files based on scope
    if scope == "last-24h":
        candidates = get_git_files_changed_last_24h()
    elif scope == "high-risk-dirs":
        candidates = get_high_risk_files(repo_root)
    elif scope == "all":
        candidates = get_all_source_files(repo_root)
    else:
        print(f"Unknown scope: {scope}", file=sys.stderr)
        return []

    # Filter by allowlist/denylist
    candidates = [
        f for f in candidates
        if not matches_denylist(f)
    ]

    # Convert to absolute paths if relative
    candidates = [
        repo_root / f if not f.is_absolute() else f
        for f in candidates
    ]

    # Filter: only existing files
    candidates = [f for f in candidates if f.exists() and f.is_file()]

    # Get metadata
    files_with_metadata = []
    total_loc = 0

    for file_path in candidates:
        metadata = get_file_metadata(file_path, repo_root)
        files_with_metadata.append(metadata)
        total_loc += metadata["lines_of_code"]

    # Sort by category (high-risk first), then by LOC (smaller first for faster review)
    files_with_metadata.sort(
        key=lambda x: (x["category"] != "high-risk", x["lines_of_code"])
    )

    # Apply budget constraints
    selected_files = []
    selected_loc = 0

    for file_meta in files_with_metadata:
        if len(selected_files) >= max_files:
            break
        if selected_loc + file_meta["lines_of_code"] > max_loc:
            break

        selected_files.append(file_meta)
        selected_loc += file_meta["lines_of_code"]

    return selected_files


def main():
    parser = argparse.ArgumentParser(
        description="Select files for nightly code review"
    )
    parser.add_argument(
        "--scope",
        choices=["last-24h", "high-risk-dirs", "all"],
        default="last-24h",
        help="Scope selection strategy"
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=50,
        help="Maximum files per run"
    )
    parser.add_argument(
        "--max-loc",
        type=int,
        default=5000,
        help="Maximum lines of code per run"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("scope-selection.json"),
        help="Output JSON file"
    )

    args = parser.parse_args()

    # Get repository root
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True
        )
        repo_root = Path(result.stdout.strip())
    except subprocess.CalledProcessError:
        print("Error: Not a git repository", file=sys.stderr)
        sys.exit(1)

    # Select files
    selected_files = select_files(
        scope=args.scope,
        repo_root=repo_root,
        max_files=args.max_files,
        max_loc=args.max_loc
    )

    # Compute summary statistics
    total_loc = sum(f["lines_of_code"] for f in selected_files)
    high_risk_count = sum(1 for f in selected_files if f["category"] == "high-risk")

    # Output result
    output_data = {
        "scope": args.scope,
        "timestamp": datetime.now().isoformat(),
        "files": selected_files,
        "summary": {
            "total_files": len(selected_files),
            "total_loc": total_loc,
            "high_risk_files": high_risk_count,
            "max_files_limit": args.max_files,
            "max_loc_limit": args.max_loc,
        }
    }

    with open(args.output, "w") as f:
        json.dump(output_data, f, indent=2)

    print(f"Selected {len(selected_files)} files ({total_loc} LOC)")
    print(f"High-risk files: {high_risk_count}")
    print(f"Output written to: {args.output}")


if __name__ == "__main__":
    main()
