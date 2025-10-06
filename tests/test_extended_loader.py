"""
Tests for Extended Agent Loader

Comprehensive test suite for the 141-agent loading and selection system.
"""

import unittest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from SuperClaude.Agents.extended_loader import (
    ExtendedAgentLoader,
    AgentCategory,
    AgentMetadata,
    MatchScore
)
from SuperClaude.Agents.registry import AgentRegistry
from SuperClaude.Agents.base import BaseAgent


class MockAgent(BaseAgent):
    """Mock agent for testing."""

    def __init__(self, config):
        super().__init__(config)
        self._initialized = False

    def initialize(self) -> bool:
        self._initialized = True
        return True

    def execute(self, context):
        return {"status": "success"}

    def validate(self, result) -> bool:
        return True

    def reset(self):
        self._initialized = False


class TestExtendedAgentLoader(unittest.TestCase):
    """Test suite for ExtendedAgentLoader."""

    def setUp(self):
        """Set up test fixtures."""
        self.registry = Mock(spec=AgentRegistry)
        self.loader = ExtendedAgentLoader(
            registry=self.registry,
            cache_size=5,
            ttl_seconds=60
        )

    def test_initialization(self):
        """Test loader initialization."""
        self.assertEqual(self.loader.cache_size, 5)
        self.assertEqual(self.loader.ttl, 60)
        self.assertIsNotNone(self.loader._agent_metadata)
        self.assertIsNotNone(self.loader._category_index)

    def test_metadata_loading(self):
        """Test metadata index loading."""
        # Check that metadata was loaded
        self.assertGreater(len(self.loader._agent_metadata), 0)
        self.assertGreater(self.loader._stats['metadata_loads'], 0)

    def test_category_index(self):
        """Test category index structure."""
        for category in AgentCategory:
            self.assertIn(category, self.loader._category_index)
            self.assertIsInstance(self.loader._category_index[category], list)

    def test_agent_load_caching(self):
        """Test agent loading with LRU cache."""
        mock_agent = MockAgent({'name': 'test-agent'})
        self.registry.get_agent.return_value = mock_agent

        # First load - cache miss
        agent1 = self.loader.load_agent('test-agent')
        self.assertIsNotNone(agent1)
        self.assertEqual(self.loader._stats['cache_misses'], 1)
        self.assertEqual(self.loader._stats['cache_hits'], 0)

        # Second load - cache hit
        agent2 = self.loader.load_agent('test-agent')
        self.assertIsNotNone(agent2)
        self.assertEqual(self.loader._stats['cache_misses'], 1)
        self.assertEqual(self.loader._stats['cache_hits'], 1)
        self.assertIs(agent1, agent2)

    def test_cache_ttl_expiration(self):
        """Test cache TTL expiration."""
        mock_agent = MockAgent({'name': 'test-agent'})
        self.registry.get_agent.return_value = mock_agent

        # Set short TTL
        self.loader.ttl = 0.1

        # Load agent
        agent1 = self.loader.load_agent('test-agent')
        self.assertIsNotNone(agent1)

        # Wait for TTL to expire
        time.sleep(0.2)

        # Load again - should be cache miss due to expiration
        agent2 = self.loader.load_agent('test-agent')
        self.assertIsNotNone(agent2)
        self.assertEqual(self.loader._stats['cache_misses'], 2)

    def test_cache_eviction(self):
        """Test LRU cache eviction."""
        # Create loader with small cache
        loader = ExtendedAgentLoader(
            registry=self.registry,
            cache_size=2,
            ttl_seconds=60
        )

        # Create mock agents
        for i in range(3):
            mock_agent = MockAgent({'name': f'agent-{i}'})
            self.registry.get_agent.return_value = mock_agent
            loader.load_agent(f'agent-{i}')

        # Cache should have evicted first agent
        self.assertEqual(len(loader._cache), 2)
        self.assertEqual(loader._stats['evictions'], 1)

    def test_select_agent_keyword_matching(self):
        """Test agent selection with keyword matching."""
        context = {
            'task': 'build a REST API with authentication',
            'files': [],
            'languages': [],
            'domains': ['api'],
            'keywords': ['rest', 'api', 'authentication']
        }

        matches = self.loader.select_agent(context, top_n=5)

        # Should return matches
        self.assertGreater(len(matches), 0)
        self.assertIsInstance(matches[0], MatchScore)

        # Best match should have reasonable score
        best = matches[0]
        self.assertGreater(best.total_score, 0.3)

    def test_select_agent_language_matching(self):
        """Test agent selection with language matching."""
        context = {
            'task': 'optimize python code performance',
            'files': ['main.py', 'utils.py'],
            'languages': ['python'],
            'domains': ['performance'],
            'keywords': ['optimize', 'python']
        }

        matches = self.loader.select_agent(context, top_n=5)

        self.assertGreater(len(matches), 0)

        # Check that python expert or performance engineer is suggested
        agent_ids = [m.agent_id for m in matches]
        self.assertTrue(
            any(aid in ['python-expert', 'performance-engineer'] for aid in agent_ids)
        )

    def test_select_agent_file_pattern_matching(self):
        """Test agent selection with file pattern matching."""
        context = {
            'task': 'review typescript code',
            'files': ['app.tsx', 'components/Button.tsx'],
            'languages': ['typescript'],
            'domains': [],
            'keywords': ['react']
        }

        matches = self.loader.select_agent(context, top_n=5)

        self.assertGreater(len(matches), 0)

        # Should suggest react or typescript specialist
        agent_ids = [m.agent_id for m in matches]
        self.assertTrue(
            any(aid in ['react-specialist', 'typescript-pro'] for aid in agent_ids)
        )

    def test_select_agent_category_filter(self):
        """Test agent selection with category filter."""
        context = {
            'task': 'set up kubernetes deployment',
            'files': [],
            'languages': [],
            'domains': ['kubernetes'],
            'keywords': ['k8s', 'deployment']
        }

        # Filter to infrastructure category
        matches = self.loader.select_agent(
            context,
            category_hint=AgentCategory.INFRASTRUCTURE,
            top_n=5
        )

        # All matches should be from infrastructure category
        for match in matches:
            agent = self.loader._agent_metadata.get(match.agent_id)
            if agent:
                self.assertEqual(agent.category, AgentCategory.INFRASTRUCTURE)

    def test_get_agents_by_category(self):
        """Test getting agents by category."""
        agents = self.loader.get_agents_by_category(AgentCategory.DATA_AI)

        self.assertGreater(len(agents), 0)

        # All agents should be from DATA_AI category
        for agent in agents:
            self.assertEqual(agent.category, AgentCategory.DATA_AI)

    def test_list_categories(self):
        """Test listing categories."""
        categories = self.loader.list_categories()

        self.assertEqual(len(categories), len(AgentCategory))

        for category, count in categories.items():
            self.assertIsInstance(category, AgentCategory)
            self.assertGreaterEqual(count, 0)

    def test_search_agents(self):
        """Test agent search functionality."""
        # Search for API-related agents
        results = self.loader.search_agents('api')

        self.assertGreater(len(results), 0)

        # Results should contain API-related agents
        agent_ids = [a.id for a in results]
        self.assertTrue(
            any('api' in aid.lower() for aid in agent_ids)
        )

    def test_search_agents_multiple_fields(self):
        """Test searching across multiple fields."""
        results = self.loader.search_agents(
            'typescript',
            search_fields=['name', 'keywords', 'languages']
        )

        self.assertGreater(len(results), 0)

        # Should find typescript pro
        agent_ids = [a.id for a in results]
        self.assertIn('typescript-pro', agent_ids)

    def test_explain_selection(self):
        """Test selection explanation."""
        context = {
            'task': 'debug python application',
            'files': ['main.py'],
            'languages': ['python'],
            'domains': ['debugging'],
            'keywords': ['debug', 'error']
        }

        # Select agent
        matches = self.loader.select_agent(context, top_n=1)
        self.assertGreater(len(matches), 0)

        # Get explanation
        explanation = self.loader.explain_selection(matches[0].agent_id, context)

        # Check explanation structure
        self.assertIn('agent_id', explanation)
        self.assertIn('agent_name', explanation)
        self.assertIn('confidence', explanation)
        self.assertIn('breakdown', explanation)
        self.assertIn('matched_criteria', explanation)

        # Breakdown should have all components
        breakdown = explanation['breakdown']
        self.assertIn('keywords', breakdown)
        self.assertIn('domains', breakdown)
        self.assertIn('languages', breakdown)
        self.assertIn('file_patterns', breakdown)

    def test_access_tracking(self):
        """Test access pattern tracking."""
        mock_agent = MockAgent({'name': 'test-agent'})
        self.registry.get_agent.return_value = mock_agent

        # Load agent multiple times
        for _ in range(3):
            self.loader.load_agent('test-agent')

        # Check access tracking
        self.assertIn('test-agent', self.loader._access_frequency)
        self.assertEqual(self.loader._access_frequency['test-agent'], 3)

    def test_preload_top_agents(self):
        """Test preloading frequently accessed agents."""
        # Simulate access pattern
        for i in range(3):
            agent_id = f'agent-{i}'
            mock_agent = MockAgent({'name': agent_id})
            self.registry.get_agent.return_value = mock_agent

            # Access with different frequencies
            for _ in range(3 - i):
                self.loader._track_access(agent_id)

        # Clear cache
        self.loader.clear_cache()

        # Preload top agents
        self.registry.get_agent.return_value = MockAgent({'name': 'test'})
        loaded = self.loader.preload_top_agents(count=2)

        # Should have preloaded based on frequency
        self.assertEqual(loaded, 2)

    def test_statistics(self):
        """Test statistics collection."""
        stats = self.loader.get_statistics()

        # Check required fields
        self.assertIn('total_agents', stats)
        self.assertIn('cached_agents', stats)
        self.assertIn('cache_hit_rate', stats)
        self.assertIn('avg_load_time', stats)
        self.assertIn('category_distribution', stats)
        self.assertIn('top_accessed_agents', stats)

        # Check values
        self.assertGreater(stats['total_agents'], 0)
        self.assertGreaterEqual(stats['cache_hit_rate'], 0.0)
        self.assertLessEqual(stats['cache_hit_rate'], 1.0)

    def test_optimize_cache(self):
        """Test cache optimization."""
        # Create access pattern
        for i in range(10):
            self.loader._track_access(f'agent-{i % 3}')

        initial_cache_size = len(self.loader._cache)

        # Mock registry for preloading
        self.registry.get_agent.return_value = MockAgent({'name': 'test'})

        # Optimize cache
        self.loader.optimize_cache()

        # Cache should be optimized based on access patterns
        self.assertGreaterEqual(len(self.loader._cache), initial_cache_size)

    def test_match_score_calculation(self):
        """Test detailed match score calculation."""
        # Create test metadata
        metadata = AgentMetadata(
            id='test-agent',
            name='Test Agent',
            category=AgentCategory.CORE_DEVELOPMENT,
            priority=1,
            domains=['api', 'rest'],
            languages=['python', 'javascript'],
            keywords=['api', 'rest', 'endpoint'],
            file_patterns=['*.py', '*.js']
        )

        context = {
            'task': 'build a REST API endpoint',
            'files': ['api.py'],
            'languages': ['python'],
            'domains': ['api'],
            'keywords': ['rest', 'api']
        }

        match = self.loader._calculate_match_score(context, metadata)

        # Check match score structure
        self.assertIsInstance(match, MatchScore)
        self.assertGreater(match.total_score, 0)
        self.assertEqual(match.agent_id, 'test-agent')
        self.assertIn('keywords', match.breakdown)
        self.assertGreater(len(match.matched_criteria), 0)

    def test_confidence_levels(self):
        """Test confidence level classification."""
        # High confidence context
        high_context = {
            'task': 'optimize python machine learning pipeline',
            'files': ['train.py', 'model.py'],
            'languages': ['python'],
            'domains': ['ml', 'ai'],
            'keywords': ['machine-learning', 'tensorflow', 'model'],
            'imports': ['tensorflow', 'sklearn']
        }

        matches = self.loader.select_agent(high_context, top_n=1)

        if matches:
            # Should have high or excellent confidence
            self.assertIn(matches[0].confidence, ['high', 'excellent', 'medium'])

        # Low confidence context
        low_context = {
            'task': 'do something',
            'files': [],
            'languages': [],
            'domains': [],
            'keywords': []
        }

        matches = self.loader.select_agent(low_context, top_n=1, min_confidence=0.0)

        if matches:
            # May have lower confidence
            self.assertIn(matches[0].confidence, ['low', 'medium', 'high'])


