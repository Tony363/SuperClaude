"""
Termination detection for SuperClaude Loop Orchestration.

Ported from archive/python-sdk-v5/Quality/quality_scorer.py lines 760-801.

These safety mechanisms prevent infinite loops by detecting:
- Oscillation: Scores alternating up/down (stuck in local minimum)
- Stagnation: Scores not changing meaningfully (plateau)
"""


def detect_oscillation(
    score_history: list[float],
    window: int = 3,
    threshold: float = 2.0,
) -> bool:
    """
    Detect if quality scores are oscillating (alternating up/down).

    This indicates the improver is stuck in a local minimum, making
    changes that undo each other. Continuing would waste resources.

    Args:
        score_history: List of quality scores from each iteration
        window: Number of recent scores to analyze (default 3)
        threshold: Minimum change to count as a direction (default 2.0)

    Returns:
        True if oscillation detected (should stop loop)

    Example:
        scores = [50.0, 60.0, 55.0, 62.0, 58.0]  # Up/down/up/down
        detect_oscillation(scores) -> True
    """
    if len(score_history) < window:
        return False

    recent = score_history[-window:]
    directions: list[int] = []

    for i in range(1, len(recent)):
        diff = recent[i] - recent[i - 1]
        # Only count significant changes
        if abs(diff) > threshold:
            directions.append(1 if diff > 0 else -1)

    # Oscillation = alternating directions
    if len(directions) >= 2:
        is_oscillating = all(directions[i] != directions[i + 1] for i in range(len(directions) - 1))
        return is_oscillating

    return False


def detect_stagnation(
    score_history: list[float],
    window: int = 3,
    threshold: float = 2.0,
) -> bool:
    """
    Detect if quality scores have stagnated (not improving).

    This indicates the improver has reached a plateau where
    further iterations won't meaningfully improve quality.

    Args:
        score_history: List of quality scores from each iteration
        window: Number of recent scores to analyze (default 3)
        threshold: Maximum variance to consider stagnant (default 2.0)

    Returns:
        True if stagnation detected (should stop loop)

    Example:
        scores = [65.0, 65.5, 64.8, 65.2]  # All within 2.0 range
        detect_stagnation(scores) -> True
    """
    if len(score_history) < window:
        return False

    recent = score_history[-window:]
    score_range = max(recent) - min(recent)

    return score_range < threshold


def check_insufficient_improvement(
    current_score: float,
    previous_score: float,
    min_improvement: float = 5.0,
) -> bool:
    """
    Check if improvement between iterations is too small.

    If the score improved by less than min_improvement points,
    continuing is unlikely to reach the threshold.

    Args:
        current_score: Score after this iteration
        previous_score: Score before this iteration
        min_improvement: Minimum improvement to continue (default 5.0)

    Returns:
        True if improvement is insufficient (should stop loop)
    """
    improvement = current_score - previous_score
    return improvement < min_improvement


def should_terminate(
    score_history: list[float],
    config_oscillation_window: int = 3,
    config_stagnation_threshold: float = 2.0,
    config_min_improvement: float = 5.0,
) -> tuple[bool, str]:
    """
    Check all termination conditions.

    Args:
        score_history: List of quality scores from each iteration
        config_oscillation_window: Window for oscillation detection
        config_stagnation_threshold: Threshold for stagnation detection
        config_min_improvement: Minimum improvement threshold

    Returns:
        Tuple of (should_stop, reason)
    """
    if len(score_history) < 2:
        return False, ""

    # Check oscillation
    if detect_oscillation(score_history, config_oscillation_window):
        return True, "oscillation"

    # Check stagnation
    if detect_stagnation(
        score_history,
        config_oscillation_window,
        config_stagnation_threshold,
    ):
        return True, "stagnation"

    # Check insufficient improvement (only if we have 2+ scores)
    if len(score_history) >= 2:
        if check_insufficient_improvement(
            score_history[-1],
            score_history[-2],
            config_min_improvement,
        ):
            return True, "insufficient_improvement"

    return False, ""
