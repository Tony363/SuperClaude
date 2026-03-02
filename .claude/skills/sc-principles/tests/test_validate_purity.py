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
    PurityViolation,
    analyze_file_purity,
    determine_context,
    generate_recommendations,
    main,
    match_path_pattern,
    validate_purity,
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


class TestFalsePositiveRegression:
    """Regression tests for patterns that previously caused false positives."""

    def test_set_add_not_flagged(self, tmp_path: Path) -> None:
        """set.add() should NOT be flagged as database I/O."""
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "collector.py"
        test_file.write_text(
            '''
def collect_unique(items: list) -> set:
    """Uses set.add() — should not be flagged."""
    result = set()
    for item in items:
        result.add(item)
    return result
'''
        )

        violations = analyze_file_purity(test_file, context="core")
        db_violations = [v for v in violations if v.io_type == "database"]
        assert len(db_violations) == 0, f"set.add() should not trigger database violation: {db_violations}"

    def test_parser_add_argument_not_flagged(self, tmp_path: Path) -> None:
        """parser.add_argument() should NOT be flagged as database I/O."""
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "config.py"
        test_file.write_text(
            '''
def build_config(parser):
    """Uses parser.add_argument() — should not be flagged."""
    parser.add_argument("--verbose")
    return parser
'''
        )

        violations = analyze_file_purity(test_file, context="core")
        db_violations = [v for v in violations if v.io_type == "database"]
        assert len(db_violations) == 0, f"parser.add_argument() should not trigger database violation: {db_violations}"

    def test_asyncio_run_not_flagged(self, tmp_path: Path) -> None:
        """asyncio.run() should NOT be flagged as subprocess I/O."""
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "runner.py"
        test_file.write_text(
            '''
def run_loop(coro):
    """Uses asyncio.run() — should not be flagged as subprocess."""
    import asyncio
    return asyncio.run(coro)
'''
        )

        violations = analyze_file_purity(test_file, context="core")
        subprocess_violations = [v for v in violations if v.io_type == "subprocess"]
        assert len(subprocess_violations) == 0, (
            f"asyncio.run() should not trigger subprocess violation: {subprocess_violations}"
        )

    def test_callback_call_not_flagged(self, tmp_path: Path) -> None:
        """callback.call() should NOT be flagged as subprocess I/O."""
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "dispatch.py"
        test_file.write_text(
            '''
def dispatch(callback, data):
    """Uses callback.call() — should not be flagged as subprocess."""
    return callback.call(data)
'''
        )

        violations = analyze_file_purity(test_file, context="core")
        subprocess_violations = [v for v in violations if v.io_type == "subprocess"]
        assert len(subprocess_violations) == 0, (
            f"callback.call() should not trigger subprocess violation: {subprocess_violations}"
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


class TestGlobalNonlocalDetection:
    """Tests for global/nonlocal statement detection (lines 250-264)."""

    def test_global_statement_flagged_in_function(self, tmp_path: Path) -> None:
        """global x inside a function should be flagged as global_state."""
        # Arrange
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "globals.py"
        test_file.write_text(
            '''
counter = 0

def increment():
    global counter
    counter += 1
    return counter
'''
        )

        # Act
        violations = analyze_file_purity(test_file, context="core")

        # Assert
        global_violations = [v for v in violations if v.io_type == "global_state"]
        assert len(global_violations) == 1
        assert "global counter" in global_violations[0].pattern

    def test_nonlocal_statement_flagged_in_function(self, tmp_path: Path) -> None:
        """nonlocal y inside a nested function should be flagged as nonlocal_state."""
        # Arrange
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "nonlocals.py"
        test_file.write_text(
            '''
def outer():
    count = 0
    def inner():
        nonlocal count
        count += 1
    inner()
    return count
'''
        )

        # Act
        violations = analyze_file_purity(test_file, context="core")

        # Assert
        nonlocal_violations = [v for v in violations if v.io_type == "nonlocal_state"]
        assert len(nonlocal_violations) == 1
        assert "nonlocal count" in nonlocal_violations[0].pattern


class TestIOModulePatternDetection:
    """Tests for IO module pattern detection via imported module names (lines 350-365)."""

    def test_requests_session_flagged_via_module_pattern(self, tmp_path: Path) -> None:
        """Calls on imported 'requests' module should be flagged via IO_MODULE_PATTERNS."""
        # Arrange
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "fetcher.py"
        test_file.write_text(
            '''
import requests

def fetch_data(url: str):
    session = requests.Session()
    return session
'''
        )

        # Act
        violations = analyze_file_purity(test_file, context="core")

        # Assert
        network_violations = [v for v in violations if v.io_type == "network"]
        assert len(network_violations) >= 1

    def test_sqlite3_connect_flagged_via_module_pattern(self, tmp_path: Path) -> None:
        """Calls on imported 'sqlite3' module should be flagged as database."""
        # Arrange
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "db_access.py"
        test_file.write_text(
            '''
import sqlite3

def get_connection():
    return sqlite3.connect(":memory:")
'''
        )

        # Act
        violations = analyze_file_purity(test_file, context="core")

        # Assert
        db_violations = [v for v in violations if v.io_type == "database"]
        assert len(db_violations) >= 1


class TestLoggingPrefixDetection:
    """Tests for logging prefix detection (lines 357-360)."""

    def test_logger_info_flagged_as_side_effect(self, tmp_path: Path) -> None:
        """logger.info() should be flagged as side_effects via IO_LOGGING_PREFIXES."""
        # Arrange
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "logged.py"
        test_file.write_text(
            '''
import logging
logger = logging.getLogger(__name__)

def process(data):
    logger.info("Processing data")
    return data
'''
        )

        # Act
        violations = analyze_file_purity(test_file, context="core")

        # Assert
        side_effect_violations = [v for v in violations if v.io_type == "side_effects"]
        assert any("logger" in v.pattern for v in side_effect_violations)


class TestGetExprNameFallbacks:
    """Tests for _get_expr_name fallback paths (lines 308-317)."""

    def test_attribute_chain_resolved(self, tmp_path: Path) -> None:
        """Complex attribute chains (a.b.c) should be resolved in _get_expr_name."""
        # Arrange
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "chained.py"
        test_file.write_text(
            '''
async def process(client):
    result = await client.api.data.fetch()
    return result
'''
        )

        # Act
        violations = analyze_file_purity(test_file, context="core")

        # Assert - should have violations with resolved attribute names
        await_violations = [v for v in violations if "await" in v.pattern]
        assert len(await_violations) >= 1

    def test_expression_fallback(self, tmp_path: Path) -> None:
        """Non-Name/Attribute expressions should get '<expression>' fallback."""
        # Arrange
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "complex_expr.py"
        test_file.write_text(
            '''
async def process():
    result = await (lambda: None)()
    return result
'''
        )

        # Act
        violations = analyze_file_purity(test_file, context="core")

        # Assert - should have some async_io violation
        async_violations = [v for v in violations if v.io_type == "async_io"]
        assert len(async_violations) >= 1


class TestPathClassification:
    """Tests for match_path_pattern and determine_context (lines 368-396)."""

    def test_match_path_pattern_glob(self) -> None:
        """fnmatch glob patterns should match paths."""
        # Arrange / Act / Assert
        assert match_path_pattern("/project/domain/model.py", "*/domain/*")
        assert not match_path_pattern("/project/src/model.py", "*/domain/*")

    def test_match_path_pattern_suffix(self) -> None:
        """File suffix patterns should match."""
        assert match_path_pattern("/project/user_service.py", "*_service.py")
        assert not match_path_pattern("/project/user_model.py", "*_service.py")

    def test_match_path_pattern_segment_fallback(self) -> None:
        """Segment-based fallback should check directory parts."""
        # "*/tests/*" stripped to "tests" should match in path parts
        assert match_path_pattern("/project/tests/test_foo.py", "*/tests/*")

    def test_determine_context_core_path(self, tmp_path: Path) -> None:
        """Files in core patterns should be classified as 'core'."""
        assert determine_context(Path("/project/domain/model.py")) == "core"
        assert determine_context(Path("/project/services/user.py")) == "core"

    def test_determine_context_shell_path(self, tmp_path: Path) -> None:
        """Files in shell patterns should be classified as 'shell'."""
        assert determine_context(Path("/project/handlers/api.py")) == "shell"
        assert determine_context(Path("/project/tests/test_api.py")) == "shell"

    def test_determine_context_default_is_shell(self, tmp_path: Path) -> None:
        """Unrecognized paths should default to 'shell'."""
        assert determine_context(Path("/random/path/foo.py")) == "shell"


class TestGenerateRecommendationsPurity:
    """Tests for generate_recommendations (lines 412-460)."""

    def test_file_io_recommendation(self) -> None:
        """File I/O violations in core should generate file I/O recommendation."""
        violations = [
            PurityViolation(
                file="test.py", function="f", line=1,
                io_type="file_io", pattern="open", context="core", severity="error",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("FILE I/O" in r for r in recs)

    def test_network_recommendation(self) -> None:
        """Network violations should generate network recommendation."""
        violations = [
            PurityViolation(
                file="test.py", function="f", line=1,
                io_type="network", pattern="requests.get", context="core", severity="error",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("NETWORK" in r for r in recs)

    def test_database_recommendation(self) -> None:
        """Database violations should generate database recommendation."""
        violations = [
            PurityViolation(
                file="test.py", function="f", line=1,
                io_type="database", pattern="execute", context="core", severity="error",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("DATABASE" in r for r in recs)

    def test_subprocess_recommendation(self) -> None:
        """Subprocess violations should generate subprocess recommendation."""
        violations = [
            PurityViolation(
                file="test.py", function="f", line=1,
                io_type="subprocess", pattern="subprocess.run", context="core", severity="error",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("SUBPROCESS" in r for r in recs)

    def test_global_state_recommendation(self) -> None:
        """Global state violations should generate global state recommendation."""
        violations = [
            PurityViolation(
                file="test.py", function="f", line=1,
                io_type="global_state", pattern="global x", context="core", severity="error",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("GLOBAL STATE" in r for r in recs)

    def test_side_effects_recommendation(self) -> None:
        """Side effects violations should generate side effects recommendation."""
        violations = [
            PurityViolation(
                file="test.py", function="f", line=1,
                io_type="side_effects", pattern="print", context="core", severity="error",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("SIDE EFFECTS" in r for r in recs)

    def test_async_io_recommendation(self) -> None:
        """Async I/O violations should generate async recommendation."""
        violations = [
            PurityViolation(
                file="test.py", function="f", line=1,
                io_type="async_io", pattern="async def f", context="core", severity="error",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("ASYNC I/O" in r for r in recs)

    def test_empty_violations_no_recommendations(self) -> None:
        """No violations should produce no recommendations."""
        recs = generate_recommendations([])
        assert recs == []

    def test_shell_violations_no_recommendations(self) -> None:
        """Shell-context violations should not generate recommendations."""
        violations = [
            PurityViolation(
                file="test.py", function="f", line=1,
                io_type="file_io", pattern="open", context="shell", severity="warning",
            )
        ]
        recs = generate_recommendations(violations)
        assert recs == []


class TestValidatePurity:
    """Tests for validate_purity orchestration (lines 463-507)."""

    def test_clean_files_pass(self, tmp_path: Path) -> None:
        """Clean files with no I/O should pass validation."""
        # Arrange
        test_file = tmp_path / "clean.py"
        test_file.write_text("def add(a, b): return a + b\n")

        # Act
        result = validate_purity(str(tmp_path), all_files=True)

        # Assert
        assert result.allowed is True
        assert result.summary["files_analyzed"] >= 1

    def test_core_violations_block(self, tmp_path: Path) -> None:
        """Core violations (errors) should block validation."""
        # Arrange
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "impure.py"
        test_file.write_text(
            '''
def process():
    print("side effect")
    return 42
'''
        )

        # Act
        result = validate_purity(str(tmp_path), all_files=True)

        # Assert
        assert result.allowed is False
        assert result.summary["errors"] > 0

    def test_strict_mode_blocks_on_warnings(self, tmp_path: Path) -> None:
        """Strict mode should block even on shell warnings."""
        # Arrange
        shell_dir = tmp_path / "handlers"
        shell_dir.mkdir()
        test_file = shell_dir / "handler.py"
        test_file.write_text(
            '''
def handle():
    print("logging")
    return True
'''
        )

        # Act
        result = validate_purity(str(tmp_path), strict=True, all_files=True)

        # Assert
        assert result.summary["warnings"] > 0
        assert result.allowed is False


class TestPurityCLI:
    """Tests for main() CLI entrypoint (lines 510-584)."""

    def test_json_output(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch", capsys: "pytest.CaptureFixture") -> None:
        """--json flag should produce JSON output."""
        import json as json_mod

        # Arrange
        test_file = tmp_path / "simple.py"
        test_file.write_text("x = 1\n")
        monkeypatch.setattr(
            "sys.argv",
            ["validate_purity", "--scope-root", str(tmp_path), "--all", "--json"],
        )

        # Act
        try:
            main()
        except SystemExit:
            pass

        # Assert
        captured = capsys.readouterr()
        output = json_mod.loads(captured.out)
        assert "allowed" in output
        assert "violations" in output
        assert "summary" in output

    def test_text_output(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch", capsys: "pytest.CaptureFixture") -> None:
        """Default text output should include key sections."""
        # Arrange
        test_file = tmp_path / "simple.py"
        test_file.write_text("x = 1\n")
        monkeypatch.setattr(
            "sys.argv",
            ["validate_purity", "--scope-root", str(tmp_path), "--all"],
        )

        # Act
        try:
            main()
        except SystemExit:
            pass

        # Assert
        captured = capsys.readouterr()
        assert "Purity Validation:" in captured.out
        assert "Files analyzed:" in captured.out

    def test_exit_code_zero_on_pass(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Clean code should exit with code 0."""
        import pytest

        # Arrange
        test_file = tmp_path / "clean.py"
        test_file.write_text("x = 1\n")
        monkeypatch.setattr(
            "sys.argv",
            ["validate_purity", "--scope-root", str(tmp_path), "--all"],
        )

        # Act / Assert
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_exit_code_two_on_block(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Blocked validation should exit with code 2."""
        import pytest

        # Arrange
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "impure.py"
        test_file.write_text(
            '''
def process():
    print("side effect")
'''
        )
        monkeypatch.setattr(
            "sys.argv",
            ["validate_purity", "--scope-root", str(tmp_path), "--all"],
        )

        # Act / Assert
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    def test_text_output_with_violations(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch", capsys: "pytest.CaptureFixture") -> None:
        """Text output with violations should show Violations and Recommendations."""
        # Arrange
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        test_file = core_dir / "impure.py"
        test_file.write_text(
            '''
def process():
    print("side effect")
'''
        )
        monkeypatch.setattr(
            "sys.argv",
            ["validate_purity", "--scope-root", str(tmp_path), "--all"],
        )

        # Act
        try:
            main()
        except SystemExit:
            pass

        # Assert
        captured = capsys.readouterr()
        assert "Violations:" in captured.out
        assert "Recommendations:" in captured.out
        assert "Hint:" in captured.out
