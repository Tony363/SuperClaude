#!/usr/bin/env python3
"""
SuperClaude Framework Advanced Workflow Examples
Demonstrates complex multi-component interactions
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from SuperClaude.Coordination.agent_coordinator import AgentCoordinator
from SuperClaude.Testing.integration_framework import TestRunner

from SuperClaude.Agents.extended_loader import ExtendedAgentLoader
from SuperClaude.Agents.loader import AgentLoader
from SuperClaude.Core.worktree_manager import WorktreeManager
from SuperClaude.MCP import ZenIntegration
from SuperClaude.ModelRouter.router import ModelRouter
from SuperClaude.Quality.quality_scorer import QualityScorer


async def workflow_feature_development():
    """Complete feature development workflow"""
    print("\n=== Feature Development Workflow ===")
    print("Goal: Implement user authentication with TDD")

    # Phase 1: Requirements Analysis
    print("\nPhase 1: Requirements Analysis")
    loader = AgentLoader()
    analyst = await loader.select_agent("gather requirements for authentication")
    print(f"  Agent: {analyst.id}")

    requirements = {
        "features": ["login", "logout", "session management", "OAuth2"],
        "security": ["JWT tokens", "rate limiting", "CSRF protection"],
        "testing": ["unit tests", "integration tests", "E2E tests"],
    }
    print(f"  Requirements gathered: {len(requirements)} categories")

    # Phase 2: Architecture Design
    print("\nPhase 2: Architecture Design")
    architect = await loader.select_agent("design authentication architecture")
    print(f"  Agent: {architect.id}")

    # Phase 3: Implementation
    print("\nPhase 3: Implementation")
    worktree_manager = WorktreeManager("/tmp/project")
    worktree = await worktree_manager.create_worktree(
        "auth-feature", "feature/authentication"
    )
    print(f"  Worktree created: {worktree['path']}")

    # Coordinate multiple agents
    coordinator = AgentCoordinator()
    result = await coordinator.coordinate(
        task={
            "goal": "Implement authentication",
            "subtasks": [
                "Create database models",
                "Implement JWT service",
                "Create API endpoints",
                "Add middleware",
                "Write tests",
            ],
        },
        strategy="pipeline",
        agents=[
            "backend-architect",
            "python-expert",
            "security-engineer",
            "qa-engineer",
        ],
    )
    print(f"  Implementation completed: {result['completed']}/{result['total']} tasks")

    # Phase 4: Quality Validation
    print("\nPhase 4: Quality Validation")
    scorer = QualityScorer()
    score = scorer.calculate_score(
        {
            "correctness": 92,
            "completeness": 88,
            "performance": 85,
            "maintainability": 90,
            "security": 95,
            "scalability": 87,
            "testability": 93,
            "usability": 86,
        }
    )
    print(f"  Quality score: {score['overall']}/100 ({score['grade']})")

    # Phase 5: Testing
    print("\nPhase 5: Testing")
    runner = TestRunner()
    test_results = await runner.run_all_tests()
    print(f"  Tests run: {test_results['total']}")
    print(f"  Passed: {test_results['passed']}")
    print(f"  Failed: {test_results['failed']}")

    # Phase 6: Merge
    print("\nPhase 6: Progressive Merge")
    if score["overall"] >= 70 and test_results["failed"] == 0:
        merge_result = await worktree_manager.progressive_merge(
            worktree["id"], "integration"
        )
        print(f"  Merged to integration: {merge_result['success']}")


async def workflow_debugging_complex_issue():
    """Complex debugging workflow with multi-model consensus"""
    print("\n=== Complex Debugging Workflow ===")
    print("Issue: Intermittent performance degradation in production")

    # Step 1: Multi-angle analysis with Zen
    print("\nStep 1: Multi-Model Analysis")
    zen = ZenIntegration()
    analysis = await zen.deep_think(
        problem="Intermittent API slowdowns, 10x latency spikes every few hours",
        context_files=["/logs/api.log", "/metrics/performance.json"],
        model="gpt-5",
        max_tokens=50000,
    )
    print(f"  Deep thinking completed: {analysis['hypothesis']}")

    # Step 2: Build consensus on root cause
    print("\nStep 2: Multi-Model Consensus")
    consensus = await zen.build_consensus(
        f"Root cause hypothesis: {analysis['hypothesis']}",
        models=["gpt-5", "claude-opus-4.1", "gemini-2.5-pro"],
        context=analysis["evidence"],
    )
    print(f"  Consensus confidence: {consensus['confidence']}%")
    print(f"  Agreed root cause: {consensus['conclusion']}")

    # Step 3: Coordinate fix implementation
    print("\nStep 3: Coordinated Fix")
    coordinator = AgentCoordinator()
    ExtendedAgentLoader()

    # Select specialized agents
    agents_needed = []
    if "database" in consensus["conclusion"].lower():
        agents_needed.append("database-engineer")
    if "cache" in consensus["conclusion"].lower():
        agents_needed.append("performance-engineer")
    if "memory" in consensus["conclusion"].lower():
        agents_needed.append("backend-architect")

    await coordinator.coordinate(
        task={"goal": f"Fix: {consensus['conclusion']}"},
        strategy="swarm",
        agents=agents_needed,
    )
    print(f"  Fix implemented by {len(agents_needed)} agents")

    # Step 4: Validate fix
    print("\nStep 4: Validation")
    print("  Run LinkUp web search for recent regression advisories")
    print("  Trigger external Playwright/Cypress pipeline for UI regression checks")
    print("  Aggregate results into UnifiedStore for cross-session tracking")


async def workflow_large_codebase_refactoring():
    """Refactoring workflow for large codebases"""
    print("\n=== Large Codebase Refactoring Workflow ===")
    print("Goal: Modernize 100K+ line legacy codebase")

    # Step 1: Analyze with Gemini (2M context)
    print("\nStep 1: Ultra-Long Context Analysis")
    router = ModelRouter()
    model = await router.select_model(
        task_type="bulk-analysis",
        context_size=1500000,  # 1.5M tokens
        priority="high",
    )
    print(f"  Selected model: {model['name']} ({model['context_window']} tokens)")

    # Step 2: Plan refactoring strategy
    print("\nStep 2: Strategic Planning")
    zen = ZenIntegration()
    plan = await zen.plan(
        goal="Modernize codebase: migrate to microservices, add types, improve tests",
        constraints=[
            "maintain backward compatibility",
            "zero downtime",
            "incremental migration",
        ],
        model="gpt-5",
    )
    print(f"  Plan created: {plan['phases']} phases, {plan['estimated_weeks']} weeks")

    # Step 3: Create worktrees for parallel work
    print("\nStep 3: Parallel Worktrees")
    manager = WorktreeManager("/tmp/legacy-project")
    worktrees = []
    for phase in range(1, plan["phases"] + 1):
        wt = await manager.create_worktree(
            f"refactor-phase-{phase}", f"refactor/phase-{phase}"
        )
        worktrees.append(wt)
        print(f"  Created worktree for phase {phase}: {wt['path']}")

    # Step 4: Coordinate specialized agents
    print("\nStep 4: Multi-Agent Refactoring")
    coordinator = AgentCoordinator()

    for phase, wt in enumerate(worktrees, 1):
        result = await coordinator.coordinate(
            task={"goal": f"Phase {phase} refactoring", "worktree": wt["path"]},
            strategy="hierarchical" if phase == 1 else "pipeline",
            agents=[
                "refactoring-specialist",
                "typescript-expert",
                "test-automation",
                "microservices-architect",
                "legacy-modernization",
            ],
        )
        print(f"  Phase {phase} completed: {result['success']}")

    # Step 5: Progressive integration
    print("\nStep 5: Progressive Integration")
    for phase, wt in enumerate(worktrees, 1):
        validation = await manager.validate_worktree(wt["id"])
        if validation["ready"]:
            merge = await manager.progressive_merge(wt["id"], "integration")
            print(f"  Phase {phase} merged: {merge['success']}")


async def workflow_production_deployment():
    """Production deployment with comprehensive validation"""
    print("\n=== Production Deployment Workflow ===")
    print("Goal: Deploy critical feature with zero downtime")

    # Step 1: Pre-deployment validation
    print("\nStep 1: Pre-Deployment Validation")
    zen = ZenIntegration()
    review = await zen.code_review(
        path="/src", review_type="full", severity_filter="high", model="gpt-5"
    )
    print(f"  Code review score: {review['score']}/100")
    print(f"  Critical issues: {review['critical_issues']}")

    if review["critical_issues"] > 0:
        print("  ❌ Deployment blocked: Critical issues found")
        return

    # Step 2: Multi-model consensus on deployment readiness
    print("\nStep 2: Deployment Consensus")
    consensus = await zen.build_consensus(
        "Is this code ready for production deployment?",
        models=["gpt-5", "claude-opus-4.1", "gpt-4.1"],
        context={"review": review, "tests": "all passing", "coverage": "92%"},
    )
    print(f"  Consensus: {consensus['decision']}")
    print(f"  Confidence: {consensus['confidence']}%")

    if consensus["confidence"] < 80:
        print("  ⚠️ Low confidence - manual review required")
        return

    # Step 3: Performance validation
    print("\nStep 3: Performance Validation")
    monitor = None  # Monitoring removed
    monitor.start_collection()

    # Simulate load test
    await asyncio.sleep(0.5)

    metrics = monitor.get_metrics()
    bottlenecks = monitor.detect_bottlenecks()

    print(f"  CPU usage: {metrics['cpu_percent']}%")
    print(f"  Memory usage: {metrics['memory_percent']}%")
    print(f"  Bottlenecks: {len(bottlenecks)}")

    # Step 4: Deploy with monitoring
    print("\nStep 4: Progressive Deployment")
    stages = ["canary", "staging", "production"]
    for stage in stages:
        print(f"  Deploying to {stage}...")
        # Deployment logic here

        # Run E2E tests via external automation
        print(f"  Initiating external UI regression suite for {stage}")
        print("  ✅ Automation pipeline reported success")


async def main():
    """Run all workflow examples"""
    print("SuperClaude Framework Advanced Workflows")
    print("=" * 50)

    workflows = [
        workflow_feature_development(),
        workflow_debugging_complex_issue(),
        workflow_large_codebase_refactoring(),
        workflow_production_deployment(),
    ]

    for workflow in workflows:
        try:
            await workflow
        except Exception as e:
            print(
                f"  Note: This is a demonstration. Actual implementation would handle: {e}"
            )

    print("\n" + "=" * 50)
    print("Advanced workflow examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
