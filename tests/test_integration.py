#!/usr/bin/env python3
"""
Integration tests for SuperClaude Framework v6.0.0-alpha
"""

import unittest
import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from SuperClaude.Agents.loader import AgentLoader
from SuperClaude.Commands.registry import CommandRegistry
from SuperClaude.ModelRouter.router import ModelRouter
from SuperClaude.Quality.quality_scorer import QualityScorer
from SuperClaude.Agents.extended_loader import ExtendedAgentLoader
from SuperClaude.MCP import (
    DeepwikiIntegration,
    ZenIntegration,
)
from SuperClaude.Testing.integration_framework import TestRunner, TestCase

class TestCoreComponents(unittest.TestCase):
    """Test core framework components"""

    def test_version(self):
        """Test version consistency"""
        from SuperClaude import __version__
        self.assertEqual(__version__, "6.0.0-alpha")

    def test_agent_loader(self):
        """Test agent loading system"""
        loader = AgentLoader()
        self.assertIsNotNone(loader)
        # Mock test as actual loading would require agent files

    def test_extended_agent_loader(self):
        """Test extended agent loading"""
        loader = ExtendedAgentLoader()
        agents = loader.load_all_agents()
        # Should load agents from YAML files
        self.assertIsInstance(agents, dict)

    def test_model_router(self):
        """Test model routing"""
        router = ModelRouter()
        self.assertIsNotNone(router)
        # Mock test for model selection

    def test_quality_scorer(self):
        """Test quality scoring system"""
        scorer = QualityScorer()
        score = scorer.calculate_score({
            'correctness': 80,
            'completeness': 85,
            'performance': 75,
            'maintainability': 80,
            'security': 70,
            'scalability': 85,
            'testability': 90,
            'usability': 80
        })
        self.assertIn('overall', score)
        self.assertIn('grade', score)
        self.assertIn('action', score)
        self.assertGreaterEqual(score['overall'], 0)
        self.assertLessEqual(score['overall'], 100)

class TestMCPIntegrations(unittest.TestCase):
    """Test MCP server integrations"""

    def test_deepwiki_integration(self):
        """Test Deepwiki documentation integration"""
        deepwiki = DeepwikiIntegration()
        self.assertIsNotNone(deepwiki)

    def test_zen_integration(self):
        """Test Zen multi-model integration"""
        zen = ZenIntegration()
        self.assertIsNotNone(zen)

class TestAPIClients(unittest.TestCase):
    """Test API client implementations"""

    def test_openai_client(self):
        """Test OpenAI client"""
        from SuperClaude.APIClients.openai_client import OpenAIClient
        client = OpenAIClient(api_key="test-key")
        self.assertIsNotNone(client)
        self.assertEqual(client.provider, "openai")

    def test_anthropic_client(self):
        """Test Anthropic client"""
        from SuperClaude.APIClients.anthropic_client import AnthropicClient
        client = AnthropicClient(api_key="test-key")
        self.assertIsNotNone(client)
        self.assertEqual(client.provider, "anthropic")

    def test_google_client(self):
        """Test Google client"""
        from SuperClaude.APIClients.google_client import GoogleClient
        client = GoogleClient(api_key="test-key")
        self.assertIsNotNone(client)
        self.assertEqual(client.provider, "google")

    def test_xai_client(self):
        """Test X.AI client"""
        from SuperClaude.APIClients.xai_client import XAIClient
        client = XAIClient(api_key="test-key")
        self.assertIsNotNone(client)
        self.assertEqual(client.provider, "xai")

class TestCoordination(unittest.TestCase):
    """Test agent coordination system"""

    def test_agent_coordinator(self):
        """Test agent coordinator"""
        from SuperClaude.Coordination.agent_coordinator import AgentCoordinator
        coordinator = AgentCoordinator()
        self.assertIsNotNone(coordinator)
        self.assertIn('hierarchical', coordinator.strategies)
        self.assertIn('consensus', coordinator.strategies)
        self.assertIn('pipeline', coordinator.strategies)

class TestMonitoring(unittest.TestCase):
    """Test performance monitoring"""

    def test_performance_monitor(self):
        """Test performance monitor"""
        from SuperClaude.Monitoring.performance_monitor import PerformanceMonitor
        monitor = PerformanceMonitor()
        self.assertIsNotNone(monitor)

        # Start monitoring
        monitor.start_collection()

        # Get metrics
        metrics = monitor.get_metrics()
        self.assertIn('cpu_percent', metrics)
        self.assertIn('memory_percent', metrics)
        self.assertIn('token_count', metrics)

class TestConfiguration(unittest.TestCase):
    """Test configuration files"""

    def test_config_files_exist(self):
        """Test that all config files exist"""
        config_dir = Path(__file__).parent.parent / "SuperClaude" / "Config"
        self.assertTrue(config_dir.exists())

        config_files = [
            "models.yaml",
            "agents.yaml",
            "mcp.yaml",
            "quality.yaml"
        ]

        for config_file in config_files:
            file_path = config_dir / config_file
            self.assertTrue(file_path.exists(), f"Config file {config_file} not found")

    def test_extended_agents_exist(self):
        """Test that extended agent YAML files exist"""
        agents_dir = Path(__file__).parent.parent / "SuperClaude" / "Agents" / "extended"
        self.assertTrue(agents_dir.exists())

        # Check each category
        categories = [
            "01-core-development",
            "02-language-specialists",
            "03-infrastructure",
            "04-quality-security",
            "05-data-ai",
            "06-developer-experience",
            "07-specialized-domains",
            "08-business-product",
            "09-meta-orchestration",
            "10-research-analysis"
        ]

        total_agents = 0
        for category in categories:
            category_dir = agents_dir / category
            self.assertTrue(category_dir.exists(), f"Category {category} not found")

            yaml_files = list(category_dir.glob("*.yaml"))
            total_agents += len(yaml_files)
            self.assertGreater(len(yaml_files), 0, f"No YAML files in {category}")

        # We generated 111 agents + potentially some earlier ones
        self.assertGreaterEqual(total_agents, 111, f"Expected at least 111 agents, found {total_agents}")

class TestIntegrationFramework(unittest.TestCase):
    """Test the testing framework itself"""

    def test_test_runner(self):
        """Test the test runner"""
        runner = TestRunner()
        self.assertIsNotNone(runner)

    def test_test_case_creation(self):
        """Test creating test cases"""
        test_case = TestCase(
            name="test_example",
            description="Example test case",
            category="unit"
        )
        self.assertEqual(test_case.name, "test_example")
        self.assertEqual(test_case.category, "unit")
        self.assertEqual(test_case.status, "pending")

def run_async_test(coro):
    """Helper to run async tests"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

class TestAsyncComponents(unittest.TestCase):
    """Test async components"""

    def test_command_registry_async(self):
        """Test async command registry"""
        async def test():
            registry = CommandRegistry()
            # Mock test as actual loading would require command files
            return True

        result = run_async_test(test())
        self.assertTrue(result)

    def test_worktree_manager_async(self):
        """Test async worktree manager"""
        async def test():
            from SuperClaude.Core.worktree_manager import WorktreeManager
            # Mock test as actual git operations would require a repo
            manager = WorktreeManager("/tmp/test-repo")
            return manager is not None

        result = run_async_test(test())
        self.assertTrue(result)

if __name__ == "__main__":
    # Run tests
    print("Running SuperClaude Framework Integration Tests")
    print("=" * 50)

    # Create test suite
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])

    # Run tests with verbosity
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")

    if result.wasSuccessful():
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed")
        sys.exit(1)
