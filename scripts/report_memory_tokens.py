#!/usr/bin/env python3
"""Estimate token usage for Claude Code memory files."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Iterable


def estimate_tokens(text: str) -> int:
    """Roughly convert character count to tokens (≈4 characters per token)."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


def iter_memory_files(root: Path) -> Iterable[tuple[Path, int]]:
    """Yield Markdown files and their estimated token counts."""
    for path in sorted(root.rglob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        yield path, estimate_tokens(content)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--install-dir",
        default="~/.claude",
        help="Target Claude installation directory (default: ~/.claude)",
    )
    args = parser.parse_args()

    install_dir = Path(args.install_dir).expanduser().resolve()
    if not install_dir.exists():
        raise SystemExit(f"Install directory not found: {install_dir}")

    entries = list(iter_memory_files(install_dir))
    if not entries:
        print(f"No Markdown memory files found under {install_dir}")
        return

    total = 0
    print(f"Memory token report for {install_dir}\n")
    for path, tokens in entries:
        total += tokens
        relative = path.relative_to(install_dir)
        print(f"{tokens:8d} tokens  {relative}")

    print("\n" + "-" * 40)
    print(f"Total estimated tokens: {total}")


if __name__ == "__main__":
    main()
