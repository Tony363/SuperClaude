"""
Requirements Analyst Agent for SuperClaude Framework

This agent specializes in requirements elicitation, analysis,
and transformation of ambiguous ideas into concrete specifications.
"""

from typing import Any, Dict, List

from ..base import BaseAgent


class RequirementsAnalyst(BaseAgent):
    """
    Agent specialized in requirements analysis and specification.

    Provides requirements discovery, user story creation, acceptance criteria,
    and structured specification generation from ambiguous inputs.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the requirements analyst.

        Args:
            config: Agent configuration
        """
        # Ensure proper configuration
        if "name" not in config:
            config["name"] = "requirements-analyst"
        if "description" not in config:
            config["description"] = (
                "Transform ambiguous ideas into concrete specifications"
            )
        if "category" not in config:
            config["category"] = "planning"

        super().__init__(config)

        # Requirements patterns and templates
        self.requirement_types = self._initialize_requirement_types()
        self.question_templates = self._initialize_question_templates()
        self.story_templates = self._initialize_story_templates()
        self.acceptance_criteria_patterns = self._initialize_acceptance_patterns()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute requirements analysis tasks.

        Args:
            context: Execution context

        Returns:
            Requirements analysis and specifications
        """
        result = {
            "success": False,
            "output": "",
            "actions_taken": [],
            "errors": [],
            "requirements": [],
            "user_stories": [],
            "acceptance_criteria": [],
            "clarifications_needed": [],
            "specification": {},
            "recommendations": [],
        }

        try:
            # Initialize if needed
            if not self._initialized:
                if not self.initialize():
                    result["errors"].append("Failed to initialize agent")
                    return result

            task = context.get("task", "")
            description = context.get("description", "")
            stakeholders = context.get("stakeholders", [])
            constraints = context.get("constraints", {})

            if not task and not description:
                result["errors"].append("No content for requirements analysis")
                return result

            self.logger.info(f"Starting requirements analysis: {task[:100]}...")

            # Phase 1: Elicit requirements
            requirements = self._elicit_requirements(task, description)
            result["requirements"] = requirements
            result["actions_taken"].append(f"Elicited {len(requirements)} requirements")

            # Phase 2: Identify clarifications needed
            clarifications = self._identify_clarifications(requirements, task)
            result["clarifications_needed"] = clarifications
            result["actions_taken"].append(
                f"Identified {len(clarifications)} clarifications needed"
            )

            # Phase 3: Create user stories
            stories = self._create_user_stories(requirements, stakeholders)
            result["user_stories"] = stories
            result["actions_taken"].append(f"Created {len(stories)} user stories")

            # Phase 4: Define acceptance criteria
            criteria = self._define_acceptance_criteria(stories, requirements)
            result["acceptance_criteria"] = criteria
            result["actions_taken"].append(
                f"Defined {len(criteria)} acceptance criteria"
            )

            # Phase 5: Generate specification
            specification = self._generate_specification(
                requirements, stories, criteria, constraints
            )
            result["specification"] = specification
            result["actions_taken"].append("Generated formal specification")

            # Phase 6: Generate recommendations
            recommendations = self._generate_recommendations(
                requirements, clarifications, specification
            )
            result["recommendations"] = recommendations

            # Phase 7: Generate requirements report
            report = self._generate_requirements_report(
                task,
                requirements,
                clarifications,
                stories,
                criteria,
                specification,
                recommendations,
            )
            result["output"] = report

            result["success"] = True
            self.log_execution(context, result)

        except Exception as e:
            self.logger.error(f"Requirements analysis failed: {e}")
            result["errors"].append(str(e))

        return result

    def validate(self, context: Dict[str, Any]) -> bool:
        """
        Check if this agent can handle the context.

        Args:
            context: Validation context

        Returns:
            True if context contains requirements tasks
        """
        task = context.get("task", "")

        # Check for requirements keywords
        requirements_keywords = [
            "requirement",
            "spec",
            "specification",
            "user story",
            "acceptance criteria",
            "feature",
            "scope",
            "define",
            "clarify",
            "analyze requirements",
            "prd",
            "brd",
        ]

        task_lower = task.lower()
        return any(keyword in task_lower for keyword in requirements_keywords)

    def _initialize_requirement_types(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize requirement types.

        Returns:
            Dictionary of requirement types
        """
        return {
            "functional": {
                "name": "Functional Requirements",
                "description": "What the system should do",
                "examples": [
                    "User authentication",
                    "Data processing",
                    "Report generation",
                ],
                "priority": "high",
            },
            "non_functional": {
                "name": "Non-Functional Requirements",
                "description": "How the system should perform",
                "examples": ["Performance", "Security", "Usability", "Reliability"],
                "priority": "high",
            },
            "business": {
                "name": "Business Requirements",
                "description": "Business goals and constraints",
                "examples": ["ROI targets", "Market positioning", "Compliance"],
                "priority": "critical",
            },
            "technical": {
                "name": "Technical Requirements",
                "description": "Technical constraints and specifications",
                "examples": ["Platform", "Integration", "Architecture"],
                "priority": "medium",
            },
            "user": {
                "name": "User Requirements",
                "description": "User needs and expectations",
                "examples": ["User experience", "Accessibility", "Training"],
                "priority": "high",
            },
        }

    def _initialize_question_templates(self) -> Dict[str, List[str]]:
        """
        Initialize question templates for elicitation.

        Returns:
            Dictionary of question templates
        """
        return {
            "functional": [
                "What specific tasks should users be able to perform?",
                "What are the input and output requirements?",
                "How should the system respond to user actions?",
                "What data needs to be stored and retrieved?",
                "What reports or outputs are required?",
            ],
            "performance": [
                "How many concurrent users must the system support?",
                "What are the response time requirements?",
                "What is the expected data volume?",
                "What are the availability requirements?",
                "Are there specific performance benchmarks?",
            ],
            "security": [
                "What authentication methods are required?",
                "What data needs encryption?",
                "Are there compliance requirements (GDPR, HIPAA)?",
                "What are the authorization levels?",
                "How should audit trails be maintained?",
            ],
            "integration": [
                "What existing systems need integration?",
                "What APIs need to be exposed?",
                "What data formats are required?",
                "Are there third-party service dependencies?",
                "What are the synchronization requirements?",
            ],
            "constraints": [
                "What is the budget constraint?",
                "What is the timeline for delivery?",
                "Are there technology stack limitations?",
                "What are the regulatory constraints?",
                "Are there organizational policies to follow?",
            ],
        }

    def _initialize_story_templates(self) -> Dict[str, str]:
        """
        Initialize user story templates.

        Returns:
            Dictionary of story templates
        """
        return {
            "standard": "As a {role}, I want to {action} so that {benefit}",
            "job_story": "When {situation}, I want to {motivation} so I can {outcome}",
            "feature": "In order to {benefit}, as a {role}, I want {feature}",
            "epic": "As {personas}, we want {big_feature} to {business_value}",
        }

    def _initialize_acceptance_patterns(self) -> List[str]:
        """
        Initialize acceptance criteria patterns.

        Returns:
            List of acceptance criteria patterns
        """
        return [
            "Given {context}, When {action}, Then {outcome}",
            "Verify that {condition} results in {expected_behavior}",
            "Ensure {requirement} is met when {scenario}",
            "User can {action} and system responds with {response}",
            "System validates {input} and {validation_result}",
        ]

    def _elicit_requirements(self, task: str, description: str) -> List[Dict[str, Any]]:
        """
        Elicit requirements from task and description.

        Args:
            task: Task description
            description: Additional description

        Returns:
            List of elicited requirements
        """
        requirements = []
        combined_text = f"{task} {description}".lower()

        # Functional requirements
        functional_keywords = [
            "create",
            "read",
            "update",
            "delete",
            "search",
            "filter",
            "sort",
            "export",
            "import",
            "generate",
        ]
        for keyword in functional_keywords:
            if keyword in combined_text:
                requirements.append(
                    {
                        "id": f"FR-{len(requirements) + 1:03d}",
                        "type": "functional",
                        "title": f"{keyword.title()} functionality",
                        "description": f"System must support {keyword} operations",
                        "priority": "high",
                        "status": "draft",
                    }
                )

        # Non-functional requirements
        if "fast" in combined_text or "performance" in combined_text:
            requirements.append(
                {
                    "id": f"NFR-{len(requirements) + 1:03d}",
                    "type": "non_functional",
                    "category": "performance",
                    "title": "Performance requirements",
                    "description": "System must meet performance benchmarks",
                    "priority": "high",
                    "status": "draft",
                }
            )

        if "secure" in combined_text or "auth" in combined_text:
            requirements.append(
                {
                    "id": f"NFR-{len(requirements) + 1:03d}",
                    "type": "non_functional",
                    "category": "security",
                    "title": "Security requirements",
                    "description": "System must implement security measures",
                    "priority": "critical",
                    "status": "draft",
                }
            )

        if "scale" in combined_text or "users" in combined_text:
            requirements.append(
                {
                    "id": f"NFR-{len(requirements) + 1:03d}",
                    "type": "non_functional",
                    "category": "scalability",
                    "title": "Scalability requirements",
                    "description": "System must scale to handle user load",
                    "priority": "high",
                    "status": "draft",
                }
            )

        # User interface requirements
        if (
            "ui" in combined_text
            or "interface" in combined_text
            or "design" in combined_text
        ):
            requirements.append(
                {
                    "id": f"UIR-{len(requirements) + 1:03d}",
                    "type": "user",
                    "title": "User interface requirements",
                    "description": "System must provide intuitive user interface",
                    "priority": "high",
                    "status": "draft",
                }
            )

        # Integration requirements
        if "api" in combined_text or "integrate" in combined_text:
            requirements.append(
                {
                    "id": f"IR-{len(requirements) + 1:03d}",
                    "type": "technical",
                    "category": "integration",
                    "title": "Integration requirements",
                    "description": "System must integrate with external services",
                    "priority": "medium",
                    "status": "draft",
                }
            )

        # Default requirement if none found
        if not requirements:
            requirements.append(
                {
                    "id": "GR-001",
                    "type": "general",
                    "title": "General system requirement",
                    "description": "System must fulfill stated objectives",
                    "priority": "high",
                    "status": "draft",
                }
            )

        return requirements

    def _identify_clarifications(
        self, requirements: List[Dict[str, Any]], task: str
    ) -> List[Dict[str, Any]]:
        """
        Identify clarifications needed.

        Args:
            requirements: Elicited requirements
            task: Task description

        Returns:
            List of clarifications needed
        """
        clarifications = []

        # Check for ambiguous terms
        ambiguous_terms = [
            "some",
            "many",
            "fast",
            "slow",
            "big",
            "small",
            "good",
            "bad",
            "appropriate",
            "suitable",
        ]
        for term in ambiguous_terms:
            if term in task.lower():
                clarifications.append(
                    {
                        "area": "Ambiguous terminology",
                        "question": f'What specifically is meant by "{term}"?',
                        "impact": "requirement_definition",
                        "priority": "high",
                    }
                )

        # Check for missing stakeholders
        if not any("user" in str(req).lower() for req in requirements):
            clarifications.append(
                {
                    "area": "Stakeholders",
                    "question": "Who are the primary users of this system?",
                    "impact": "user_requirements",
                    "priority": "critical",
                }
            )

        # Check for missing constraints
        constraint_keywords = ["budget", "timeline", "deadline", "resources"]
        if not any(keyword in task.lower() for keyword in constraint_keywords):
            clarifications.append(
                {
                    "area": "Constraints",
                    "question": "What are the time and budget constraints?",
                    "impact": "project_planning",
                    "priority": "high",
                }
            )

        # Check for missing success criteria
        clarifications.append(
            {
                "area": "Success Criteria",
                "question": "How will success be measured for this project?",
                "impact": "acceptance_criteria",
                "priority": "high",
            }
        )

        # Check for missing non-functional requirements
        if not any(req["type"] == "non_functional" for req in requirements):
            clarifications.append(
                {
                    "area": "Non-Functional Requirements",
                    "question": "What are the performance, security, and usability requirements?",
                    "impact": "system_quality",
                    "priority": "high",
                }
            )

        return clarifications

    def _create_user_stories(
        self, requirements: List[Dict[str, Any]], stakeholders: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Create user stories from requirements.

        Args:
            requirements: Elicited requirements
            stakeholders: List of stakeholders

        Returns:
            List of user stories
        """
        stories = []

        # Default stakeholders if none provided
        if not stakeholders:
            stakeholders = ["User", "Administrator", "System"]

        for req in requirements:
            if req["type"] == "functional":
                for stakeholder in stakeholders[:3]:  # Limit to 3 stakeholders
                    story = {
                        "id": f"US-{len(stories) + 1:03d}",
                        "requirement_id": req["id"],
                        "title": f"{stakeholder} {req['title']}",
                        "story": self.story_templates["standard"].format(
                            role=stakeholder.lower(),
                            action=req["title"].lower(),
                            benefit=req.get("description", "achieve goal"),
                        ),
                        "priority": req["priority"],
                        "points": self._estimate_story_points(req),
                        "status": "todo",
                    }
                    stories.append(story)

        return stories

    def _estimate_story_points(self, requirement: Dict[str, Any]) -> int:
        """
        Estimate story points for requirement.

        Args:
            requirement: Requirement dict

        Returns:
            Estimated story points
        """
        # Simple estimation based on priority and type
        base_points = 3

        if requirement.get("priority") == "critical":
            base_points += 5
        elif requirement.get("priority") == "high":
            base_points += 3
        elif requirement.get("priority") == "medium":
            base_points += 1

        if requirement.get("type") == "non_functional":
            base_points += 2

        return min(13, base_points)  # Cap at 13 (Fibonacci)

    def _define_acceptance_criteria(
        self, stories: List[Dict[str, Any]], requirements: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Define acceptance criteria for user stories.

        Args:
            stories: User stories
            requirements: Requirements

        Returns:
            List of acceptance criteria
        """
        criteria = []

        for story in stories[:10]:  # Limit to 10 stories
            # Create multiple acceptance criteria per story
            criteria.append(
                {
                    "id": f"AC-{len(criteria) + 1:03d}",
                    "story_id": story["id"],
                    "criteria": f"Given user is authenticated, "
                    f"When they {story['title'].lower()}, "
                    f"Then the system should respond successfully",
                    "type": "functional",
                    "testable": True,
                }
            )

            # Add validation criteria
            criteria.append(
                {
                    "id": f"AC-{len(criteria) + 1:03d}",
                    "story_id": story["id"],
                    "criteria": "System validates all inputs and provides clear error messages",
                    "type": "validation",
                    "testable": True,
                }
            )

            # Add performance criteria for high priority stories
            if story.get("priority") in ["critical", "high"]:
                criteria.append(
                    {
                        "id": f"AC-{len(criteria) + 1:03d}",
                        "story_id": story["id"],
                        "criteria": "Response time must be under 2 seconds",
                        "type": "performance",
                        "testable": True,
                    }
                )

        return criteria

    def _generate_specification(
        self,
        requirements: List[Dict[str, Any]],
        stories: List[Dict[str, Any]],
        criteria: List[Dict[str, Any]],
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate formal specification.

        Args:
            requirements: Requirements list
            stories: User stories
            criteria: Acceptance criteria
            constraints: Project constraints

        Returns:
            Formal specification
        """
        specification = {
            "version": "1.0.0",
            "status": "draft",
            "summary": {
                "total_requirements": len(requirements),
                "functional": len(
                    [r for r in requirements if r["type"] == "functional"]
                ),
                "non_functional": len(
                    [r for r in requirements if r["type"] == "non_functional"]
                ),
                "user_stories": len(stories),
                "acceptance_criteria": len(criteria),
            },
            "priorities": {
                "critical": len(
                    [r for r in requirements if r.get("priority") == "critical"]
                ),
                "high": len([r for r in requirements if r.get("priority") == "high"]),
                "medium": len(
                    [r for r in requirements if r.get("priority") == "medium"]
                ),
                "low": len([r for r in requirements if r.get("priority") == "low"]),
            },
            "scope": {"in_scope": [], "out_of_scope": [], "future_considerations": []},
            "constraints": constraints
            or {"budget": "TBD", "timeline": "TBD", "technology": "TBD"},
            "risks": [],
            "dependencies": [],
            "assumptions": [],
        }

        # Define scope based on requirements
        for req in requirements:
            if req.get("priority") in ["critical", "high"]:
                specification["scope"]["in_scope"].append(req["title"])
            elif req.get("priority") == "low":
                specification["scope"]["future_considerations"].append(req["title"])

        # Identify risks
        if specification["priorities"]["critical"] > 3:
            specification["risks"].append(
                {
                    "description": "High number of critical requirements",
                    "impact": "high",
                    "mitigation": "Prioritize and phase implementation",
                }
            )

        # Add assumptions
        specification["assumptions"] = [
            "Users have basic technical knowledge",
            "Internet connectivity is available",
            "Modern browsers are supported",
        ]

        return specification

    def _generate_recommendations(
        self,
        requirements: List[Dict[str, Any]],
        clarifications: List[Dict[str, Any]],
        specification: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Generate recommendations.

        Args:
            requirements: Requirements list
            clarifications: Clarifications needed
            specification: Formal specification

        Returns:
            List of recommendations
        """
        recommendations = []

        # Clarification recommendations
        if len(clarifications) > 3:
            recommendations.append(
                {
                    "priority": "critical",
                    "category": "Requirements Clarity",
                    "recommendation": "Schedule stakeholder workshop to clarify requirements",
                    "benefit": "Reduce ambiguity and rework",
                }
            )

        # Prioritization recommendations
        if specification["priorities"]["critical"] > 5:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "Scope Management",
                    "recommendation": "Consider phased delivery approach",
                    "benefit": "Manage risk and deliver value incrementally",
                }
            )

        # Testing recommendations
        recommendations.append(
            {
                "priority": "high",
                "category": "Quality Assurance",
                "recommendation": "Create test cases from acceptance criteria early",
                "benefit": "Ensure requirements are testable and complete",
            }
        )

        # Documentation recommendations
        recommendations.append(
            {
                "priority": "medium",
                "category": "Documentation",
                "recommendation": "Maintain requirements traceability matrix",
                "benefit": "Track requirement implementation and testing",
            }
        )

        # Process recommendations
        if not specification.get("constraints"):
            recommendations.append(
                {
                    "priority": "high",
                    "category": "Planning",
                    "recommendation": "Define project constraints and success metrics",
                    "benefit": "Clear project boundaries and goals",
                }
            )

        return recommendations

    def _generate_requirements_report(
        self,
        task: str,
        requirements: List[Dict[str, Any]],
        clarifications: List[Dict[str, Any]],
        stories: List[Dict[str, Any]],
        criteria: List[Dict[str, Any]],
        specification: Dict[str, Any],
        recommendations: List[Dict[str, Any]],
    ) -> str:
        """
        Generate comprehensive requirements report.

        Args:
            task: Original task
            requirements: Requirements list
            clarifications: Clarifications needed
            stories: User stories
            criteria: Acceptance criteria
            specification: Formal specification
            recommendations: Recommendations

        Returns:
            Requirements analysis report
        """
        lines = []

        # Header
        lines.append("# Requirements Analysis Report\n")
        lines.append(f"**Task**: {task}\n")
        lines.append(f"**Version**: {specification['version']}")
        lines.append(f"**Status**: {specification['status'].title()}\n")

        # Executive Summary
        lines.append("## Executive Summary\n")
        summary = specification["summary"]
        lines.append(f"- **Total Requirements**: {summary['total_requirements']}")
        lines.append(f"- **Functional**: {summary['functional']}")
        lines.append(f"- **Non-Functional**: {summary['non_functional']}")
        lines.append(f"- **User Stories**: {summary['user_stories']}")
        lines.append(f"- **Acceptance Criteria**: {summary['acceptance_criteria']}")

        # Requirements
        lines.append("\n## Requirements\n")
        for req_type in ["functional", "non_functional", "technical", "user"]:
            type_reqs = [r for r in requirements if r["type"] == req_type]
            if type_reqs:
                lines.append(f"\n### {req_type.replace('_', ' ').title()} Requirements")
                for req in type_reqs[:5]:  # Limit to 5 per type
                    priority_emoji = {
                        "critical": "🔴",
                        "high": "🟡",
                        "medium": "🟢",
                        "low": "⚪",
                    }.get(req["priority"], "⚪")
                    lines.append(f"{priority_emoji} **{req['id']}**: {req['title']}")
                    lines.append(f"   - {req['description']}")

        # Clarifications Needed
        if clarifications:
            lines.append("\n## Clarifications Required\n")
            for clarification in clarifications[:5]:
                priority_emoji = {"critical": "🚨", "high": "⚠️", "medium": "ℹ️"}.get(
                    clarification["priority"], "❓"
                )
                lines.append(f"{priority_emoji} **{clarification['area']}**")
                lines.append(f"   - Question: {clarification['question']}")
                lines.append(
                    f"   - Impact: {clarification['impact'].replace('_', ' ').title()}"
                )

        # User Stories
        if stories:
            lines.append("\n## User Stories\n")
            for story in stories[:5]:
                lines.append(f"**{story['id']}**: {story['story']}")
                lines.append(f"   - Priority: {story['priority'].title()}")
                lines.append(f"   - Story Points: {story['points']}")

        # Acceptance Criteria Sample
        if criteria:
            lines.append("\n## Acceptance Criteria (Sample)\n")
            for criterion in criteria[:5]:
                lines.append(f"- **{criterion['id']}**: {criterion['criteria']}")

        # Scope
        lines.append("\n## Scope Definition\n")
        scope = specification["scope"]
        if scope["in_scope"]:
            lines.append("### In Scope")
            for item in scope["in_scope"][:5]:
                lines.append(f"- ✅ {item}")

        if scope["out_of_scope"]:
            lines.append("\n### Out of Scope")
            for item in scope["out_of_scope"][:5]:
                lines.append(f"- ❌ {item}")

        if scope["future_considerations"]:
            lines.append("\n### Future Considerations")
            for item in scope["future_considerations"][:5]:
                lines.append(f"- 🔮 {item}")

        # Priorities
        lines.append("\n## Priority Distribution\n")
        priorities = specification["priorities"]
        lines.append(f"- 🔴 Critical: {priorities['critical']}")
        lines.append(f"- 🟡 High: {priorities['high']}")
        lines.append(f"- 🟢 Medium: {priorities['medium']}")
        lines.append(f"- ⚪ Low: {priorities['low']}")

        # Recommendations
        if recommendations:
            lines.append("\n## Recommendations\n")
            for rec in recommendations:
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

        # Next Steps
        lines.append("\n## Next Steps\n")
        lines.append("1. Review and validate requirements with stakeholders")
        lines.append("2. Address critical clarifications")
        lines.append("3. Prioritize user stories for first sprint")
        lines.append("4. Create detailed technical specifications")
        lines.append("5. Develop test cases from acceptance criteria")
        lines.append("6. Establish requirements baseline")

        return "\n".join(lines)
