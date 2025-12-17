"""
Performance Engineer Agent for SuperClaude Framework

This agent specializes in performance analysis, optimization,
and bottleneck identification for code and systems.
"""

import re
from typing import Any

from ..base import BaseAgent


class PerformanceEngineer(BaseAgent):
    """
    Agent specialized in performance optimization.

    Analyzes code and systems for performance issues, identifies
    bottlenecks, and provides optimization recommendations.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the performance engineer.

        Args:
            config: Agent configuration
        """
        # Ensure proper configuration
        if "name" not in config:
            config["name"] = "performance-engineer"
        if "description" not in config:
            config["description"] = "Optimize performance and identify bottlenecks"
        if "category" not in config:
            config["category"] = "optimization"

        super().__init__(config)

        # Performance patterns and anti-patterns
        self.performance_patterns = self._initialize_patterns()
        self.optimization_strategies = self._initialize_strategies()

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute performance analysis and optimization.

        Args:
            context: Execution context

        Returns:
            Performance analysis results
        """
        result = {
            "success": False,
            "output": "",
            "actions_taken": [],
            "errors": [],
            "bottlenecks": [],
            "optimizations": [],
            "metrics": {},
        }

        try:
            # Initialize if needed
            if not self._initialized:
                if not self.initialize():
                    result["errors"].append("Failed to initialize agent")
                    return result

            task = context.get("task", "")
            code = context.get("code", "")
            system_info = context.get("system_info", {})

            if not task and not code:
                result["errors"].append("No performance target specified")
                return result

            self.logger.info(f"Starting performance analysis: {task[:100]}...")

            # Phase 1: Identify performance issues
            issues = self._identify_performance_issues(task, code, system_info)
            result["actions_taken"].append(
                f"Identified {len(issues)} performance issues"
            )

            # Phase 2: Detect bottlenecks
            bottlenecks = self._detect_bottlenecks(issues, code)
            result["bottlenecks"] = bottlenecks
            result["actions_taken"].append(f"Detected {len(bottlenecks)} bottlenecks")

            # Phase 3: Generate optimization strategies
            optimizations = self._generate_optimizations(issues, bottlenecks)
            result["optimizations"] = optimizations
            result["actions_taken"].append(
                f"Generated {len(optimizations)} optimizations"
            )

            # Phase 4: Calculate performance metrics
            metrics = self._calculate_metrics(issues, bottlenecks, optimizations)
            result["metrics"] = metrics

            # Phase 5: Create performance report
            report = self._generate_performance_report(
                task, issues, bottlenecks, optimizations, metrics
            )
            result["output"] = report

            result["success"] = True
            self.log_execution(context, result)

        except Exception as e:
            self.logger.error(f"Performance analysis failed: {e}")
            result["errors"].append(str(e))

        return result

    def validate(self, context: dict[str, Any]) -> bool:
        """
        Check if this agent can handle the context.

        Args:
            context: Validation context

        Returns:
            True if context contains performance task
        """
        task = context.get("task", "")

        # Check for performance keywords
        performance_keywords = [
            "performance",
            "slow",
            "optimize",
            "speed",
            "bottleneck",
            "latency",
            "throughput",
            "efficiency",
            "profile",
            "benchmark",
            "scaling",
            "resource",
        ]

        task_lower = task.lower()
        return any(keyword in task_lower for keyword in performance_keywords)

    def _initialize_patterns(self) -> dict[str, dict[str, Any]]:
        """
        Initialize performance patterns and anti-patterns.

        Returns:
            Dictionary of performance patterns
        """
        return {
            "n_plus_one": {
                "description": "N+1 query problem",
                "severity": "high",
                "category": "database",
                "impact": "Linear performance degradation",
            },
            "nested_loops": {
                "description": "Nested loops with high complexity",
                "severity": "high",
                "category": "algorithm",
                "impact": "O(n²) or worse complexity",
            },
            "synchronous_io": {
                "description": "Blocking I/O operations",
                "severity": "medium",
                "category": "io",
                "impact": "Thread blocking and poor concurrency",
            },
            "memory_leak": {
                "description": "Potential memory leak",
                "severity": "high",
                "category": "memory",
                "impact": "Growing memory usage over time",
            },
            "inefficient_algorithm": {
                "description": "Suboptimal algorithm choice",
                "severity": "medium",
                "category": "algorithm",
                "impact": "Unnecessary computation",
            },
            "excessive_allocation": {
                "description": "Excessive memory allocation",
                "severity": "medium",
                "category": "memory",
                "impact": "GC pressure and memory churn",
            },
            "missing_cache": {
                "description": "Missing caching opportunity",
                "severity": "medium",
                "category": "optimization",
                "impact": "Repeated expensive computations",
            },
            "unoptimized_query": {
                "description": "Database query without indexes",
                "severity": "high",
                "category": "database",
                "impact": "Full table scans",
            },
            "string_concatenation": {
                "description": "Inefficient string concatenation",
                "severity": "low",
                "category": "algorithm",
                "impact": "O(n²) string building",
            },
            "busy_waiting": {
                "description": "CPU-intensive polling",
                "severity": "medium",
                "category": "concurrency",
                "impact": "Wasted CPU cycles",
            },
        }

    def _initialize_strategies(self) -> dict[str, dict[str, Any]]:
        """
        Initialize optimization strategies.

        Returns:
            Dictionary of optimization strategies
        """
        return {
            "caching": {
                "applies_to": [
                    "repeated_computation",
                    "expensive_operation",
                    "missing_cache",
                ],
                "description": "Implement caching for expensive operations",
                "complexity": "low",
                "impact": "high",
            },
            "batch_processing": {
                "applies_to": ["n_plus_one", "multiple_operations"],
                "description": "Process multiple items in batches",
                "complexity": "medium",
                "impact": "high",
            },
            "async_io": {
                "applies_to": ["synchronous_io", "blocking_operation"],
                "description": "Use asynchronous I/O operations",
                "complexity": "medium",
                "impact": "high",
            },
            "algorithm_optimization": {
                "applies_to": ["nested_loops", "inefficient_algorithm"],
                "description": "Use more efficient algorithms",
                "complexity": "high",
                "impact": "high",
            },
            "indexing": {
                "applies_to": ["unoptimized_query", "slow_lookup"],
                "description": "Add database indexes",
                "complexity": "low",
                "impact": "high",
            },
            "pooling": {
                "applies_to": ["excessive_allocation", "resource_creation"],
                "description": "Use object/connection pooling",
                "complexity": "medium",
                "impact": "medium",
            },
            "lazy_loading": {
                "applies_to": ["eager_loading", "unnecessary_computation"],
                "description": "Defer computation until needed",
                "complexity": "low",
                "impact": "medium",
            },
            "parallelization": {
                "applies_to": ["cpu_bound", "independent_operations"],
                "description": "Parallelize independent operations",
                "complexity": "high",
                "impact": "high",
            },
            "data_structure_optimization": {
                "applies_to": ["inefficient_lookup", "poor_access_pattern"],
                "description": "Use appropriate data structures",
                "complexity": "medium",
                "impact": "medium",
            },
        }

    def _identify_performance_issues(
        self, task: str, code: str, system_info: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Identify performance issues.

        Args:
            task: Task description
            code: Code snippet
            system_info: System information

        Returns:
            List of identified issues
        """
        issues = []

        # Analyze task description
        task_lower = task.lower()

        # Check for mentioned performance problems
        if "slow" in task_lower:
            issues.append(
                {
                    "type": "general_slowness",
                    "description": "System or code running slowly",
                    "severity": "medium",
                    "source": "task_description",
                }
            )

        if "memory" in task_lower:
            issues.append(
                {
                    "type": "memory_issue",
                    "description": "Memory-related performance problem",
                    "severity": "high",
                    "source": "task_description",
                }
            )

        if "database" in task_lower or "query" in task_lower:
            issues.append(
                {
                    "type": "database_performance",
                    "description": "Database query performance issue",
                    "severity": "high",
                    "source": "task_description",
                }
            )

        # Analyze code patterns if provided
        if code:
            # Check for nested loops
            if re.search(r"for.*:\s*\n\s*for.*:", code):
                issues.append(
                    {
                        "type": "nested_loops",
                        "description": "Nested loops detected",
                        "severity": "medium",
                        "source": "code_analysis",
                    }
                )

            # Check for string concatenation in loops
            if re.search(r'for.*:\s*\n.*\+=\s*["\']', code):
                issues.append(
                    {
                        "type": "string_concatenation",
                        "description": "String concatenation in loop",
                        "severity": "low",
                        "source": "code_analysis",
                    }
                )

            # Check for potential N+1 queries
            if re.search(r"for.*:\s*\n.*query|select|find", code, re.IGNORECASE):
                issues.append(
                    {
                        "type": "n_plus_one",
                        "description": "Potential N+1 query problem",
                        "severity": "high",
                        "source": "code_analysis",
                    }
                )

        # Check system info
        if system_info:
            if system_info.get("cpu_usage", 0) > 80:
                issues.append(
                    {
                        "type": "high_cpu",
                        "description": "High CPU utilization",
                        "severity": "high",
                        "source": "system_metrics",
                    }
                )

            if system_info.get("memory_usage", 0) > 80:
                issues.append(
                    {
                        "type": "high_memory",
                        "description": "High memory usage",
                        "severity": "high",
                        "source": "system_metrics",
                    }
                )

        return issues

    def _detect_bottlenecks(
        self, issues: list[dict[str, Any]], code: str
    ) -> list[dict[str, Any]]:
        """
        Detect performance bottlenecks.

        Args:
            issues: Identified issues
            code: Code snippet

        Returns:
            List of bottlenecks
        """
        bottlenecks = []

        # Group issues by severity and type
        [i for i in issues if i["severity"] == "high"]

        # Database bottlenecks
        db_issues = [
            i for i in issues if "database" in i["type"] or "query" in i["type"]
        ]
        if db_issues:
            bottlenecks.append(
                {
                    "type": "database",
                    "description": "Database operations are a bottleneck",
                    "impact": "high",
                    "issues": db_issues,
                }
            )

        # CPU bottlenecks
        cpu_issues = [
            i
            for i in issues
            if "cpu" in i["type"] or "algorithm" in i.get("description", "").lower()
        ]
        if cpu_issues:
            bottlenecks.append(
                {
                    "type": "cpu",
                    "description": "CPU-intensive operations bottleneck",
                    "impact": "high"
                    if any(i["severity"] == "high" for i in cpu_issues)
                    else "medium",
                    "issues": cpu_issues,
                }
            )

        # Memory bottlenecks
        memory_issues = [i for i in issues if "memory" in i["type"]]
        if memory_issues:
            bottlenecks.append(
                {
                    "type": "memory",
                    "description": "Memory allocation/usage bottleneck",
                    "impact": "high",
                    "issues": memory_issues,
                }
            )

        # I/O bottlenecks
        io_issues = [
            i for i in issues if "io" in i["type"] or "synchronous" in i["type"]
        ]
        if io_issues:
            bottlenecks.append(
                {
                    "type": "io",
                    "description": "I/O operations bottleneck",
                    "impact": "medium",
                    "issues": io_issues,
                }
            )

        # Algorithm complexity bottlenecks
        if any("nested_loops" in i["type"] for i in issues):
            bottlenecks.append(
                {
                    "type": "algorithm",
                    "description": "Algorithm complexity bottleneck",
                    "impact": "high",
                    "issues": [
                        i
                        for i in issues
                        if "loop" in i["type"] or "algorithm" in i["type"]
                    ],
                }
            )

        return bottlenecks

    def _generate_optimizations(
        self, issues: list[dict[str, Any]], bottlenecks: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Generate optimization recommendations.

        Args:
            issues: Identified issues
            bottlenecks: Detected bottlenecks

        Returns:
            List of optimizations
        """
        optimizations = []

        # Map bottlenecks to strategies
        for bottleneck in bottlenecks:
            b_type = bottleneck["type"]

            if b_type == "database":
                optimizations.extend(
                    [
                        {
                            "strategy": "indexing",
                            "description": "Add indexes to frequently queried columns",
                            "priority": 1,
                            "expected_improvement": "50-90% query time reduction",
                        },
                        {
                            "strategy": "batch_processing",
                            "description": "Batch multiple queries into single operations",
                            "priority": 2,
                            "expected_improvement": "70% reduction in database round trips",
                        },
                    ]
                )

            elif b_type == "cpu":
                optimizations.extend(
                    [
                        {
                            "strategy": "algorithm_optimization",
                            "description": "Replace O(n²) algorithms with O(n log n) alternatives",
                            "priority": 1,
                            "expected_improvement": "Order of magnitude speedup for large datasets",
                        },
                        {
                            "strategy": "parallelization",
                            "description": "Parallelize CPU-intensive operations",
                            "priority": 3,
                            "expected_improvement": "2-4x speedup on multi-core systems",
                        },
                    ]
                )

            elif b_type == "memory":
                optimizations.extend(
                    [
                        {
                            "strategy": "pooling",
                            "description": "Implement object pooling to reduce allocations",
                            "priority": 2,
                            "expected_improvement": "30-50% reduction in GC pressure",
                        },
                        {
                            "strategy": "data_structure_optimization",
                            "description": "Use more memory-efficient data structures",
                            "priority": 3,
                            "expected_improvement": "20-40% memory usage reduction",
                        },
                    ]
                )

            elif b_type == "io":
                optimizations.append(
                    {
                        "strategy": "async_io",
                        "description": "Convert synchronous I/O to asynchronous",
                        "priority": 1,
                        "expected_improvement": "3-5x throughput increase",
                    }
                )

        # Add caching as general optimization
        if len(issues) > 0:
            optimizations.append(
                {
                    "strategy": "caching",
                    "description": "Implement caching for expensive operations",
                    "priority": 2,
                    "expected_improvement": "60-90% reduction for cached operations",
                }
            )

        # Sort by priority
        optimizations.sort(key=lambda x: x["priority"])

        # Remove duplicates
        seen = set()
        unique_optimizations = []
        for opt in optimizations:
            key = opt["strategy"]
            if key not in seen:
                seen.add(key)
                unique_optimizations.append(opt)

        return unique_optimizations

    def _calculate_metrics(
        self,
        issues: list[dict[str, Any]],
        bottlenecks: list[dict[str, Any]],
        optimizations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Calculate performance metrics.

        Args:
            issues: Identified issues
            bottlenecks: Detected bottlenecks
            optimizations: Recommended optimizations

        Returns:
            Performance metrics
        """
        # Calculate severity score
        severity_scores = {"high": 3, "medium": 2, "low": 1}
        total_severity = sum(severity_scores.get(i["severity"], 1) for i in issues)

        # Calculate impact score
        impact_scores = {"high": 3, "medium": 2, "low": 1}
        total_impact = sum(
            impact_scores.get(b.get("impact", "medium"), 2) for b in bottlenecks
        )

        # Performance health score (0-100)
        max_severity = len(issues) * 3
        health_score = 100 - (total_severity / max(max_severity, 1)) * 100

        return {
            "performance_health": max(0, int(health_score)),
            "issues_count": len(issues),
            "bottlenecks_count": len(bottlenecks),
            "optimizations_count": len(optimizations),
            "severity_score": total_severity,
            "impact_score": total_impact,
            "priority_optimizations": sum(
                1 for o in optimizations if o["priority"] == 1
            ),
        }

    def _generate_performance_report(
        self,
        task: str,
        issues: list[dict[str, Any]],
        bottlenecks: list[dict[str, Any]],
        optimizations: list[dict[str, Any]],
        metrics: dict[str, Any],
    ) -> str:
        """
        Generate performance analysis report.

        Args:
            task: Original task
            issues: Identified issues
            bottlenecks: Detected bottlenecks
            optimizations: Recommended optimizations
            metrics: Performance metrics

        Returns:
            Performance report
        """
        lines = []

        # Header
        lines.append("# Performance Analysis Report\n")
        lines.append(f"**Task**: {task}\n")

        # Performance Health
        lines.append("\n## Performance Health Score\n")
        health = metrics["performance_health"]
        if health >= 80:
            health_status = "🟢 Good"
        elif health >= 60:
            health_status = "🟡 Fair"
        else:
            health_status = "🔴 Poor"
        lines.append(f"**Score**: {health}/100 ({health_status})")

        # Issues section
        lines.append("\n## Issues Identified\n")
        if issues:
            for issue in issues[:5]:
                severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    issue["severity"], "⚪"
                )
                lines.append(
                    f"- {severity_icon} **{issue['type'].replace('_', ' ').title()}**: {issue['description']}"
                )
            if len(issues) > 5:
                lines.append(f"- *(and {len(issues) - 5} more issues)*")
        else:
            lines.append("*No significant performance issues detected.*")

        # Bottlenecks section
        lines.append("\n## Performance Bottlenecks\n")
        if bottlenecks:
            for bottleneck in bottlenecks:
                impact_level = bottleneck.get("impact", "medium").upper()
                lines.append(f"### {bottleneck['type'].title()} Bottleneck")
                lines.append(f"- **Impact**: {impact_level}")
                lines.append(f"- **Description**: {bottleneck['description']}")
        else:
            lines.append("*No major bottlenecks identified.*")

        # Optimizations section
        lines.append("\n## Optimization Recommendations\n")
        if optimizations:
            for i, opt in enumerate(optimizations[:5], 1):
                lines.append(f"{i}. **{opt['strategy'].replace('_', ' ').title()}**")
                lines.append(f"   - {opt['description']}")
                lines.append(
                    f"   - Expected improvement: {opt['expected_improvement']}"
                )
        else:
            lines.append("*System is already well-optimized.*")

        # Metrics section
        lines.append("\n## Metrics Summary\n")
        lines.append(f"- Issues found: {metrics['issues_count']}")
        lines.append(f"- Bottlenecks detected: {metrics['bottlenecks_count']}")
        lines.append(f"- Optimizations available: {metrics['optimizations_count']}")
        lines.append(
            f"- High-priority optimizations: {metrics['priority_optimizations']}"
        )

        # Next steps
        lines.append("\n## Next Steps\n")
        lines.append("1. **Profile**: Measure actual performance before optimization")
        lines.append("2. **Prioritize**: Focus on high-impact optimizations first")
        lines.append("3. **Implement**: Apply optimizations incrementally")
        lines.append("4. **Measure**: Verify improvements with benchmarks")
        lines.append("5. **Monitor**: Set up ongoing performance monitoring")

        return "\n".join(lines)
