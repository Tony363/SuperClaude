"""Repository-level retrieval utilities for agent grounding."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


EXCLUDED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "__pycache__",
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    ".superclaude_metrics",
}

ALLOWED_SUFFIXES = {
    ".py",
    ".md",
    ".txt",
    ".rst",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".cfg",
}


@dataclass(frozen=True)
class RetrievalHit:
    file: str
    line: int
    snippet: str


class RepoRetriever:
    """Simple text-based retriever for the local repository."""

    def __init__(self, root: Path, *, max_files: int = 2000) -> None:
        self.root = Path(root)
        self.max_files = max_files
        self._candidate_files = self._discover_files()

    def _discover_files(self) -> List[Path]:
        files: List[Path] = []
        for path in self.root.rglob("*"):
            if path.is_dir():
                if path.name in EXCLUDED_DIRECTORIES:
                    # Skip walking into excluded directory
                    entries = list(path.glob("*"))
                    for entry in entries:
                        if entry.is_dir():
                            continue
                    continue
                continue

            if path.suffix.lower() not in ALLOWED_SUFFIXES:
                continue

            if any(part in EXCLUDED_DIRECTORIES for part in path.relative_to(self.root).parts):
                continue

            files.append(path)
            if len(files) >= self.max_files:
                break
        return files

    def retrieve(self, query: str, *, limit: int = 5, context_radius: int = 2) -> List[RetrievalHit]:
        query = (query or "").strip()
        if not query or len(query) < 3:
            return []

        pattern = re.compile(re.escape(query), re.IGNORECASE)
        hits: List[RetrievalHit] = []

        for file_path in self._candidate_files:
            if len(hits) >= limit:
                break
            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            match = pattern.search(text)
            if not match:
                continue

            lines = text.splitlines()
            # Determine line number containing first match
            cumulative = 0
            target_line = 0
            for idx, line in enumerate(lines, start=1):
                cumulative += len(line) + 1
                if cumulative >= match.start():
                    target_line = idx
                    break

            start = max(0, target_line - 1 - context_radius)
            end = min(len(lines), target_line - 1 + context_radius + 1)
            snippet = "\n".join(lines[start:end]).strip()

            rel = file_path.relative_to(self.root)
            hits.append(RetrievalHit(file=str(rel), line=target_line, snippet=snippet))

        return hits

    def refresh(self) -> None:
        """Refresh the retriever file list."""
        self._candidate_files = self._discover_files()
