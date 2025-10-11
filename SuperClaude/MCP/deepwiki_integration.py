"""
Deepwiki MCP Integration

Implements a lightweight documentation helper that wraps the Deepwiki MCP
endpoint and provides caching, search, and convenience utilities used by
the SuperClaude test-suite.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

logger = logging.getLogger(__name__)


class DocumentationType(Enum):
    """Documentation categories supported by Deepwiki."""

    API_REFERENCE = "api_reference"
    GUIDE = "guide"
    TUTORIAL = "tutorial"
    EXAMPLE = "example"
    PATTERN = "pattern"
    CHANGELOG = "changelog"
    USER_GUIDE = "user_guide"
    MISC = "misc"

    @classmethod
    def from_value(cls, value: Optional[str]) -> "DocumentationType":
        if not value:
            return cls.GUIDE
        normalized = value.strip().lower().replace(" ", "_")
        for member in cls:
            if member.value == normalized:
                return member
        return cls.MISC


@dataclass
class DeepwikiDocument:
    """Represents a documentation record returned from Deepwiki."""

    title: str
    library: str
    content: str
    url: str
    doc_type: DocumentationType
    category: Optional[str] = None
    version: Optional[str] = None
    examples: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    snippet: Optional[str] = None


@dataclass
class DeepwikiSearchResult:
    """Search results returned from repository search."""

    query: str
    documents: List[DeepwikiDocument]
    total_results: int
    search_time_ms: float
    filters_applied: Dict[str, Any] = field(default_factory=dict)
    limit: int = 0
    total: int = 0  # Backwards compatibility alias

    def __post_init__(self):
        if not self.total:
            self.total = self.total_results


class DeepwikiIntegration:
    """Deepwiki integration with caching and convenience helpers."""

    DEFAULT_CACHE_TTL = 60  # seconds
    DEFAULT_MAX_CACHE_SIZE = 128

    SUPPORTED_LIBRARIES: Iterable[str] = (
        "react",
        "vue",
        "angular",
        "express",
        "tensorflow",
        "python",
        "django",
        "flask",
        "pytorch",
        "aws",
        "gcp",
        "azure",
    )

    def __init__(
        self,
        mcp_client: Optional[Any] = None,
        cache_ttl: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.mcp_client = mcp_client
        self.config = config or {}

        self.cache_ttl = cache_ttl if cache_ttl is not None else self.DEFAULT_CACHE_TTL
        self.MAX_CACHE_SIZE = self.DEFAULT_MAX_CACHE_SIZE

        self.cache: Dict[str, DeepwikiDocument] = {}
        self.cache_timestamps: Dict[str, datetime] = {}
        self._cache_order: deque[str] = deque()

        self.request_stats: Dict[str, Any] = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "last_request_at": None,
        }

        self.roots = [
            Path(self.config.get("docs_dir", "Docs")),
            Path(self.config.get("alt_docs_dir", "docs")),
        ]

    # --------------------------------------------------------------------- #
    # Lifecycle
    # --------------------------------------------------------------------- #
    def initialize(self) -> bool:
        return True

    async def initialize_session(self) -> bool:
        return True

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    async def fetch_documentation(
        self,
        library: str,
        topic: Optional[str] = None,
        version: Optional[str] = None,
        force_refresh: bool = False,
    ) -> DeepwikiDocument:
        """Fetch documentation for a library/topic/version combination."""
        library_key = library.lower()
        self._validate_library(library_key)

        cache_key = self._get_cache_key(library_key, topic, version)
        self._record_request()

        if not force_refresh:
            cached = self._get_cached_document(cache_key)
            if cached:
                self.request_stats["cache_hits"] += 1
                return cached

        self.request_stats["cache_misses"] += 1
        payload = await self._fetch_from_mcp(
            library=library_key,
            topic=topic,
            version=version,
        )
        document = self._build_document(
            library=library_key,
            topic=topic,
            version=version,
            payload=payload,
            doc_type=DocumentationType.from_value(
                payload.get("metadata", {}).get("doc_type")
            ),
        )
        self._update_cache(cache_key, document)
        return document

    async def search_repository(
        self,
        query: str,
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> DeepwikiSearchResult:
        """Search local documentation repositories."""
        start = time.perf_counter()
        filters = filters or {}
        query_lower = query.lower()
        results: List[DeepwikiDocument] = []

        for root in self.roots:
            if not root.exists():
                continue
            for path in root.rglob("*.md"):
                try:
                    text = path.read_text(encoding="utf-8")
                except Exception:  # pragma: no cover - unexpected decoding issues
                    continue

                if query_lower not in text.lower() and query_lower not in path.name.lower():
                    continue

                library = filters.get("library") or path.stem.split("_")[0].lower()
                doc_type = filters.get("doc_type") or DocumentationType.GUIDE
                snippet = text[:160].replace("\n", " ") if text else ""

                document = DeepwikiDocument(
                    title=path.stem,
                    library=library,
                    content=text,
                    url=str(path),
                    doc_type=doc_type,
                    snippet=snippet,
                )

                # Apply library/doc_type filters strictly
                if filters.get("library") and document.library != filters["library"]:
                    continue
                if filters.get("doc_type") and document.doc_type != filters["doc_type"]:
                    continue

                results.append(document)
                if len(results) >= limit:
                    break
            if len(results) >= limit:
                break

        elapsed_ms = max((time.perf_counter() - start) * 1000.0, 0.01)
        total_results = len(results)
        return DeepwikiSearchResult(
            query=query,
            documents=results,
            total_results=total_results,
            search_time_ms=elapsed_ms,
            filters_applied=filters,
            limit=limit,
        )

    async def get_code_examples(
        self,
        library: str,
        topic: str,
        max_examples: int = 3,
    ) -> List[str]:
        """Retrieve code examples for a library/topic."""
        library_key = library.lower()
        self._validate_library(library_key)
        payload = await self._fetch_from_mcp(
            library=library_key,
            topic=f"{topic}/examples",
            max_depth=1,
            mode="examples",
        )
        examples = payload.get("examples", []) or []
        if examples:
            return examples[:max_examples]
        return [self._generate_example_template(library_key, topic)]

    async def get_api_reference(
        self,
        library: str,
        topic: str,
        include_examples: bool = False,
    ) -> DeepwikiDocument:
        """Fetch API reference documentation for a topic."""
        library_key = library.lower()
        self._validate_library(library_key)

        payload = await self._fetch_from_mcp(
            library=library_key,
            topic=f"api/{topic}",
            max_depth=0,
            mode="api",
        )
        document = self._build_document(
            library=library_key,
            topic=topic,
            version=None,
            payload=payload,
            doc_type=DocumentationType.API_REFERENCE,
        )
        if include_examples:
            document.examples = await self.get_code_examples(library_key, topic)
        return document

    async def prefetch_common_docs(
        self,
        libraries: Iterable[str],
    ) -> None:
        """Prefetch documentation for commonly used libraries."""
        for library in libraries:
            try:
                await self.fetch_documentation(
                    library=library,
                    force_refresh=True,
                )
            except Exception as exc:  # pragma: no cover - defensive
                logger.debug("Prefetch failed for %s: %s", library, exc)

    def clear_cache(self) -> None:
        """Remove all cached documentation."""
        self.cache.clear()
        self.cache_timestamps.clear()
        self._cache_order.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Return statistics about the documentation cache."""
        cache_size = len(self.cache)
        cached_libraries = sorted({key.split(":")[0] for key in self.cache})
        total_requests = max(self.request_stats["total_requests"], 1)
        return {
            "cache_size": cache_size,
            "max_cache_size": self.MAX_CACHE_SIZE,
            "cache_ttl": self.cache_ttl,
            "cache_hit_rate": self.request_stats["cache_hits"] / total_requests,
            "request_stats": dict(self.request_stats),
            "cached_libraries": cached_libraries,
        }

    # ------------------------------------------------------------------ #
    # Compatibility helpers
    # ------------------------------------------------------------------ #
    async def search(self, query: str, limit: int = 10) -> DeepwikiSearchResult:
        """Backwards compatible alias for search_repository."""
        return await self.search_repository(query, limit=limit)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    def _validate_library(self, library: str) -> None:
        if library not in self.SUPPORTED_LIBRARIES:
            raise ValueError(f"Library '{library}' is not supported by Deepwiki.")

    def _record_request(self) -> None:
        self.request_stats["total_requests"] += 1
        self.request_stats["last_request_at"] = datetime.now().isoformat()

    def _get_cache_key(
        self,
        library: str,
        topic: Optional[str] = None,
        version: Optional[str] = None,
    ) -> str:
        parts = [library]
        if topic:
            parts.append(topic)
        if version:
            parts.append(f"v{version}")
        return ":".join(parts)

    def _get_cached_document(self, key: str) -> Optional[DeepwikiDocument]:
        if key not in self.cache:
            return None
        timestamp = self.cache_timestamps.get(key)
        if not timestamp:
            return None
        if self.cache_ttl is not None and self.cache_ttl <= 0:
            return None
        if datetime.now() - timestamp > timedelta(seconds=self.cache_ttl):
            # Expired entry
            self.cache.pop(key, None)
            self.cache_timestamps.pop(key, None)
            try:
                self._cache_order.remove(key)
            except ValueError:
                pass
            return None
        return self.cache[key]

    def _update_cache(self, key: str, document: DeepwikiDocument) -> None:
        self.cache[key] = document
        self.cache_timestamps[key] = datetime.now()
        if key in self._cache_order:
            self._cache_order.remove(key)
        self._cache_order.append(key)
        self._prune_cache_if_needed()

    def _prune_cache_if_needed(self) -> None:
        while len(self.cache) > self.MAX_CACHE_SIZE:
            oldest_key = self._cache_order.popleft()
            self.cache.pop(oldest_key, None)
            self.cache_timestamps.pop(oldest_key, None)

    async def _fetch_from_mcp(
        self,
        library: str,
        topic: Optional[str] = None,
        version: Optional[str] = None,
        max_depth: Optional[int] = None,
        mode: str = "aggregate",
    ) -> Dict[str, Any]:
        self._ensure_mcp_client()

        url = self._compose_url(library, topic, version)
        params = {
            "url": url,
            "maxDepth": max_depth if max_depth is not None else (1 if topic else 0),
            "mode": mode,
        }
        response = await self.mcp_client.deepwiki_fetch(**params)
        return response or {}

    def _compose_url(
        self,
        library: str,
        topic: Optional[str],
        version: Optional[str],
    ) -> str:
        base = library
        if version:
            base = f"{library}@{version}"
        if topic:
            sanitized = topic.strip("/")
            return f"{base}/{sanitized}"
        return base

    def _ensure_mcp_client(self) -> None:
        if not self.mcp_client or not hasattr(self.mcp_client, "deepwiki_fetch"):
            raise RuntimeError("MCP client not initialized or missing deepwiki_fetch.")

    def _build_document(
        self,
        library: str,
        topic: Optional[str],
        version: Optional[str],
        payload: Dict[str, Any],
        doc_type: DocumentationType,
    ) -> DeepwikiDocument:
        content = payload.get("content") or ""
        snippet = content[:200].replace("\n", " ") if content else None
        metadata = payload.get("metadata", {}).copy()
        examples = payload.get("examples", []) or []

        document = DeepwikiDocument(
            title=payload.get("title") or topic or library.title(),
            library=library,
            content=content,
            url=payload.get("url") or self._compose_url(library, topic, version),
            doc_type=doc_type,
            category=topic,
            version=version,
            examples=list(examples),
            metadata=metadata,
            snippet=snippet,
        )
        return document

    def _generate_example_template(self, library: str, topic: str) -> str:
        topic_label = topic.replace("-", " ").title()
        library_label = library.title()
        template = (
            f"// {library_label} {topic} example\n"
            f"import {library_label if library == 'react' else library_label} from '{library}';\n"
            f"function {topic_label.replace(' ', '')}Example() {{\n"
            f"    return <div>{library_label} {topic} example</div>;\n"
            f"}}\n"
        )
        return template
