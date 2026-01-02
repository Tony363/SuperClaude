"""Contract validation helpers for MCP schema comparison.

Provides utilities to compare response schemas between fake and live
MCP servers to detect schema drift.
"""

from __future__ import annotations

from typing import Any, Optional


def assert_schema_matches(
    reference: object,
    candidate: object,
    path: str = "root",
    allow_extra_keys: bool = False,
) -> None:
    """
    Recursively asserts that the schema of two objects matches.

    - Compares types at each level.
    - For dicts, ensures keys are identical (or subset if allow_extra_keys).
    - For lists, ensures they are both lists and compares the schema of their
      first elements (assumes homogeneous lists).
    - Ignores actual values of primitives (str, int, float, bool).

    Args:
        reference: The object with the expected schema (e.g., from FakeMCPServer).
        candidate: The object to validate (e.g., from the live MCP service).
        path: The current path for clear error messages.
        allow_extra_keys: If True, candidate may have extra keys not in reference.

    Raises:
        AssertionError: If schemas do not match.
    """
    # Handle None cases
    if reference is None and candidate is None:
        return
    if reference is None or candidate is None:
        assert False, (
            f"Nullability mismatch at path '{path}': "
            f"reference is {'None' if reference is None else 'not None'}, "
            f"candidate is {'None' if candidate is None else 'not None'}"
        )

    # Type comparison
    ref_type = type(reference)
    cand_type = type(candidate)

    # Allow int/float interchangeability for numeric types
    numeric_types = (int, float)
    if isinstance(reference, numeric_types) and isinstance(candidate, numeric_types):
        return  # Both are numeric, schema matches

    assert ref_type is cand_type, (
        f"Type mismatch at path '{path}': "
        f"expected {ref_type.__name__}, got {cand_type.__name__}"
    )

    if isinstance(reference, dict):
        reference_keys = set(reference.keys())
        candidate_keys = set(candidate.keys())

        # Check for missing keys in candidate
        missing_keys = reference_keys - candidate_keys
        if missing_keys:
            assert False, (
                f"Missing keys at path '{path}': {sorted(list(missing_keys))}"
            )

        # Check for extra keys in candidate (if not allowed)
        if not allow_extra_keys:
            extra_keys = candidate_keys - reference_keys
            if extra_keys:
                assert False, (
                    f"Extra keys at path '{path}': {sorted(list(extra_keys))}\n"
                    f"Set allow_extra_keys=True if live responses may have additional fields."
                )

        # Recursively check all reference keys
        for key in reference_keys:
            assert_schema_matches(
                reference[key],
                candidate[key],
                path=f"{path}.{key}",
                allow_extra_keys=allow_extra_keys,
            )

    elif isinstance(reference, list):
        # Assumption: We compare the schema of the first element in non-empty lists.
        # This is a practical heuristic for testing API list responses.
        if len(reference) > 0 and len(candidate) > 0:
            assert_schema_matches(
                reference[0],
                candidate[0],
                path=f"{path}[0]",
                allow_extra_keys=allow_extra_keys,
            )
        # If one or both are empty, we just care that they are both lists,
        # which is already handled by the initial type check.


def extract_schema(obj: object) -> dict[str, Any]:
    """
    Extract a schema representation from an object.

    Useful for debugging and logging what schema was observed.

    Args:
        obj: Object to extract schema from.

    Returns:
        A dict representing the schema with type names as values.
    """
    if obj is None:
        return {"_type": "null"}

    if isinstance(obj, dict):
        return {
            "_type": "object",
            "_keys": {key: extract_schema(value) for key, value in obj.items()},
        }

    if isinstance(obj, list):
        if len(obj) > 0:
            return {
                "_type": "array",
                "_items": extract_schema(obj[0]),
            }
        return {"_type": "array", "_items": None}

    return {"_type": type(obj).__name__}


def schema_diff(
    reference: object,
    candidate: object,
    path: str = "root",
) -> list[str]:
    """
    Compute a list of schema differences between two objects.

    Unlike assert_schema_matches, this returns all differences rather
    than failing on the first one.

    Args:
        reference: The expected schema.
        candidate: The actual schema.
        path: Current path for error messages.

    Returns:
        List of difference descriptions.
    """
    diffs: list[str] = []

    if reference is None and candidate is None:
        return diffs
    if reference is None:
        diffs.append(f"{path}: expected None, got {type(candidate).__name__}")
        return diffs
    if candidate is None:
        diffs.append(f"{path}: expected {type(reference).__name__}, got None")
        return diffs

    ref_type = type(reference)
    cand_type = type(candidate)

    # Allow int/float interchangeability
    numeric_types = (int, float)
    if isinstance(reference, numeric_types) and isinstance(candidate, numeric_types):
        return diffs

    if ref_type is not cand_type:
        diffs.append(
            f"{path}: type mismatch - expected {ref_type.__name__}, got {cand_type.__name__}"
        )
        return diffs

    if isinstance(reference, dict):
        reference_keys = set(reference.keys())
        candidate_keys = set(candidate.keys())

        missing = reference_keys - candidate_keys
        extra = candidate_keys - reference_keys

        for key in sorted(missing):
            diffs.append(f"{path}.{key}: missing in candidate")
        for key in sorted(extra):
            diffs.append(f"{path}.{key}: extra in candidate")

        for key in reference_keys & candidate_keys:
            diffs.extend(schema_diff(reference[key], candidate[key], f"{path}.{key}"))

    elif isinstance(reference, list):
        if len(reference) > 0 and len(candidate) > 0:
            diffs.extend(schema_diff(reference[0], candidate[0], f"{path}[0]"))

    return diffs
