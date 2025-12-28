"""
Learning Guide Agent for SuperClaude Framework

This agent focuses on progressive skill development, providing layered
explanations, annotated examples, and practice exercises that reinforce
understanding for different learning styles.
"""

from textwrap import indent
from typing import Any

from ..base import BaseAgent


class LearningGuide(BaseAgent):
    """
    Agent specialized in teaching programming concepts through
    progressive explanations and guided practice.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the learning guide agent with sensible defaults.

        Args:
            config: Agent configuration loaded from markdown metadata.
        """
        if "name" not in config:
            config["name"] = "learning-guide"
        if "description" not in config:
            config["description"] = (
                "Teach programming concepts with progressive learning paths "
                "and practical exercises"
            )
        if "category" not in config:
            config["category"] = "communication"

        super().__init__(config)

        self.learning_levels: dict[str, dict[str, Any]] = {}
        self.explanation_styles: dict[str, str] = {}
        self.practice_templates: dict[str, list[str]] = {}

    def _setup(self):
        """Configure learning strategies and practice templates."""
        self.learning_levels = {
            "beginner": {
                "focus": "Foundational concepts and vocabulary",
                "strategies": [
                    "Define terminology before using it",
                    "Use analogies and visuals to ground ideas",
                    "Limit cognitive load to a single idea per step",
                ],
            },
            "intermediate": {
                "focus": "Applied understanding and pattern recognition",
                "strategies": [
                    "Connect new ideas to familiar patterns",
                    "Compare alternative approaches with trade-offs",
                    "Highlight common pitfalls and debugging cues",
                ],
            },
            "advanced": {
                "focus": "Systems thinking and optimization",
                "strategies": [
                    "Expose underlying theory and implementation details",
                    "Discuss performance, scaling, and maintainability",
                    "Encourage experimentation with variations",
                ],
            },
        }

        self.explanation_styles = {
            "concept": "High-level overview that frames why the concept matters.",
            "mechanics": "Step-by-step breakdown of how the concept works.",
            "example": "Annotated example that demonstrates the idea in action.",
            "practice": "Exercises that reinforce the concept through doing.",
        }

        self.practice_templates = {
            "beginner": [
                "Re-state the core concept in your own words.",
                "Identify where this concept appears in day-to-day development.",
                "Modify a provided snippet to change a single behaviour.",
            ],
            "intermediate": [
                "Implement a small feature that relies on the concept.",
                "Spot and fix an intentional bug related to the concept.",
                "Refactor an example to improve clarity or performance.",
            ],
            "advanced": [
                "Design an alternative implementation and compare trade-offs.",
                "Stress-test the concept with edge cases or performance inputs.",
                "Document team guidelines that capture best practices.",
            ],
        }

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Build a progressive learning package for the requested concept.

        Returns a dictionary describing the generated learning materials.
        """
        result = {
            "success": False,
            "output": "",
            "actions_taken": [],
            "errors": [],
            "skill_level": None,
            "concepts_identified": [],
        }

        try:
            if not self._initialized and not self.initialize():
                result["errors"].append("Failed to initialize learning guide")
                return result

            topic = (
                context.get("concept") or context.get("topic") or context.get("task")
            )
            if not topic:
                result["errors"].append(
                    "No concept or topic supplied for learning guidance"
                )
                return result

            skill_level, indicators = self._assess_skill_level(context)
            result["skill_level"] = skill_level
            result["actions_taken"].append(
                f"Assessed learner level: {skill_level} ({', '.join(indicators)})"
            )

            key_concepts = self._extract_key_concepts(topic, context)
            result["concepts_identified"] = key_concepts
            result["actions_taken"].append(
                f"Identified {len(key_concepts)} key concept areas"
            )

            explanation = self._build_explanation(
                topic, key_concepts, skill_level, context
            )
            result["actions_taken"].append("Generated layered explanation")

            examples = self._create_examples(topic, context, skill_level)
            if examples:
                result["actions_taken"].append(
                    f"Prepared {len(examples)} worked examples"
                )

            practice = self._design_practice(topic, skill_level, context)
            result["actions_taken"].append(
                f"Created {len(practice)} practice activities"
            )

            resources = self._recommend_resources(topic, skill_level, context)
            if resources:
                result["actions_taken"].append("Suggested supplemental resources")

            result["output"] = self._format_learning_package(
                topic=topic,
                skill_level=skill_level,
                explanation=explanation,
                examples=examples,
                practice=practice,
                resources=resources,
            )

            result["success"] = True
            self.log_execution(context, result)

        except Exception as exc:
            self.logger.error(f"Learning guidance failed: {exc}")
            result["errors"].append(str(exc))

        return result

    def validate(self, context: dict[str, Any]) -> bool:
        """
        Determine if this agent is an appropriate match for the context.
        """
        task = (context.get("task") or context.get("concept") or "").lower()

        keywords = [
            "learn",
            "tutorial",
            "explain",
            "guide",
            "teaching",
            "walkthrough",
            "education",
            "how does",
            "why does",
            "step by step",
        ]
        return any(keyword in task for keyword in keywords)

    def _assess_skill_level(self, context: dict[str, Any]) -> tuple[str, list[str]]:
        """
        Infer skill level from context hints.
        """
        explicit = context.get("skill_level") or context.get("experience")
        if isinstance(explicit, str):
            normalized = explicit.strip().lower()
            if normalized in self.learning_levels:
                return normalized, ["explicit request"]

        indicators: list[str] = []
        task = (context.get("task") or "").lower()

        if any(
            word in task
            for word in ["introduction", "basics", "fundamentals", "explain like"]
        ):
            indicators.append("introductory phrasing")
            return "beginner", indicators
        if any(
            word in task for word in ["optimize", "scale", "architecture", "trade-off"]
        ):
            indicators.append("advanced terminology")
            return "advanced", indicators
        if any(word in task for word in ["walkthrough", "step", "explain"]):
            indicators.append("explanation request")

        return "intermediate", indicators or ["default level"]

    def _extract_key_concepts(self, topic: str, context: dict[str, Any]) -> list[str]:
        """
        Identify sub-concepts to cover in the learning path.
        """
        explicit = context.get("focus_areas")
        if isinstance(explicit, list) and explicit:
            return [str(item) for item in explicit]

        supplemental = context.get("related_topics", [])
        if isinstance(supplemental, list) and supplemental:
            return [topic] + [str(item) for item in supplemental]

        return [topic]

    def _build_explanation(
        self, topic: str, concepts: list[str], level: str, context: dict[str, Any]
    ) -> dict[str, str]:
        """
        Create layered explanation notes keyed by explanation style.
        """
        notes: dict[str, str] = {}
        audience = context.get("audience", "engineer")

        concept_summary = (
            f"{topic} for {audience}s focuses on {', '.join(concepts[:3])}."
            if len(concepts) > 1
            else f"{topic} is the core concept under review."
        )
        notes["concept"] = concept_summary

        mechanics_detail = (
            "Break the concept into discrete steps:\n"
            "- Understand the problem the concept solves\n"
            "- Follow the typical workflow or algorithm involved\n"
            "- Connect each step to observable outcomes in the code"
        )
        if level == "advanced":
            mechanics_detail += (
                "\n- Inspect underlying implementation details and performance costs"
            )
        notes["mechanics"] = mechanics_detail

        notes["example"] = (
            "Develop one canonical example that walks through the concept, "
            "annotating *why* each step matters and what to watch for."
        )

        strategy = self.learning_levels[level]["strategies"]
        notes["practice"] = "Learning strategies:\n" + "\n".join(
            f"- {item}" for item in strategy
        )

        return notes

    def _create_examples(
        self, topic: str, context: dict[str, Any], level: str
    ) -> list[dict[str, Any]]:
        """
        Generate example scaffolds tailored to the learner level.
        """
        code = context.get("code") or context.get("snippet")
        language = context.get("language", "python")

        examples: list[dict[str, Any]] = []
        if code:
            examples.append(
                {
                    "title": f"Walkthrough: {topic} in practice",
                    "language": language,
                    "explanation": "Highlight the intent of each significant line or block.",
                    "code": code,
                }
            )

        examples.append(
            {
                "title": "Concept checkpoint",
                "language": language,
                "explanation": (
                    "Introduce a short example that intentionally leaves a gap "
                    "for the learner to reason about. Provide hints instead of the final answer."
                ),
                "code": None,
            }
        )

        if level == "advanced":
            examples.append(
                {
                    "title": "Variant exploration",
                    "language": language,
                    "explanation": (
                        "Compare two implementations and discuss trade-offs involving readability, "
                        "performance, and maintainability."
                    ),
                    "code": None,
                }
            )

        return examples

    def _design_practice(
        self, topic: str, level: str, context: dict[str, Any]
    ) -> list[str]:
        """
        Provide practice prompts that reinforce the concept.
        """
        prompts = list(self.practice_templates[level])

        if context.get("project_context"):
            prompts.append(
                "Apply the concept to the active project: identify one concrete task where it fits "
                "and outline the steps you would take."
            )

        prompts.append(
            f"Reflect on the biggest insight you gained about {topic} and how it changes your approach."
        )
        return prompts

    def _recommend_resources(
        self, topic: str, level: str, context: dict[str, Any]
    ) -> list[str]:
        """
        Suggest follow-up resources if hints are supplied.
        """
        provided = context.get("resources")
        if isinstance(provided, list) and provided:
            return provided

        resource_bank = {
            "beginner": [
                "Official getting started guide or tutorial",
                "Interactive sandbox demonstrating the concept",
                "Glossary of key terms encountered in this lesson",
            ],
            "intermediate": [
                "Depth article or engineering blog post on the concept",
                "Real-world case study demonstrating successful application",
                "Practice repository with incremental challenges",
            ],
            "advanced": [
                "Academic or standards reference detailing theory",
                "Performance benchmarking guides and tooling",
                "Design review checklist tailored to the concept",
            ],
        }
        return resource_bank[level]

    def _format_learning_package(
        self,
        topic: str,
        skill_level: str,
        explanation: dict[str, str],
        examples: list[dict[str, Any]],
        practice: list[str],
        resources: list[str],
    ) -> str:
        """
        Assemble the final markdown package for delivery.
        """
        sections: list[str] = []

        sections.append(f"# Learning Guide: {topic.title()}")
        sections.append(f"**Skill Level**: {skill_level.title()}")

        sections.append("## Concept Overview")
        overview = [
            f"**Concept focus**: {explanation['concept']}",
            f"**Practice focus**: {self.learning_levels[skill_level]['focus']}",
        ]
        sections.append("\n".join(overview))

        sections.append("## How It Works")
        sections.append(explanation["mechanics"])

        sections.append("## Worked Examples")
        example_lines: list[str] = []
        for item in examples:
            example_lines.append(f"- **{item['title']}** – {item['explanation']}")
            if item["code"]:
                code_block = indent(item["code"].strip(), "    ")
                example_lines.append(
                    "    ```{lang}\n{code}\n    ```".format(
                        lang=item.get("language", "text"), code=code_block.strip()
                    )
                )
        sections.append("\n".join(example_lines))

        sections.append("## Practice Activities")
        sections.append("\n".join(f"- {prompt}" for prompt in practice))

        sections.append("## Reinforcement Strategies")
        sections.append(explanation["practice"])

        sections.append("## Suggested Resources")
        sections.append("\n".join(f"- {resource}" for resource in resources))

        return "\n\n".join(sections)
