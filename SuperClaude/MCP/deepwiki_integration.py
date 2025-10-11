"""
Deepwiki MCP Integration (Local Doc Search)

Implements simple filesystem-based search over project documentation
folders to emulate a documentation repository.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional
from pathlib import Path


class DocumentationType(Enum):
    user_guide = "user_guide"
    api_reference = "api_reference"
    tutorial = "tutorial"
    misc = "misc"


@dataclass
class DeepwikiDocument:
    title: str
    path: str
    doc_type: DocumentationType
    snippet: str


@dataclass
class DeepwikiSearchResult:
    query: str
    documents: List[DeepwikiDocument]
    total: int


class DeepwikiIntegration:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.roots = [
            Path(self.config.get("docs_dir", "Docs")),
            Path(self.config.get("alt_docs_dir", "docs")),
        ]

    def initialize(self):
        return True

    async def initialize_session(self):
        return True

    async def search(self, query: str, limit: int = 10) -> DeepwikiSearchResult:
        q = query.lower()
        results: List[DeepwikiDocument] = []
        for root in self.roots:
            if not root.exists():
                continue
            for path in root.rglob("*.md"):
                try:
                    text = path.read_text(encoding="utf-8")
                except Exception:
                    continue
                if q in text.lower() or q in path.name.lower():
                    snippet = text[:140].replace("\n", " ") if text else ""
                    results.append(
                        DeepwikiDocument(
                            title=path.stem,
                            path=str(path),
                            doc_type=DocumentationType.misc,
                            snippet=snippet,
                        )
                    )
                if len(results) >= limit:
                    break
        return DeepwikiSearchResult(query=query, documents=results, total=len(results))

