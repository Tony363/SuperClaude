"""
Deepwiki MCP Integration for SuperClaude Framework.

Provides documentation fetching and library reference capabilities.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
import json
import asyncio
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class DocumentationType(Enum):
    """Types of documentation available."""
    API_REFERENCE = "api_reference"
    GUIDE = "guide"
    TUTORIAL = "tutorial"
    EXAMPLE = "example"
    PATTERN = "pattern"
    CHANGELOG = "changelog"


@dataclass
class DeepwikiDocument:
    """Documentation result from Deepwiki MCP."""
    title: str
    content: str
    url: str
    library: str
    category: str
    doc_type: DocumentationType
    examples: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: Optional[str] = None
    last_updated: Optional[datetime] = None


@dataclass
class DeepwikiSearchResult:
    """Search result from Deepwiki."""
    query: str
    total_results: int
    documents: List[DeepwikiDocument]
    filters_applied: Dict[str, Any]
    search_time_ms: float


class DeepwikiIntegration:
    """
    Integration with Deepwiki MCP for documentation fetching.

    Features:
    - Library documentation retrieval
    - Framework pattern lookup
    - Code example fetching
    - API reference access
    - Cached documentation management
    - Multi-version support
    """

    SUPPORTED_LIBRARIES = [
        'react', 'vue', 'angular', 'svelte', 'solid',  # Frontend
        'express', 'fastapi', 'django', 'flask', 'nestjs',  # Backend
        'nextjs', 'nuxt', 'remix', 'gatsby', 'astro',  # Full-stack
        'tensorflow', 'pytorch', 'scikit-learn', 'pandas', 'numpy',  # ML/Data
        'typescript', 'javascript', 'python', 'rust', 'go'  # Languages
    ]

    CACHE_TTL = 3600  # 1 hour default cache
    MAX_CACHE_SIZE = 100  # Maximum cached documents

    def __init__(self, mcp_client=None, cache_ttl: int = CACHE_TTL):
        """
        Initialize Deepwiki integration.

        Args:
            mcp_client: Optional MCP client for Deepwiki server
            cache_ttl: Cache time-to-live in seconds
        """
        self.mcp_client = mcp_client
        self.cache = {}
        self.cache_ttl = cache_ttl
        self.cache_timestamps = {}
        self.request_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'errors': 0
        }

    def _get_cache_key(self,
                       library: str,
                       topic: Optional[str] = None,
                       version: Optional[str] = None) -> str:
        """Generate cache key for documentation."""
        parts = [library]
        if topic:
            parts.append(topic)
        if version:
            parts.append(f"v{version}")
        return ":".join(parts)

    def _is_cache_valid(self, key: str) -> bool:
        """Check if cached item is still valid."""
        if key not in self.cache_timestamps:
            return False

        timestamp = self.cache_timestamps[key]
        age = datetime.now() - timestamp
        return age.total_seconds() < self.cache_ttl

    def _update_cache(self, key: str, document: DeepwikiDocument):
        """Update cache with new document."""
        # Enforce cache size limit
        if len(self.cache) >= self.MAX_CACHE_SIZE:
            # Remove oldest cached item
            oldest_key = min(self.cache_timestamps, key=self.cache_timestamps.get)
            del self.cache[oldest_key]
            del self.cache_timestamps[oldest_key]

        self.cache[key] = document
        self.cache_timestamps[key] = datetime.now()

    async def fetch_documentation(self,
                                   library: str,
                                   topic: Optional[str] = None,
                                   version: Optional[str] = None,
                                   doc_type: Optional[DocumentationType] = None) -> DeepwikiDocument:
        """
        Fetch documentation for a library or specific topic.

        Args:
            library: Library name (e.g., 'react', 'vue')
            topic: Specific topic within library (optional)
            version: Library version (optional)
            doc_type: Type of documentation to fetch (optional)

        Returns:
            DeepwikiDocument with fetched content

        Raises:
            ValueError: If library is not supported
            RuntimeError: If MCP client is not available
        """
        if library not in self.SUPPORTED_LIBRARIES:
            raise ValueError(f"Library '{library}' not supported. Supported: {', '.join(self.SUPPORTED_LIBRARIES[:5])}...")

        if not self.mcp_client:
            raise RuntimeError("MCP client not initialized for Deepwiki")

        # Check cache first
        cache_key = self._get_cache_key(library, topic, version)
        if cache_key in self.cache and self._is_cache_valid(cache_key):
            self.request_stats['cache_hits'] += 1
            logger.debug(f"Cache hit for {cache_key}")
            return self.cache[cache_key]

        self.request_stats['cache_misses'] += 1
        self.request_stats['total_requests'] += 1

        try:
            # Prepare request parameters
            params = {
                'url': library if not topic else f"{library}/{topic}",
                'maxDepth': 1 if topic else 0,
                'mode': 'aggregate'
            }

            if version:
                params['url'] = f"{params['url']}@{version}"

            # Call MCP client
            logger.info(f"Fetching documentation for {library}{f'/{topic}' if topic else ''}")
            result = await self.mcp_client.deepwiki_fetch(**params)

            # Parse and create document
            document = DeepwikiDocument(
                title=result.get('title', f"{library} Documentation"),
                content=result.get('content', ''),
                url=result.get('url', f"https://deepwiki.com/{library}"),
                library=library,
                category=topic or 'general',
                doc_type=doc_type or DocumentationType.API_REFERENCE,
                examples=result.get('examples', []),
                metadata=result.get('metadata', {}),
                version=version,
                last_updated=datetime.now()
            )

            # Update cache
            self._update_cache(cache_key, document)

            return document

        except Exception as e:
            self.request_stats['errors'] += 1
            logger.error(f"Error fetching documentation: {e}")
            raise

    async def search_repository(self,
                                query: str,
                                filters: Optional[Dict[str, Any]] = None,
                                limit: int = 10) -> DeepwikiSearchResult:
        """
        Search documentation repository.

        Args:
            query: Search query
            filters: Optional filters (library, doc_type, version)
            limit: Maximum number of results

        Returns:
            DeepwikiSearchResult with matching documents
        """
        if not self.mcp_client:
            raise RuntimeError("MCP client not initialized for Deepwiki")

        start_time = datetime.now()
        filters = filters or {}

        try:
            # Perform search through MCP
            logger.info(f"Searching documentation: '{query}'")

            # For now, implement a simple search simulation
            # In production, this would call the actual MCP search endpoint
            documents = []

            # Filter by library if specified
            libraries_to_search = [filters.get('library')] if filters.get('library') else self.SUPPORTED_LIBRARIES[:5]

            for library in libraries_to_search:
                if query.lower() in library.lower():
                    doc = DeepwikiDocument(
                        title=f"{library} - {query}",
                        content=f"Documentation for {query} in {library}",
                        url=f"https://deepwiki.com/{library}/{query.replace(' ', '-')}",
                        library=library,
                        category="search_result",
                        doc_type=filters.get('doc_type', DocumentationType.GUIDE),
                        examples=[],
                        metadata={'search_query': query}
                    )
                    documents.append(doc)

                    if len(documents) >= limit:
                        break

            elapsed_ms = (datetime.now() - start_time).total_seconds() * 1000

            return DeepwikiSearchResult(
                query=query,
                total_results=len(documents),
                documents=documents,
                filters_applied=filters,
                search_time_ms=elapsed_ms
            )

        except Exception as e:
            logger.error(f"Error searching documentation: {e}")
            raise

    async def get_code_examples(self,
                                library: str,
                                pattern: str,
                                max_examples: int = 5) -> List[str]:
        """
        Get code examples for a specific pattern.

        Args:
            library: Library name
            pattern: Pattern or concept to find examples for
            max_examples: Maximum number of examples to return

        Returns:
            List of code examples
        """
        if library not in self.SUPPORTED_LIBRARIES:
            raise ValueError(f"Library '{library}' not supported")

        try:
            # Fetch documentation with examples focus
            doc = await self.fetch_documentation(
                library=library,
                topic=f"examples/{pattern}",
                doc_type=DocumentationType.EXAMPLE
            )

            # Extract code examples from document
            examples = doc.examples[:max_examples] if doc.examples else []

            # If no examples in the document, generate basic template
            if not examples:
                logger.warning(f"No examples found for {library}/{pattern}, generating template")
                examples = [self._generate_example_template(library, pattern)]

            return examples

        except Exception as e:
            logger.error(f"Error getting code examples: {e}")
            raise

    def _generate_example_template(self, library: str, pattern: str) -> str:
        """Generate a basic example template when none found."""
        templates = {
            'react': f"""// React {pattern} example
