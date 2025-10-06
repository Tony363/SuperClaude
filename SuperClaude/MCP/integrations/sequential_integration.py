"""
Sequential MCP Integration for SuperClaude Framework.

Provides complex analysis orchestration and systematic problem solving.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class AnalysisType(Enum):
    """Types of sequential analysis."""
    ROOT_CAUSE = "root_cause"
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"
    SECURITY = "security"
    DEBUGGING = "debugging"
    DESIGN = "design"


@dataclass
class AnalysisStep:
    """Single step in sequential analysis."""
    step_number: int
    description: str
    hypothesis: Optional[str] = None
    evidence: List[str] = field(default_factory=list)
    conclusion: Optional[str] = None
    confidence: float = 0.0
    next_steps: List[str] = field(default_factory=list)


@dataclass
class SequentialAnalysis:
    """Complete sequential analysis result."""
    analysis_type: AnalysisType
    problem_statement: str
    steps: List[AnalysisStep]
    final_conclusion: str
    recommendations: List[str]
    confidence_score: float
    total_steps: int
    execution_time: float


class SequentialIntegration:
    """
    Integration with Sequential MCP for complex analysis.

    Features:
    - Multi-step reasoning orchestration
    - Hypothesis testing and validation
    - Evidence gathering and synthesis
    - Cross-domain problem analysis
    - Systematic decomposition
    """

    MAX_STEPS = 20
    MIN_CONFIDENCE = 0.7

    def __init__(self, mcp_client=None):
        """
        Initialize Sequential integration.

        Args:
            mcp_client: Optional MCP client for Sequential server
        """
        self.mcp_client = mcp_client
        self.analysis_cache = {}
        self.step_templates = self._load_step_templates()

    def _load_step_templates(self) -> Dict[AnalysisType, List[str]]:
        """Load analysis step templates for different types."""
        return {
            AnalysisType.ROOT_CAUSE: [
                "Identify symptoms and immediate observations",
                "Gather system state and context",
                "Form initial hypotheses",
                "Test each hypothesis systematically",
                "Identify root cause with evidence",
                "Validate root cause",
                "Propose solution"
            ],
            AnalysisType.ARCHITECTURE: [
                "Analyze current system structure",
                "Identify components and dependencies",
                "Evaluate design patterns",
                "Assess scalability factors",
                "Review security considerations",
                "Identify improvement opportunities",
                "Propose architecture changes"
            ],
            AnalysisType.PERFORMANCE: [
                "Profile current performance metrics",
                "Identify bottlenecks",
                "Analyze resource utilization",
                "Review algorithmic complexity",
                "Test optimization hypotheses",
                "Validate improvements",
                "Document performance gains"
            ],
            AnalysisType.SECURITY: [
                "Identify attack surface",
                "Review authentication/authorization",
                "Analyze data flow and boundaries",
                "Check for common vulnerabilities",
                "Assess encryption and secrets",
                "Review access controls",
                "Propose security enhancements"
            ],
            AnalysisType.DEBUGGING: [
                "Reproduce the issue",
                "Isolate problem scope",
                "Trace execution flow",
                "Examine state changes",
                "Identify anomalies",
                "Locate root cause",
                "Implement and verify fix"
            ],
            AnalysisType.DESIGN: [
                "Understand requirements",
                "Analyze constraints",
                "Explore design alternatives",
                "Evaluate trade-offs",
                "Select optimal approach",
                "Detail implementation plan",
                "Define success metrics"
            ]
        }

    async def analyze(self,
                      problem: str,
                      analysis_type: AnalysisType,
                      context: Optional[Dict[str, Any]] = None,
                      max_steps: Optional[int] = None) -> SequentialAnalysis:
        """
        Perform sequential analysis on a problem.

        Args:
            problem: Problem statement to analyze
            analysis_type: Type of analysis to perform
            context: Additional context for analysis
            max_steps: Maximum steps (defaults to MAX_STEPS)

        Returns:
            SequentialAnalysis with complete results
        """
        start_time = datetime.now()
        max_steps = min(max_steps or self.MAX_STEPS, self.MAX_STEPS)

        # Check cache
        cache_key = f"{analysis_type.value}:{problem[:100]}"
        if cache_key in self.analysis_cache:
            logger.debug(f"Returning cached analysis for {cache_key}")
            return self.analysis_cache[cache_key]

        # Get step template
        template_steps = self.step_templates.get(analysis_type, [])

        # Execute analysis steps
        steps = []
        current_confidence = 0.0

        for i, step_desc in enumerate(template_steps[:max_steps], 1):
            step = await self._execute_step(
                step_number=i,
                description=step_desc,
                problem=problem,
                previous_steps=steps,
                context=context
            )
            steps.append(step)

            # Update confidence
            current_confidence = max(current_confidence, step.confidence)

            # Early termination if high confidence reached
            if current_confidence >= self.MIN_CONFIDENCE and i >= 3:
                logger.info(f"High confidence ({current_confidence:.2f}) reached at step {i}")
                break

        # Generate final conclusion
        final_conclusion = self._synthesize_conclusion(steps, problem)

        # Generate recommendations
        recommendations = self._generate_recommendations(steps, analysis_type)

        # Calculate execution time
        execution_time = (datetime.now() - start_time).total_seconds()

        # Create analysis result
        analysis = SequentialAnalysis(
            analysis_type=analysis_type,
            problem_statement=problem,
            steps=steps,
            final_conclusion=final_conclusion,
            recommendations=recommendations,
            confidence_score=current_confidence,
            total_steps=len(steps),
            execution_time=execution_time
        )

        # Cache result
        self.analysis_cache[cache_key] = analysis

        return analysis

    async def _execute_step(self,
                            step_number: int,
                            description: str,
                            problem: str,
                            previous_steps: List[AnalysisStep],
                            context: Optional[Dict[str, Any]]) -> AnalysisStep:
        """
        Execute a single analysis step.

        Args:
            step_number: Current step number
            description: Step description
            problem: Original problem
            previous_steps: Previously executed steps
            context: Additional context

        Returns:
            Completed AnalysisStep
        """
        # Build step context
        step_context = {
            'problem': problem,
            'step_description': description,
            'previous_conclusions': [s.conclusion for s in previous_steps if s.conclusion],
            'context': context or {}
        }

        # Execute step (would call actual MCP server in production)
        if self.mcp_client:
            # Real MCP execution
            result = await self.mcp_client.execute_step(step_context)
            hypothesis = result.get('hypothesis')
            evidence = result.get('evidence', [])
            conclusion = result.get('conclusion')
            confidence = result.get('confidence', 0.5)
            next_steps = result.get('next_steps', [])
        else:
            # Mock execution for testing
            hypothesis = f"Hypothesis for {description}"
            evidence = [f"Evidence point {i+1}" for i in range(2)]
            conclusion = f"Conclusion from {description}"
            confidence = min(0.5 + step_number * 0.1, 0.95)
            next_steps = [f"Next step {i+1}" for i in range(2)] if step_number < 5 else []

        return AnalysisStep(
            step_number=step_number,
            description=description,
            hypothesis=hypothesis,
            evidence=evidence,
            conclusion=conclusion,
            confidence=confidence,
            next_steps=next_steps
        )

    def _synthesize_conclusion(self, steps: List[AnalysisStep], problem: str) -> str:
        """
        Synthesize final conclusion from all steps.

        Args:
            steps: All executed steps
            problem: Original problem

        Returns:
            Synthesized conclusion
        """
        if not steps:
            return "No analysis steps completed"

        # Gather all conclusions
        conclusions = [s.conclusion for s in steps if s.conclusion]

        # Find highest confidence step
        highest_confidence_step = max(steps, key=lambda s: s.confidence)

        # Synthesize
        synthesis = f"After {len(steps)} steps of analysis for '{problem[:100]}...', "
        synthesis += f"the investigation reached {highest_confidence_step.confidence:.0%} confidence. "

        if highest_confidence_step.conclusion:
            synthesis += f"Key finding: {highest_confidence_step.conclusion}"

        return synthesis

    def _generate_recommendations(self,
                                   steps: List[AnalysisStep],
                                   analysis_type: AnalysisType) -> List[str]:
        """
        Generate recommendations based on analysis.

        Args:
            steps: Completed analysis steps
            analysis_type: Type of analysis performed

        Returns:
            List of recommendations
        """
        recommendations = []

        # Gather all next steps
        all_next_steps = []
        for step in steps:
            all_next_steps.extend(step.next_steps)

        # Type-specific recommendations
        if analysis_type == AnalysisType.ROOT_CAUSE:
            recommendations.append("Implement identified fix with proper testing")
            recommendations.append("Add monitoring to prevent recurrence")
            recommendations.append("Document root cause for knowledge base")

        elif analysis_type == AnalysisType.ARCHITECTURE:
            recommendations.append("Prioritize architectural improvements by impact")
            recommendations.append("Create migration plan for proposed changes")
            recommendations.append("Update documentation to reflect new architecture")

        elif analysis_type == AnalysisType.PERFORMANCE:
            recommendations.append("Implement optimizations in order of impact")
            recommendations.append("Establish performance benchmarks")
            recommendations.append("Set up continuous performance monitoring")

        elif analysis_type == AnalysisType.SECURITY:
            recommendations.append("Address critical vulnerabilities immediately")
            recommendations.append("Implement security monitoring and alerting")
            recommendations.append("Schedule regular security audits")

        elif analysis_type == AnalysisType.DEBUGGING:
            recommendations.append("Add regression tests for the bug")
            recommendations.append("Review similar code for the same issue")
            recommendations.append("Update error handling and logging")

        elif analysis_type == AnalysisType.DESIGN:
            recommendations.append("Create proof of concept for validation")
            recommendations.append("Get stakeholder feedback on design")
            recommendations.append("Plan incremental implementation approach")

        # Add unique next steps as recommendations
        unique_next_steps = list(set(all_next_steps))[:3]
        recommendations.extend(unique_next_steps)

        return recommendations[:5]  # Limit to 5 recommendations

    def validate_hypothesis(self,
                            hypothesis: str,
                            evidence: List[str]) -> Tuple[bool, float]:
        """
        Validate a hypothesis against evidence.

        Args:
            hypothesis: Hypothesis to validate
            evidence: Supporting evidence

        Returns:
            Tuple of (is_valid, confidence)
        """
        if not evidence:
            return False, 0.0

        # Simple validation based on evidence count
        evidence_score = min(len(evidence) / 5.0, 1.0)

        # Check for contradictions (simple keyword check)
        contradictions = sum(1 for e in evidence if 'not' in e.lower() or 'false' in e.lower())
        contradiction_penalty = contradictions * 0.2

        confidence = max(0.0, evidence_score - contradiction_penalty)
        is_valid = confidence >= 0.5

        return is_valid, confidence

    async def debug_problem(self,
                             error_message: str,
                             stack_trace: Optional[str] = None,
                             code_context: Optional[str] = None) -> SequentialAnalysis:
        """
        Specialized debugging analysis.

        Args:
            error_message: Error message to debug
            stack_trace: Optional stack trace
            code_context: Optional code context

        Returns:
            SequentialAnalysis for debugging
        """
        context = {
            'error_message': error_message,
            'stack_trace': stack_trace,
            'code_context': code_context
        }

        return await self.analyze(
            problem=f"Debug error: {error_message}",
            analysis_type=AnalysisType.DEBUGGING,
            context=context
        )

    async def analyze_architecture(self,
                                    system_description: str,
                                    components: List[str],
                                    requirements: Optional[List[str]] = None) -> SequentialAnalysis:
        """
        Analyze system architecture.

        Args:
            system_description: Description of the system
            components: List of system components
            requirements: Optional requirements to consider

        Returns:
            SequentialAnalysis for architecture
        """
        context = {
            'components': components,
            'requirements': requirements or []
        }

        return await self.analyze(
            problem=f"Analyze architecture: {system_description}",
            analysis_type=AnalysisType.ARCHITECTURE,
            context=context
        )

    def export_analysis(self, analysis: SequentialAnalysis) -> str:
        """
        Export analysis to markdown format.

        Args:
            analysis: Analysis to export

        Returns:
            Markdown formatted string
        """
        lines = [
            f"# Sequential Analysis: {analysis.analysis_type.value.replace('_', ' ').title()}",
            "",
            f"**Problem**: {analysis.problem_statement}",
            f"**Confidence**: {analysis.confidence_score:.0%}",
            f"**Steps**: {analysis.total_steps}",
            f"**Time**: {analysis.execution_time:.2f}s",
            "",
            "## Analysis Steps",
            ""
        ]

        for step in analysis.steps:
            lines.append(f"### Step {step.step_number}: {step.description}")
            if step.hypothesis:
                lines.append(f"**Hypothesis**: {step.hypothesis}")
            if step.evidence:
                lines.append("**Evidence**:")
                for evidence in step.evidence:
                    lines.append(f"- {evidence}")
            if step.conclusion:
                lines.append(f"**Conclusion**: {step.conclusion}")
            lines.append(f"**Confidence**: {step.confidence:.0%}")
            lines.append("")

        lines.extend([
            "## Final Conclusion",
            analysis.final_conclusion,
            "",
            "## Recommendations"
        ])

        for i, rec in enumerate(analysis.recommendations, 1):
            lines.append(f"{i}. {rec}")

        return "\n".join(lines)