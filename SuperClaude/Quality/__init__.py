"""
SuperClaude Quality compatibility module.

Re-exports quality modules from the archived Python SDK.
"""

from __future__ import annotations

import sys
from pathlib import Path

_archive_path = Path(__file__).parent.parent.parent / "archive" / "python-sdk-v5"
if str(_archive_path) not in sys.path:
    sys.path.insert(0, str(_archive_path))

# Lazy imports to avoid Python version compatibility issues
__all__ = [
    "GeneratedDocValidation",
    "GeneratedValidator",
    "QualityScorer",
    "ValidationIssue",
    "ValidationPipeline",
    "ValidationReport",
]


def __getattr__(name: str):
    """Lazy import pattern."""
    from Quality import __getattr__ as quality_getattr

    return quality_getattr(name)
