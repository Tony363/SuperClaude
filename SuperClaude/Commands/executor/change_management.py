"""
Change management utilities for the SuperClaude Command Executor.

Provides functions for deriving change plans, applying changes,
generating stubs, and managing implementation artifacts.
"""

import json
import logging
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .utils import deduplicate, slugify

logger = logging.getLogger(__name__)


def derive_change_plan(
    agent_outputs: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Build a change plan from agent outputs."""
    plan: List[Dict[str, Any]] = []

    for agent_output in agent_outputs.values():
        for key in (
            "proposed_changes",
            "generated_files",
            "file_updates",
            "changes",
        ):
            plan.extend(extract_agent_change_specs(agent_output.get(key)))

    return plan


def extract_agent_change_specs(candidate: Any) -> List[Dict[str, Any]]:
    """Normalise agent-proposed change structures into change descriptors."""
    proposals: List[Dict[str, Any]] = []
    if candidate is None:
        return proposals

    if isinstance(candidate, dict):
        if "path" in candidate and "content" in candidate:
            proposals.append(normalize_change_descriptor(candidate))
        else:
            for key, value in candidate.items():
                if isinstance(value, dict) and "content" in value:
                    descriptor = dict(value)
                    descriptor.setdefault("path", key)
                    proposals.append(normalize_change_descriptor(descriptor))
                else:
                    proposals.append(
                        normalize_change_descriptor(
                            {
                                "path": str(key),
                                "content": value,
                                "mode": "replace",
                            }
                        )
                    )
    elif isinstance(candidate, (list, tuple, set)):
        for item in candidate:
            proposals.extend(extract_agent_change_specs(item))

    return proposals


def normalize_change_descriptor(descriptor: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure change descriptors retain metadata flags like auto_stub."""
    return {
        "path": str(descriptor.get("path")),
        "content": descriptor.get("content", ""),
        "mode": descriptor.get("mode", "replace"),
    }


def assess_stub_requirement(
    applied_changes: List[str],
    agent_result: Dict[str, Any],
    requires_evidence: bool,
    *,
    default_reason: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """
    Decide whether to emit an auto-generated stub or queue a follow-up action.

    Returns:
        Tuple of (action, reason) where action is 'stub', 'followup', or 'none'.
    """
    if applied_changes:
        return "none", None

    status = str(agent_result.get("status") or "").lower()
    if status == "executed":
        return "none", None

    explicit_followup = agent_result.get("requires_followup")
    if isinstance(explicit_followup, str):
        return "followup", explicit_followup
    if explicit_followup:
        return "followup", default_reason or "Agent requested follow-up handling."

    errors = agent_result.get("errors") or []
    if errors:
        return "followup", errors[0]

    if requires_evidence:
        return "stub", default_reason or "Command requires implementation evidence."

    if status == "plan-only":
        return (
            "followup",
            default_reason or "Plan-only response provided without concrete changes.",
        )

    return (
        "followup",
        default_reason or "Automation unable to produce concrete changes.",
    )


def build_default_evidence_entry(
    session_id: str,
    command_name: str,
    agent_result: Dict[str, Any],
    results: Dict[str, Any],
    *,
    slug: str,
    session_fragment: str,
    label_suffix: str,
) -> Dict[str, Any]:
    """Build the default evidence markdown entry."""
    rel_path = (
        Path("SuperClaude")
        / "Implementation"
        / f"{slug}-{session_fragment}{label_suffix}.md"
    )

    content = render_default_evidence_document(
        session_id, command_name, agent_result, results
    )
    return {
        "path": str(rel_path),
        "content": content,
        "mode": "replace",
        "auto_stub": True,
    }


def render_default_evidence_document(
    session_id: str,
    command_name: str,
    agent_result: Dict[str, Any],
    results: Dict[str, Any],
) -> str:
    """Render a fallback implementation evidence markdown document."""
    title = command_name
    timestamp = datetime.now().isoformat()
    lines: List[str] = [
        f"# Implementation Evidence — {title}",
        "",
        f"- session: {session_id}",
        f"- generated: {timestamp}",
        f"- command: /sc:{command_name}",
        "",
    ]

    summary = results.get("primary_summary")
    if summary:
        lines.extend(["## Summary", summary, ""])

    operations = results.get("agent_operations") or []
    if operations:
        lines.append("## Planned Operations")
        lines.extend(f"- {op}" for op in operations)
        lines.append("")

    notes = agent_result.get("notes") or []
    if notes:
        lines.append("## Agent Notes")
        lines.extend(f"- {note}" for note in notes)
        lines.append("")

    warnings = agent_result.get("warnings") or []
    if warnings:
        lines.append("## Agent Warnings")
        lines.extend(f"- {warning}" for warning in warnings)
        lines.append("")

    return "\n".join(lines).strip() + "\n"


def build_generic_stub_change(
    command_name: str,
    session_id: str,
    summary: str,
) -> Dict[str, Any]:
    """Create a minimal stub change plan so generic commands leave evidence."""
    timestamp = datetime.now().isoformat()
    slug_val = slugify(command_name)
    session_fragment = (session_id or "session")[:8]
    file_name = f"{slug_val}-{session_fragment}.md"
    rel_path = Path("SuperClaude") / "Implementation" / "Auto" / "generic" / file_name

    lines = [
        f"# Generic Change Plan — /sc:{command_name}",
        "",
        f"- session: {session_id}",
        f"- generated: {timestamp}",
        f"- command: /sc:{command_name}",
        "",
        "## Summary",
        summary,
        "",
        "## Next Steps",
        "- Replace this autogenerated stub with concrete implementation details.",
        "- Capture resulting diffs to upgrade this placeholder plan.",
    ]

    return {
        "path": str(rel_path),
        "content": "\n".join(lines).strip() + "\n",
        "mode": "replace",
        "auto_stub": True,
    }


def infer_auto_stub_extension(
    command_arguments: List[str],
    parameters: Dict[str, Any],
    agent_result: Dict[str, Any],
) -> str:
    """Infer the file extension for auto-generated stubs."""
    language_hint = str(parameters.get("language") or "").lower()
    framework_hint = str(parameters.get("framework") or "").lower()
    request_blob = " ".join(
        [
            " ".join(command_arguments).lower(),
            language_hint,
            framework_hint,
            " ".join(parameters.get("targets", []) or []),
        ]
    )

    def has_any(*needles: str) -> bool:
        return any(needle in request_blob for needle in needles)

    if has_any("readme", "docs", "documentation", "spec", "adr"):
        return "md"
    if has_any("component", "frontend", "ui", "tsx", "react") or framework_hint in {
        "react",
        "next",
        "nextjs",
    }:
        return "tsx"
    if has_any("typescript", "ts", "lambda", "api") or framework_hint in {
        "express",
        "node",
    }:
        return "ts"
    if has_any("javascript", "linkup"):
        return "js"
    if has_any("vue") or framework_hint == "vue":
        return "vue"
    if has_any("svelte") or framework_hint in {"svelte", "solid"}:
        return "svelte"
    if has_any("rust") or framework_hint == "rust":
        return "rs"
    if has_any("golang", " go") or framework_hint in {"go", "golang"}:
        return "go"
    if has_any("java", "spring") or framework_hint == "java":
        return "java"
    if has_any("csharp", "c#", ".net", "dotnet") or framework_hint in {
        "csharp",
        ".net",
        "dotnet",
    }:
        return "cs"
    if has_any("yaml", "config", "manifest"):
        return "yaml"

    default_ext = agent_result.get("default_extension")
    if isinstance(default_ext, str) and default_ext:
        return default_ext

    return "py"


def infer_auto_stub_category(command_name: str) -> str:
    """Infer the category for auto-generated stubs."""
    if command_name in {"test", "improve", "cleanup", "reflect"}:
        return "quality"
    if command_name in {"build", "workflow", "git"}:
        return "engineering"
    return "engineering" if command_name == "implement" else "general"


def build_auto_stub_entry(
    command_name: str,
    command_arguments: List[str],
    session_id: str,
    parameters: Dict[str, Any],
    agent_result: Dict[str, Any],
    results: Dict[str, Any],
    *,
    slug: str,
    session_fragment: str,
    label_suffix: str,
) -> Optional[Dict[str, Any]]:
    """Build an auto-generated stub entry."""
    extension = infer_auto_stub_extension(command_arguments, parameters, agent_result)
    category = infer_auto_stub_category(command_name)
    if not extension:
        return None

    file_name = f"{slug}-{session_fragment}{label_suffix}.{extension}"
    rel_path = Path("SuperClaude") / "Implementation" / "Auto" / category / file_name

    content = render_auto_stub_content(
        command_name,
        command_arguments,
        session_id,
        agent_result,
        results,
        extension=extension,
        slug=slug,
        session_fragment=session_fragment,
    )

    return {
        "path": str(rel_path),
        "content": content,
        "mode": "replace",
        "auto_stub": True,
    }


def render_auto_stub_content(
    command_name: str,
    command_arguments: List[str],
    session_id: str,
    agent_result: Dict[str, Any],
    results: Dict[str, Any],
    *,
    extension: str,
    slug: str,
    session_fragment: str,
) -> str:
    """Render auto-generated stub content."""
    title = " ".join(command_arguments) or command_name
    timestamp = datetime.now().isoformat()
    operations = agent_result.get("operations") or results.get("agent_operations") or []
    notes = agent_result.get("notes") or results.get("agent_notes") or []

    if not operations:
        operations = [
            "Review requirements and confirm scope with stakeholders",
            "Implement the planned changes in code",
            "Add or update tests to cover the new behavior",
        ]

    deduped_operations = deduplicate(operations)
    deduped_notes = deduplicate(notes)

    def format_ops(prefix: str = "#") -> str:
        return "\n".join(f"{prefix}  - {op}" for op in deduped_operations)

    def format_notes_fn(prefix: str = "#") -> str:
        if not notes:
            return ""
        return "\n".join(f"{prefix}  - {note}" for note in deduped_notes)

    function_name = slug.replace("-", "_") or f"auto_task_{session_fragment}"
    if not function_name[0].isalpha():
        function_name = f"auto_task_{session_fragment}"

    if extension == "py":
        ops_literal = repr(deduped_operations)
        notes_literal = repr(deduped_notes)
        body = textwrap.dedent(
            f'''
            """Auto-generated implementation plan for {title}.

            Generated by the SuperClaude auto-implementation pipeline on {timestamp}.
            The function records the captured plan so it can be actioned later.
            """

            from __future__ import annotations

            import json
            import os
            from datetime import datetime
            from pathlib import Path
            from typing import Any, Dict


            def {function_name}() -> Dict[str, Any]:
                """Record and return the auto-generated implementation plan."""
                plan: Dict[str, Any] = {{
                    "title": {json.dumps(title)},
                    "session": {json.dumps(session_id or "")},
                    "generated_at": {json.dumps(timestamp)},
                    "operations": {ops_literal},
                    "notes": {notes_literal},
                }}

                metrics_root = Path(os.getenv("SUPERCLAUDE_METRICS_DIR", ".superclaude_metrics"))
                metrics_root.mkdir(parents=True, exist_ok=True)
                log_path = metrics_root / "auto_implementation_plans.jsonl"
                with log_path.open("a", encoding="utf-8") as handle:
                    entry = {{
                        **plan,
                        "recorded_at": datetime.utcnow().isoformat() + "Z",
                    }}
                    handle.write(json.dumps(entry) + "\\n")

                return plan


            # Planned operations
            {format_ops()}

            # Additional context
            {format_notes_fn() or "#  - No additional agent notes recorded"}
            '''
        ).strip()
        return body + "\n"

    if extension in {"ts", "tsx", "js"}:
        plan_literal = json.dumps(deduped_operations, indent=2)
        notes_literal_ts = json.dumps(deduped_notes, indent=2)
        import_block = """import fs from 'node:fs';\nimport path from 'node:path';"""
        if extension == "js":
            export_signature = f"export async function {function_name}()"
        else:
            export_signature = f"export async function {function_name}(): Promise<Record<string, unknown>>"

        body = textwrap.dedent(
            f"""
            {import_block}

            {export_signature} {{
              const plan = {{
                title: {json.dumps(title)},
                session: {json.dumps(session_id or "")},
                generatedAt: {json.dumps(timestamp)},
                operations: {plan_literal},
                notes: {notes_literal_ts},
              }};

              const metricsDir = process.env.SUPERCLAUDE_METRICS_DIR ?? '.superclaude_metrics';
              await fs.promises.mkdir(metricsDir, {{ recursive: true }});
              const logPath = path.join(metricsDir, 'auto_implementation_plans.jsonl');
              const entry = {{ ...plan, recordedAt: new Date().toISOString() }};
              await fs.promises.appendFile(logPath, JSON.stringify(entry) + '\\n', {{ encoding: 'utf8' }});

              return plan;
            }}

            // Planned operations
            {format_ops("//")}

            {format_notes_fn("//") or "//  - No additional agent notes recorded"}
            """
        ).strip()
        return body + "\n"

    if extension == "md":
        lines = [
            f"# Auto-generated Implementation Stub — {title}",
            "",
            f"- session: {session_id}",
            f"- generated: {timestamp}",
            f"- command: /sc:{command_name}",
            "",
            "## Planned Operations",
        ]
        lines.extend(f"- {op}" for op in deduplicate(operations))
        if notes:
            lines.append("")
            lines.append("## Agent Notes")
            lines.extend(f"- {note}" for note in deduplicate(notes))
        return "\n".join(lines).strip() + "\n"

    comment_prefix = (
        "//" if extension in {"java", "cs", "rs", "go", "vue", "svelte"} else "#"
    )

    body = textwrap.dedent(
        f"""
        {comment_prefix} Auto-generated implementation stub for {title}.
        {comment_prefix} Generated on {timestamp}. Replace with real implementation after completing the plan.

        {comment_prefix} Planned operations
        {format_ops(comment_prefix)}

        {format_notes_fn(comment_prefix) or f"{comment_prefix}  - No additional agent notes recorded"}
        """
    ).strip()
    return body + "\n"


def apply_changes_fallback(
    changes: List[Dict[str, Any]],
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Apply changes directly to the repository when the manager is unavailable."""
    base_path = Path(repo_root or Path.cwd())
    applied: List[str] = []
    warnings: List[str] = []

    for change in changes:
        rel_path = change.get("path")
        if not rel_path:
            warnings.append("Change missing path")
            continue

        rel_path = Path(rel_path)
        if rel_path.is_absolute() or ".." in rel_path.parts:
            warnings.append(f"Invalid path outside repository: {rel_path}")
            continue

        target_path = (base_path / rel_path).resolve()
        try:
            target_path.relative_to(base_path)
        except ValueError:
            warnings.append(f"Path escapes repository: {rel_path}")
            continue

        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            mode = change.get("mode", "replace")
            content = change.get("content", "")
            if mode == "append" and target_path.exists():
                with target_path.open("a", encoding="utf-8") as handle:
                    handle.write(str(content))
            else:
                target_path.write_text(str(content), encoding="utf-8")
        except Exception as exc:
            warnings.append(f"Failed writing {rel_path}: {exc}")
            continue

        applied.append(str(target_path.relative_to(base_path)))

    return {
        "applied": applied,
        "warnings": warnings,
        "base_path": str(base_path),
        "session": "direct",
    }


__all__ = [
    "apply_changes_fallback",
    "assess_stub_requirement",
    "build_auto_stub_entry",
    "build_default_evidence_entry",
    "build_generic_stub_change",
    "derive_change_plan",
    "extract_agent_change_specs",
    "infer_auto_stub_category",
    "infer_auto_stub_extension",
    "normalize_change_descriptor",
    "render_auto_stub_content",
    "render_default_evidence_document",
]
