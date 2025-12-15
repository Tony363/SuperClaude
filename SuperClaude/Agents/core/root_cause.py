"""
Root Cause Analyst Agent for SuperClaude Framework

This agent specializes in systematic investigation and debugging,
finding the underlying causes of issues through evidence-based analysis.
"""

import re
from typing import Any, Dict, List, Optional

from ..base import BaseAgent


class RootCauseAnalyst(BaseAgent):
    """
    Agent specialized in systematic problem investigation.

    Uses evidence-based analysis and hypothesis testing to identify
    root causes of issues, bugs, and system failures.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the root cause analyst.

        Args:
            config: Agent configuration
        """
        # Ensure proper configuration
        if "name" not in config:
            config["name"] = "root-cause-analyst"
        if "description" not in config:
            config["description"] = "Systematically investigate complex problems"
        if "category" not in config:
            config["category"] = "analysis"

        super().__init__(config)

        # Investigation state
        self.current_investigation = None
        self.hypotheses = []
        self.evidence = []

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute root cause analysis.

        Args:
            context: Execution context

        Returns:
            Analysis results with findings
        """
        result = {
            "success": False,
            "output": "",
            "actions_taken": [],
            "errors": [],
            "findings": {},
            "root_cause": None,
        }

        try:
            # Initialize if needed
            if not self._initialized:
                if not self.initialize():
                    result["errors"].append("Failed to initialize agent")
                    return result

            task = context.get("task", "")
            if not task:
                result["errors"].append("No issue to investigate")
                return result

            # Start investigation
            self.logger.info(f"Starting root cause analysis: {task[:100]}...")
            self._start_investigation(task)

            # Phase 1: Gather evidence
            evidence = self._gather_evidence(task, context)
            result["actions_taken"].append(
                f"Gathered {len(evidence)} pieces of evidence"
            )

            # Phase 2: Form hypotheses
            hypotheses = self._form_hypotheses(evidence)
            result["actions_taken"].append(f"Formed {len(hypotheses)} hypotheses")

            # Phase 3: Test hypotheses
            tested_hypotheses = self._test_hypotheses(hypotheses, evidence)
            result["actions_taken"].append("Tested hypotheses against evidence")

            # Phase 4: Identify root cause
            root_cause = self._identify_root_cause(tested_hypotheses)

            if root_cause:
                result["root_cause"] = root_cause
                result["actions_taken"].append("Identified root cause")
            else:
                result["actions_taken"].append(
                    "Root cause unclear - more investigation needed"
                )

            # Phase 5: Generate report
            report = self._generate_investigation_report(
                task, evidence, tested_hypotheses, root_cause
            )
            result["output"] = report

            # Store findings
            result["findings"] = {
                "evidence": evidence,
                "hypotheses": [h["description"] for h in tested_hypotheses],
                "root_cause": root_cause,
                "confidence": self._calculate_confidence(root_cause, tested_hypotheses),
            }

            result["success"] = True
            self.log_execution(context, result)

        except Exception as e:
            self.logger.error(f"Investigation failed: {e}")
            result["errors"].append(str(e))

        return result

    def validate(self, context: Dict[str, Any]) -> bool:
        """
        Check if this agent can handle the context.

        Args:
            context: Validation context

        Returns:
            True if context contains investigation-worthy task
        """
        task = context.get("task", "")

        # Check for investigation keywords
        investigation_keywords = [
            "debug",
            "investigate",
            "analyze",
            "root cause",
            "why",
            "issue",
            "problem",
            "error",
            "failure",
            "broken",
            "not working",
            "bug",
            "crash",
        ]

        task_lower = task.lower()
        return any(keyword in task_lower for keyword in investigation_keywords)

    def _start_investigation(self, issue: str):
        """
        Initialize a new investigation.

        Args:
            issue: Issue description
        """
        self.current_investigation = {"issue": issue, "started": True}
        self.hypotheses = []
        self.evidence = []
        self.logger.debug(f"Investigation started: {issue}")

    def _gather_evidence(
        self, issue: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Gather evidence related to the issue.

        Args:
            issue: Issue description
            context: Execution context

        Returns:
            List of evidence items
        """
        evidence = []

        # Extract symptoms from issue description
        symptoms = self._extract_symptoms(issue)
        for symptom in symptoms:
            evidence.append(
                {"type": "symptom", "description": symptom, "relevance": "high"}
            )

        # Check for error patterns
        error_patterns = self._find_error_patterns(issue)
        for pattern in error_patterns:
            evidence.append(
                {"type": "error_pattern", "description": pattern, "relevance": "high"}
            )

        # Context clues
        files = context.get("files", [])
        if files:
            evidence.append(
                {
                    "type": "context",
                    "description": f"Involves {len(files)} files",
                    "relevance": "medium",
                    "details": files[:5],  # First 5 files
                }
            )

        # Timing information
        if "when" in issue.lower():
            evidence.append(
                {
                    "type": "timing",
                    "description": "Issue has temporal aspect",
                    "relevance": "medium",
                }
            )

        self.evidence = evidence
        return evidence

    def _extract_symptoms(self, issue: str) -> List[str]:
        """
        Extract symptoms from issue description.

        Args:
            issue: Issue description

        Returns:
            List of symptoms
        """
        symptoms = []

        # Common symptom patterns
        patterns = [
            r"(?:fails?|failing) (?:to |when |at )?(\w+(?:\s+\w+)*)",
            r"(?:error|exception|crash)(?:s|es|ed)? (?:in|at|during) (\w+(?:\s+\w+)*)",
            r"(?:can\'t|cannot|unable to) (\w+(?:\s+\w+)*)",
            r"(\w+(?:\s+\w+)*) (?:not working|broken|failing)",
            r"(?:returns?|gives?|shows?) (?:wrong |incorrect |invalid )?(\w+(?:\s+\w+)*)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, issue, re.IGNORECASE)
            symptoms.extend(matches)

        return symptoms[:5]  # Limit to top 5 symptoms

    def _find_error_patterns(self, issue: str) -> List[str]:
        """
        Find error patterns in issue description.

        Args:
            issue: Issue description

        Returns:
            List of error patterns
        """
        patterns = []

        # Common error types
        error_types = {
            "null": "Null reference or undefined value",
            "timeout": "Operation timeout or deadlock",
            "permission": "Permission or authorization issue",
            "connection": "Network or connection problem",
            "memory": "Memory leak or allocation issue",
            "syntax": "Syntax or parsing error",
            "type": "Type mismatch or conversion error",
            "index": "Index out of bounds or array error",
            "file": "File I/O or path issue",
            "config": "Configuration or settings problem",
        }

        issue_lower = issue.lower()
        for key, description in error_types.items():
            if key in issue_lower:
                patterns.append(description)

        return patterns

    def _form_hypotheses(self, evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Form hypotheses based on evidence.

        Args:
            evidence: Collected evidence

        Returns:
            List of hypotheses
        """
        hypotheses = []

        # Analyze evidence patterns
        symptom_count = sum(1 for e in evidence if e["type"] == "symptom")
        error_count = sum(1 for e in evidence if e["type"] == "error_pattern")

        # Form hypotheses based on evidence
        if error_count > 0:
            # Error-based hypotheses
            for e in evidence:
                if e["type"] == "error_pattern":
                    hypotheses.append(
                        {
                            "description": f"Root cause: {e['description']}",
                            "confidence": 0.7,
                            "supporting_evidence": [e],
                        }
                    )

        if symptom_count > 0:
            # Symptom-based hypotheses
            symptoms = [e for e in evidence if e["type"] == "symptom"]
            if len(symptoms) > 2:
                hypotheses.append(
                    {
                        "description": "Multiple related failures suggest systemic issue",
                        "confidence": 0.6,
                        "supporting_evidence": symptoms,
                    }
                )

        # Default hypotheses if nothing specific found
        if not hypotheses:
            hypotheses.append(
                {
                    "description": "Configuration or environment issue",
                    "confidence": 0.3,
                    "supporting_evidence": evidence,
                }
            )

        self.hypotheses = hypotheses
        return hypotheses

    def _test_hypotheses(
        self, hypotheses: List[Dict[str, Any]], evidence: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Test hypotheses against evidence.

        Args:
            hypotheses: List of hypotheses
            evidence: Available evidence

        Returns:
            List of tested hypotheses with updated confidence
        """
        tested = []

        for hypothesis in hypotheses:
            # Count supporting vs contradicting evidence
            supporting = len(hypothesis.get("supporting_evidence", []))
            total_evidence = len(evidence)

            # Adjust confidence based on evidence ratio
            if total_evidence > 0:
                evidence_ratio = supporting / total_evidence
                hypothesis["confidence"] *= 1 + evidence_ratio
                hypothesis["confidence"] = min(hypothesis["confidence"], 0.95)

            tested.append(hypothesis)

        # Sort by confidence
        tested.sort(key=lambda h: h["confidence"], reverse=True)
        return tested

    def _identify_root_cause(self, hypotheses: List[Dict[str, Any]]) -> Optional[str]:
        """
        Identify most likely root cause.

        Args:
            hypotheses: Tested hypotheses

        Returns:
            Root cause description or None
        """
        if not hypotheses:
            return None

        # Take highest confidence hypothesis
        best = hypotheses[0]

        # Need minimum confidence threshold
        if best["confidence"] >= 0.5:
            return best["description"]

        return None

    def _calculate_confidence(
        self, root_cause: Optional[str], hypotheses: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate overall confidence in findings.

        Args:
            root_cause: Identified root cause
            hypotheses: All hypotheses

        Returns:
            Confidence score
        """
        if not root_cause or not hypotheses:
            return 0.0

        # Get confidence of root cause hypothesis
        for h in hypotheses:
            if h["description"] == root_cause:
                return h["confidence"]

        return 0.0

    def _generate_investigation_report(
        self,
        issue: str,
        evidence: List[Dict[str, Any]],
        hypotheses: List[Dict[str, Any]],
        root_cause: Optional[str],
    ) -> str:
        """
        Generate investigation report.

        Args:
            issue: Original issue
            evidence: Collected evidence
            hypotheses: Tested hypotheses
            root_cause: Identified root cause

        Returns:
            Report string
        """
        lines = []

        # Header
        lines.append("# Root Cause Analysis Report\n")
        lines.append(f"**Issue**: {issue}\n")

        # Evidence section
        lines.append("\n## Evidence Collected\n")
        for e in evidence[:5]:  # Top 5 evidence items
            lines.append(f"- **{e['type'].title()}**: {e['description']}")

        if len(evidence) > 5:
            lines.append(f"- *(and {len(evidence) - 5} more items)*")

        # Hypotheses section
        lines.append("\n## Hypotheses Tested\n")
        for i, h in enumerate(hypotheses[:3], 1):
            lines.append(f"{i}. {h['description']} (confidence: {h['confidence']:.1%})")

        # Root cause section
        lines.append("\n## Root Cause\n")
        if root_cause:
            confidence = self._calculate_confidence(root_cause, hypotheses)
            lines.append(f"**Identified**: {root_cause}")
            lines.append(f"**Confidence**: {confidence:.1%}")
        else:
            lines.append("*Unable to determine root cause with sufficient confidence.*")
            lines.append("*Additional investigation required.*")

        # Recommendations
        lines.append("\n## Recommendations\n")
        if root_cause:
            lines.append(f"1. Address the identified issue: {root_cause}")
            lines.append("2. Verify fix resolves all symptoms")
            lines.append("3. Add monitoring to prevent recurrence")
        else:
            lines.append("1. Gather more specific error logs")
            lines.append("2. Reproduce issue in controlled environment")
            lines.append("3. Perform systematic component isolation")

        return "\n".join(lines)
