"""
System Architect Agent for SuperClaude Framework

This agent specializes in designing scalable system architectures,
evaluating design patterns, and making architectural decisions.
"""

from typing import Any

from ..base import BaseAgent


class SystemArchitect(BaseAgent):
    """
    Agent specialized in system architecture and design.

    Provides architectural analysis, pattern recommendations, system design,
    and scalability assessments for software projects.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the system architect.

        Args:
            config: Agent configuration
        """
        # Ensure proper configuration
        if "name" not in config:
            config["name"] = "system-architect"
        if "description" not in config:
            config["description"] = "Design scalable system architecture"
        if "category" not in config:
            config["category"] = "architecture"

        super().__init__(config)

        # Architecture patterns and principles
        self.patterns = self._initialize_patterns()
        self.principles = self._initialize_principles()
        self.quality_attributes = self._initialize_quality_attributes()

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute architectural analysis and design tasks.

        Args:
            context: Execution context

        Returns:
            Architecture assessment and recommendations
        """
        result = {
            "success": False,
            "output": "",
            "actions_taken": [],
            "errors": [],
            "architecture_analysis": {},
            "patterns_identified": [],
            "recommendations": [],
            "design_decisions": [],
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
            context.get("scope", "system")

            if not task and not files and not code:
                result["errors"].append("No content to analyze architecturally")
                return result

            self.logger.info(f"Starting architectural analysis: {task[:100]}...")

            # Phase 1: Analyze current architecture
            current_arch = self._analyze_current_architecture(files, code)
            result["architecture_analysis"] = current_arch
            result["actions_taken"].append(
                f"Analyzed {len(current_arch.get('components', []))} components"
            )

            # Phase 2: Identify patterns
            patterns = self._identify_patterns(current_arch, code)
            result["patterns_identified"] = patterns
            result["actions_taken"].append(
                f"Identified {len(patterns)} architectural patterns"
            )

            # Phase 3: Evaluate quality attributes
            quality_assessment = self._evaluate_quality_attributes(
                current_arch, patterns
            )
            result["actions_taken"].append("Evaluated quality attributes")

            # Phase 4: Generate design decisions
            decisions = self._generate_design_decisions(
                task, current_arch, quality_assessment
            )
            result["design_decisions"] = decisions
            result["actions_taken"].append(
                f"Generated {len(decisions)} design decisions"
            )

            # Phase 5: Create recommendations
            recommendations = self._create_recommendations(
                current_arch, patterns, quality_assessment, decisions
            )
            result["recommendations"] = recommendations

            # Phase 6: Generate architecture report
            report = self._generate_architecture_report(
                task,
                current_arch,
                patterns,
                quality_assessment,
                decisions,
                recommendations,
            )
            result["output"] = report

            result["success"] = True
            self.log_execution(context, result)

        except Exception as e:
            self.logger.error(f"Architecture analysis failed: {e}")
            result["errors"].append(str(e))

        return result

    def validate(self, context: dict[str, Any]) -> bool:
        """
        Check if this agent can handle the context.

        Args:
            context: Validation context

        Returns:
            True if context contains architecture tasks
        """
        task = context.get("task", "")

        # Check for architecture keywords
        arch_keywords = [
            "architect",
            "architecture",
            "design",
            "system design",
            "scalab",
            "pattern",
            "microservice",
            "monolith",
            "distributed",
            "component",
            "module",
            "structure",
        ]

        task_lower = task.lower()
        return any(keyword in task_lower for keyword in arch_keywords)

    def _initialize_patterns(self) -> dict[str, dict[str, Any]]:
        """
        Initialize architectural patterns.

        Returns:
            Dictionary of architectural patterns
        """
        return {
            "layered": {
                "name": "Layered Architecture",
                "description": "Organize system into hierarchical layers",
                "pros": ["Separation of concerns", "Testability", "Maintainability"],
                "cons": ["Performance overhead", "Rigid structure"],
                "use_cases": ["Enterprise applications", "Traditional web apps"],
            },
            "microservices": {
                "name": "Microservices Architecture",
                "description": "Decompose system into small, independent services",
                "pros": ["Scalability", "Technology diversity", "Fault isolation"],
                "cons": ["Complexity", "Network overhead", "Data consistency"],
                "use_cases": ["Large-scale systems", "Cloud-native apps"],
            },
            "event_driven": {
                "name": "Event-Driven Architecture",
                "description": "Components communicate through events",
                "pros": ["Loose coupling", "Scalability", "Real-time processing"],
                "cons": [
                    "Debugging complexity",
                    "Event ordering",
                    "Testing difficulty",
                ],
                "use_cases": ["Real-time systems", "IoT applications"],
            },
            "hexagonal": {
                "name": "Hexagonal Architecture",
                "description": "Core business logic isolated from external concerns",
                "pros": ["Testability", "Flexibility", "Technology agnostic"],
                "cons": ["Initial complexity", "More abstractions"],
                "use_cases": ["Domain-driven design", "Complex business logic"],
            },
            "serverless": {
                "name": "Serverless Architecture",
                "description": "Functions as a service without server management",
                "pros": ["No server management", "Auto-scaling", "Cost-effective"],
                "cons": ["Vendor lock-in", "Cold starts", "Debugging challenges"],
                "use_cases": ["Event processing", "APIs", "Batch jobs"],
            },
        }

    def _initialize_principles(self) -> list[dict[str, Any]]:
        """
        Initialize architectural principles.

        Returns:
            List of architectural principles
        """
        return [
            {
                "name": "SOLID",
                "description": "Single Responsibility, Open-Closed, Liskov, Interface Segregation, Dependency Inversion",
                "category": "design",
            },
            {
                "name": "DRY",
                "description": "Don't Repeat Yourself - avoid duplication",
                "category": "maintainability",
            },
            {
                "name": "KISS",
                "description": "Keep It Simple, Stupid - prefer simplicity",
                "category": "simplicity",
            },
            {
                "name": "YAGNI",
                "description": "You Aren't Gonna Need It - avoid over-engineering",
                "category": "simplicity",
            },
            {
                "name": "Separation of Concerns",
                "description": "Different concerns should be in different modules",
                "category": "modularity",
            },
        ]

    def _initialize_quality_attributes(self) -> dict[str, dict[str, Any]]:
        """
        Initialize quality attributes for evaluation.

        Returns:
            Dictionary of quality attributes
        """
        return {
            "performance": {
                "description": "System responsiveness and throughput",
                "metrics": ["response_time", "throughput", "resource_usage"],
                "weight": 0.2,
            },
            "scalability": {
                "description": "Ability to handle increased load",
                "metrics": ["horizontal_scaling", "vertical_scaling", "elasticity"],
                "weight": 0.2,
            },
            "security": {
                "description": "Protection against threats",
                "metrics": ["authentication", "authorization", "encryption"],
                "weight": 0.15,
            },
            "maintainability": {
                "description": "Ease of modification and updates",
                "metrics": ["modularity", "testability", "documentation"],
                "weight": 0.15,
            },
            "reliability": {
                "description": "System availability and fault tolerance",
                "metrics": ["uptime", "fault_tolerance", "recovery"],
                "weight": 0.15,
            },
            "usability": {
                "description": "User experience and ease of use",
                "metrics": ["ui_consistency", "accessibility", "learnability"],
                "weight": 0.15,
            },
        }

    def _analyze_current_architecture(
        self, files: list[str], code: str
    ) -> dict[str, Any]:
        """
        Analyze the current system architecture.

        Args:
            files: File paths
            code: Code content

        Returns:
            Current architecture analysis
        """
        architecture = {
            "components": [],
            "layers": [],
            "dependencies": [],
            "patterns_detected": [],
            "complexity": "unknown",
        }

        # Analyze file structure for components
        if files:
            components = self._extract_components_from_files(files)
            architecture["components"] = components

            # Detect layers
            layers = self._detect_layers(files)
            architecture["layers"] = layers

        # Analyze code for patterns
        if code:
            # Detect design patterns
            if "class" in code and "getInstance" in code:
                architecture["patterns_detected"].append("Singleton")
            if "Observer" in code or "addEventListener" in code:
                architecture["patterns_detected"].append("Observer")
            if "Factory" in code or "create" in code:
                architecture["patterns_detected"].append("Factory")

        # Estimate complexity
        num_components = len(architecture["components"])
        if num_components < 5:
            architecture["complexity"] = "simple"
        elif num_components < 15:
            architecture["complexity"] = "moderate"
        else:
            architecture["complexity"] = "complex"

        return architecture

    def _extract_components_from_files(self, files: list[str]) -> list[dict[str, Any]]:
        """
        Extract components from file structure.

        Args:
            files: List of file paths

        Returns:
            List of components
        """
        components = []
        component_dirs = set()

        for file_path in files:
            parts = file_path.split("/")

            # Look for common component patterns
            if "components" in parts or "modules" in parts or "services" in parts:
                idx = max(
                    parts.index(x) if x in parts else -1
                    for x in ["components", "modules", "services"]
                )
                if idx >= 0 and idx + 1 < len(parts):
                    component_name = parts[idx + 1]
                    if component_name not in component_dirs:
                        component_dirs.add(component_name)
                        components.append(
                            {"name": component_name, "type": parts[idx], "files": []}
                        )

        # Add files to components
        for component in components:
            for file_path in files:
                if component["name"] in file_path:
                    component["files"].append(file_path)

        return components

    def _detect_layers(self, files: list[str]) -> list[str]:
        """
        Detect architectural layers from files.

        Args:
            files: List of file paths

        Returns:
            List of detected layers
        """
        layers = []
        layer_patterns = {
            "presentation": ["ui", "view", "frontend", "client"],
            "business": ["service", "business", "domain", "core"],
            "data": ["repository", "dao", "model", "entity"],
            "infrastructure": ["config", "util", "helper", "infra"],
        }

        for layer_name, patterns in layer_patterns.items():
            for file_path in files:
                if any(pattern in file_path.lower() for pattern in patterns):
                    if layer_name not in layers:
                        layers.append(layer_name)
                    break

        return layers

    def _identify_patterns(
        self, architecture: dict[str, Any], code: str
    ) -> list[dict[str, Any]]:
        """
        Identify architectural patterns.

        Args:
            architecture: Current architecture analysis
            code: Code content

        Returns:
            List of identified patterns
        """
        patterns = []

        # Check for microservices indicators
        if len(architecture["components"]) > 5 and "api" in str(architecture):
            patterns.append(
                {
                    "pattern": "microservices",
                    "confidence": 0.7,
                    "indicators": ["Multiple components", "API presence"],
                }
            )

        # Check for layered architecture
        if len(architecture["layers"]) >= 3:
            patterns.append(
                {
                    "pattern": "layered",
                    "confidence": 0.8,
                    "indicators": ["Clear layer separation"],
                }
            )

        # Check for event-driven
        if code and ("event" in code.lower() or "message" in code.lower()):
            patterns.append(
                {
                    "pattern": "event_driven",
                    "confidence": 0.6,
                    "indicators": ["Event/message handling"],
                }
            )

        return patterns

    def _evaluate_quality_attributes(
        self, architecture: dict[str, Any], patterns: list[dict[str, Any]]
    ) -> dict[str, float]:
        """
        Evaluate quality attributes.

        Args:
            architecture: Current architecture
            patterns: Identified patterns

        Returns:
            Quality attribute scores
        """
        scores = {}

        for attr_name, attr_info in self.quality_attributes.items():
            score = 50  # Base score

            # Adjust based on architecture complexity
            if attr_name == "maintainability":
                if architecture["complexity"] == "simple":
                    score += 20
                elif architecture["complexity"] == "complex":
                    score -= 20

            # Adjust based on patterns
            for pattern in patterns:
                if pattern["pattern"] == "microservices":
                    if attr_name == "scalability":
                        score += 20
                    elif attr_name == "maintainability":
                        score -= 10
                elif pattern["pattern"] == "layered":
                    if attr_name == "maintainability":
                        score += 15

            scores[attr_name] = min(100, max(0, score))

        return scores

    def _generate_design_decisions(
        self, task: str, architecture: dict[str, Any], quality_scores: dict[str, float]
    ) -> list[dict[str, Any]]:
        """
        Generate design decisions.

        Args:
            task: Task description
            architecture: Current architecture
            quality_scores: Quality attribute scores

        Returns:
            List of design decisions
        """
        decisions = []

        # Decision based on scalability needs
        if quality_scores.get("scalability", 0) < 60:
            decisions.append(
                {
                    "area": "Scalability",
                    "decision": "Consider microservices or serverless architecture",
                    "rationale": "Current architecture may not scale effectively",
                    "impact": "Improved horizontal scaling capabilities",
                }
            )

        # Decision based on maintainability
        if quality_scores.get("maintainability", 0) < 70:
            decisions.append(
                {
                    "area": "Maintainability",
                    "decision": "Implement clearer module boundaries",
                    "rationale": "Current structure shows high coupling",
                    "impact": "Easier to modify and test components",
                }
            )

        # Decision based on security
        if quality_scores.get("security", 0) < 80:
            decisions.append(
                {
                    "area": "Security",
                    "decision": "Add security layer with authentication gateway",
                    "rationale": "Centralize security concerns",
                    "impact": "Improved security posture",
                }
            )

        return decisions

    def _create_recommendations(
        self,
        architecture: dict[str, Any],
        patterns: list[dict[str, Any]],
        quality_scores: dict[str, float],
        decisions: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Create architectural recommendations.

        Args:
            architecture: Current architecture
            patterns: Identified patterns
            quality_scores: Quality scores
            decisions: Design decisions

        Returns:
            List of recommendations
        """
        recommendations = []

        # Pattern-based recommendations
        if not patterns:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "structure",
                    "recommendation": "Adopt a clear architectural pattern",
                    "benefit": "Improved consistency and maintainability",
                }
            )

        # Component recommendations
        if len(architecture["components"]) > 20:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "modularity",
                    "recommendation": "Consider consolidating related components",
                    "benefit": "Reduced complexity and dependencies",
                }
            )

        # Layer recommendations
        if (
            "presentation" in architecture["layers"]
            and "data" in architecture["layers"]
        ):
            if "business" not in architecture["layers"]:
                recommendations.append(
                    {
                        "priority": "high",
                        "category": "separation",
                        "recommendation": "Add business logic layer",
                        "benefit": "Better separation of concerns",
                    }
                )

        # Quality-based recommendations
        lowest_quality = min(quality_scores.items(), key=lambda x: x[1])
        if lowest_quality[1] < 60:
            recommendations.append(
                {
                    "priority": "critical",
                    "category": "quality",
                    "recommendation": f"Focus on improving {lowest_quality[0]}",
                    "benefit": f"Address weakest quality attribute (score: {lowest_quality[1]})",
                }
            )

        return recommendations

    def _generate_architecture_report(
        self,
        task: str,
        architecture: dict[str, Any],
        patterns: list[dict[str, Any]],
        quality_scores: dict[str, float],
        decisions: list[dict[str, Any]],
        recommendations: list[dict[str, Any]],
    ) -> str:
        """
        Generate comprehensive architecture report.

        Args:
            task: Original task
            architecture: Architecture analysis
            patterns: Identified patterns
            quality_scores: Quality scores
            decisions: Design decisions
            recommendations: Recommendations

        Returns:
            Architecture report
        """
        lines = []

        # Header
        lines.append("# Architecture Analysis Report\n")
        lines.append(f"**Task**: {task}\n")

        # Current Architecture
        lines.append("\n## Current Architecture\n")
        lines.append(f"**Complexity**: {architecture['complexity'].title()}")
        lines.append(f"**Components**: {len(architecture['components'])}")
        if architecture["layers"]:
            lines.append(f"**Layers**: {', '.join(architecture['layers'])}")
        if architecture["patterns_detected"]:
            lines.append(
                f"**Detected Patterns**: {', '.join(architecture['patterns_detected'])}"
            )

        # Component Details
        if architecture["components"]:
            lines.append("\n### Components")
            for comp in architecture["components"][:10]:  # Limit to top 10
                lines.append(
                    f"- **{comp['name']}** ({comp['type']}): {len(comp.get('files', []))} files"
                )

        # Identified Patterns
        if patterns:
            lines.append("\n## Architectural Patterns\n")
            for pattern in patterns:
                pattern_info = self.patterns.get(pattern["pattern"], {})
                lines.append(
                    f"### {pattern_info.get('name', pattern['pattern'].title())}"
                )
                lines.append(f"**Confidence**: {pattern['confidence'] * 100:.0f}%")
                lines.append(f"**Indicators**: {', '.join(pattern['indicators'])}")

        # Quality Assessment
        lines.append("\n## Quality Attributes\n")
        for attr_name, score in sorted(
            quality_scores.items(), key=lambda x: x[1], reverse=True
        ):
            emoji = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
            lines.append(f"{emoji} **{attr_name.title()}**: {score:.0f}/100")

        # Design Decisions
        if decisions:
            lines.append("\n## Design Decisions\n")
            for decision in decisions:
                lines.append(f"### {decision['area']}")
                lines.append(f"**Decision**: {decision['decision']}")
                lines.append(f"**Rationale**: {decision['rationale']}")
                lines.append(f"**Impact**: {decision['impact']}")

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
                    f"{priority_emoji} **{rec['category'].title()}**: {rec['recommendation']}"
                )
                lines.append(f"   - Benefit: {rec['benefit']}")

        # Architecture Principles
        lines.append("\n## Applied Principles\n")
        for principle in self.principles[:5]:  # Top 5 principles
            lines.append(f"- **{principle['name']}**: {principle['description']}")

        # Next Steps
        lines.append("\n## Next Steps\n")
        lines.append("1. Review and prioritize recommendations")
        lines.append("2. Create detailed design documents for critical changes")
        lines.append("3. Establish architecture decision records (ADRs)")
        lines.append("4. Plan incremental migration if patterns need to change")
        lines.append("5. Set up architecture validation in CI/CD pipeline")

        return "\n".join(lines)
