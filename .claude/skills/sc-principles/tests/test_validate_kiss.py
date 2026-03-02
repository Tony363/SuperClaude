"""Tests for validate_kiss.py - KISS principle validator.

TDD Cycle 3: KISS validator tests
- Function length should count inclusive lines (fix off-by-one)
- Complexity thresholds should trigger violations correctly
- Nesting depth detection should work accurately

TDD Cycle 4: Cognitive complexity
- Cognitive complexity should weight nested structures more heavily
- Should flag code that is hard to read even with moderate cyclomatic complexity

TDD Cycle 5: Edge case hardening
- Syntax errors should be silently skipped (no crash)
- Unicode decode errors should be silently skipped
- Empty files should be handled gracefully
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest  # noqa: F401 - used in type annotations

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from validate_kiss import (
    KISSThresholds,
    KISSViolation,
    analyze_file_kiss,
    calculate_complexity,
    generate_recommendations,
    main,
    try_mccabe_complexity,
    validate_kiss,
)


class TestFunctionLengthValidation:
    """TDD Cycle 3: Function length should be measured correctly."""

    def test_function_length_counts_inclusive_lines(self, tmp_path: Path) -> None:
        """
        Scenario: A 3-line function should be measured as 3 lines.
        Expected: With max_function_lines=2, should violate with value=3.

        Rationale: Function length should be inclusive (end_lineno - lineno + 1).
        The current implementation has off-by-one (end_lineno - lineno).
        """
        # 1. Setup: 3-line function
        test_file = tmp_path / "sample.py"
        test_file.write_text(
            """def f():
    x = 1
    return x
"""
        )

        # 2. Action: Analyze with threshold=2 (should flag 3-line function)
        thresholds = KISSThresholds(max_function_lines=2)
        violations = analyze_file_kiss(test_file, thresholds)

        # 3. Assertion: Should detect length violation with value=3
        length_violations = [
            v for v in violations if v.violation_type == "length" and v.function == "f"
        ]
        assert len(length_violations) == 1, (
            f"Expected 1 length violation for 3-line function with max=2. "
            f"Got {len(length_violations)}: {length_violations}"
        )
        assert length_violations[0].value == 3, (
            f"Expected value=3 for 3-line function. Got {length_violations[0].value}"
        )
        assert length_violations[0].threshold == 2

    def test_function_length_at_threshold_no_violation(self, tmp_path: Path) -> None:
        """
        Scenario: A 3-line function with max_function_lines=3.
        Expected: No violation (exactly at threshold).

        Rationale: Functions at the threshold should pass.
        """
        # 1. Setup: Same 3-line function
        test_file = tmp_path / "sample.py"
        test_file.write_text(
            """def f():
    x = 1
    return x
"""
        )

        # 2. Action: Analyze with threshold=3 (should NOT flag)
        thresholds = KISSThresholds(max_function_lines=3)
        violations = analyze_file_kiss(test_file, thresholds)

        # 3. Assertion: No length violation
        length_violations = [
            v for v in violations if v.violation_type == "length" and v.function == "f"
        ]
        assert len(length_violations) == 0, (
            f"Expected no violation for 3-line function with max=3. Got {length_violations}"
        )

    def test_one_liner_function_counts_as_one(self, tmp_path: Path) -> None:
        """
        Scenario: A single-line function (lambda-like def).
        Expected: Measured as 1 line, not 0.

        Rationale: Edge case - the bug would make this 0 lines.
        """
        # 1. Setup: Single-line function
        test_file = tmp_path / "sample.py"
        test_file.write_text(
            """def f(): return 42
