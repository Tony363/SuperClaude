"""Tests for validate_purity.py - Purity validator for Functional Core pattern.

TDD Cycle 1: Async pattern detection
- async def functions should be flagged as impure (they imply I/O scheduling)
- await expressions should be detected as I/O patterns

TDD Cycle 2: AsyncFor and AsyncWith detection
- async for loops should be flagged as impure (they imply async iteration)
- async with context managers should be flagged as impure (they imply async resources)

TDD Cycle 5: Edge case hardening
- Syntax errors should be silently skipped (no crash)
- Unicode decode errors should be silently skipped
- Empty files should be handled gracefully
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from validate_purity import (
    analyze_file_purity,
)


class TestAsyncPatternDetection:
    """TDD Cycle 1: Async functions should be detected as impure."""

    def test_async_def_flagged_as_impure_in_core(self, tmp_path: Path) -> None:
        """
        Scenario: An async function is defined in a 'core' context module.
        Expected: The validator flags it as impure because async implies I/O scheduling.

        Rationale: In "Functional Core, Imperative Shell" pattern, async functions
        belong in the shell (they await external operations). Core logic should
        be synchronous and pure.
        """
        # 1. Setup: Create a file in a 'core' path with async function
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "calculator.py"
        test_file.write_text(
            '''
async def fetch_and_calculate(user_id: int) -> float:
    """This should be flagged - async in core module."""
    user = await get_user(user_id)
    return user.balance * 1.1
'''
        )

        # 2. Action: Analyze the file (context will be 'core' due to path)
        violations = analyze_file_purity(test_file, context="core")

        # 3. Assertion: Should detect async as impure
        assert len(violations) > 0, "Async functions in core should be flagged as impure"

        # Check that the violation is about async
        async_violations = [v for v in violations if v.io_type == "async_io"]
        assert len(async_violations) > 0, "Should specifically flag async_io pattern"

    def test_await_expression_flagged_as_io(self, tmp_path: Path) -> None:
        """
        Scenario: A function contains await expressions.
        Expected: Each await is flagged as an I/O operation.

        Rationale: 'await' means we're waiting on an external operation,
        which is inherently impure (non-deterministic timing, external state).
        """
        # 1. Setup: File with multiple await expressions
        core_dir = tmp_path / "services"
        core_dir.mkdir()
        test_file = core_dir / "user_service.py"
        test_file.write_text(
            '''
async def process_user(user_id: int) -> dict:
    """Multiple awaits should each be flagged."""
    user = await fetch_user(user_id)
    profile = await fetch_profile(user_id)
    return {"user": user, "profile": profile}
'''
        )

        # 2. Action
        violations = analyze_file_purity(test_file, context="core")

        # 3. Assertion: Should detect await expressions
        await_violations = [v for v in violations if "await" in v.pattern.lower()]
        assert len(await_violations) >= 2, "Each await should be flagged"

    def test_async_allowed_in_shell_context(self, tmp_path: Path) -> None:
        """
        Scenario: An async function in a 'shell' context (e.g., handlers/).
        Expected: Only a warning, not an error - shell can be impure.

        Rationale: Handlers, adapters, and API endpoints are the "shell"
        where I/O is expected and allowed.
        """
        # 1. Setup: File in a 'shell' path
        shell_dir = tmp_path / "handlers"
        shell_dir.mkdir()
        test_file = shell_dir / "api_handler.py"
        test_file.write_text(
            '''
async def handle_request(request):
    """Async is fine in handlers - this is the shell."""
    data = await request.json()
    return {"status": "ok"}
'''
        )

        # 2. Action: Analyze with shell context
        violations = analyze_file_purity(test_file, context="shell")

        # 3. Assertion: Should be warnings, not errors
        if violations:
            assert all(v.severity == "warning" for v in violations), (
                "Shell async should be warnings only, not errors"
            )

    def test_sync_function_not_flagged_for_async(self, tmp_path: Path) -> None:
        """
        Scenario: A regular synchronous function (no async/await).
        Expected: No async-related violations.

        Rationale: Pure synchronous functions are exactly what we want in core.
        """
        # 1. Setup: Normal sync function
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "math_utils.py"
        test_file.write_text(
            '''
def calculate_discount(price: float, rate: float) -> float:
    """Pure function - no async, no I/O."""
    return price * (1 - rate)
'''
        )

        # 2. Action
        violations = analyze_file_purity(test_file, context="core")

        # 3. Assertion: No async violations
        async_violations = [v for v in violations if v.io_type == "async_io"]
        assert len(async_violations) == 0, "Sync functions should not have async violations"


class TestAsyncForAndAsyncWithDetection:
    """TDD Cycle 2: AsyncFor and AsyncWith should be detected as impure."""

    def test_async_for_flagged_as_impure_in_core(self, tmp_path: Path) -> None:
        """
        Scenario: An async for loop is used inside an async function in core.
        Expected: The async for should be flagged as async_io violation.

        Rationale: async for implies awaiting on each iteration - external I/O.
        """
        # 1. Setup: File with async for loop
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "streaming.py"
        test_file.write_text(
            '''
async def process_stream(stream):
    """Async for should be flagged."""
    results = []
    async for item in stream:
        results.append(item)
    return results
'''
        )

        # 2. Action
        violations = analyze_file_purity(test_file, context="core")

        # 3. Assertion: Should detect async for as async_io
        patterns = [v.pattern for v in violations if v.io_type == "async_io"]
        assert any("async for" in pat for pat in patterns), (
            f"Should flag async for as async_io. Patterns found: {patterns}"
        )

    def test_async_with_flagged_as_impure_in_core(self, tmp_path: Path) -> None:
        """
        Scenario: An async with context manager is used in core.
        Expected: The async with should be flagged as async_io violation.

        Rationale: async with implies acquiring async resources - external I/O.
        """
        # 1. Setup: File with async with
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "resources.py"
        test_file.write_text(
            '''
async def use_connection(client):
    """Async with should be flagged."""
    async with client.connect() as conn:
        return conn.status
'''
        )

        # 2. Action
        violations = analyze_file_purity(test_file, context="core")

        # 3. Assertion: Should detect async with as async_io
        patterns = [v.pattern for v in violations if v.io_type == "async_io"]
        assert any("async with" in pat for pat in patterns), (
            f"Should flag async with as async_io. Patterns found: {patterns}"
        )

    def test_async_for_and_with_combined(self, tmp_path: Path) -> None:
        """
        Scenario: Both async for and async with in the same function.
        Expected: Both should be flagged separately.

        Rationale: Each construct represents a separate I/O pattern.
        """
        # 1. Setup: File with both constructs
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "combined.py"
        test_file.write_text(
            '''
async def fetch_all(client):
    """Both async constructs used."""
    async with client.session() as s:
        async for item in s.stream():
            yield item
'''
        )

        # 2. Action
        violations = analyze_file_purity(test_file, context="core")

        # 3. Assertion: Both should be flagged
        patterns = [v.pattern for v in violations if v.io_type == "async_io"]
        assert any("async with" in pat for pat in patterns), (
            f"Should flag async with. Patterns: {patterns}"
        )
        assert any("async for" in pat for pat in patterns), (
            f"Should flag async for. Patterns: {patterns}"
        )

    def test_async_for_with_severity_in_shell(self, tmp_path: Path) -> None:
        """
        Scenario: Async for/with in shell context (handlers/).
        Expected: Should be warnings, not errors.

        Rationale: Shell is allowed to be impure - it's the I/O boundary.
        """
        # 1. Setup: File in shell path
        shell_dir = tmp_path / "handlers"
        shell_dir.mkdir()
        test_file = shell_dir / "stream_handler.py"
        test_file.write_text(
            '''
async def handle_stream(request):
    """In shell - async is allowed."""
    async for chunk in request.stream():
        yield chunk
'''
        )

        # 2. Action
        violations = analyze_file_purity(test_file, context="shell")

        # 3. Assertion: Should be warnings, not errors
        async_violations = [v for v in violations if v.io_type == "async_io"]
        if async_violations:
            assert all(v.severity == "warning" for v in async_violations), (
                "Shell async should be warnings only"
            )


class TestEdgeCaseHandling:
    """TDD Cycle 5: Edge case hardening for robustness."""

    def test_syntax_error_file_skipped_without_crash(self, tmp_path: Path) -> None:
        """
        Scenario: A file with Python syntax errors.
        Expected: Should not crash, return empty violations.

        Rationale: Validators should be robust to malformed files.
        """
        # 1. Setup: File with syntax error
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "broken.py"
        test_file.write_text(
            """def broken(
    return 1
"""
        )

        # 2. Action: Should not crash
        violations = analyze_file_purity(test_file, context="core")

        # 3. Assertion: Empty violations (couldn't parse)
        assert violations == [], "Syntax error files should return empty violations"

    def test_unicode_decode_error_skipped_without_crash(self, tmp_path: Path) -> None:
        """
        Scenario: A file with invalid UTF-8 bytes.
        Expected: Should not crash, return empty violations.

        Rationale: Validators should handle encoding issues gracefully.
        """
        # 1. Setup: File with invalid UTF-8
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "binary.py"
        test_file.write_bytes(b"\xff\xfe\xfa def foo(): pass")

        # 2. Action: Should not crash
        violations = analyze_file_purity(test_file, context="core")

        # 3. Assertion: Empty violations (couldn't decode)
        assert violations == [], "Unicode error files should return empty violations"

    def test_empty_file_handled_gracefully(self, tmp_path: Path) -> None:
        """
        Scenario: An empty Python file.
        Expected: Should not crash, return empty violations.

        Rationale: Empty files are valid Python but have no functions.
        """
        # 1. Setup: Empty file
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "empty.py"
        test_file.write_text("")

        # 2. Action: Should not crash
        violations = analyze_file_purity(test_file, context="core")

        # 3. Assertion: Empty violations (no functions)
        assert violations == [], "Empty files should return empty violations"

    def test_file_with_only_comments_handled(self, tmp_path: Path) -> None:
        """
        Scenario: A file with only comments and docstrings.
        Expected: Should not crash, return empty violations.
        """
        # 1. Setup: Comments-only file
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "comments.py"
        test_file.write_text(
            '''# This is a comment
"""
This is a module docstring.
"""
# Another comment
'''
        )

        # 2. Action: Should not crash
        violations = analyze_file_purity(test_file, context="core")

        # 3. Assertion: Empty violations (no functions)
        assert violations == [], "Comment-only files should return empty violations"
