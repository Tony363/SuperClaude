"""
Extended Agent System Integration Demo

Demonstrates integration with SuperClaude framework components.
"""

import sys
from pathlib import Path

# Add SuperClaude to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from SuperClaude.Agents import ExtendedAgentLoader, AgentCategory


class SuperClaudeOrchestrator:
    """
    Example orchestrator showing integration patterns.
    """

    def __init__(self):
        """Initialize with extended agent loader."""
        self.loader = ExtendedAgentLoader(
            cache_size=25,  # Larger cache for orchestration
            ttl_seconds=3600  # 1 hour TTL
        )
        print("✓ SuperClaude Orchestrator initialized")
        print(f"  Loaded metadata for {len(self.loader._agent_metadata)} agents")
        print()

    def handle_development_task(self, task_description: str, project_files: list):
        """
        Handle a development task with intelligent agent selection.

        Args:
            task_description: Description of the task
            project_files: List of relevant project files
        """
        print("=" * 70)
        print("DEVELOPMENT TASK")
        print("=" * 70)
        print(f"Task: {task_description}\n")

        # Analyze files to determine context
        context = self._analyze_context(task_description, project_files)

        print("Context Analysis:")
        print(f"  Languages: {', '.join(context['languages'])}")
        print(f"  Domains: {', '.join(context['domains'])}")
        print(f"  Keywords: {', '.join(context['keywords'][:5])}")
        print()

        # Select best agent
        matches = self.loader.select_agent(context, top_n=3)

        print("Agent Selection:")
        for i, match in enumerate(matches, 1):
            agent = self.loader._agent_metadata.get(match.agent_id)
            if agent:
                print(f"  {i}. {agent.name} ({match.confidence}, score: {match.total_score:.3f})")

        if matches:
            best = matches[0]
            agent_meta = self.loader._agent_metadata.get(best.agent_id)
            print(f"\n→ Selected: {agent_meta.name}")
            print(f"  Confidence: {best.confidence}")
            print(f"  Reasoning: {', '.join(best.matched_criteria[:2])}")

        print()

    def handle_multi_phase_project(self):
        """
        Demonstrate multi-phase project with different agents.
        """
        print("=" * 70)
        print("MULTI-PHASE PROJECT WORKFLOW")
        print("=" * 70)
        print()

        phases = [
            {
                'name': 'Phase 1: Requirements Analysis',
                'context': {
                    'task': 'Analyze requirements for e-commerce platform',
                    'domains': ['requirements', 'business', 'analysis'],
                    'keywords': ['requirements', 'specification', 'scope']
                }
            },
            {
                'name': 'Phase 2: API Design',
                'context': {
                    'task': 'Design RESTful API for product catalog',
                    'domains': ['api', 'rest', 'design'],
                    'keywords': ['api', 'rest', 'design', 'openapi']
                }
            },
            {
                'name': 'Phase 3: Backend Implementation',
                'context': {
                    'task': 'Implement Python/Django backend',
                    'files': ['views.py', 'models.py', 'serializers.py'],
                    'languages': ['python'],
                    'domains': ['backend', 'django'],
                    'keywords': ['django', 'python', 'backend', 'api']
                }
            },
            {
                'name': 'Phase 4: Frontend Development',
                'context': {
                    'task': 'Build React frontend with TypeScript',
                    'files': ['App.tsx', 'components/*.tsx'],
                    'languages': ['typescript', 'javascript'],
                    'domains': ['frontend', 'react'],
                    'keywords': ['react', 'typescript', 'hooks', 'components']
                }
            },
            {
                'name': 'Phase 5: Testing & QA',
                'context': {
                    'task': 'Write comprehensive test suite',
                    'files': ['test_*.py', '*.test.tsx'],
                    'domains': ['testing', 'qa'],
                    'keywords': ['test', 'pytest', 'jest', 'coverage']
                }
            },
            {
                'name': 'Phase 6: Deployment',
                'context': {
                    'task': 'Set up Kubernetes deployment pipeline',
                    'files': ['deployment.yaml', 'service.yaml'],
                    'domains': ['devops', 'kubernetes'],
                    'keywords': ['kubernetes', 'deployment', 'ci/cd', 'helm']
                }
            }
        ]

        for phase in phases:
            print(f"📋 {phase['name']}")

            # Select best agent for phase
            matches = self.loader.select_agent(phase['context'], top_n=1)

            if matches:
                agent_meta = self.loader._agent_metadata.get(matches[0].agent_id)
                print(f"   → Agent: {agent_meta.name}")
                print(f"   → Category: {agent_meta.category.value}")
                print(f"   → Confidence: {matches[0].confidence}")
            print()

    def demonstrate_category_specialization(self):
        """
        Show how category filtering works for specialized domains.
        """
        print("=" * 70)
        print("CATEGORY SPECIALIZATION")
        print("=" * 70)
        print()

        scenarios = [
            {
                'title': 'Machine Learning Pipeline',
                'category': AgentCategory.DATA_AI,
                'context': {
                    'task': 'Build ML training pipeline',
                    'domains': ['ml', 'data'],
                    'keywords': ['machine-learning', 'training', 'pipeline']
                }
            },
            {
                'title': 'Security Audit',
                'category': AgentCategory.QUALITY_SECURITY,
                'context': {
                    'task': 'Perform security vulnerability assessment',
                    'domains': ['security', 'audit'],
                    'keywords': ['security', 'vulnerability', 'audit']
                }
            },
            {
                'title': 'Cloud Infrastructure',
                'category': AgentCategory.INFRASTRUCTURE,
                'context': {
                    'task': 'Design AWS cloud architecture',
                    'domains': ['cloud', 'aws', 'infrastructure'],
                    'keywords': ['aws', 'cloud', 'architecture', 's3', 'ec2']
                }
            }
        ]

        for scenario in scenarios:
            print(f"🎯 {scenario['title']}")
            print(f"   Category: {scenario['category'].value}")

            # Filter to specific category
            matches = self.loader.select_agent(
                scenario['context'],
                category_hint=scenario['category'],
                top_n=3
            )

            print("   Top Agents:")
            for i, match in enumerate(matches, 1):
                agent_meta = self.loader._agent_metadata.get(match.agent_id)
                if agent_meta:
                    print(f"     {i}. {agent_meta.name} (score: {match.total_score:.3f})")
            print()

    def show_performance_metrics(self):
        """
        Display current performance metrics.
        """
        print("=" * 70)
        print("PERFORMANCE METRICS")
        print("=" * 70)
        print()

        stats = self.loader.get_statistics()

        print("Agent Inventory:")
        print(f"  Total Agents: {stats['total_agents']}")
        print(f"  Cached Agents: {stats['cached_agents']}/{stats['max_cache_size']}")
        print()

        print("Performance:")
        print(f"  Total Loads: {stats['agent_loads']}")
        print(f"  Cache Hits: {stats['cache_hits']}")
        print(f"  Cache Misses: {stats['cache_misses']}")
        print(f"  Hit Rate: {stats['cache_hit_rate']:.1%}")
        print(f"  Avg Load Time: {stats['avg_load_time']:.3f}s")
        print()

        if stats['top_accessed_agents']:
            print("Most Used Agents:")
            for agent_id, count in list(stats['top_accessed_agents'].items())[:5]:
                print(f"  • {agent_id}: {count} accesses")
        print()

    def _analyze_context(self, task: str, files: list) -> dict:
        """
        Analyze task and files to build context.

        Args:
            task: Task description
            files: List of file paths

        Returns:
            Context dictionary
        """
        context = {
            'task': task,
            'files': files,
            'languages': [],
            'domains': [],
            'keywords': []
        }

        # Detect languages from file extensions
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.rb': 'ruby',
            '.php': 'php',
            '.cs': 'csharp',
            '.kt': 'kotlin',
            '.swift': 'swift'
        }

        seen_languages = set()
        for file in files:
            ext = Path(file).suffix
            if ext in language_map:
                lang = language_map[ext]
                if lang not in seen_languages:
                    context['languages'].append(lang)
                    seen_languages.add(lang)

        # Extract keywords from task
        task_lower = task.lower()
        keyword_indicators = {
            'api': ['api', 'rest', 'graphql', 'endpoint'],
            'frontend': ['frontend', 'ui', 'component', 'react', 'vue'],
            'backend': ['backend', 'server', 'database', 'api'],
            'testing': ['test', 'qa', 'coverage', 'validate'],
            'security': ['security', 'auth', 'authentication', 'vulnerability'],
            'performance': ['performance', 'optimize', 'speed', 'latency'],
            'devops': ['deploy', 'docker', 'kubernetes', 'ci/cd'],
            'database': ['database', 'sql', 'query', 'migration']
        }

        seen_domains = set()
        seen_keywords = set()

        for domain, keywords in keyword_indicators.items():
            for keyword in keywords:
                if keyword in task_lower:
                    if domain not in seen_domains:
                        context['domains'].append(domain)
                        seen_domains.add(domain)
                    if keyword not in seen_keywords:
                        context['keywords'].append(keyword)
                        seen_keywords.add(keyword)

        return context


def main():
    """
    Run integration demonstration.
    """
    print()
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║     EXTENDED AGENT SYSTEM - INTEGRATION DEMONSTRATION             ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print()

    # Initialize orchestrator
    orchestrator = SuperClaudeOrchestrator()

    # Demo 1: Single development task
    orchestrator.handle_development_task(
        "Implement GraphQL API with authentication and rate limiting",
        ['schema.graphql', 'resolvers.py', 'auth.py', 'middleware.py']
    )

    # Demo 2: Multi-phase project
    orchestrator.handle_multi_phase_project()

    # Demo 3: Category specialization
    orchestrator.demonstrate_category_specialization()

    # Demo 4: Performance metrics
    orchestrator.show_performance_metrics()

    print("=" * 70)
    print("DEMONSTRATION COMPLETE")
    print("=" * 70)
    print()
    print("Key Takeaways:")
    print("  ✓ Intelligent agent selection based on rich context")
    print("  ✓ Multi-phase workflow with specialized agents per phase")
    print("  ✓ Category filtering for domain-specific tasks")
    print("  ✓ Performance optimization with LRU caching")
    print("  ✓ Comprehensive metrics and monitoring")
    print()


if __name__ == '__main__':
    main()
