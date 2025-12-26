"""
Type definitions for SuperClaude SDK integration.

Re-exports types from client.py for backwards compatibility and
provides additional type utilities.
"""

from __future__ import annotations

from enum import Enum

# Re-export main types from client
from .client import ExecutionResult, SDKMessage, SDKOptions


class TerminationReason(str, Enum):
    """Reason for agentic loop termination.

    Used by SDKExecutionResult to indicate why the loop stopped.
    Inherits from str for easy serialization and comparison.
    """

    # Success conditions
    THRESHOLD_MET = "threshold_met"  # Quality score met threshold
    SINGLE_ITERATION = "single_iteration"  # No loop needed (direct success)

    # Stop conditions (not failures)
    MAX_ITERATIONS = "max_iterations"  # Hit iteration limit
    STAGNATION = "stagnation"  # Improvement below MIN_IMPROVEMENT
    OSCILLATION = "oscillation"  # Score bouncing between values
    TIMEOUT = "timeout"  # Wall-clock timeout exceeded

    # Error conditions
    SCORER_ERROR = "scorer_error"  # QualityScorer raised exception
    EXECUTION_ERROR = "execution_error"  # SDK execution failed

    # Fallback conditions
    FALLBACK = "fallback"  # Requested fallback to Skills/Legacy
    SDK_UNAVAILABLE = "sdk_unavailable"  # SDK not installed/available


__all__ = [
    "SDKMessage",
    "SDKOptions",
    "ExecutionResult",
    "TerminationReason",
]