"""
        )

        # 2. Action: Analyze with threshold=0 (should flag any function)
        thresholds = KISSThresholds(max_function_lines=0)
        violations = analyze_file_kiss(test_file, thresholds)

        # 3. Assertion: Should detect with value=1
        length_violations = [
            v for v in violations if v.violation_type == "length" and v.function == "f"
        ]
        assert len(length_violations) == 1, (
            f"Expected violation for 1-line function with max=0. Got {len(length_violations)}"
        )
        assert length_violations[0].value == 1, (
            f"Expected value=1 for single-line function. Got {length_violations[0].value}"
        )


class TestComplexityValidation:
    """TDD Cycle 3: Cyclomatic complexity detection."""

    def test_high_complexity_flagged(self, tmp_path: Path) -> None:
        """
        Scenario: Function with many branches (high cyclomatic complexity).
        Expected: Should be flagged when exceeding threshold.

        Rationale: Cyclomatic complexity = edges - nodes + 2 * connected components.
        For simpler calculation: 1 + number of decision points (if, elif, for, while, etc).
        """
        # 1. Setup: Function with multiple decision points
        test_file = tmp_path / "complex.py"
        test_file.write_text(
            """def complex_func(a, b, c, d, e):
    if a:
        return 1
    elif b:
        return 2
    elif c:
        return 3
    elif d:
        return 4
    elif e:
        return 5
    else:
        for i in range(10):
            if i > 5:
                return i
        while a:
            if b:
                break
    return 0
"""
        )

        # 2. Action: Analyze with low threshold
        thresholds = KISSThresholds(max_complexity=5)
        violations = analyze_file_kiss(test_file, thresholds)

        # 3. Assertion: Should detect complexity violation
        complexity_violations = [v for v in violations if v.violation_type == "complexity"]
        assert len(complexity_violations) >= 1, (
            f"Expected complexity violation for highly branched function. "
            f"Violations found: {violations}"
        )

    def test_simple_function_no_complexity_violation(self, tmp_path: Path) -> None:
        """
        Scenario: Simple function with minimal branching.
        Expected: No complexity violation with reasonable threshold.
        """
        # 1. Setup: Simple function
        test_file = tmp_path / "simple.py"
        test_file.write_text(
            """def simple(x):
    return x * 2
"""
        )

        # 2. Action: Analyze with default threshold
        thresholds = KISSThresholds(max_complexity=10)
        violations = analyze_file_kiss(test_file, thresholds)

        # 3. Assertion: No complexity violation
        complexity_violations = [v for v in violations if v.violation_type == "complexity"]
        assert len(complexity_violations) == 0


class TestNestingDepthValidation:
    """TDD Cycle 3: Nesting depth detection."""

    def test_deep_nesting_flagged(self, tmp_path: Path) -> None:
        """
        Scenario: Function with deeply nested code.
        Expected: Should be flagged when exceeding threshold.

        Rationale: Deep nesting makes code hard to follow.
        """
        # 1. Setup: Deeply nested function
        test_file = tmp_path / "nested.py"
        test_file.write_text(
            """def deeply_nested(a, b, c, d, e):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return "too deep"
    return "ok"
"""
        )

        # 2. Action: Analyze with low nesting threshold
        thresholds = KISSThresholds(max_nesting_depth=3)
        violations = analyze_file_kiss(test_file, thresholds)

        # 3. Assertion: Should detect nesting violation
        nesting_violations = [v for v in violations if v.violation_type == "nesting"]
        assert len(nesting_violations) >= 1, (
            f"Expected nesting violation for deeply nested function. Violations found: {violations}"
        )

    def test_shallow_nesting_no_violation(self, tmp_path: Path) -> None:
        """
        Scenario: Function with acceptable nesting.
        Expected: No nesting violation.
        """
        # 1. Setup: Shallow function
        test_file = tmp_path / "shallow.py"
        test_file.write_text(
            """def shallow(x):
    if x > 0:
        return x
    return 0
"""
        )

        # 2. Action: Analyze with default threshold
        thresholds = KISSThresholds(max_nesting_depth=4)
        violations = analyze_file_kiss(test_file, thresholds)

        # 3. Assertion: No nesting violation
        nesting_violations = [v for v in violations if v.violation_type == "nesting"]
        assert len(nesting_violations) == 0


class TestParameterCountValidation:
    """TDD Cycle 3: Parameter count detection."""

    def test_many_parameters_flagged_as_warning(self, tmp_path: Path) -> None:
        """
        Scenario: Function with many parameters.
        Expected: Should be flagged as warning (not error).

        Rationale: Many parameters suggest function does too much.
        """
        # 1. Setup: Function with many params
        test_file = tmp_path / "many_params.py"
        test_file.write_text(
            """def many_params(a, b, c, d, e, f, g):
    return a + b + c + d + e + f + g
