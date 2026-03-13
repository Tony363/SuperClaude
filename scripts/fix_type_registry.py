#!/usr/bin/env python3
"""
Fix-type registry: single source of truth for autofix capabilities.

Both normalize_findings.py and apply_autofix.py import from here.
Adding a new fix type requires only updating FIX_TYPES below —
eligibility and handler dispatch are driven by this registry.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FixType:
    name: str
    confidence_threshold: float
    categories: tuple[str, ...]
    tool_command: str  # {file} and {codes} are placeholders
    safe: bool  # Whether this fix type preserves runtime behavior
    max_passes: int  # For idempotency (1 = deterministic, 2-3 = lint)
    ruff_select_codes: tuple[str, ...] | None  # Ruff rule codes, if applicable
    description: str


FIX_TYPES: dict[str, FixType] = {
    "ruff_format": FixType(
        name="ruff_format",
        confidence_threshold=0.95,
        categories=("quality",),
        tool_command="ruff format {file}",
        safe=True,
        max_passes=1,
        ruff_select_codes=None,
        description="Auto-format Python files with ruff",
    ),
    "ruff_lint_fix": FixType(
        name="ruff_lint_fix",
        confidence_threshold=0.90,
        categories=("quality",),
        tool_command="ruff check --select {codes} --fix {file}",
        safe=True,
        max_passes=3,
        ruff_select_codes=("F401", "I001"),
        description="Fix unused imports (F401) and import sorting (I001)",
    ),
    "llm_single_file": FixType(
        name="llm_single_file",
        confidence_threshold=0.80,
        categories=("quality", "performance"),
        tool_command="",  # No CLI tool — handled by Claude Code Action
        safe=False,  # Requires human review
        max_passes=0,  # Not applicable — no idempotency check
        ruff_select_codes=None,
        description="LLM-generated single-file fix (Phase 3: conservative scope)",
    ),
}

# Inference rules: map suggestion text patterns to fix type names
SUGGESTION_INFERENCE_RULES: list[tuple[list[str], str]] = [
    (["ruff format", "formatting", "auto-format"], "ruff_format"),
    (["unused import", "import sort", "f401", "i001", "remove import"], "ruff_lint_fix"),
    # Phase 3: LLM single-file patterns (conservative)
    (
        [
            "unused variable",
            "dead code",
            "unreachable code",
            "remove dead",
            "type hint",
            "type annotation",
            "add type",
            "missing docstring",
            "add docstring",
        ],
        "llm_single_file",
    ),
]


def get_fix_type(name: str) -> FixType | None:
    """Look up a fix type by name."""
    return FIX_TYPES.get(name)


def get_all_fix_types() -> dict[str, FixType]:
    """Return a copy of all registered fix types."""
    return dict(FIX_TYPES)


def is_known_fix_type(name: str) -> bool:
    """Check if a fix type name is registered."""
    return name in FIX_TYPES


def infer_fix_type(suggestion: str, explicit_fix_type: str = "") -> str | None:
    """
    Infer fix type name from explicit field or suggestion text.

    Returns the fix type name string, or None if no match.
    """
    # Prefer explicit fix_type field
    if explicit_fix_type and is_known_fix_type(explicit_fix_type.lower()):
        return explicit_fix_type.lower()

    # Fallback: match suggestion text against inference rules
    suggestion_lower = suggestion.lower()
    for patterns, fix_type_name in SUGGESTION_INFERENCE_RULES:
        for pattern in patterns:
            if pattern in suggestion_lower:
                return fix_type_name

    return None
