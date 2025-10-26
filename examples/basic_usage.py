#!/usr/bin/env python3
"""
SuperClaude Framework Basic Usage Examples
Demonstrates core functionality of v6.0.0-alpha
"""

import asyncio
import os
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from SuperClaude.Agents.loader import AgentLoader
from SuperClaude.Commands.registry import CommandRegistry
from SuperClaude.ModelRouter.router import ModelRouter
from SuperClaude.Quality.quality_scorer import QualityScorer
from SuperClaude.Core.worktree_manager import WorktreeManager
from SuperClaude.Agents.extended_loader import ExtendedAgentLoader

async def example_agent_loading():
    """Example: Loading and using agents"""
    print("\n=== Agent Loading Example ===")

    # Load core agents
    core_loader = AgentLoader()
    core_agents = await core_loader.get_available_agents()
    print(f"Loaded {len(core_agents)} core agents")

    # Load extended agents
    extended_loader = ExtendedAgentLoader()
    extended_agents = extended_loader.load_all_agents()
    print(f"Loaded {len(extended_agents)} extended agents")

    # Select an agent for a task
    task = "Debug authentication flow"
    agent = await core_loader.select_agent(task)
    print(f"Selected agent for '{task}': {agent.id}")

async def example_model_routing():
    """Example: Intelligent model routing"""
    print("\n=== Model Routing Example ===")

    router = ModelRouter()

    # Route for deep thinking
    model = await router.select_model(
        task_type="deep-thinking",
        context_size=45000,
        priority="high"
    )
    print(f"Deep thinking model: {model['name']} ({model['context_window']} tokens)")

    # Route for long context
    model = await router.select_model(
        task_type="bulk-analysis",
        context_size=500000,
        priority="medium"
    )
    print(f"Long context model: {model['name']} ({model['context_window']} tokens)")

    # Route for fast iteration
    model = await router.select_model(
        task_type="quick-fix",
        context_size=5000,
        priority="low"
    )
    print(f"Fast iteration model: {model['name']} ({model['context_window']} tokens)")

async def example_command_registry():
    """Example: Command discovery and execution"""
    print("\n=== Command Registry Example ===")

    registry = CommandRegistry()

    # Load all commands
    commands = await registry.load_commands()
    print(f"Loaded {len(commands)} commands")

    # Search for specific command
    git_commands = await registry.search_commands("git")
    print(f"Found {len(git_commands)} git-related commands")

    # Get command details
    if git_commands:
        cmd = git_commands[0]
        print(f"Command: {cmd['name']}")
        print(f"Description: {cmd['description']}")
        print(f"Category: {cmd['metadata'].get('category', 'general')}")

def example_quality_scoring():
    """Example: Quality scoring system"""
    print("\n=== Quality Scoring Example ===")

    scorer = QualityScorer()

    # Score a code implementation
    metrics = {
        'correctness': 85,
        'completeness': 90,
        'performance': 75,
        'maintainability': 80,
        'security': 70,
        'scalability': 85,
        'testability': 95,
        'usability': 80
    }

    score = scorer.calculate_score(metrics)
    print(f"Overall quality score: {score['overall']}/100")
    print(f"Grade: {score['grade']}")
    print(f"Action: {score['action']}")

    # Show dimension breakdown
    print("\nDimension scores:")
    for dim, value in metrics.items():
        print(f"  {dim}: {value}/100")

async def example_worktree_management():
    """Example: Git worktree management"""
    print("\n=== Worktree Management Example ===")

    manager = WorktreeManager("/tmp/demo-repo")

    # Create worktree for feature
    worktree = await manager.create_worktree(
        task_id="auth-feature",
        branch="feature/authentication"
    )
    print(f"Created worktree: {worktree['path']}")
    print(f"Branch: {worktree['branch']}")

    # List active worktrees
    worktrees = await manager.list_worktrees()
    print(f"Active worktrees: {len(worktrees)}")

    # Validate before merge
    validation = await manager.validate_worktree(worktree['id'])
    print(f"Validation status: {validation['status']}")
    print(f"Ready to merge: {validation['ready']}")

async def example_mcp_integration():
    """Example: MCP server integration"""
    print("\n=== MCP Integration Example ===")

    # Import MCP integrations
    from SuperClaude.MCP import (
        ZenIntegration,
        RubeIntegration,
    )

    # Zen multi-model consensus
    zen = ZenIntegration()
    consensus = await zen.build_consensus(
        "Should we migrate to microservices?",
        models=["gpt-5", "claude-opus-4.1", "gemini-2.5-pro"]
    )
    print(f"Consensus reached: {consensus['agreement']}")
    print(f"Confidence: {consensus['confidence']}%")

    # Optional Rube automation (dry-run by default)
    os.environ.setdefault("SC_RUBE_MODE", "dry-run")
    rube = RubeIntegration()
    rube.initialize()
    await rube.initialize_session()
    dry_run = await rube.invoke("demo.tool", {"ping": "pong"})
    print(f"Rube invocation status: {dry_run['status']}")

async def example_coordination():
    """Example: Multi-agent coordination"""
    print("\n=== Agent Coordination Example ===")

    from SuperClaude.Coordination.agent_coordinator import AgentCoordinator

    coordinator = AgentCoordinator()

    # Define complex task
    task = {
        'goal': 'Implement secure authentication system',
        'subtasks': [
            'Design auth architecture',
            'Implement JWT tokens',
            'Add OAuth2 support',
            'Create user management',
            'Write tests',
            'Document API'
        ]
    }

    # Coordinate agents
    result = await coordinator.coordinate(
        task=task,
        strategy='hierarchical',
        agents=['system-architect', 'backend-architect', 'security-engineer', 'technical-writer']
    )

    print(f"Coordination strategy: {result['strategy']}")
    print(f"Agents involved: {len(result['agents'])}")
    print(f"Tasks completed: {result['completed']}/{result['total']}")
    print(f"Time taken: {result['duration']}s")

async def example_performance_monitoring():
    """Example: Performance monitoring"""
    print("\n=== Performance Monitoring Example ===")

    from SuperClaude.Monitoring.performance_monitor import PerformanceMonitor

    monitor = PerformanceMonitor()

    # Start monitoring
    monitor.start_collection()

    # Simulate some operations
    await asyncio.sleep(0.1)

    # Get metrics
    metrics = monitor.get_metrics()
    print(f"CPU Usage: {metrics['cpu_percent']}%")
    print(f"Memory Usage: {metrics['memory_percent']}%")
    print(f"Token Usage: {metrics['token_count']}")
    print(f"Cache Hit Rate: {metrics['cache_hit_rate']}%")

    # Check for bottlenecks
    bottlenecks = monitor.detect_bottlenecks()
    if bottlenecks:
        print(f"Bottlenecks detected: {', '.join(bottlenecks)}")

async def main():
    """Run all examples"""
    print("SuperClaude Framework v6.0.0-alpha Examples")
    print("=" * 50)

    # Run examples
    await example_agent_loading()
    await example_model_routing()
    await example_command_registry()
    example_quality_scoring()
    await example_worktree_management()
    await example_mcp_integration()
    await example_coordination()
    await example_performance_monitoring()

    print("\n" + "=" * 50)
    print("Examples completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