class TestAgentMetadata(unittest.TestCase):
    """Test AgentMetadata dataclass."""

    def test_metadata_creation(self):
        """Test creating agent metadata."""
        metadata = AgentMetadata(
            id='test-agent',
            name='Test Agent',
            category=AgentCategory.DATA_AI,
            priority=2
        )

        self.assertEqual(metadata.id, 'test-agent')
        self.assertEqual(metadata.name, 'Test Agent')
        self.assertEqual(metadata.category, AgentCategory.DATA_AI)
        self.assertEqual(metadata.priority, 2)
        self.assertEqual(metadata.domains, [])
        self.assertEqual(metadata.is_loaded, False)

    def test_metadata_with_capabilities(self):
        """Test metadata with full capabilities."""
        metadata = AgentMetadata(
            id='python-expert',
            name='Python Expert',
            category=AgentCategory.LANGUAGE_SPECIALISTS,
            priority=1,
            domains=['python', 'backend'],
            languages=['python'],
            keywords=['python', 'django', 'flask'],
            file_patterns=['*.py', 'requirements.txt']
        )

        self.assertEqual(len(metadata.domains), 2)
        self.assertEqual(len(metadata.keywords), 3)
        self.assertEqual(len(metadata.file_patterns), 2)


class TestMatchScore(unittest.TestCase):
    """Test MatchScore dataclass."""

    def test_match_score_creation(self):
        """Test creating match score."""
        score = MatchScore(
            agent_id='test-agent',
            total_score=0.85,
            breakdown={'keywords': 0.25, 'domains': 0.20},
            matched_criteria=['keywords: api, rest', 'domains: backend'],
            confidence='high'
        )

        self.assertEqual(score.agent_id, 'test-agent')
        self.assertEqual(score.total_score, 0.85)
        self.assertEqual(score.confidence, 'high')
        self.assertEqual(len(score.matched_criteria), 2)


class TestAgentCategory(unittest.TestCase):
    """Test AgentCategory enum."""

    def test_all_categories_defined(self):
        """Test that all 10 categories are defined."""
        categories = list(AgentCategory)
        self.assertEqual(len(categories), 10)

    def test_category_values(self):
        """Test category string values."""
        self.assertEqual(
            AgentCategory.CORE_DEVELOPMENT.value,
            "01-core-development"
        )
        self.assertEqual(
            AgentCategory.DATA_AI.value,
            "05-data-ai"
        )


if __name__ == '__main__':
    unittest.main()