import React from 'react';

const {pattern.replace('-', '_').title()}Component = () => {{
  return <div>{pattern} implementation</div>;
}};

export default {pattern.replace('-', '_').title()}Component;""",

            'vue': f"""<!-- Vue {pattern} example -->
<template>
  <div>{pattern} implementation</div>
</template>

<script>
export default {{
  name: '{pattern.replace('-', '_').title()}Component'
}}
</script>""",

            'python': f"""# Python {pattern} example

def {pattern.replace('-', '_')}():
    \"\"\"Implementation of {pattern}\"\"\"
    pass

if __name__ == "__main__":
    {pattern.replace('-', '_')}()"""
        }

        return templates.get(library, f"// {library} {pattern} example\n// Implementation needed")

    async def get_api_reference(self,
                                library: str,
                                api_name: str,
                                include_examples: bool = True) -> DeepwikiDocument:
        """
        Get API reference documentation.

        Args:
            library: Library name
            api_name: API method or class name
            include_examples: Whether to include usage examples

        Returns:
            DeepwikiDocument with API reference
        """
        doc = await self.fetch_documentation(
            library=library,
            topic=f"api/{api_name}",
            doc_type=DocumentationType.API_REFERENCE
        )

        if include_examples:
            examples = await self.get_code_examples(library, api_name, max_examples=3)
            doc.examples = examples

        return doc

    def clear_cache(self):
        """Clear the documentation cache."""
        self.cache.clear()
        self.cache_timestamps.clear()
        logger.info("Documentation cache cleared")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'cache_size': len(self.cache),
            'max_cache_size': self.MAX_CACHE_SIZE,
            'cache_ttl': self.cache_ttl,
            'request_stats': self.request_stats,
            'cached_libraries': list(set(key.split(':')[0] for key in self.cache.keys()))
        }

    async def prefetch_common_docs(self, libraries: Optional[List[str]] = None):
        """
        Prefetch commonly used documentation to cache.

        Args:
            libraries: List of libraries to prefetch (defaults to top 5)
        """
        libraries = libraries or self.SUPPORTED_LIBRARIES[:5]

        logger.info(f"Prefetching documentation for: {', '.join(libraries)}")

        for library in libraries:
            try:
                await self.fetch_documentation(library)
                logger.debug(f"Prefetched {library} documentation")
            except Exception as e:
                logger.warning(f"Failed to prefetch {library}: {e}")

        logger.info("Prefetch complete")


# Export classes
__all__ = ['DeepwikiIntegration', 'DeepwikiDocument', 'DeepwikiSearchResult', 'DocumentationType']