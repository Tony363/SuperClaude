"""
Frontend Architect Agent for SuperClaude Framework

This agent specializes in frontend architecture, UI/UX design patterns,
component systems, and modern web development best practices.
"""

from pathlib import Path
from typing import Any

from ..base import BaseAgent


class FrontendArchitect(BaseAgent):
    """
    Agent specialized in frontend architecture and development.

    Provides UI/UX design, component architecture, state management,
    and frontend best practices for modern web applications.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the frontend architect.

        Args:
            config: Agent configuration
        """
        # Ensure proper configuration
        if "name" not in config:
            config["name"] = "frontend-architect"
        if "description" not in config:
            config["description"] = "Create accessible, performant user interfaces"
        if "category" not in config:
            config["category"] = "frontend"

        super().__init__(config)

        # Frontend patterns and technologies
        self.frameworks = self._initialize_frameworks()
        self.ui_patterns = self._initialize_ui_patterns()
        self.state_patterns = self._initialize_state_patterns()
        self.performance_metrics = self._initialize_performance_metrics()

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute frontend architecture tasks.

        Args:
            context: Execution context

        Returns:
            Frontend architecture analysis and recommendations
        """
        result = {
            "success": False,
            "output": "",
            "actions_taken": [],
            "errors": [],
            "component_architecture": {},
            "ui_patterns": [],
            "state_management": {},
            "performance_analysis": {},
            "accessibility_audit": {},
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
                result["errors"].append("No content for frontend analysis")
                return result

            self.logger.info(
                f"Starting frontend architecture analysis: {task[:100]}..."
            )

            # Phase 1: Analyze component architecture
            component_arch = self._analyze_component_architecture(task, files, code)
            result["component_architecture"] = component_arch
            result["actions_taken"].append(
                f"Analyzed {len(component_arch.get('components', []))} components"
            )

            # Phase 2: Identify UI patterns
            ui_patterns = self._identify_ui_patterns(component_arch, code)
            result["ui_patterns"] = ui_patterns
            result["actions_taken"].append(f"Identified {len(ui_patterns)} UI patterns")

            # Phase 3: Analyze state management
            state_mgmt = self._analyze_state_management(task, files, code)
            result["state_management"] = state_mgmt
            result["actions_taken"].append("Analyzed state management approach")

            # Phase 4: Performance analysis
            performance = self._analyze_performance(component_arch, code)
            result["performance_analysis"] = performance
            result["actions_taken"].append("Completed performance analysis")

            # Phase 5: Accessibility audit
            accessibility = self._audit_accessibility(code, component_arch)
            result["accessibility_audit"] = accessibility
            result["actions_taken"].append("Completed accessibility audit")

            # Phase 6: Generate recommendations
            recommendations = self._generate_recommendations(
                component_arch, ui_patterns, state_mgmt, performance, accessibility
            )
            result["recommendations"] = recommendations

            # Phase 7: Generate frontend report
            report = self._generate_frontend_report(
                task,
                component_arch,
                ui_patterns,
                state_mgmt,
                performance,
                accessibility,
                recommendations,
            )
            result["output"] = report

            result["success"] = True
            self.log_execution(context, result)

        except Exception as e:
            self.logger.error(f"Frontend architecture analysis failed: {e}")
            result["errors"].append(str(e))

        return result

    def validate(self, context: dict[str, Any]) -> bool:
        """
        Check if this agent can handle the context.

        Args:
            context: Validation context

        Returns:
            True if context contains frontend tasks
        """
        task = context.get("task", "")

        # Check for frontend keywords
        frontend_keywords = [
            "frontend",
            "ui",
            "ux",
            "component",
            "react",
            "vue",
            "angular",
            "css",
            "style",
            "design",
            "interface",
            "responsive",
            "accessibility",
            "state management",
            "redux",
            "webpack",
            "vite",
        ]

        task_lower = task.lower()
        return any(keyword in task_lower for keyword in frontend_keywords)

    def _initialize_frameworks(self) -> dict[str, dict[str, Any]]:
        """
        Initialize frontend frameworks.

        Returns:
            Dictionary of frameworks
        """
        return {
            "react": {
                "name": "React",
                "type": "library",
                "pros": ["Component reusability", "Virtual DOM", "Large ecosystem"],
                "cons": ["Learning curve", "Boilerplate", "JSX complexity"],
                "best_for": ["SPAs", "Complex UIs", "Large teams"],
            },
            "vue": {
                "name": "Vue.js",
                "type": "framework",
                "pros": ["Gentle learning curve", "Template syntax", "Reactive"],
                "cons": ["Smaller ecosystem", "Less enterprise adoption"],
                "best_for": ["Progressive enhancement", "Small to medium apps"],
            },
            "angular": {
                "name": "Angular",
                "type": "framework",
                "pros": ["Full framework", "TypeScript", "Enterprise ready"],
                "cons": ["Steep learning curve", "Verbose", "Performance overhead"],
                "best_for": ["Enterprise apps", "Large teams", "Complex requirements"],
            },
            "svelte": {
                "name": "Svelte",
                "type": "compiler",
                "pros": ["No virtual DOM", "Small bundle", "Simple syntax"],
                "cons": ["Smaller community", "Less tooling"],
                "best_for": ["Performance-critical apps", "Small bundles"],
            },
        }

    def _initialize_ui_patterns(self) -> dict[str, dict[str, Any]]:
        """
        Initialize UI design patterns.

        Returns:
            Dictionary of UI patterns
        """
        return {
            "atomic_design": {
                "name": "Atomic Design",
                "description": "Hierarchical component organization",
                "levels": ["Atoms", "Molecules", "Organisms", "Templates", "Pages"],
                "benefits": ["Consistency", "Reusability", "Scalability"],
            },
            "container_presenter": {
                "name": "Container/Presenter",
                "description": "Separate logic from presentation",
                "benefits": ["Testability", "Reusability", "Separation of concerns"],
            },
            "compound_components": {
                "name": "Compound Components",
                "description": "Related components share state",
                "benefits": ["Flexibility", "API simplicity", "Composition"],
            },
            "render_props": {
                "name": "Render Props",
                "description": "Share code between components using props",
                "benefits": ["Code reuse", "Flexibility", "Type safety"],
            },
            "hooks_pattern": {
                "name": "Custom Hooks",
                "description": "Extract component logic into reusable functions",
                "benefits": ["Logic reuse", "Testing", "Composition"],
            },
        }

    def _initialize_state_patterns(self) -> dict[str, dict[str, Any]]:
        """
        Initialize state management patterns.

        Returns:
            Dictionary of state patterns
        """
        return {
            "local_state": {
                "name": "Local Component State",
                "complexity": "low",
                "use_cases": ["Form inputs", "UI toggles", "Component-specific data"],
            },
            "context_api": {
                "name": "Context API",
                "complexity": "medium",
                "use_cases": ["Theme", "User auth", "Localization"],
            },
            "redux": {
                "name": "Redux",
                "complexity": "high",
                "use_cases": ["Complex state", "Time travel", "Predictable updates"],
            },
            "mobx": {
                "name": "MobX",
                "complexity": "medium",
                "use_cases": ["Reactive state", "Less boilerplate", "OOP style"],
            },
            "zustand": {
                "name": "Zustand",
                "complexity": "low",
                "use_cases": ["Simple global state", "Small bundle", "TypeScript"],
            },
        }

    def _initialize_performance_metrics(self) -> dict[str, dict[str, Any]]:
        """
        Initialize performance metrics.

        Returns:
            Dictionary of performance metrics
        """
        return {
            "fcp": {
                "name": "First Contentful Paint",
                "target": "< 1.8s",
                "weight": 0.15,
            },
            "lcp": {
                "name": "Largest Contentful Paint",
                "target": "< 2.5s",
                "weight": 0.25,
            },
            "fid": {"name": "First Input Delay", "target": "< 100ms", "weight": 0.15},
            "cls": {
                "name": "Cumulative Layout Shift",
                "target": "< 0.1",
                "weight": 0.15,
            },
            "tti": {"name": "Time to Interactive", "target": "< 3.8s", "weight": 0.15},
            "bundle_size": {"name": "Bundle Size", "target": "< 200KB", "weight": 0.15},
        }

    def _analyze_component_architecture(
        self, task: str, files: list[str], code: str
    ) -> dict[str, Any]:
        """
        Analyze component architecture.

        Args:
            task: Task description
            files: File paths
            code: Code content

        Returns:
            Component architecture analysis
        """
        architecture = {
            "framework": "unknown",
            "components": [],
            "structure": "unknown",
            "styling": "unknown",
            "routing": False,
            "testing": False,
        }

        # Detect framework
        if code:
            if "import React" in code or "from 'react'" in code:
                architecture["framework"] = "react"
            elif "Vue.component" in code or "createApp" in code:
                architecture["framework"] = "vue"
            elif "@angular" in code or "NgModule" in code:
                architecture["framework"] = "angular"
            elif "svelte" in code.lower():
                architecture["framework"] = "svelte"

        # Analyze component structure from files
        if files:
            component_files = [
                f
                for f in files
                if any(
                    ext in f for ext in [".jsx", ".tsx", ".vue", ".svelte", "component"]
                )
            ]

            for file_path in component_files:
                component_name = Path(file_path).stem
                architecture["components"].append(
                    {
                        "name": component_name,
                        "path": file_path,
                        "type": self._classify_component(component_name, file_path),
                    }
                )

        # Detect structure pattern
        if any("container" in str(c) for c in architecture["components"]):
            architecture["structure"] = "container/presenter"
        elif any(
            "atom" in str(files).lower() or "molecule" in str(files).lower()
            for files in files
        ):
            architecture["structure"] = "atomic"
        else:
            architecture["structure"] = "flat"

        # Detect styling approach
        if "styled-components" in code or "emotion" in code:
            architecture["styling"] = "css-in-js"
        elif ".module.css" in str(files) or ".module.scss" in str(files):
            architecture["styling"] = "css-modules"
        elif "tailwind" in code.lower():
            architecture["styling"] = "tailwind"
        else:
            architecture["styling"] = "traditional-css"

        # Detect routing
        if "router" in code.lower() or "route" in code.lower():
            architecture["routing"] = True

        # Detect testing
        if ".test." in str(files) or ".spec." in str(files):
            architecture["testing"] = True

        return architecture

    def _classify_component(self, name: str, path: str) -> str:
        """
        Classify component type.

        Args:
            name: Component name
            path: Component path

        Returns:
            Component classification
        """
        name_lower = name.lower()
        path_lower = path.lower()

        if "page" in path_lower or "view" in path_lower:
            return "page"
        elif "layout" in name_lower:
            return "layout"
        elif "container" in name_lower:
            return "container"
        elif "atom" in path_lower:
            return "atom"
        elif "molecule" in path_lower:
            return "molecule"
        elif "organism" in path_lower:
            return "organism"
        elif "hook" in name_lower:
            return "hook"
        elif "util" in path_lower or "helper" in path_lower:
            return "utility"
        else:
            return "component"

    def _identify_ui_patterns(
        self, architecture: dict[str, Any], code: str
    ) -> list[dict[str, Any]]:
        """
        Identify UI patterns.

        Args:
            architecture: Component architecture
            code: Code content

        Returns:
            List of UI patterns
        """
        patterns = []

        # Check for atomic design
        if architecture["structure"] == "atomic":
            patterns.append(
                {
                    "pattern": "atomic_design",
                    "confidence": 0.9,
                    "implementation": "Full atomic hierarchy detected",
                }
            )

        # Check for container/presenter
        if architecture["structure"] == "container/presenter":
            patterns.append(
                {
                    "pattern": "container_presenter",
                    "confidence": 0.8,
                    "implementation": "Logic/presentation separation",
                }
            )

        # Check for hooks pattern (React)
        if "use" in code and architecture["framework"] == "react":
            patterns.append(
                {
                    "pattern": "hooks_pattern",
                    "confidence": 0.7,
                    "implementation": "Custom hooks for logic reuse",
                }
            )

        # Check for compound components
        if "children" in code and "Context" in code:
            patterns.append(
                {
                    "pattern": "compound_components",
                    "confidence": 0.6,
                    "implementation": "Shared state through context",
                }
            )

        return patterns

    def _analyze_state_management(
        self, task: str, files: list[str], code: str
    ) -> dict[str, Any]:
        """
        Analyze state management approach.

        Args:
            task: Task description
            files: File paths
            code: Code content

        Returns:
            State management analysis
        """
        state_mgmt = {
            "approach": "local",
            "library": None,
            "complexity": "low",
            "global_state": False,
            "async_handling": False,
        }

        # Detect state management library
        if "redux" in code.lower() or "createStore" in code:
            state_mgmt["approach"] = "flux"
            state_mgmt["library"] = "redux"
            state_mgmt["complexity"] = "high"
            state_mgmt["global_state"] = True
        elif "mobx" in code.lower() or "observable" in code:
            state_mgmt["approach"] = "reactive"
            state_mgmt["library"] = "mobx"
            state_mgmt["complexity"] = "medium"
            state_mgmt["global_state"] = True
        elif "zustand" in code.lower():
            state_mgmt["approach"] = "hooks"
            state_mgmt["library"] = "zustand"
            state_mgmt["complexity"] = "low"
            state_mgmt["global_state"] = True
        elif "Context" in code and "Provider" in code:
            state_mgmt["approach"] = "context"
            state_mgmt["library"] = "context-api"
            state_mgmt["complexity"] = "medium"
            state_mgmt["global_state"] = True

        # Detect async handling
        if "async" in code or "await" in code or "promise" in code.lower():
            state_mgmt["async_handling"] = True

        return state_mgmt

    def _analyze_performance(
        self, architecture: dict[str, Any], code: str
    ) -> dict[str, Any]:
        """
        Analyze performance considerations.

        Args:
            architecture: Component architecture
            code: Code content

        Returns:
            Performance analysis
        """
        performance = {
            "optimizations": [],
            "issues": [],
            "score": 50,  # Base score
        }

        # Check for code splitting
        if "lazy" in code or "import(" in code:
            performance["optimizations"].append("Code splitting")
            performance["score"] += 10
        else:
            performance["issues"].append("No code splitting detected")

        # Check for memoization
        if "memo" in code or "useMemo" in code or "useCallback" in code:
            performance["optimizations"].append("Memoization")
            performance["score"] += 10

        # Check for virtualization
        if "virtual" in code.lower() or "window" in code:
            performance["optimizations"].append("List virtualization")
            performance["score"] += 10

        # Check for image optimization
        if 'loading="lazy"' in code or "Image" in code:
            performance["optimizations"].append("Lazy loading")
            performance["score"] += 5

        # Check for bundle size concerns
        num_components = len(architecture.get("components", []))
        if num_components > 50:
            performance["issues"].append("Large number of components")
            performance["score"] -= 10

        # Cap score at 100
        performance["score"] = min(100, max(0, performance["score"]))

        return performance

    def _audit_accessibility(
        self, code: str, architecture: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Audit accessibility compliance.

        Args:
            code: Code content
            architecture: Component architecture

        Returns:
            Accessibility audit results
        """
        audit = {
            "score": 50,  # Base score
            "issues": [],
            "compliance": [],
        }

        # Check for semantic HTML
        semantic_tags = ["<header", "<nav", "<main", "<footer", "<article", "<section"]
        if any(tag in code for tag in semantic_tags):
            audit["compliance"].append("Semantic HTML")
            audit["score"] += 10
        else:
            audit["issues"].append("Missing semantic HTML elements")

        # Check for ARIA attributes
        if "aria-" in code or "role=" in code:
            audit["compliance"].append("ARIA attributes")
            audit["score"] += 10
        else:
            audit["issues"].append("No ARIA attributes found")

        # Check for alt text
        if "<img" in code and "alt=" in code:
            audit["compliance"].append("Alt text for images")
            audit["score"] += 10
        elif "<img" in code:
            audit["issues"].append("Missing alt text for images")
            audit["score"] -= 10

        # Check for keyboard navigation
        if "onKeyDown" in code or "onKeyPress" in code or "tabIndex" in code:
            audit["compliance"].append("Keyboard navigation")
            audit["score"] += 10

        # Check for focus management
        if "focus" in code.lower():
            audit["compliance"].append("Focus management")
            audit["score"] += 5

        # Check for color contrast (simple check)
        if "contrast" in code.lower() or "a11y" in code.lower():
            audit["compliance"].append("Accessibility considerations")
            audit["score"] += 5

        # Cap score at 100
        audit["score"] = min(100, max(0, audit["score"]))

        return audit

    def _generate_recommendations(
        self,
        architecture: dict[str, Any],
        ui_patterns: list[dict[str, Any]],
        state_mgmt: dict[str, Any],
        performance: dict[str, Any],
        accessibility: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Generate frontend recommendations.

        Args:
            architecture: Component architecture
            ui_patterns: UI patterns
            state_mgmt: State management
            performance: Performance analysis
            accessibility: Accessibility audit

        Returns:
            List of recommendations
        """
        recommendations = []

        # Component architecture recommendations
        if not architecture["testing"]:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "Testing",
                    "recommendation": "Add component tests (Jest, React Testing Library)",
                    "benefit": "Ensure component reliability and prevent regressions",
                }
            )

        if architecture["structure"] == "flat" and len(architecture["components"]) > 10:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "Architecture",
                    "recommendation": "Organize components using atomic design or feature folders",
                    "benefit": "Better scalability and maintainability",
                }
            )

        # Performance recommendations
        if performance["score"] < 70:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "Performance",
                    "recommendation": "Implement code splitting and lazy loading",
                    "benefit": "Reduce initial bundle size and improve load times",
                }
            )

        if "Memoization" not in performance.get("optimizations", []):
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "Performance",
                    "recommendation": "Use React.memo, useMemo, and useCallback for optimization",
                    "benefit": "Prevent unnecessary re-renders",
                }
            )

        # Accessibility recommendations
        if accessibility["score"] < 70:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "Accessibility",
                    "recommendation": "Conduct WCAG 2.1 AA compliance audit",
                    "benefit": "Ensure application is usable by all users",
                }
            )

        # State management recommendations
        if state_mgmt["complexity"] == "high" and not state_mgmt["library"]:
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "State Management",
                    "recommendation": "Consider simpler state solution (Context API, Zustand)",
                    "benefit": "Reduce complexity and bundle size",
                }
            )

        # Styling recommendations
        if architecture["styling"] == "traditional-css":
            recommendations.append(
                {
                    "priority": "low",
                    "category": "Styling",
                    "recommendation": "Consider CSS-in-JS or CSS Modules for component scoping",
                    "benefit": "Prevent style conflicts and improve maintainability",
                }
            )

        return recommendations

    def _generate_frontend_report(
        self,
        task: str,
        architecture: dict[str, Any],
        ui_patterns: list[dict[str, Any]],
        state_mgmt: dict[str, Any],
        performance: dict[str, Any],
        accessibility: dict[str, Any],
        recommendations: list[dict[str, Any]],
    ) -> str:
        """
        Generate comprehensive frontend report.

        Args:
            task: Original task
            architecture: Component architecture
            ui_patterns: UI patterns
            state_mgmt: State management
            performance: Performance analysis
            accessibility: Accessibility audit
            recommendations: Recommendations

        Returns:
            Frontend architecture report
        """
        lines = []

        # Header
        lines.append("# Frontend Architecture Report\n")
        lines.append(f"**Task**: {task}\n")

        # Component Architecture
        lines.append("\n## Component Architecture\n")
        lines.append(f"**Framework**: {architecture['framework'].title()}")
        lines.append(
            f"**Structure**: {architecture['structure'].replace('_', ' ').title()}"
        )
        lines.append(
            f"**Styling**: {architecture['styling'].replace('-', ' ').title()}"
        )
        lines.append(f"**Components**: {len(architecture['components'])}")
        lines.append(
            f"**Routing**: {'✅ Configured' if architecture['routing'] else '❌ Not configured'}"
        )
        lines.append(
            f"**Testing**: {'✅ Tests found' if architecture['testing'] else '❌ No tests'}"
        )

        if architecture["components"]:
            lines.append("\n### Component Breakdown")
            component_types = {}
            for comp in architecture["components"]:
                comp_type = comp["type"]
                component_types[comp_type] = component_types.get(comp_type, 0) + 1

            for comp_type, count in sorted(component_types.items()):
                lines.append(f"- {comp_type.title()}: {count}")

        # UI Patterns
        if ui_patterns:
            lines.append("\n## UI Design Patterns\n")
            for pattern in ui_patterns:
                pattern_info = self.ui_patterns.get(pattern["pattern"], {})
                lines.append(f"### {pattern_info.get('name', pattern['pattern'])}")
                lines.append(f"**Confidence**: {pattern['confidence'] * 100:.0f}%")
                lines.append(f"**Implementation**: {pattern['implementation']}")

        # State Management
        lines.append("\n## State Management\n")
        lines.append(f"**Approach**: {state_mgmt['approach'].title()}")
        if state_mgmt["library"]:
            lines.append(f"**Library**: {state_mgmt['library'].title()}")
        lines.append(f"**Complexity**: {state_mgmt['complexity'].title()}")
        lines.append(
            f"**Global State**: {'✅ Yes' if state_mgmt['global_state'] else '❌ No'}"
        )
        lines.append(
            f"**Async Handling**: {'✅ Yes' if state_mgmt['async_handling'] else '❌ No'}"
        )

        # Performance
        lines.append("\n## Performance Analysis\n")
        score_emoji = (
            "🟢"
            if performance["score"] >= 80
            else "🟡"
            if performance["score"] >= 60
            else "🔴"
        )
        lines.append(f"{score_emoji} **Score**: {performance['score']}/100")

        if performance["optimizations"]:
            lines.append("\n### Optimizations")
            for opt in performance["optimizations"]:
                lines.append(f"- ✅ {opt}")

        if performance["issues"]:
            lines.append("\n### Issues")
            for issue in performance["issues"]:
                lines.append(f"- ⚠️ {issue}")

        # Accessibility
        lines.append("\n## Accessibility Audit\n")
        score_emoji = (
            "🟢"
            if accessibility["score"] >= 80
            else "🟡"
            if accessibility["score"] >= 60
            else "🔴"
        )
        lines.append(f"{score_emoji} **Score**: {accessibility['score']}/100")

        if accessibility["compliance"]:
            lines.append("\n### Compliance")
            for item in accessibility["compliance"]:
                lines.append(f"- ✅ {item}")

        if accessibility["issues"]:
            lines.append("\n### Issues")
            for issue in accessibility["issues"]:
                lines.append(f"- ⚠️ {issue}")

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

        # Best Practices Checklist
        lines.append("\n## Best Practices Checklist\n")
        lines.append("- [ ] Component documentation with prop types")
        lines.append("- [ ] Error boundaries for graceful failures")
        lines.append("- [ ] Loading states and skeletons")
        lines.append("- [ ] Responsive design (mobile-first)")
        lines.append("- [ ] Progressive enhancement")
        lines.append("- [ ] Browser compatibility testing")
        lines.append("- [ ] Performance monitoring (Web Vitals)")
        lines.append("- [ ] Accessibility testing (screen readers)")
        lines.append("- [ ] Internationalization (i18n) support")
        lines.append("- [ ] SEO optimization (meta tags, structured data)")

        return "\n".join(lines)
