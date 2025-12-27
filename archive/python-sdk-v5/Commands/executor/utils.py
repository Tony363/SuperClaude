"""
Utility functions for the SuperClaude Command Executor.

Provides common helper functions for type coercion, string manipulation,
evidence normalization, and flag handling.
"""

from typing import Any


def slugify(value: str) -> str:
    """Create a filesystem-safe slug from arbitrary text."""
    sanitized = "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in value.lower()
    )
    sanitized = "-".join(part for part in sanitized.split("-") if part)
    return sanitized or "implementation"


def truncate_output(text: str, max_length: int = 800) -> str:
    """Limit captured command output to a manageable size."""
    if not text or len(text) <= max_length:
        return text
    head = text[: max_length // 2].rstrip()
    tail = text[-max_length // 2 :].lstrip()
    return f"{head}\n... [truncated] ...\n{tail}"


def normalize_evidence_value(value: Any) -> list[str]:
    """Normalize evidence values into a flat list of strings."""
    items: list[str] = []
    if value is None:
        return items

    if isinstance(value, list):
        for item in value:
            items.extend(normalize_evidence_value(item))
        return items

    if isinstance(value, dict):
        for key, subvalue in value.items():
            sub_items = normalize_evidence_value(subvalue)
            if sub_items:
                for sub_item in sub_items:
                    items.append(f"{key}: {sub_item}")
            else:
                items.append(f"{key}: {subvalue}")
        return items

    text = str(value).strip()
    if text:
        items.append(text)
    return items


def extract_output_evidence(output: dict[str, Any], key: str) -> list[str]:
    """Extract evidence from an output dictionary for a specific key."""
    if key not in output:
        return []
    return normalize_evidence_value(output.get(key))


def deduplicate(items: list[str]) -> list[str]:
    """Remove duplicate evidence entries preserving order."""
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        normalized = item.strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(normalized)
    return deduped


def ensure_list(container: dict[str, Any], key: str) -> list[str]:
    """Ensure a dictionary value is a list, normalizing if necessary."""
    value = container.get(key)
    if isinstance(value, list):
        return value
    if value is None:
        container[key] = []
        return container[key]
    container[key] = [str(value)]
    return container[key]


def is_truthy(value: Any) -> bool:
    """Interpret diverse flag representations as boolean truthy values."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {"1", "true", "yes", "on", "enabled"}
    return False


def coerce_float(value: Any, default: float | None) -> float | None:
    """Best-effort float coercion."""
    try:
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp_int(value: Any, minimum: int, maximum: int, default: int) -> int:
    """Coerce to int and clamp within bounds."""
    try:
        if isinstance(value, bool):
            intval = 1 if value else 0
        else:
            intval = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, intval))


def to_list(value: Any) -> list[str]:
    """Normalize value into a list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, (set, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    if not text:
        return []
    if "," in text:
        return [part.strip() for part in text.split(",") if part.strip()]
    return [text]


__all__ = [
    "slugify",
    "truncate_output",
    "normalize_evidence_value",
    "extract_output_evidence",
    "deduplicate",
    "ensure_list",
    "is_truthy",
    "coerce_float",
    "clamp_int",
    "to_list",
]
