"""
Refactoring Expert Agent for SuperClaude Framework

This agent specializes in code refactoring, improving code quality,
maintainability, and structure without changing functionality.
"""

import re
from typing import Any, Dict, List

from ..base import BaseAgent


class RefactoringExpert(BaseAgent):
    """
    Agent specialized in code refactoring and quality improvement.

    Analyzes code for improvement opportunities and provides
    refactoring recommendations with focus on maintainability.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the refactoring expert.

        Args:
            config: Agent configuration
        """
        # Ensure proper configuration
        if "name" not in config:
            config["name"] = "refactoring-expert"
        if "description" not in config:
            config["description"] = (
                "Improve code quality through systematic refactoring"
            )
        if "category" not in config:
            config["category"] = "quality"

        super().__init__(config)

        # Code smell patterns
        self.code_smells = self._initialize_code_smells()
        self.refactoring_patterns = self._initialize_refactoring_patterns()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute refactoring analysis and recommendations.

        Args:
            context: Execution context

        Returns:
            Refactoring recommendations
        """
        result = {
            "success": False,
            "output": "",
            "actions_taken": [],
            "errors": [],
            "improvements": [],
            "metrics": {},
        }

        try:
            # Initialize if needed
            if not self._initialized:
                if not self.initialize():
                    result["errors"].append("Failed to initialize agent")
                    return result

            task = context.get("task", "")
            files = context.get("files", [])
            code_snippet = context.get("code", "")

            if not task and not code_snippet and not files:
                result["errors"].append("No code to refactor")
                return result

            self.logger.info(f"Starting refactoring analysis: {task[:100]}...")

            # Phase 1: Analyze code smells
            smells = self._detect_code_smells(task, code_snippet, files)
            result["actions_taken"].append(f"Detected {len(smells)} code smells")

            # Phase 2: Identify improvement opportunities
            opportunities = self._identify_opportunities(smells, task)
            result["actions_taken"].append(
                f"Identified {len(opportunities)} improvement opportunities"
            )

            # Phase 3: Generate refactoring plan
            refactoring_plan = self._create_refactoring_plan(opportunities)
            result["actions_taken"].append("Created refactoring plan")

            # Phase 4: Estimate impact
            impact = self._estimate_impact(refactoring_plan)
            result["metrics"] = impact

            # Phase 5: Generate recommendations
            recommendations = self._generate_recommendations(
                task, smells, refactoring_plan, impact
            )
            result["output"] = recommendations

            # Store improvements
            result["improvements"] = [
                {
                    "type": item["type"],
                    "description": item["description"],
                    "priority": item.get("priority", "medium"),
                }
                for item in refactoring_plan
            ]

            result["success"] = True
            self.log_execution(context, result)

        except Exception as e:
            self.logger.error(f"Refactoring analysis failed: {e}")
            result["errors"].append(str(e))

        return result

    def validate(self, context: Dict[str, Any]) -> bool:
        """
        Check if this agent can handle the context.

        Args:
            context: Validation context

        Returns:
            True if context contains refactoring task
        """
        task = context.get("task", "")

        # Check for refactoring keywords
        refactoring_keywords = [
            "refactor",
            "improve",
            "clean",
            "optimize code",
            "restructure",
            "simplify",
            "reduce complexity",
            "code smell",
            "technical debt",
            "maintainability",
        ]

        task_lower = task.lower()
        return any(keyword in task_lower for keyword in refactoring_keywords)

    def _initialize_code_smells(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize code smell detection patterns.

        Returns:
            Dictionary of code smell patterns
        """
        return {
            "long_function": {
                "description": "Function too long (>50 lines)",
                "severity": "medium",
                "pattern": r"def\s+\w+[^}]{500,}",
            },
            "duplicate_code": {
                "description": "Duplicated code blocks",
                "severity": "high",
                "pattern": None,  # Requires semantic analysis
            },
            "large_class": {
                "description": "Class with too many responsibilities",
                "severity": "medium",
                "pattern": r"class\s+\w+[^}]{2000,}",
            },
            "long_parameter_list": {
                "description": "Function with >5 parameters",
                "severity": "low",
                "pattern": r"def\s+\w+\([^)]{100,}\)",
            },
            "god_object": {
                "description": "Object that knows too much",
                "severity": "high",
                "pattern": None,  # Requires dependency analysis
            },
            "complex_conditional": {
                "description": "Deeply nested conditionals",
                "severity": "medium",
                "pattern": r"if.*:\s*\n.*if.*:\s*\n.*if",
            },
            "magic_numbers": {
                "description": "Hard-coded numeric values",
                "severity": "low",
                "pattern": r"[^0-9\.](?:[1-9]\d{2,}|[2-9]\d)(?:[^0-9\.]|$)",
            },
            "dead_code": {
                "description": "Unused code",
                "severity": "medium",
                "pattern": None,  # Requires usage analysis
            },
        }

    def _initialize_refactoring_patterns(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize refactoring patterns.

        Returns:
            Dictionary of refactoring patterns
        """
        return {
            "extract_method": {
                "applies_to": ["long_function", "duplicate_code"],
                "description": "Extract code into separate methods",
                "complexity": "low",
            },
            "extract_class": {
                "applies_to": ["large_class", "god_object"],
                "description": "Split class responsibilities",
                "complexity": "medium",
            },
            "introduce_parameter_object": {
                "applies_to": ["long_parameter_list"],
                "description": "Group parameters into object",
                "complexity": "low",
            },
            "replace_conditional_with_polymorphism": {
                "applies_to": ["complex_conditional"],
                "description": "Use polymorphism instead of conditionals",
                "complexity": "high",
            },
            "extract_constant": {
                "applies_to": ["magic_numbers"],
                "description": "Replace magic numbers with constants",
                "complexity": "low",
            },
            "remove_dead_code": {
                "applies_to": ["dead_code"],
                "description": "Remove unused code",
                "complexity": "low",
            },
            "rename_method": {
                "applies_to": ["unclear_naming"],
                "description": "Improve method names",
                "complexity": "low",
            },
            "simplify_conditional": {
                "applies_to": ["complex_conditional"],
                "description": "Simplify conditional expressions",
                "complexity": "medium",
            },
        }

    def _detect_code_smells(
        self, task: str, code: str, files: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Detect code smells in the provided context.

        Args:
            task: Task description
            code: Code snippet
            files: List of file paths

        Returns:
            List of detected code smells
        """
        smells = []

        # Analyze task description for mentioned issues
        task_lower = task.lower()

        for smell_name, smell_info in self.code_smells.items():
            # Check if smell is mentioned in task
            if smell_name.replace("_", " ") in task_lower:
                smells.append(
                    {
                        "type": smell_name,
                        "description": smell_info["description"],
                        "severity": smell_info["severity"],
                        "source": "task_description",
                    }
                )
            # Check pattern if available and code provided
            elif code and smell_info["pattern"]:
                if re.search(smell_info["pattern"], code):
                    smells.append(
                        {
                            "type": smell_name,
                            "description": smell_info["description"],
                            "severity": smell_info["severity"],
                            "source": "code_analysis",
                        }
                    )

        # Generic smell detection based on keywords
        generic_smells = {
            "complex": "high_complexity",
            "messy": "poor_organization",
            "unclear": "unclear_naming",
            "slow": "performance_issue",
            "repetitive": "duplicate_code",
        }

        for keyword, smell_type in generic_smells.items():
            if keyword in task_lower and not any(
                s["type"] == smell_type for s in smells
            ):
                smells.append(
                    {
                        "type": smell_type,
                        "description": f"Potential {smell_type.replace('_', ' ')} issue",
                        "severity": "medium",
                        "source": "keyword_detection",
                    }
                )

        return smells

    def _identify_opportunities(
        self, smells: List[Dict[str, Any]], task: str
    ) -> List[Dict[str, Any]]:
        """
        Identify refactoring opportunities based on code smells.

        Args:
            smells: Detected code smells
            task: Task description

        Returns:
            List of improvement opportunities
        """
        opportunities = []

        for smell in smells:
            smell_type = smell["type"]

            # Find applicable refactoring patterns
            for pattern_name, pattern_info in self.refactoring_patterns.items():
                if smell_type in pattern_info.get("applies_to", []):
                    opportunities.append(
                        {
                            "smell": smell_type,
                            "refactoring": pattern_name,
                            "description": pattern_info["description"],
                            "complexity": pattern_info["complexity"],
                            "severity": smell["severity"],
                        }
                    )

        # Prioritize opportunities
        priority_map = {
            ("high", "low"): 1,  # High severity, low complexity
            ("high", "medium"): 2,  # High severity, medium complexity
            ("medium", "low"): 3,  # Medium severity, low complexity
            ("high", "high"): 4,  # High severity, high complexity
            ("medium", "medium"): 5,  # Medium severity, medium complexity
            ("low", "low"): 6,  # Low severity, low complexity
            ("medium", "high"): 7,  # Medium severity, high complexity
            ("low", "medium"): 8,  # Low severity, medium complexity
            ("low", "high"): 9,  # Low severity, high complexity
        }

        for opp in opportunities:
            key = (opp["severity"], opp["complexity"])
            opp["priority"] = priority_map.get(key, 5)

        # Sort by priority
        opportunities.sort(key=lambda x: x["priority"])

        return opportunities

    def _create_refactoring_plan(
        self, opportunities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Create a refactoring plan from opportunities.

        Args:
            opportunities: Identified opportunities

        Returns:
            Refactoring plan
        """
        plan = []

        # Group by refactoring type
        grouped = {}
        for opp in opportunities:
            ref_type = opp["refactoring"]
            if ref_type not in grouped:
                grouped[ref_type] = []
            grouped[ref_type].append(opp)

        # Create plan items
        for ref_type, items in grouped.items():
            # Aggregate information
            severities = [item["severity"] for item in items]
            max_severity = max(severities, key=["low", "medium", "high"].index)

            plan.append(
                {
                    "type": ref_type,
                    "description": items[0]["description"],
                    "targets": [item["smell"] for item in items],
                    "priority": min(item["priority"] for item in items),
                    "complexity": items[0]["complexity"],
                    "severity": max_severity,
                    "count": len(items),
                }
            )

        # Sort by priority
        plan.sort(key=lambda x: x["priority"])

        return plan[:10]  # Limit to top 10 refactorings

    def _estimate_impact(self, plan: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Estimate the impact of refactoring plan.

        Args:
            plan: Refactoring plan

        Returns:
            Impact metrics
        """
        # Calculate metrics
        complexity_reduction = 0
        maintainability_improvement = 0
        risk_level = 0

        complexity_impact = {
            "extract_method": 20,
            "extract_class": 30,
            "introduce_parameter_object": 10,
            "replace_conditional_with_polymorphism": 25,
            "extract_constant": 5,
            "remove_dead_code": 15,
            "rename_method": 5,
            "simplify_conditional": 15,
        }

        risk_levels = {"low": 1, "medium": 2, "high": 3}

        for item in plan:
            ref_type = item["type"]
            complexity = item["complexity"]
            count = item.get("count", 1)

            # Calculate complexity reduction
            if ref_type in complexity_impact:
                complexity_reduction += complexity_impact[ref_type] * count

            # Calculate maintainability improvement
            if item["severity"] == "high":
                maintainability_improvement += 30 * count
            elif item["severity"] == "medium":
                maintainability_improvement += 20 * count
            else:
                maintainability_improvement += 10 * count

            # Calculate risk
            risk_level += risk_levels.get(complexity, 2) * count

        # Normalize scores
        total_items = sum(item.get("count", 1) for item in plan)
        if total_items > 0:
            risk_level = risk_level / total_items

        return {
            "complexity_reduction": min(complexity_reduction, 100),
            "maintainability_improvement": min(maintainability_improvement, 100),
            "risk_level": ["low", "medium", "high"][min(int(risk_level), 2)],
            "estimated_effort_hours": total_items * 2,  # Rough estimate
        }

    def _generate_recommendations(
        self,
        task: str,
        smells: List[Dict[str, Any]],
        plan: List[Dict[str, Any]],
        impact: Dict[str, Any],
    ) -> str:
        """
        Generate refactoring recommendations report.

        Args:
            task: Original task
            smells: Detected code smells
            plan: Refactoring plan
            impact: Impact metrics

        Returns:
            Recommendations report
        """
        lines = []

        # Header
        lines.append("# Refactoring Recommendations\n")
        lines.append(f"**Analysis**: {task}\n")

        # Code smells section
        lines.append("\n## Code Smells Detected\n")
        if smells:
            for smell in smells[:5]:
                severity_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    smell["severity"], "⚪"
                )
                lines.append(
                    f"- {severity_icon} **{smell['type'].replace('_', ' ').title()}**: {smell['description']}"
                )

            if len(smells) > 5:
                lines.append(f"- *(and {len(smells) - 5} more issues)*")
        else:
            lines.append("*No significant code smells detected.*")

        # Refactoring plan section
        lines.append("\n## Refactoring Plan\n")
        if plan:
            for i, item in enumerate(plan[:5], 1):
                lines.append(f"{i}. **{item['type'].replace('_', ' ').title()}**")
                lines.append(f"   - {item['description']}")
                lines.append(
                    f"   - Priority: {['High', 'Medium', 'Low'][min(item['priority'] // 3, 2)]}"
                )
                lines.append(f"   - Complexity: {item['complexity'].capitalize()}")
        else:
            lines.append("*No refactoring opportunities identified.*")

        # Impact section
        lines.append("\n## Expected Impact\n")
        lines.append(f"- **Complexity Reduction**: {impact['complexity_reduction']}%")
        lines.append(
            f"- **Maintainability Improvement**: {impact['maintainability_improvement']}%"
        )
        lines.append(f"- **Risk Level**: {impact['risk_level'].capitalize()}")
        lines.append(
            f"- **Estimated Effort**: {impact['estimated_effort_hours']} hours"
        )

        # Best practices section
        lines.append("\n## Best Practices\n")
        lines.append(
            "1. **Test Coverage**: Ensure comprehensive tests before refactoring"
        )
        lines.append("2. **Incremental Changes**: Refactor in small, verifiable steps")
        lines.append("3. **Version Control**: Commit frequently during refactoring")
        lines.append("4. **Code Review**: Have refactored code reviewed by peers")
        lines.append("5. **Documentation**: Update documentation after refactoring")

        return "\n".join(lines)
