"""
Strategist-class Fullstack Developer agent.

Promotes the high-traffic ``fullstack-developer`` persona from a generic
markdown wrapper into a Python-backed strategist that applies coordinated
frontend/backend reasoning, validation advice, and remediation loops.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ..heuristic_markdown import HeuristicMarkdownAgent


@dataclass
class _SurfaceAnalysis:
    """Lightweight inspection of the current repository context."""

    frontend_files: List[str] = field(default_factory=list)
    backend_files: List[str] = field(default_factory=list)
    shared_files: List[str] = field(default_factory=list)
    tests: List[str] = field(default_factory=list)


class FullstackDeveloper(HeuristicMarkdownAgent):
    """Hybrid strategist that balances frontend and backend changes."""

    STRATEGIST_TIER = True

    FRONTEND_KEYWORDS = [
        "react",
        "next",
        "component",
        "ui",
        "ux",
        "css",
        "tailwind",
        "layout",
    ]
    BACKEND_KEYWORDS = [
        "api",
        "endpoint",
        "service",
        "database",
        "model",
        "schema",
        "controller",
    ]

    def __init__(self, config: Dict[str, Any]):
        defaults = {
            "name": "fullstack-developer",
            "description": (
                "Design backend/frontend changes in tandem, ensuring contracts, "
                "tests, and deployment hooks stay in sync."
            ),
            "category": "core-development",
        }
        merged = {**defaults, **config}
        super().__init__(merged)

        self.frontend_patterns = (".tsx", ".ts", ".js", ".jsx", ".css", ".scss")
        self.backend_patterns = (".py", ".go", ".rs", ".java", ".kt", ".rb", ".cs")
        self.contract_patterns = ("schema", "interface", "type", "dto")

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #

    def validate(self, context: Dict[str, Any]) -> bool:
        """Prefer tasks that touch both front and backend concerns."""
        task = str(context.get("task", "")).lower()
        if not task:
            return False
        frontend = any(keyword in task for keyword in self.FRONTEND_KEYWORDS)
        backend = any(keyword in task for keyword in self.BACKEND_KEYWORDS)
        if frontend and backend:
            return True

        files = context.get("files") or []
        if not isinstance(files, list):
            files = []
        frontend_hits = sum(
            1 for path in files if any(path.endswith(ext) for ext in self.frontend_patterns)
        )
        backend_hits = sum(
            1 for path in files if any(path.endswith(ext) for ext in self.backend_patterns)
        )
        return frontend_hits > 0 and backend_hits > 0

    # ------------------------------------------------------------------ #
    # Execution
    # ------------------------------------------------------------------ #

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the heuristic markdown execution, then augment with additional
        strategy layers that align frontend/backend changes.
        """
        result = super().execute(context)
        analysis = self._inspect_context(context)

        strategy = {
            "backend": self._build_backend_strategy(context, analysis),
            "frontend": self._build_frontend_strategy(context, analysis),
            "contracts": self._build_contract_strategy(context, analysis),
            "testing": self._build_testing_strategy(context, analysis),
            "deployment": self._build_deployment_strategy(context, analysis),
        }

        result["fullstack_strategy"] = strategy

        remediation = self._derive_remediation_paths(result, strategy)
        if remediation:
            result["remediation_paths"] = remediation

        if result.get("status") == "plan-only":
            result.setdefault("warnings", []).append(
                "Strategist generated coordinated backend/frontend plan. "
                "Apply concrete diffs or rerun with live file targets to satisfy guardrails."
            )

        return result

    # ------------------------------------------------------------------ #
    # Strategy builders
    # ------------------------------------------------------------------ #

    def _inspect_context(self, context: Dict[str, Any]) -> _SurfaceAnalysis:
        files = context.get("files") or []
        if not isinstance(files, list):
            files = []

        frontend: List[str] = []
        backend: List[str] = []
        shared: List[str] = []
        tests: List[str] = []

        for raw_path in files:
            path = str(raw_path)
            lowered = path.lower()
            if any(lowered.endswith(ext) for ext in self.frontend_patterns):
                frontend.append(path)
            if any(lowered.endswith(ext) for ext in self.backend_patterns):
                backend.append(path)
            if any(token in lowered for token in self.contract_patterns):
                shared.append(path)
            if "test" in lowered or lowered.endswith(("_spec.ts", "_spec.py")):
                tests.append(path)

        return _SurfaceAnalysis(
            frontend_files=frontend,
            backend_files=backend,
            shared_files=shared,
            tests=tests,
        )

    def _build_backend_strategy(
        self,
        context: Dict[str, Any],
        analysis: _SurfaceAnalysis,
    ) -> Dict[str, Any]:
        task = str(context.get("task", "")).strip()
        baseline = {
            "summary": "Design or adjust backend endpoints and domain logic.",
            "considerations": [],
            "suggested_files": analysis.backend_files[:5],
        }
        if "graphql" in task.lower():
            baseline["considerations"].append("Update schema resolvers and regenerate types.")
        if "fastapi" in task.lower():
            baseline["considerations"].append("Add pydantic models and route signature updates.")
        if not baseline["suggested_files"]:
            baseline["considerations"].append(
                "Identify the service layer or handler that owns the requested capability."
            )
        return baseline

    def _build_frontend_strategy(
        self,
        context: Dict[str, Any],
        analysis: _SurfaceAnalysis,
    ) -> Dict[str, Any]:
        task = str(context.get("task", "")).strip()
        baseline = {
            "summary": "Adjust UI components and state management to consume the backend updates.",
            "considerations": [],
            "suggested_files": analysis.frontend_files[:5],
        }
        if "accessibility" in task.lower():
            baseline["considerations"].append("Include axe checks and ARIA annotations.")
        if "react server component" in task.lower() or "rsc" in task.lower():
            baseline["considerations"].append("Validate server/client component split and data fetching.")
        if not baseline["suggested_files"]:
            baseline["considerations"].append(
                "Determine the entry component that renders the new capability."
            )
        return baseline

    def _build_contract_strategy(
        self,
        context: Dict[str, Any],
        analysis: _SurfaceAnalysis,
    ) -> Dict[str, Any]:
        task = str(context.get("task", "")).strip()
        contracts = {
            "summary": "Keep shared contracts (types, schemas) aligned between backend and frontend.",
            "actions": [],
            "files": analysis.shared_files[:5],
        }
        if "validation" in task.lower():
            contracts["actions"].append("Document validation requirements in shared DTOs.")
        if not contracts["files"]:
            contracts["actions"].append("Introduce a shared contract module for new responses.")
        return contracts

    def _build_testing_strategy(
        self,
        context: Dict[str, Any],
        analysis: _SurfaceAnalysis,
    ) -> Dict[str, Any]:
        tests = analysis.tests[:5]
        actions = [
            "Cover backend service changes with unit tests.",
            "Add integration test exercising the new contract.",
            "Update frontend tests (unit or Playwright) for user flows.",
        ]
        if not tests:
            actions.append("No existing tests detected; create new suites in backend and frontend directories.")
        return {
            "summary": "Ensure regressions are prevented across the stack.",
            "existing_tests": tests,
            "actions": actions,
        }

    def _build_deployment_strategy(
        self,
        context: Dict[str, Any],
        analysis: _SurfaceAnalysis,
    ) -> Dict[str, Any]:
        task = str(context.get("task", "")).lower()
        actions: List[str] = []
        if "feature flag" in task:
            actions.append("Add feature flag toggles and document rollout plan.")
        if any(token in task for token in ("docker", "container", "k8s", "helm")):
            actions.append("Update container image or Helm chart to include new service dependencies.")
        if not actions:
            actions.append("Review CI/CD workflow to ensure both backend and frontend build steps remain green.")
        return {
            "summary": "Confirm deployment/observability alignment.",
            "actions": actions,
        }

    # ------------------------------------------------------------------ #
    # Remediation
    # ------------------------------------------------------------------ #

    def _derive_remediation_paths(
        self,
        result: Dict[str, Any],
        strategy: Dict[str, Any],
    ) -> List[str]:
        remediation: List[str] = []
        if result.get("status") == "plan-only":
            remediation.append(
                "Switch to a strategist-tier agent (backend-architect + frontend-architect) "
                "if concrete repository diffs are required automatically."
            )
        static_validation = result.get("static_validation") or []
        if static_validation:
            remediation.append("Resolve static validation issues before re-running guardrails.")
        if strategy["testing"]["existing_tests"]:
            remediation.append("Update listed tests to reflect new behaviour.")
        else:
            remediation.append("Draft smoke tests covering the new end-to-end path.")
        return remediation