"""
        )

        # 2. Action: Analyze with low param threshold
        thresholds = KISSThresholds(max_parameters=5)
        violations = analyze_file_kiss(test_file, thresholds)

        # 3. Assertion: Should detect parameter warning
        param_violations = [v for v in violations if v.violation_type == "parameters"]
        assert len(param_violations) >= 1, (
            f"Expected parameter violation for 7-param function. Violations found: {violations}"
        )
        # Parameters are warnings, not errors
        assert param_violations[0].severity == "warning"


class TestCognitiveComplexityValidation:
    """TDD Cycle 4: Cognitive complexity detection.

    Cognitive complexity weights nested structures more heavily than cyclomatic.
    Each control structure adds 1 + current nesting depth.
    """

    def test_cognitive_complexity_flags_nested_conditionals(self, tmp_path: Path) -> None:
        """
        Scenario: Deeply nested conditionals with moderate cyclomatic complexity.
        Expected: Should be flagged for cognitive complexity.

        Rationale: Nested code is harder to understand even if branch count is low.
        """
        # 1. Setup: Nested conditional pyramid
        test_file = tmp_path / "nested.py"
        test_file.write_text(
            """def decision(x):
    if x > 0:
        if x > 10:
            if x > 20:
                return 1
            else:
                return 2
        else:
            return 3
    else:
        return 4
"""
        )

        # 2. Action: Analyze with low cognitive threshold but high cyclomatic
        thresholds = KISSThresholds(
            max_complexity=50,  # High - won't trigger cyclomatic
            warning_complexity=50,
            max_cognitive_complexity=5,  # Low - should trigger cognitive
        )
        violations = analyze_file_kiss(test_file, thresholds)

        # 3. Assertion: Should detect cognitive complexity violation
        cog_violations = [
            v
            for v in violations
            if v.violation_type == "cognitive_complexity" and v.function == "decision"
        ]
        assert len(cog_violations) == 1, (
            f"Expected 1 cognitive complexity violation. "
            f"Got {len(cog_violations)}: {[v for v in violations]}"
        )
        assert cog_violations[0].severity == "error"
        assert cog_violations[0].threshold == 5
        assert cog_violations[0].value > 5

    def test_simple_function_no_cognitive_violation(self, tmp_path: Path) -> None:
        """
        Scenario: Simple function with low cognitive complexity.
        Expected: No cognitive violation.
        """
        # 1. Setup: Simple function
        test_file = tmp_path / "simple.py"
        test_file.write_text(
            """def simple(x):
    if x > 0:
        return x
    return 0
"""
        )

        # 2. Action: Analyze with default thresholds
        thresholds = KISSThresholds(max_cognitive_complexity=15)
        violations = analyze_file_kiss(test_file, thresholds)

        # 3. Assertion: No cognitive violation
        cog_violations = [v for v in violations if v.violation_type == "cognitive_complexity"]
        assert len(cog_violations) == 0

    def test_cognitive_complexity_counts_loops_and_try(self, tmp_path: Path) -> None:
        """
        Scenario: Function with nested loops and try/except.
        Expected: Each control structure adds 1 + nesting depth.

        Rationale: Loops and exception handling also contribute to cognitive load.
        """
        # 1. Setup: Function with various control structures
        test_file = tmp_path / "mixed.py"
        test_file.write_text(
            """def process(items):
    for item in items:
        try:
            if item.valid:
                while item.pending:
                    item.process()
        except Exception:
            pass
