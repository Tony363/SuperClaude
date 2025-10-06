"""
Tests for Deepwiki MCP Integration
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from SuperClaude.MCP.deepwiki_integration import (
    DeepwikiIntegration,
    DeepwikiDocument,
    DeepwikiSearchResult,
    DocumentationType
)


class TestDeepwikiIntegration:
    """Test suite for Deepwiki integration."""

    @pytest.fixture
    def mock_mcp_client(self):
        """Create mock MCP client."""
        client = Mock()
        client.deepwiki_fetch = AsyncMock()
        return client

    @pytest.fixture
    def deepwiki(self, mock_mcp_client):
        """Create Deepwiki integration instance."""
        return DeepwikiIntegration(mcp_client=mock_mcp_client, cache_ttl=60)

    @pytest.mark.asyncio
    async def test_fetch_documentation_basic(self, deepwiki, mock_mcp_client):
        """Test basic documentation fetching."""
        # Setup mock response
        mock_mcp_client.deepwiki_fetch.return_value = {
            'title': 'React Documentation',
            'content': 'React is a JavaScript library for building user interfaces.',
            'url': 'https://deepwiki.com/react',
            'examples': ['const App = () => <div>Hello</div>;'],
            'metadata': {'version': '18.2.0'}
        }

        # Fetch documentation
        doc = await deepwiki.fetch_documentation('react')

        # Verify
        assert doc.title == 'React Documentation'
        assert doc.library == 'react'
        assert doc.content == 'React is a JavaScript library for building user interfaces.'
        assert len(doc.examples) == 1
        assert doc.metadata['version'] == '18.2.0'

        # Verify MCP client was called correctly
        mock_mcp_client.deepwiki_fetch.assert_called_once_with(
            url='react',
            maxDepth=0,
            mode='aggregate'
        )

    @pytest.mark.asyncio
    async def test_fetch_documentation_with_topic(self, deepwiki, mock_mcp_client):
        """Test fetching documentation with specific topic."""
        # Setup mock response
        mock_mcp_client.deepwiki_fetch.return_value = {
            'title': 'React Hooks',
            'content': 'Hooks let you use state and other React features.',
            'url': 'https://deepwiki.com/react/hooks',
            'examples': ['const [count, setCount] = useState(0);'],
            'metadata': {}
        }

        # Fetch documentation with topic
        doc = await deepwiki.fetch_documentation('react', topic='hooks')

        # Verify
        assert doc.title == 'React Hooks'
        assert doc.category == 'hooks'

        # Verify MCP client was called with topic
        mock_mcp_client.deepwiki_fetch.assert_called_once_with(
            url='react/hooks',
            maxDepth=1,
            mode='aggregate'
        )

    @pytest.mark.asyncio
    async def test_fetch_documentation_with_version(self, deepwiki, mock_mcp_client):
        """Test fetching documentation with specific version."""
        mock_mcp_client.deepwiki_fetch.return_value = {
            'title': 'React v17 Documentation',
            'content': 'React version 17 documentation.',
            'url': 'https://deepwiki.com/react@17',
            'examples': [],
            'metadata': {}
        }

        # Fetch with version
        doc = await deepwiki.fetch_documentation('react', version='17.0.0')

        # Verify version handling
        assert doc.version == '17.0.0'
        mock_mcp_client.deepwiki_fetch.assert_called_once_with(
            url='react@17.0.0',
            maxDepth=0,
            mode='aggregate'
        )

    @pytest.mark.asyncio
    async def test_cache_functionality(self, deepwiki, mock_mcp_client):
        """Test cache hit and miss functionality."""
        mock_response = {
            'title': 'Vue Documentation',
            'content': 'Vue.js documentation.',
            'url': 'https://deepwiki.com/vue',
            'examples': [],
            'metadata': {}
        }
        mock_mcp_client.deepwiki_fetch.return_value = mock_response

        # First call - cache miss
        doc1 = await deepwiki.fetch_documentation('vue')
        assert deepwiki.request_stats['cache_misses'] == 1
        assert deepwiki.request_stats['cache_hits'] == 0

        # Second call - cache hit
        doc2 = await deepwiki.fetch_documentation('vue')
        assert deepwiki.request_stats['cache_hits'] == 1
        assert deepwiki.request_stats['cache_misses'] == 1

        # Verify MCP client was only called once
        assert mock_mcp_client.deepwiki_fetch.call_count == 1

        # Documents should be the same
        assert doc1.title == doc2.title
        assert doc1.content == doc2.content

    @pytest.mark.asyncio
    async def test_cache_expiry(self, mock_mcp_client):
        """Test cache expiry after TTL."""
        # Create integration with very short TTL
        deepwiki = DeepwikiIntegration(mcp_client=mock_mcp_client, cache_ttl=0)

        mock_mcp_client.deepwiki_fetch.return_value = {
            'title': 'Angular Documentation',
            'content': 'Angular framework documentation.',
            'url': 'https://deepwiki.com/angular',
            'examples': [],
            'metadata': {}
        }

        # First call
        await deepwiki.fetch_documentation('angular')

        # Second call after TTL expired
        await asyncio.sleep(0.1)
        await deepwiki.fetch_documentation('angular')

        # Both should be cache misses due to expired TTL
        assert deepwiki.request_stats['cache_misses'] == 2
        assert deepwiki.request_stats['cache_hits'] == 0
        assert mock_mcp_client.deepwiki_fetch.call_count == 2

    @pytest.mark.asyncio
    async def test_unsupported_library_error(self, deepwiki):
        """Test error handling for unsupported libraries."""
        with pytest.raises(ValueError) as exc_info:
            await deepwiki.fetch_documentation('nonexistent-library')

        assert "not supported" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_no_mcp_client_error(self):
        """Test error when MCP client is not initialized."""
        deepwiki = DeepwikiIntegration(mcp_client=None)

        with pytest.raises(RuntimeError) as exc_info:
            await deepwiki.fetch_documentation('react')

        assert "MCP client not initialized" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_search_repository(self, deepwiki, mock_mcp_client):
        """Test repository search functionality."""
        result = await deepwiki.search_repository('react hooks', limit=5)

        assert isinstance(result, DeepwikiSearchResult)
        assert result.query == 'react hooks'
        assert result.total_results <= 5
        assert isinstance(result.documents, list)
        assert result.search_time_ms > 0

    @pytest.mark.asyncio
    async def test_search_with_filters(self, deepwiki):
        """Test search with library filter."""
        filters = {'library': 'vue', 'doc_type': DocumentationType.TUTORIAL}
        result = await deepwiki.search_repository('components', filters=filters)

        assert result.filters_applied == filters
        # All results should be from Vue
        for doc in result.documents:
            assert doc.library == 'vue'

    @pytest.mark.asyncio
    async def test_get_code_examples(self, deepwiki, mock_mcp_client):
        """Test code example retrieval."""
        mock_mcp_client.deepwiki_fetch.return_value = {
            'title': 'React useState Examples',
            'content': 'Examples of useState hook.',
            'url': 'https://deepwiki.com/react/examples/useState',
            'examples': [
                'const [count, setCount] = useState(0);',
                'const [name, setName] = useState("");',
                'const [items, setItems] = useState([]);'
            ],
            'metadata': {}
        }

        examples = await deepwiki.get_code_examples('react', 'useState', max_examples=2)

        assert len(examples) == 2
        assert 'useState' in examples[0]
        assert 'useState' in examples[1]

    @pytest.mark.asyncio
    async def test_get_code_examples_fallback_template(self, deepwiki, mock_mcp_client):
        """Test code example template generation when no examples found."""
        mock_mcp_client.deepwiki_fetch.return_value = {
            'title': 'React Custom Hook',
            'content': 'Documentation for custom hooks.',
            'url': 'https://deepwiki.com/react/examples/custom-hook',
            'examples': [],  # No examples
            'metadata': {}
        }

        examples = await deepwiki.get_code_examples('react', 'custom-hook')

        assert len(examples) == 1
        assert 'React custom-hook example' in examples[0]
        assert 'import React' in examples[0]

    @pytest.mark.asyncio
    async def test_get_api_reference(self, deepwiki, mock_mcp_client):
        """Test API reference fetching."""
        mock_mcp_client.deepwiki_fetch.side_effect = [
            # First call for API reference
            {
                'title': 'useState API',
                'content': 'useState is a Hook that lets you add React state.',
                'url': 'https://deepwiki.com/react/api/useState',
                'examples': [],
                'metadata': {'signature': 'const [state, setState] = useState(initialState)'}
            },
            # Second call for examples
            {
                'title': 'useState Examples',
                'content': 'Examples',
                'url': 'https://deepwiki.com/react/examples/useState',
                'examples': ['const [count, setCount] = useState(0);'],
                'metadata': {}
            }
        ]

        doc = await deepwiki.get_api_reference('react', 'useState', include_examples=True)

        assert doc.title == 'useState API'
        assert doc.doc_type == DocumentationType.API_REFERENCE
        assert len(doc.examples) > 0

    def test_clear_cache(self, deepwiki):
        """Test cache clearing."""
        # Add some items to cache
        deepwiki.cache['test:key'] = Mock()
        deepwiki.cache_timestamps['test:key'] = datetime.now()

        assert len(deepwiki.cache) == 1

        # Clear cache
        deepwiki.clear_cache()

        assert len(deepwiki.cache) == 0
        assert len(deepwiki.cache_timestamps) == 0

    def test_get_cache_stats(self, deepwiki):
        """Test cache statistics retrieval."""
        # Add some test data
        deepwiki.cache['react:hooks'] = Mock()
        deepwiki.cache['vue:components'] = Mock()
        deepwiki.request_stats['total_requests'] = 10
        deepwiki.request_stats['cache_hits'] = 3

        stats = deepwiki.get_cache_stats()

        assert stats['cache_size'] == 2
        assert stats['max_cache_size'] == deepwiki.MAX_CACHE_SIZE
        assert stats['cache_ttl'] == 60
        assert stats['request_stats']['total_requests'] == 10
        assert stats['request_stats']['cache_hits'] == 3
        assert 'react' in stats['cached_libraries']
        assert 'vue' in stats['cached_libraries']

    @pytest.mark.asyncio
    async def test_prefetch_common_docs(self, deepwiki, mock_mcp_client):
        """Test prefetching common documentation."""
        mock_mcp_client.deepwiki_fetch.return_value = {
            'title': 'Documentation',
            'content': 'Content',
            'url': 'https://deepwiki.com/',
            'examples': [],
            'metadata': {}
        }

        # Prefetch top 3 libraries
        await deepwiki.prefetch_common_docs(['react', 'vue', 'angular'])

        # Should have called fetch 3 times
        assert mock_mcp_client.deepwiki_fetch.call_count == 3

        # Cache should contain 3 entries
        assert len(deepwiki.cache) == 3

    @pytest.mark.asyncio
    async def test_prefetch_with_failure(self, deepwiki, mock_mcp_client):
        """Test prefetching handles failures gracefully."""
        # Make one library fail
        mock_mcp_client.deepwiki_fetch.side_effect = [
            {'title': 'React', 'content': 'React docs', 'url': 'url', 'examples': [], 'metadata': {}},
            Exception("Network error"),
            {'title': 'Angular', 'content': 'Angular docs', 'url': 'url', 'examples': [], 'metadata': {}}
        ]

        # Prefetch should continue despite failure
        await deepwiki.prefetch_common_docs(['react', 'vue', 'angular'])

        # Should have attempted all 3
        assert mock_mcp_client.deepwiki_fetch.call_count == 3

        # Cache should contain 2 successful entries
        assert len(deepwiki.cache) == 2

    def test_cache_key_generation(self, deepwiki):
        """Test cache key generation for different parameters."""
        key1 = deepwiki._get_cache_key('react')
        assert key1 == 'react'

        key2 = deepwiki._get_cache_key('react', 'hooks')
        assert key2 == 'react:hooks'

        key3 = deepwiki._get_cache_key('react', 'hooks', '18.2.0')
        assert key3 == 'react:hooks:v18.2.0'

    def test_cache_size_limit(self, deepwiki):
        """Test cache size limit enforcement."""
        # Set a small cache size for testing
        deepwiki.MAX_CACHE_SIZE = 3

        # Add items exceeding the limit
        for i in range(5):
            key = f'lib{i}:topic'
            deepwiki._update_cache(key, Mock())

        # Cache should only contain the last 3 items
        assert len(deepwiki.cache) == 3
        assert 'lib2:topic' in deepwiki.cache
        assert 'lib3:topic' in deepwiki.cache
        assert 'lib4:topic' in deepwiki.cache
        assert 'lib0:topic' not in deepwiki.cache
        assert 'lib1:topic' not in deepwiki.cache

    def test_supported_libraries(self, deepwiki):
        """Test supported libraries list."""
        assert 'react' in deepwiki.SUPPORTED_LIBRARIES
        assert 'vue' in deepwiki.SUPPORTED_LIBRARIES
        assert 'angular' in deepwiki.SUPPORTED_LIBRARIES
        assert 'express' in deepwiki.SUPPORTED_LIBRARIES
        assert 'tensorflow' in deepwiki.SUPPORTED_LIBRARIES
        assert 'python' in deepwiki.SUPPORTED_LIBRARIES

    def test_documentation_type_enum(self):
        """Test DocumentationType enum values."""
        assert DocumentationType.API_REFERENCE.value == 'api_reference'
        assert DocumentationType.GUIDE.value == 'guide'
        assert DocumentationType.TUTORIAL.value == 'tutorial'
        assert DocumentationType.EXAMPLE.value == 'example'
        assert DocumentationType.PATTERN.value == 'pattern'
        assert DocumentationType.CHANGELOG.value == 'changelog'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])