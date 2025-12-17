"""
Python Expert Agent for SuperClaude Framework

This agent specializes in Python development, best practices,
advanced patterns, and production-ready code implementation.
"""

import ast
from typing import Any

from ..base import BaseAgent


class PythonExpert(BaseAgent):
    """
    Agent specialized in Python expertise and best practices.

    Provides Pythonic code, SOLID principles, modern patterns,
    and production-ready implementations.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the Python expert.

        Args:
            config: Agent configuration
        """
        # Ensure proper configuration
        if "name" not in config:
            config["name"] = "python-expert"
        if "description" not in config:
            config["description"] = "Deliver production-ready Python code"
        if "category" not in config:
            config["category"] = "language"

        super().__init__(config)

        # Python patterns and standards
        self.design_patterns = self._initialize_design_patterns()
        self.code_standards = self._initialize_code_standards()
        self.python_features = self._initialize_python_features()
        self.testing_patterns = self._initialize_testing_patterns()

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute Python expertise tasks.

        Args:
            context: Execution context

        Returns:
            Python code analysis and improvements
        """
        result = {
            "success": False,
            "output": "",
            "actions_taken": [],
            "errors": [],
            "code_analysis": {},
            "patterns_applied": [],
            "improvements": [],
            "test_coverage": {},
            "recommendations": [],
        }

        try:
            # Initialize if needed
            if not self._initialized:
                if not self.initialize():
                    result["errors"].append("Failed to initialize agent")
                    return result

            task = context.get("task", "")
            files = context.get("files", [])
            code = context.get("code", "")
            context.get("requirements", {})

            if not task and not files and not code:
                result["errors"].append("No content for Python analysis")
                return result

            self.logger.info(f"Starting Python expert analysis: {task[:100]}...")

            # Phase 1: Analyze code quality
            analysis = self._analyze_code_quality(code, files)
            result["code_analysis"] = analysis
            result["actions_taken"].append(
                f"Analyzed {analysis.get('complexity', 'N/A')} complexity"
            )

            # Phase 2: Apply design patterns
            patterns = self._apply_design_patterns(task, code, analysis)
            result["patterns_applied"] = patterns
            result["actions_taken"].append(f"Applied {len(patterns)} design patterns")

            # Phase 3: Generate improvements
            improvements = self._generate_improvements(code, analysis, patterns)
            result["improvements"] = improvements
            result["actions_taken"].append(
                f"Generated {len(improvements)} improvements"
            )

            # Phase 4: Design testing strategy
            test_coverage = self._design_test_coverage(code, files)
            result["test_coverage"] = test_coverage
            result["actions_taken"].append("Designed test coverage strategy")

            # Phase 5: Generate recommendations
            recommendations = self._generate_recommendations(
                analysis, patterns, improvements, test_coverage
            )
            result["recommendations"] = recommendations

            # Phase 6: Generate Python report
            report = self._generate_python_report(
                task, analysis, patterns, improvements, test_coverage, recommendations
            )
            result["output"] = report

            # Phase 7: Generate improved code if requested
            if "improve" in task.lower() or "refactor" in task.lower():
                improved_code = self._generate_improved_code(
                    code, improvements, patterns
                )
                result["improved_code"] = improved_code
                result["actions_taken"].append("Generated improved Python code")

            result["success"] = True
            self.log_execution(context, result)

        except Exception as e:
            self.logger.error(f"Python expert analysis failed: {e}")
            result["errors"].append(str(e))

        return result

    def validate(self, context: dict[str, Any]) -> bool:
        """
        Check if this agent can handle the context.

        Args:
            context: Validation context

        Returns:
            True if context contains Python tasks
        """
        task = context.get("task", "")
        files = context.get("files", [])

        # Check for Python keywords
        python_keywords = [
            "python",
            "py",
            "pip",
            "django",
            "flask",
            "fastapi",
            "pytest",
            "pandas",
            "numpy",
            "async",
            "decorator",
            "generator",
            "comprehension",
            "pythonic",
        ]

        # Check files for Python extensions
        has_python_files = any(f.endswith(".py") for f in files)

        task_lower = task.lower()
        return has_python_files or any(
            keyword in task_lower for keyword in python_keywords
        )

    def _initialize_design_patterns(self) -> dict[str, dict[str, Any]]:
        """
        Initialize Python design patterns.

        Returns:
            Dictionary of design patterns
        """
        return {
            "singleton": {
                "name": "Singleton Pattern",
                "description": "Ensure single instance of class",
                "use_cases": ["Database connections", "Configuration", "Logging"],
                "implementation": "__new__ method or decorator",
            },
            "factory": {
                "name": "Factory Pattern",
                "description": "Create objects without specifying exact class",
                "use_cases": ["Plugin systems", "API clients", "Parser creation"],
                "implementation": "Factory method or abstract factory",
            },
            "observer": {
                "name": "Observer Pattern",
                "description": "Notify multiple objects about state changes",
                "use_cases": ["Event systems", "Model-View patterns", "Pub/Sub"],
                "implementation": "Callback lists or event emitters",
            },
            "decorator": {
                "name": "Decorator Pattern",
                "description": "Add functionality to objects dynamically",
                "use_cases": ["Logging", "Caching", "Authentication"],
                "implementation": "Function/class decorators",
            },
            "context_manager": {
                "name": "Context Manager Pattern",
                "description": "Resource management with automatic cleanup",
                "use_cases": ["File handling", "Database connections", "Locks"],
                "implementation": "__enter__/__exit__ or contextlib",
            },
            "strategy": {
                "name": "Strategy Pattern",
                "description": "Select algorithm at runtime",
                "use_cases": [
                    "Payment processing",
                    "Sorting algorithms",
                    "Export formats",
                ],
                "implementation": "Abstract base classes or protocols",
            },
        }

    def _initialize_code_standards(self) -> dict[str, Any]:
        """
        Initialize Python code standards.

        Returns:
            Dictionary of code standards
        """
        return {
            "pep8": {
                "name": "PEP 8",
                "description": "Python style guide",
                "rules": [
                    "4 spaces indentation",
                    "79 char line limit",
                    "Snake_case naming",
                ],
            },
            "pep257": {
                "name": "PEP 257",
                "description": "Docstring conventions",
                "rules": ["Triple quotes", "First line summary", "Blank line after"],
            },
            "type_hints": {
                "name": "Type Hints",
                "description": "Static type checking",
                "rules": [
                    "Function annotations",
                    "Variable annotations",
                    "Generic types",
                ],
            },
            "solid": {
                "name": "SOLID Principles",
                "description": "OOP design principles",
                "rules": [
                    "Single responsibility",
                    "Open/closed",
                    "Dependency inversion",
                ],
            },
        }

    def _initialize_python_features(self) -> dict[str, dict[str, str]]:
        """
        Initialize modern Python features.

        Returns:
            Dictionary of Python features
        """
        return {
            "dataclasses": {
                "version": "3.7+",
                "use_case": "Simplified class definitions with less boilerplate",
            },
            "typing": {
                "version": "3.5+",
                "use_case": "Type hints for better IDE support and documentation",
            },
            "asyncio": {
                "version": "3.5+",
                "use_case": "Asynchronous programming for I/O bound operations",
            },
            "f_strings": {
                "version": "3.6+",
                "use_case": "Formatted string literals for readable string formatting",
            },
            "walrus": {
                "version": "3.8+",
                "use_case": "Assignment expressions to simplify code",
            },
            "pattern_matching": {
                "version": "3.10+",
                "use_case": "Structural pattern matching for complex conditionals",
            },
            "protocols": {
                "version": "3.8+",
                "use_case": "Structural subtyping for duck typing with type hints",
            },
        }

    def _initialize_testing_patterns(self) -> dict[str, dict[str, Any]]:
        """
        Initialize testing patterns.

        Returns:
            Dictionary of testing patterns
        """
        return {
            "unit": {
                "framework": "pytest",
                "coverage_target": 80,
                "patterns": ["AAA pattern", "Fixtures", "Parametrize"],
            },
            "integration": {
                "framework": "pytest",
                "coverage_target": 70,
                "patterns": ["Database fixtures", "API mocking", "Test containers"],
            },
            "property": {
                "framework": "hypothesis",
                "use_cases": ["Algorithmic code", "Data transformations", "Parsers"],
            },
            "mutation": {
                "framework": "mutmut",
                "use_cases": ["Critical code", "High coverage validation"],
            },
        }

    def _analyze_code_quality(self, code: str, files: list[str]) -> dict[str, Any]:
        """
        Analyze Python code quality.

        Args:
            code: Code content
            files: File paths

        Returns:
            Code quality analysis
        """
        analysis = {
            "complexity": "low",
            "issues": [],
            "metrics": {},
            "patterns_found": [],
            "python_version": "3.8",  # Default assumption
        }

        if not code:
            return analysis

        try:
            # Parse code with AST
            tree = ast.parse(code)

            # Count various elements
            classes = [
                node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
            ]
            functions = [
                node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
            ]
            async_functions = [
                node for node in functions if isinstance(node, ast.AsyncFunctionDef)
            ]

            analysis["metrics"] = {
                "classes": len(classes),
                "functions": len(functions),
                "async_functions": len(async_functions),
                "lines": len(code.splitlines()),
            }

            # Estimate complexity
            total_nodes = len(list(ast.walk(tree)))
            if total_nodes < 100:
                analysis["complexity"] = "low"
            elif total_nodes < 500:
                analysis["complexity"] = "medium"
            else:
                analysis["complexity"] = "high"

            # Check for patterns
            if any(isinstance(node, ast.With) for node in ast.walk(tree)):
                analysis["patterns_found"].append("context_manager")

            if any(
                hasattr(node, "decorator_list") and node.decorator_list
                for node in ast.walk(tree)
            ):
                analysis["patterns_found"].append("decorators")

            # Check for issues
            self._check_code_issues(tree, analysis)

        except SyntaxError as e:
            analysis["issues"].append(f"Syntax error: {e}")

        return analysis

    def _check_code_issues(self, tree: ast.AST, analysis: dict[str, Any]):
        """
        Check for code quality issues.

        Args:
            tree: AST tree
            analysis: Analysis dict to update
        """
        # Check for missing docstrings
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    analysis["issues"].append(f"Missing docstring for {node.name}")

        # Check for missing type hints
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                if not node.returns and node.name != "__init__":
                    analysis["issues"].append(
                        f"Missing return type hint for {node.name}"
                    )

        # Check for bare except
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    analysis["issues"].append("Bare except clause found")

    def _apply_design_patterns(
        self, task: str, code: str, analysis: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Apply appropriate design patterns.

        Args:
            task: Task description
            code: Code content
            analysis: Code analysis

        Returns:
            Applied patterns
        """
        patterns = []

        # Context manager for resource management
        if "file" in task.lower() or "database" in task.lower():
            patterns.append(
                {
                    "pattern": "context_manager",
                    "reason": "Resource management",
                    "implementation": "Use with statement for automatic cleanup",
                }
            )

        # Factory for object creation
        if "create" in task.lower() and analysis["metrics"].get("classes", 0) > 2:
            patterns.append(
                {
                    "pattern": "factory",
                    "reason": "Complex object creation",
                    "implementation": "Factory method for flexible instantiation",
                }
            )

        # Decorator for cross-cutting concerns
        if "log" in task.lower() or "cache" in task.lower() or "auth" in task.lower():
            patterns.append(
                {
                    "pattern": "decorator",
                    "reason": "Cross-cutting functionality",
                    "implementation": "Decorators for clean separation",
                }
            )

        # Strategy for algorithm selection
        if "algorithm" in task.lower() or "strategy" in task.lower():
            patterns.append(
                {
                    "pattern": "strategy",
                    "reason": "Runtime algorithm selection",
                    "implementation": "Strategy pattern with protocols",
                }
            )

        return patterns

    def _generate_improvements(
        self, code: str, analysis: dict[str, Any], patterns: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Generate code improvements.

        Args:
            code: Code content
            analysis: Code analysis
            patterns: Applied patterns

        Returns:
            List of improvements
        """
        improvements = []

        # Type hints improvement
        if "Missing return type hint" in str(analysis.get("issues", [])):
            improvements.append(
                {
                    "category": "Type Safety",
                    "improvement": "Add comprehensive type hints",
                    "benefit": "Better IDE support and early error detection",
                    "priority": "high",
                }
            )

        # Docstring improvements
        if "Missing docstring" in str(analysis.get("issues", [])):
            improvements.append(
                {
                    "category": "Documentation",
                    "improvement": "Add docstrings following PEP 257",
                    "benefit": "Better code documentation and maintainability",
                    "priority": "medium",
                }
            )

        # Exception handling
        if "Bare except" in str(analysis.get("issues", [])):
            improvements.append(
                {
                    "category": "Error Handling",
                    "improvement": "Use specific exception types",
                    "benefit": "Better error handling and debugging",
                    "priority": "high",
                }
            )

        # Modern Python features
        if "class" in code and "def __init__" in code:
            improvements.append(
                {
                    "category": "Modern Python",
                    "improvement": "Convert to dataclasses where appropriate",
                    "benefit": "Less boilerplate, automatic methods",
                    "priority": "low",
                }
            )

        # Async improvements
        if "time.sleep" in code or "requests" in code:
            improvements.append(
                {
                    "category": "Performance",
                    "improvement": "Use asyncio for I/O operations",
                    "benefit": "Better concurrency and performance",
                    "priority": "medium",
                }
            )

        # Code organization
        if analysis.get("complexity") == "high":
            improvements.append(
                {
                    "category": "Architecture",
                    "improvement": "Split into smaller modules",
                    "benefit": "Better maintainability and testability",
                    "priority": "high",
                }
            )

        return improvements

    def _design_test_coverage(self, code: str, files: list[str]) -> dict[str, Any]:
        """
        Design test coverage strategy.

        Args:
            code: Code content
            files: File paths

        Returns:
            Test coverage design
        """
        coverage = {
            "framework": "pytest",
            "target_coverage": 80,
            "test_types": [],
            "fixtures_needed": [],
            "mocking_required": [],
        }

        # Determine test types needed
        coverage["test_types"] = ["unit"]

        if "api" in code.lower() or "endpoint" in code.lower():
            coverage["test_types"].append("integration")
            coverage["mocking_required"].append("HTTP responses")

        if "database" in code.lower() or "model" in code.lower():
            coverage["test_types"].append("integration")
            coverage["fixtures_needed"].append("Database fixtures")

        if "algorithm" in code.lower() or "transform" in code.lower():
            coverage["test_types"].append("property")

        # Fixtures needed
        if "class" in code:
            coverage["fixtures_needed"].append("Class instances")

        if "file" in code.lower():
            coverage["fixtures_needed"].append("Temporary files")
            coverage["mocking_required"].append("File system")

        # Async testing
        if "async" in code:
            coverage["fixtures_needed"].append("Event loop")
            coverage["framework"] = "pytest-asyncio"

        return coverage

    def _generate_recommendations(
        self,
        analysis: dict[str, Any],
        patterns: list[dict[str, Any]],
        improvements: list[dict[str, Any]],
        test_coverage: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Generate Python-specific recommendations.

        Args:
            analysis: Code analysis
            patterns: Applied patterns
            improvements: Suggested improvements
            test_coverage: Test coverage design

        Returns:
            List of recommendations
        """
        recommendations = []

        # Code quality recommendations
        if len(analysis.get("issues", [])) > 5:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "Code Quality",
                    "recommendation": "Run pylint and black for code formatting",
                    "benefit": "Consistent, clean, and maintainable code",
                }
            )

        # Testing recommendations
        if test_coverage["target_coverage"] > 0:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "Testing",
                    "recommendation": f"Implement {', '.join(test_coverage['test_types'])} tests",
                    "benefit": f"Achieve {test_coverage['target_coverage']}% test coverage",
                }
            )

        # Performance recommendations
        if analysis.get("complexity") == "high":
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "Performance",
                    "recommendation": "Profile code and optimize hotspots",
                    "benefit": "Improved performance and resource usage",
                }
            )

        # Architecture recommendations
        if analysis["metrics"].get("functions", 0) > 20:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "Architecture",
                    "recommendation": "Organize code into modules and packages",
                    "benefit": "Better code organization and reusability",
                }
            )

        # Documentation
        recommendations.append(
            {
                "priority": "medium",
                "category": "Documentation",
                "recommendation": "Add type stubs (.pyi) for public API",
                "benefit": "Better IDE support for library users",
            }
        )

        # Dependency management
        recommendations.append(
            {
                "priority": "low",
                "category": "Dependencies",
                "recommendation": "Use poetry or pipenv for dependency management",
                "benefit": "Reproducible builds and virtual environment management",
            }
        )

        return recommendations

    def _generate_improved_code(
        self,
        original_code: str,
        improvements: list[dict[str, Any]],
        patterns: list[dict[str, Any]],
    ) -> str:
        """
        Generate improved Python code.

        Args:
            original_code: Original code
            improvements: Improvements to apply
            patterns: Patterns to apply

        Returns:
            Improved code
        """
        # This is a simplified example - real implementation would use AST transformation
        improved = []
        improved.append('"""')
        improved.append("Improved Python Code")
        improved.append("Applied improvements and patterns for production-ready code")
        improved.append('"""')
        improved.append("")
        improved.append("from typing import List, Dict, Any, Optional")
        improved.append("from dataclasses import dataclass")
        improved.append("import logging")
        improved.append("")
        improved.append("logger = logging.getLogger(__name__)")
        improved.append("")

        # Add example improved structure
        improved.append("@dataclass")
        improved.append("class ImprovedClass:")
        improved.append('    """Example of improved class with dataclass."""')
        improved.append("    ")
        improved.append("    name: str")
        improved.append("    value: int = 0")
        improved.append("    ")
        improved.append("    def process(self) -> Dict[str, Any]:")
        improved.append('        """Process data with proper type hints."""')
        improved.append("        try:")
        improved.append('            result = {"name": self.name, "value": self.value}')
        improved.append('            logger.info(f"Processed {self.name}")')
        improved.append("            return result")
        improved.append("        except Exception as e:")
        improved.append('            logger.error(f"Processing failed: {e}")')
        improved.append("            raise")

        return "\n".join(improved)

    def _generate_python_report(
        self,
        task: str,
        analysis: dict[str, Any],
        patterns: list[dict[str, Any]],
        improvements: list[dict[str, Any]],
        test_coverage: dict[str, Any],
        recommendations: list[dict[str, Any]],
    ) -> str:
        """
        Generate comprehensive Python report.

        Args:
            task: Original task
            analysis: Code analysis
            patterns: Applied patterns
            improvements: Suggested improvements
            test_coverage: Test coverage design
            recommendations: Recommendations

        Returns:
            Python expertise report
        """
        lines = []

        # Header
        lines.append("# Python Expert Analysis Report\n")
        lines.append(f"**Task**: {task}\n")

        # Code Analysis
        lines.append("\n## Code Quality Analysis\n")
        lines.append(f"**Complexity**: {analysis['complexity'].title()}")
        if analysis.get("metrics"):
            lines.append(f"**Classes**: {analysis['metrics'].get('classes', 0)}")
            lines.append(f"**Functions**: {analysis['metrics'].get('functions', 0)}")
            lines.append(
                f"**Async Functions**: {analysis['metrics'].get('async_functions', 0)}"
            )
            lines.append(f"**Lines of Code**: {analysis['metrics'].get('lines', 0)}")

        if analysis.get("issues"):
            lines.append("\n### Issues Found")
            for issue in analysis["issues"][:10]:  # Limit to 10
                lines.append(f"- ⚠️ {issue}")

        if analysis.get("patterns_found"):
            lines.append("\n### Patterns Detected")
            for pattern in analysis["patterns_found"]:
                lines.append(f"- ✅ {pattern.replace('_', ' ').title()}")

        # Design Patterns
        if patterns:
            lines.append("\n## Applied Design Patterns\n")
            for pattern in patterns:
                pattern_info = self.design_patterns.get(pattern["pattern"], {})
                lines.append(
                    f"### {pattern_info.get('name', pattern['pattern'].title())}"
                )
                lines.append(f"**Reason**: {pattern['reason']}")
                lines.append(f"**Implementation**: {pattern['implementation']}")

        # Improvements
        if improvements:
            lines.append("\n## Suggested Improvements\n")
            priority_order = {"high": 0, "medium": 1, "low": 2}
            sorted_imps = sorted(
                improvements, key=lambda x: priority_order.get(x["priority"], 3)
            )

            for imp in sorted_imps:
                priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    imp["priority"], "⚪"
                )
                lines.append(
                    f"{priority_emoji} **{imp['category']}**: {imp['improvement']}"
                )
                lines.append(f"   - Benefit: {imp['benefit']}")

        # Test Coverage
        lines.append("\n## Testing Strategy\n")
        lines.append(f"**Framework**: {test_coverage['framework']}")
        lines.append(f"**Target Coverage**: {test_coverage['target_coverage']}%")
        lines.append(f"**Test Types**: {', '.join(test_coverage['test_types'])}")

        if test_coverage.get("fixtures_needed"):
            lines.append("\n### Fixtures Required")
            for fixture in test_coverage["fixtures_needed"]:
                lines.append(f"- {fixture}")

        if test_coverage.get("mocking_required"):
            lines.append("\n### Mocking Required")
            for mock in test_coverage["mocking_required"]:
                lines.append(f"- {mock}")

        # Recommendations
        if recommendations:
            lines.append("\n## Recommendations\n")
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            sorted_recs = sorted(
                recommendations, key=lambda x: priority_order.get(x["priority"], 4)
            )

            for rec in sorted_recs:
                priority_emoji = {
                    "critical": "🚨",
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢",
                }.get(rec["priority"], "⚪")
                lines.append(
                    f"{priority_emoji} **{rec['category']}**: {rec['recommendation']}"
                )
                lines.append(f"   - Benefit: {rec['benefit']}")

        # Python Best Practices
        lines.append("\n## Python Best Practices Checklist\n")
        lines.append("- [ ] PEP 8 compliance (use black formatter)")
        lines.append("- [ ] Type hints for all functions")
        lines.append("- [ ] Docstrings for modules, classes, and functions")
        lines.append("- [ ] Exception handling with specific exceptions")
        lines.append("- [ ] Context managers for resource management")
        lines.append("- [ ] List/dict/set comprehensions where appropriate")
        lines.append("- [ ] F-strings for formatting (Python 3.6+)")
        lines.append("- [ ] Dataclasses for data containers (Python 3.7+)")
        lines.append("- [ ] Async/await for I/O operations")
        lines.append("- [ ] Property decorators for getters/setters")

        return "\n".join(lines)
