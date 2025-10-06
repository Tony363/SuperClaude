"""
Extended Agent System Usage Examples

Demonstrates various usage patterns for the 141-agent system.
"""

from SuperClaude.Agents.extended_loader import (
    ExtendedAgentLoader,
    AgentCategory
)


def example_basic_loading():
    """Example 1: Basic agent loading."""
    print("=" * 60)
    print("Example 1: Basic Agent Loading")
    print("=" * 60)

    loader = ExtendedAgentLoader(cache_size=10, ttl_seconds=300)

    # Load specific agent
    agent = loader.load_agent('typescript-pro')

    if agent:
        print(f"✓ Loaded: {agent.name}")
        print(f"  Category: {agent.category}")
    else:
        print("✗ Failed to load agent")

    # Show statistics
    stats = loader.get_statistics()
    print(f"\nStatistics:")
    print(f"  Total agents: {stats['total_agents']}")
    print(f"  Cache size: {stats['cached_agents']}/{stats['max_cache_size']}")


def example_intelligent_selection():
    """Example 2: Intelligent agent selection."""
    print("\n" + "=" * 60)
    print("Example 2: Intelligent Agent Selection")
    print("=" * 60)

    loader = ExtendedAgentLoader()

    # Define task context
    context = {
        'task': 'Build a GraphQL API with authentication and rate limiting',
        'files': ['schema.graphql', 'resolvers.py', 'auth.py'],
        'languages': ['python', 'graphql'],
        'domains': ['api', 'backend', 'graphql', 'authentication'],
        'keywords': ['graphql', 'api', 'authentication', 'rate-limit']
    }

    print(f"Task: {context['task']}\n")

    # Get top 5 suggestions
    matches = loader.select_agent(context, top_n=5)

    print(f"Top {len(matches)} Agent Suggestions:\n")

    for i, match in enumerate(matches, 1):
        agent = loader._agent_metadata.get(match.agent_id)
        if agent:
            print(f"{i}. {agent.name} (ID: {agent.id})")
            print(f"   Score: {match.total_score:.3f} | Confidence: {match.confidence}")
            print(f"   Matched: {', '.join(match.matched_criteria[:2])}")
            print()


def example_category_filtering():
    """Example 3: Category-based selection."""
    print("=" * 60)
    print("Example 3: Category-Based Selection")
    print("=" * 60)

    loader = ExtendedAgentLoader()

    # Infrastructure task
    context = {
        'task': 'Set up Kubernetes cluster with monitoring and logging',
        'domains': ['kubernetes', 'devops', 'monitoring'],
        'keywords': ['k8s', 'prometheus', 'grafana', 'elk']
    }

    print(f"Task: {context['task']}\n")

    # Filter to infrastructure category
    matches = loader.select_agent(
        context,
        category_hint=AgentCategory.INFRASTRUCTURE,
        top_n=3
    )

    print(f"Infrastructure Agents:\n")

    for match in matches:
        agent = loader._agent_metadata.get(match.agent_id)
        if agent:
            print(f"• {agent.name}")
            print(f"  Domains: {', '.join(agent.domains)}")
            print(f"  Score: {match.total_score:.3f}\n")


def example_search_and_discovery():
    """Example 4: Search and discovery."""
    print("=" * 60)
    print("Example 4: Search and Discovery")
    print("=" * 60)

    loader = ExtendedAgentLoader()

    # Search for React-related agents
    print("Searching for 'react'...\n")

    results = loader.search_agents('react')

    for agent in results[:5]:
        print(f"• {agent.name} (ID: {agent.id})")
        print(f"  Category: {agent.category.value}")
        print(f"  Languages: {', '.join(agent.languages)}")
        print()

    # List all categories
    print("\nAll Categories:\n")

    categories = loader.list_categories()
    for category, count in sorted(categories.items(), key=lambda x: x[0].value):
        print(f"• {category.value}: {count} agents")


def example_detailed_explanation():
    """Example 5: Detailed selection explanation."""
    print("\n" + "=" * 60)
    print("Example 5: Detailed Selection Explanation")
    print("=" * 60)

    loader = ExtendedAgentLoader()

    context = {
        'task': 'Optimize machine learning model training pipeline',
        'files': ['train.py', 'model.py', 'data_loader.py'],
        'languages': ['python'],
        'domains': ['ml', 'ai', 'data'],
        'keywords': ['machine-learning', 'tensorflow', 'optimization'],
        'imports': ['tensorflow', 'sklearn', 'pandas']
    }

    print(f"Task: {context['task']}\n")

    # Select best agent
    matches = loader.select_agent(context, top_n=1)

    if matches:
        best = matches[0]
        explanation = loader.explain_selection(best.agent_id, context)

        print(f"Selected Agent: {explanation['agent_name']}\n")
        print(f"Confidence: {explanation['confidence']}")
        print(f"Total Score: {explanation['total_score']:.3f}\n")

        print("Score Breakdown:")
        for component, score in explanation['breakdown'].items():
            percentage = score / explanation['total_score'] * 100
            print(f"  {component:15} {score:.3f} ({percentage:.1f}%)")

        print("\nMatched Criteria:")
        for criterion in explanation['matched_criteria']:
            print(f"  • {criterion}")

        print("\nAgent Capabilities:")
        metadata = explanation['metadata']
        print(f"  Domains: {', '.join(metadata['domains'])}")
        print(f"  Languages: {', '.join(metadata['languages'])}")
        print(f"  Keywords: {', '.join(metadata['keywords'][:5])}")


