"""
Heuristic-enhanced Markdown agent base classes.

These helpers extend ``GenericMarkdownAgent`` with lightweight validation,
synthetic diff inspection, and structured follow-up guidance so that
auto-generated extended personas provide more than a one-pass plan.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from .generic import GenericMarkdownAgent


@dataclass
class _StaticIssue:
    """Container describing quick static validation results."""

    path: str
    message: str
    severity: str = "warning"


class HeuristicMarkdownAgent(GenericMarkdownAgent):
    """
    Generic markdown agent with static validation, diff heuristics,
    and retry guidance hooks.
    """

    MAX_PLAN_RETRIES = 2

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Run the base markdown execution, then augment the result with
        lightweight heuristics to reduce plan-only fallbacks.
        """
        result = super().execute(context)

        # Apply heuristics after the base execution so we can reason about
        # synthesised changes and detected operations.
        static_issues = self._run_static_checks(context, result)
        retry_hint = self._maybe_request_retry(context, result, static_issues)
        follow_up = self._build_follow_up_actions(
            context, result, static_issues, retry_hint
        )

        if static_issues:
            warnings = self._ensure_list(result, "warnings")
            for issue in static_issues:
                warning = f"{issue.path}: {issue.message}"
                if warning not in warnings:
                    warnings.append(warning)
            result.setdefault(
                "static_validation",
                [
                    {
                        "path": issue.path,
                        "message": issue.message,
                        "severity": issue.severity,
                    }
                    for issue in static_issues
                ],
            )

        if retry_hint:
            details = self._ensure_dict(result, "retry_guidance")
            if retry_hint not in details.get("notes", []):
                details.setdefault("notes", []).append(retry_hint)

        if follow_up:
            result["follow_up_actions"] = follow_up

        return result

    # ------------------------------------------------------------------
    # Heuristic helpers
    # ------------------------------------------------------------------

    def _run_static_checks(
        self, context: dict[str, Any], result: dict[str, Any]
    ) -> list[_StaticIssue]:
        """
        Perform lightweight static validation on proposed changes.
        """
        issues: list[_StaticIssue] = []
        changes = self._collect_candidate_changes(context, result)

        for change in changes:
            path = change.get("path", "")
            content = change.get("content", "")
            if not path or not isinstance(content, str):
                continue

            if path.endswith(".py"):
                issues.extend(self._validate_python_snippet(path, content))
            elif path.endswith((".ts", ".tsx", ".js")):
                issues.extend(self._validate_ts_snippet(path, content))
            elif path.endswith(".md"):
                issues.extend(self._validate_markdown_snippet(path, content))

        return issues

    def _maybe_request_retry(
        self,
        context: dict[str, Any],
        result: dict[str, Any],
        static_issues: list[_StaticIssue],
    ) -> str | None:
        """
        Decide whether the agent should ask the coordinator for a retry.
        """
        status = result.get("status")
        if status == "executed":
            return None

        retry_count = int(context.get("retry_count", 0))
        if retry_count >= self.MAX_PLAN_RETRIES:
            return None

        missing_changes = status == "plan-only" and not result.get("actions_taken")
        static_failures = any(issue.severity == "error" for issue in static_issues)

        if missing_changes or static_failures:
            if static_failures:
                return (
                    "Static validation failed for generated changes; rerun with a "
                    "core strategist or adjust the prompt with concrete constraints."
                )

            return (
                "No concrete changes detected after plan synthesis; rerun with a "
                "strategist-tier persona or provide precise file targets."
            )

        return None

    def _build_follow_up_actions(
        self,
        context: dict[str, Any],
        result: dict[str, Any],
        static_issues: list[_StaticIssue],
        retry_hint: str | None,
    ) -> list[str]:
        """
        Build structured follow-up actions for operators.
        """
        follow_up: list[str] = []
        task = str(context.get("task", "")).strip()
        if retry_hint:
            follow_up.append(retry_hint)

        if static_issues:
            follow_up.append(
                "Resolve the static validation errors noted above before applying changes."
            )

        if result.get("status") == "plan-only":
            follow_up.append(
                "Translate the proposed plan into concrete repository edits; "
                "guardrails require real diffs before the command can succeed."
            )

        if task and "test" not in task.lower():
            follow_up.append(
                "Add or update automated tests that exercise the proposed changes."
            )

        return follow_up

    # ------------------------------------------------------------------
    # Language-specific heuristics
    # ------------------------------------------------------------------

    def _validate_python_snippet(self, path: str, content: str) -> list[_StaticIssue]:
        """Basic Python syntax validation."""
        issues: list[_StaticIssue] = []
        try:
            compile(content, path, "exec")
        except SyntaxError as exc:
            msg = f"Syntax error (line {exc.lineno}): {exc.msg}"
            issues.append(_StaticIssue(path=path, message=msg, severity="error"))
        return issues

    def _validate_ts_snippet(self, path: str, content: str) -> list[_StaticIssue]:
        """
        Simple TypeScript/JavaScript validation catching common mistakes like
        unmatched braces or missing exports.
        """
        issues: list[_StaticIssue] = []
        stack: list[str] = []
        pairs = {"{": "}", "(": ")", "[": "]"}
        opening = set(pairs.keys())
        closing = {v: k for k, v in pairs.items()}

        for idx, char in enumerate(content):
            if char in opening:
                stack.append(char)
            elif char in closing:
                if not stack or stack[-1] != closing[char]:
                    issues.append(
                        _StaticIssue(
                            path=path,
                            message=f"Unmatched '{char}' detected near char {idx}",
                            severity="error",
                        )
                    )
                    break
                stack.pop()

        if stack:
            issues.append(
                _StaticIssue(
                    path=path,
                    message="Unclosed braces detected in generated snippet",
                    severity="error",
                )
            )

        export_match = re.search(r"export\s+(class|function|const)\s+\w+", content)
        if "export" in content and not export_match:
            issues.append(
                _StaticIssue(
                    path=path,
                    message="`export` keyword present but no exportable symbol detected.",
                )
            )

        return issues

    def _validate_markdown_snippet(self, path: str, content: str) -> list[_StaticIssue]:
        """Ensure markdown headings progress sequentially."""
        issues: list[_StaticIssue] = []
        last_level = 1
        for lineno, line in enumerate(content.splitlines(), start=1):
            if line.startswith("#"):
                level = len(line.split(" ", 1)[0])
                if level - last_level > 1:
                    issues.append(
                        _StaticIssue(
                            path=path,
                            message=f"Heading level jumps from H{last_level} to H{level} at line {lineno}",
                        )
                    )
                last_level = level
        return issues

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _collect_candidate_changes(
        self, context: dict[str, Any], result: dict[str, Any]
    ) -> Iterable[dict[str, Any]]:
        """
        Determine candidate change dictionaries from context/result.
        """
        if isinstance(result.get("proposed_changes"), list):
            yield from result["proposed_changes"]  # type: ignore[arg-type]
        elif isinstance(context.get("proposed_changes"), list):
            yield from context["proposed_changes"]  # type: ignore[arg-type]

    def _ensure_list(self, result: dict[str, Any], key: str) -> list[Any]:
        """Ensure ``result[key]`` is a list and return it."""
        value = result.get(key)
        if isinstance(value, list):
            return value
        new_list: list[Any] = []
        result[key] = new_list
        return new_list

    def _ensure_dict(self, result: dict[str, Any], key: str) -> dict[str, Any]:
        """Ensure ``result[key]`` is a dict and return it."""
        value = result.get(key)
        if isinstance(value, dict):
            return value
        new_dict: dict[str, Any] = {}
        result[key] = new_dict
        return new_dict