"""
        )

        # 2. Action: Analyze with low threshold
        thresholds = KISSThresholds(
            max_complexity=50,
            warning_complexity=50,
            max_cognitive_complexity=5,
        )
        violations = analyze_file_kiss(test_file, thresholds)

        # 3. Assertion: Should detect cognitive complexity
        cog_violations = [v for v in violations if v.violation_type == "cognitive_complexity"]
        assert len(cog_violations) >= 1, (
            f"Expected cognitive complexity violation for nested loops/try. Got: {violations}"
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
        test_file = tmp_path / "broken.py"
        test_file.write_text(
            """def broken(
    return 1
"""
        )

        # 2. Action: Should not crash
        thresholds = KISSThresholds()
        violations = analyze_file_kiss(test_file, thresholds)

        # 3. Assertion: Empty violations (couldn't parse)
        assert violations == [], "Syntax error files should return empty violations"

    def test_unicode_decode_error_skipped_without_crash(self, tmp_path: Path) -> None:
        """
        Scenario: A file with invalid UTF-8 bytes.
        Expected: Should not crash, return empty violations.

        Rationale: Validators should handle encoding issues gracefully.
        """
        # 1. Setup: File with invalid UTF-8
        test_file = tmp_path / "binary.py"
        test_file.write_bytes(b"\xff\xfe\xfa def foo(): pass")

        # 2. Action: Should not crash
        thresholds = KISSThresholds()
        violations = analyze_file_kiss(test_file, thresholds)

        # 3. Assertion: Empty violations (couldn't decode)
        assert violations == [], "Unicode error files should return empty violations"

    def test_empty_file_handled_gracefully(self, tmp_path: Path) -> None:
        """
        Scenario: An empty Python file.
        Expected: Should not crash, return empty violations.

        Rationale: Empty files are valid Python but have no functions.
        """
        # 1. Setup: Empty file
        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        # 2. Action: Should not crash
        thresholds = KISSThresholds()
        violations = analyze_file_kiss(test_file, thresholds)

        # 3. Assertion: Empty violations (no functions)
        assert violations == [], "Empty files should return empty violations"

    def test_file_with_only_comments_handled(self, tmp_path: Path) -> None:
        """
        Scenario: A file with only comments and docstrings.
        Expected: Should not crash, return empty violations.
        """
        # 1. Setup: Comments-only file
        test_file = tmp_path / "comments.py"
        test_file.write_text(
            '''# This is a comment
"""
This is a module docstring.
"""
# Another comment
'''
        )

        # 2. Action: Should not crash
        thresholds = KISSThresholds()
        violations = analyze_file_kiss(test_file, thresholds)

        # 3. Assertion: Empty violations (no functions)
        assert violations == [], "Comment-only files should return empty violations"


class TestComprehensionComplexity:
    """Tests for comprehension complexity counting (lines 94-97)."""

    def test_list_comprehension_with_ifs_adds_complexity(self, tmp_path: Path) -> None:
        """List comprehension with if clauses should add to complexity."""
        import ast

        # Arrange - comprehension with 2 if clauses
        code = """
def filter_items(items):
    return [x for x in items if x > 0 if x < 100]
"""
        tree = ast.parse(code)
        func_node = tree.body[0]

        # Act
        complexity = calculate_complexity(func_node)

        # Assert: 1 (base) + 1 (comprehension) + 2 (ifs) = 4
        assert complexity >= 4

    def test_nested_comprehension_adds_complexity(self, tmp_path: Path) -> None:
        """Nested comprehensions should each add complexity."""
        import ast

        code = """
def matrix_ops(matrix):
    return [cell for row in matrix for cell in row if cell > 0]
"""
        tree = ast.parse(code)
        func_node = tree.body[0]

        complexity = calculate_complexity(func_node)
        # 1 (base) + 2 (two comprehension clauses) + 1 (if) = 4
        assert complexity >= 4


class TestMccabeIntegration:
    """Tests for try_mccabe_complexity (lines 181-209)."""

    def test_mccabe_parses_output(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Mccabe output should be parsed into func->complexity map."""
        from unittest.mock import MagicMock

        # Arrange
        test_file = tmp_path / "complex.py"
        test_file.write_text("def f(): pass\n")

        mock_result = MagicMock()
        # Format: file:line:col:'funcname':complexity (5 colon-separated parts)
        mock_result.stdout = "complex.py:1:1:'f':8\n"

        monkeypatch.setattr(
            "validate_kiss.subprocess.run", lambda *a, **kw: mock_result
        )

        # Act
        result = try_mccabe_complexity(test_file, threshold=5)

        # Assert
        assert "f" in result
        assert result["f"] == 8

    def test_mccabe_not_installed_returns_empty(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
        """When mccabe is not installed, should return empty dict."""
        from unittest.mock import MagicMock

        test_file = tmp_path / "simple.py"
        test_file.write_text("def f(): pass\n")

        monkeypatch.setattr(
            "validate_kiss.subprocess.run",
            MagicMock(side_effect=FileNotFoundError("mccabe not found")),
        )

        result = try_mccabe_complexity(test_file, threshold=5)
        assert result == {}

    def test_mccabe_unparseable_line_skipped(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Unparseable mccabe output lines should be skipped."""
        from unittest.mock import MagicMock

        test_file = tmp_path / "complex.py"
        test_file.write_text("def f(): pass\n")

        mock_result = MagicMock()
        mock_result.stdout = "not:a:valid:line without number\n"

        monkeypatch.setattr(
            "validate_kiss.subprocess.run", lambda *a, **kw: mock_result
        )

        result = try_mccabe_complexity(test_file, threshold=5)
        # Should not crash, may or may not have entries
        assert isinstance(result, dict)

    def test_mccabe_result_used_in_analysis(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
        """When mccabe returns a result for a function, it should be used over AST calculation."""
        from unittest.mock import MagicMock

        test_file = tmp_path / "tested.py"
        test_file.write_text(
            '''def simple():
    return 1
'''
        )

        # Mock mccabe to return high complexity for 'simple'
        mock_result = MagicMock()
        mock_result.stdout = f"{test_file}:1:1:'simple':15\n"
        monkeypatch.setattr(
            "validate_kiss.subprocess.run", lambda *a, **kw: mock_result
        )

        # Act
        thresholds = KISSThresholds(max_complexity=10, warning_complexity=7)
        violations = analyze_file_kiss(test_file, thresholds)

        # Assert - should use mccabe's value of 15
        complexity_violations = [v for v in violations if v.violation_type == "complexity"]
        assert len(complexity_violations) == 1
        assert complexity_violations[0].value == 15


class TestVarargKwargCounting:
    """Tests for *args/**kwargs parameter counting (lines 265-268)."""

    def test_vararg_and_kwarg_counted(self, tmp_path: Path) -> None:
        """*args and **kwargs should each count as one parameter."""
        test_file = tmp_path / "varargs.py"
        test_file.write_text(
            '''def many(a, b, c, *args, **kwargs):
    return a + b + c
'''
        )

        # max_parameters=4 should flag because: a, b, c, *args, **kwargs = 5
        thresholds = KISSThresholds(max_parameters=4)
        violations = analyze_file_kiss(test_file, thresholds)

        param_violations = [v for v in violations if v.violation_type == "parameters"]
        assert len(param_violations) == 1
        assert param_violations[0].value == 5


class TestGenerateRecommendationsKISS:
    """Tests for generate_recommendations (lines 314-343)."""

    def test_complexity_recommendation(self) -> None:
        """Complexity violations should generate complexity recommendation."""
        violations = [
            KISSViolation(
                file="test.py", function="f", line=1,
                violation_type="complexity", value=15, threshold=10, severity="error",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("COMPLEXITY" in r for r in recs)

    def test_length_recommendation(self) -> None:
        """Length violations should generate length recommendation."""
        violations = [
            KISSViolation(
                file="test.py", function="f", line=1,
                violation_type="length", value=60, threshold=50, severity="error",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("LENGTH" in r for r in recs)

    def test_nesting_recommendation(self) -> None:
        """Nesting violations should generate nesting recommendation."""
        violations = [
            KISSViolation(
                file="test.py", function="f", line=1,
                violation_type="nesting", value=5, threshold=4, severity="error",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("NESTING" in r for r in recs)

    def test_parameters_recommendation(self) -> None:
        """Parameter violations should generate parameters recommendation."""
        violations = [
            KISSViolation(
                file="test.py", function="f", line=1,
                violation_type="parameters", value=8, threshold=5, severity="warning",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("PARAMETERS" in r for r in recs)

    def test_empty_violations_no_recommendations(self) -> None:
        """No violations should produce no recommendations."""
        recs = generate_recommendations([])
        assert recs == []


class TestValidateKISS:
    """Tests for validate_kiss orchestration (lines 346-378)."""

    def test_clean_files_pass(self, tmp_path: Path) -> None:
        """Clean simple files should pass validation."""
        test_file = tmp_path / "clean.py"
        test_file.write_text("def add(a, b): return a + b\n")

        result = validate_kiss(str(tmp_path), all_files=True)
        assert result.allowed is True
        assert result.summary["files_analyzed"] >= 1

    def test_errors_block_validation(self, tmp_path: Path) -> None:
        """Files with complexity errors should block validation."""
        # Create a very complex function
        test_file = tmp_path / "complex.py"
        test_file.write_text(
            '''def mega_complex(a, b, c, d, e, f, g, h, i, j, k):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        if f:
                            return 1
    return 0
'''
        )

        thresholds = KISSThresholds(max_nesting_depth=3)
        result = validate_kiss(str(tmp_path), thresholds=thresholds, all_files=True)
        assert result.allowed is False

    def test_strict_mode_blocks_on_warnings(self, tmp_path: Path) -> None:
        """Strict mode should block on warnings too."""
        test_file = tmp_path / "many_params.py"
        test_file.write_text(
            '''def f(a, b, c, d, e, f_param, g):
    return a
'''
        )

        thresholds = KISSThresholds(max_parameters=5)
        result = validate_kiss(str(tmp_path), thresholds=thresholds, strict=True, all_files=True)
        assert result.summary["warnings"] > 0
        assert result.allowed is False

    def test_default_thresholds_used(self, tmp_path: Path) -> None:
        """When no thresholds passed, defaults should be used."""
        test_file = tmp_path / "simple.py"
        test_file.write_text("x = 1\n")

        result = validate_kiss(str(tmp_path), all_files=True)
        assert result.allowed is True


class TestKISSCLI:
    """Tests for main() CLI entrypoint (lines 381-477)."""

    def test_json_output(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch", capsys: "pytest.CaptureFixture") -> None:
        """--json flag should produce JSON output."""
        import json as json_mod

        test_file = tmp_path / "simple.py"
        test_file.write_text("x = 1\n")
        monkeypatch.setattr(
            "sys.argv",
            ["validate_kiss", "--scope-root", str(tmp_path), "--all", "--json"],
        )

        try:
            main()
        except SystemExit:
            pass

        captured = capsys.readouterr()
        output = json_mod.loads(captured.out)
        assert "allowed" in output
        assert "summary" in output

    def test_text_output(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch", capsys: "pytest.CaptureFixture") -> None:
        """Default text output should include key sections."""
        test_file = tmp_path / "simple.py"
        test_file.write_text("x = 1\n")
        monkeypatch.setattr(
            "sys.argv",
            ["validate_kiss", "--scope-root", str(tmp_path), "--all"],
        )

        try:
            main()
        except SystemExit:
            pass

        captured = capsys.readouterr()
        assert "KISS Validation:" in captured.out
        assert "Files analyzed:" in captured.out

    def test_exit_code_zero_on_pass(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Clean code should exit with code 0."""
        import pytest

        test_file = tmp_path / "clean.py"
        test_file.write_text("x = 1\n")
        monkeypatch.setattr(
            "sys.argv",
            ["validate_kiss", "--scope-root", str(tmp_path), "--all"],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_exit_code_two_on_block(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Blocked validation should exit with code 2."""
        import pytest

        test_file = tmp_path / "complex.py"
        test_file.write_text(
            '''def deep(a, b, c, d, e):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return 1
    return 0
'''
        )
        monkeypatch.setattr(
            "sys.argv",
            ["validate_kiss", "--scope-root", str(tmp_path), "--all", "--max-depth", "3"],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    def test_text_output_with_violations(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch", capsys: "pytest.CaptureFixture") -> None:
        """Text output with violations should show details."""
        test_file = tmp_path / "complex.py"
        test_file.write_text(
            '''def deep(a, b, c, d, e):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return 1
    return 0
'''
        )
        monkeypatch.setattr(
            "sys.argv",
            ["validate_kiss", "--scope-root", str(tmp_path), "--all", "--max-depth", "3"],
        )

        try:
            main()
        except SystemExit:
            pass

        captured = capsys.readouterr()
        assert "Violations:" in captured.out