def example_performance_optimization():
    """Example 6: Performance optimization."""
    print("\n" + "=" * 60)
    print("Example 6: Performance Optimization")
    print("=" * 60)

    loader = ExtendedAgentLoader(cache_size=20)

    # Simulate access pattern
    print("Simulating access pattern...\n")

    access_pattern = [
        'python-expert', 'typescript-pro', 'react-specialist',
        'python-expert', 'typescript-pro', 'python-expert',
        'kubernetes-specialist', 'python-expert'
    ]

    for agent_id in access_pattern:
        loader._track_access(agent_id)

    # Show statistics before optimization
    stats = loader.get_statistics()
    print("Statistics Before Optimization:")
    print(f"  Cache size: {stats['cached_agents']}/{stats['max_cache_size']}")
    print(f"  Top accessed agents:")
    for agent_id, count in list(stats['top_accessed_agents'].items())[:5]:
        print(f"    • {agent_id}: {count} accesses")

    # Optimize cache
    print("\nOptimizing cache based on access patterns...")
    loader.optimize_cache()

    # Show statistics after optimization
    stats = loader.get_statistics()
    print("\nStatistics After Optimization:")
    print(f"  Cache size: {stats['cached_agents']}/{stats['max_cache_size']}")
    print(f"  Agents preloaded based on frequency")


def example_multi_agent_workflow():
    """Example 7: Multi-agent workflow."""
    print("\n" + "=" * 60)
    print("Example 7: Multi-Agent Workflow")
    print("=" * 60)

    loader = ExtendedAgentLoader(cache_size=30)

    # Define multi-step workflow
    workflow_steps = [
        {
            'name': 'Design API',
            'context': {
                'task': 'Design RESTful API endpoints',
                'domains': ['api', 'rest'],
                'keywords': ['api', 'rest', 'endpoint', 'design']
            }
        },
        {
            'name': 'Implement Backend',
            'context': {
                'task': 'Implement Python Flask backend',
                'files': ['app.py', 'routes.py'],
                'languages': ['python'],
                'keywords': ['flask', 'python', 'backend']
            }
        },
        {
            'name': 'Add Security',
            'context': {
                'task': 'Add authentication and authorization',
                'domains': ['security', 'authentication'],
                'keywords': ['auth', 'security', 'jwt']
            }
        },
        {
            'name': 'Write Tests',
            'context': {
                'task': 'Write unit and integration tests',
                'files': ['test_app.py', 'test_auth.py'],
                'domains': ['testing'],
                'keywords': ['test', 'pytest', 'unittest']
            }
        }
    ]

    print("Multi-step workflow:\n")

    for step in workflow_steps:
        print(f"Step: {step['name']}")

        # Select best agent for step
        matches = loader.select_agent(step['context'], top_n=1)

        if matches:
            agent = loader._agent_metadata.get(matches[0].agent_id)
            if agent:
                print(f"  → Agent: {agent.name}")
                print(f"     Confidence: {matches[0].confidence}")
                print()


def example_category_exploration():
    """Example 8: Category exploration."""
    print("=" * 60)
    print("Example 8: Category Exploration")
    print("=" * 60)

    loader = ExtendedAgentLoader()

    # Explore Data & AI category
    category = AgentCategory.DATA_AI

    print(f"Category: {category.value}\n")

    agents = loader.get_agents_by_category(category)

    print(f"Found {len(agents)} agents:\n")

    for agent in sorted(agents, key=lambda a: a.priority):
        print(f"• {agent.name} (Priority {agent.priority})")
        print(f"  {agent.description[:80]}...")
        print(f"  Languages: {', '.join(agent.languages)}")
        print(f"  Keywords: {', '.join(agent.keywords[:5])}")
        print()


def main():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("EXTENDED AGENT SYSTEM USAGE EXAMPLES")
    print("=" * 60 + "\n")

    examples = [
        example_basic_loading,
        example_intelligent_selection,
        example_category_filtering,
        example_search_and_discovery,
        example_detailed_explanation,
        example_performance_optimization,
        example_multi_agent_workflow,
        example_category_exploration
    ]

    for example in examples:
        try:
            example()
            print()
        except Exception as e:
            print(f"Error in {example.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == '__main__':
    main()
