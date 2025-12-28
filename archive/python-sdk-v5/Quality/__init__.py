"""SuperClaude Quality package."""

from __future__ import annotations

# Lazy imports to avoid circular dependencies and version issues
__all__ = [
    "GeneratedDocValidation",
    "GeneratedValidator",
    "QualityScorer",
    "ValidationIssue",
    "ValidationPipeline",
    "ValidationReport",
]


def __getattr__(name: str):
    """Lazy import pattern for Quality submodules."""
    if name in ("GeneratedDocValidation", "GeneratedValidator", "ValidationIssue", "ValidationReport"):
        from .generated_validator import (
            GeneratedDocValidation,
            GeneratedValidator,
            ValidationIssue,
            ValidationReport,
        )
        return locals()[name]
    elif name == "QualityScorer":
        from .quality_scorer import QualityScorer
        return QualityScorer
    elif name == "ValidationPipeline":
        from .validation_pipeline import ValidationPipeline
        return ValidationPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
