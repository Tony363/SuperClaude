#!/usr/bin/env python3
"""Tests for Let It Crash validator."""

from pathlib import Path

from scripts.validate_crash import (
    CrashThresholds,
    CrashViolation,
    analyze_file_crash,
    generate_recommendations,
    main,
    validate_crash,
)


class TestBareExceptDetection:
    """Test detection of bare except: clauses."""

    def test_bare_except(self, tmp_path: Path) -> None:
        """Bare except: should be flagged as error."""
        code = """
def bad_function():
    try:
        risky_operation()
    except:
        pass
"""
        test_file = tmp_path / "bare_except.py"
        test_file.write_text(code)

        violations = analyze_file_crash(test_file, CrashThresholds())

        assert any(v.violation_type == "bare_except" for v in violations)
        assert any(v.severity == "error" for v in violations)

    def test_except_pass(self, tmp_path: Path) -> None:
        """except: pass should be flagged as error."""
        code = """
def silent_failure():
    try:
        something()
    except Exception:
        pass
"""
        test_file = tmp_path / "except_pass.py"
        test_file.write_text(code)

        violations = analyze_file_crash(test_file, CrashThresholds())

        assert any(v.violation_type == "except_pass" for v in violations)


class TestExceptionSwallowing:
    """Test detection of swallowed exceptions."""

    def test_exception_swallowed(self, tmp_path: Path) -> None:
        """except Exception without re-raise should be warning in core paths."""
        # Place in a core path (not in handlers/adapters/api/cli/scripts/tests)
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        code = """
def swallows_error():
    try:
        something()
    except Exception as e:
        print(f"Error: {e}")
        return None
"""
        test_file = core_dir / "swallowed.py"
        test_file.write_text(code)

        violations = analyze_file_crash(test_file, CrashThresholds())
        assert any(v.violation_type == "exception_swallowed" for v in violations)

    def test_exception_with_reraise_ok(self, tmp_path: Path) -> None:
        """except with re-raise should NOT be flagged."""
        code = """
def handles_properly():
    try:
        something()
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
"""
        test_file = tmp_path / "reraise.py"
        test_file.write_text(code)

        violations = analyze_file_crash(test_file, CrashThresholds())

        # Re-raise is acceptable
        assert not any(v.violation_type == "exception_swallowed" for v in violations)

    def test_specific_exception_ok(self, tmp_path: Path) -> None:
        """Catching specific exceptions is acceptable."""
        code = """
def handles_specific():
    try:
        something()
    except ValueError as e:
        return default_value
"""
        test_file = tmp_path / "specific.py"
        test_file.write_text(code)

        violations = analyze_file_crash(test_file, CrashThresholds())

        # Specific exceptions are OK
        assert not any(v.violation_type == "bare_except" for v in violations)


class TestNestedTryExcept:
    """Test detection of nested try/except patterns."""

    def test_nested_try_except(self, tmp_path: Path) -> None:
        """Nested try/except should be flagged as warning."""
        code = """
def complex_fallback():
    try:
        primary_operation()
    except:
        try:
            fallback_operation()
        except:
            try:
                last_resort()
            except:
                return None
"""
        test_file = tmp_path / "nested.py"
        test_file.write_text(code)

        violations = analyze_file_crash(test_file, CrashThresholds())

        assert any(v.violation_type == "nested_try_except" for v in violations)


class TestShellPathExceptions:
    """Test that shell paths have relaxed rules."""

    def test_adapters_path_relaxed(self, tmp_path: Path) -> None:
        """Files in adapters/ should have relaxed error handling rules."""
        adapters_dir = tmp_path / "adapters"
        adapters_dir.mkdir()

        code = """
def external_api_call():
    try:
        response = api.get(url)
    except Exception as e:
        logger.error(f"API failed: {e}")
        return None
"""
        test_file = adapters_dir / "external.py"
        test_file.write_text(code)

        violations = analyze_file_crash(test_file, CrashThresholds())
        # Shell paths should NOT flag exception_swallowed
        assert not any(v.violation_type == "exception_swallowed" for v in violations)

    def test_api_path_relaxed(self, tmp_path: Path) -> None:
        """Files in api/ should have relaxed error handling rules."""
        api_dir = tmp_path / "api"
        api_dir.mkdir()

        code = """
@app.get("/users/{id}")
def get_user(id: int):
    try:
        return db.get_user(id)
    except Exception as e:
        raise HTTPException(500, "Database error")
"""
        test_file = api_dir / "routes.py"
        test_file.write_text(code)

        violations = analyze_file_crash(test_file, CrashThresholds())
        # API handlers can catch and convert exceptions — no swallowed warning
        assert not any(v.violation_type == "exception_swallowed" for v in violations)


class TestValidationResult:
    """Test overall validation result."""

    def test_clean_file_passes(self, tmp_path: Path) -> None:
        """Clean files should pass validation."""
        code = """
def simple_function(x: int) -> int:
    return x * 2
"""
        test_file = tmp_path / "clean.py"
        test_file.write_text(code)

        result = validate_crash(str(tmp_path), all_files=True)
        assert result.allowed

    def test_json_output(self, tmp_path: Path) -> None:
        """Result should be JSON serializable."""
        code = "x = 1"
        test_file = tmp_path / "simple.py"
        test_file.write_text(code)

        result = validate_crash(str(tmp_path), all_files=True)

        # Should not raise
        import json

        json.dumps(
            {
                "allowed": result.allowed,
                "violations": result.violations,
                "summary": result.summary,
            }
        )


class TestEdgeCases:
    """Test edge cases."""

    def test_syntax_error_file(self, tmp_path: Path) -> None:
        """Syntax errors should not crash validator."""
        test_file = tmp_path / "bad.py"
        test_file.write_text("def broken(")

        violations = analyze_file_crash(test_file, CrashThresholds())
        # Should return empty list, not crash
        assert violations == []

    def test_empty_file(self, tmp_path: Path) -> None:
        """Empty files should not crash."""
        test_file = tmp_path / "empty.py"
        test_file.write_text("")

        violations = analyze_file_crash(test_file, CrashThresholds())
        assert violations == []

    def test_try_finally_without_except(self, tmp_path: Path) -> None:
        """try/finally without except should not be flagged."""
        code = """
def uses_finally():
    f = open("file.txt")
    try:
        return f.read()
    finally:
        f.close()
"""
        test_file = tmp_path / "finally_only.py"
        test_file.write_text(code)

        violations = analyze_file_crash(test_file, CrashThresholds())

        # try/finally is fine
        assert not violations


class TestAsyncFunctionTracking:
    """Tests for async function context tracking (lines 92-97)."""

    def test_async_function_context_tracked(self, tmp_path: Path) -> None:
        """Async function names should be tracked in violation context."""
        code = """
async def async_handler():
    try:
        await do_thing()
    except:
        pass
"""
        test_file = tmp_path / "async_crash.py"
        test_file.write_text(code)

        violations = analyze_file_crash(test_file, CrashThresholds())

        # Should have violations with async function context
        assert any(v.context == "async_handler" for v in violations)


class TestDocstringOnlyPassBody:
    """Tests for docstring-only handler body detection (lines 175-177)."""

    def test_docstring_only_treated_as_pass(self, tmp_path: Path) -> None:
        """except body with only a docstring should be treated as pass."""
        code = '''
def bad_handler():
    try:
        risky()
    except Exception:
        "This is just a docstring, effectively pass"
'''
        test_file = tmp_path / "docstring_pass.py"
        test_file.write_text(code)

        violations = analyze_file_crash(test_file, CrashThresholds())

        assert any(v.violation_type == "except_pass" for v in violations)


class TestBroadExceptionTuple:
    """Tests for broad exception detection with tuple (lines 188-194)."""

    def test_exception_tuple_with_broad(self, tmp_path: Path) -> None:
        """except (ValueError, Exception) should be flagged as broad."""
        # Place in core path to get exception_swallowed
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        code = """
def handler():
    try:
        risky()
    except (ValueError, Exception) as e:
        return None
"""
        test_file = core_dir / "tuple_except.py"
        test_file.write_text(code)

        violations = analyze_file_crash(test_file, CrashThresholds())

        assert any(v.violation_type == "exception_swallowed" for v in violations)

    def test_exception_tuple_without_broad_not_flagged(self, tmp_path: Path) -> None:
        """except (ValueError, TypeError) should NOT be flagged as broad."""
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        code = """
def handler():
    try:
        risky()
    except (ValueError, TypeError) as e:
        return None
"""
        test_file = core_dir / "specific_tuple.py"
        test_file.write_text(code)

        violations = analyze_file_crash(test_file, CrashThresholds())

        assert not any(v.violation_type == "exception_swallowed" for v in violations)


class TestGenerateRecommendationsCrash:
    """Tests for generate_recommendations (lines 225-254)."""

    def test_bare_except_recommendation(self) -> None:
        """Bare except violations should generate appropriate recommendation."""
        violations = [
            CrashViolation(
                file="test.py", line=1, violation_type="bare_except",
                message="test", severity="error",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("BARE EXCEPT" in r for r in recs)

    def test_except_pass_recommendation(self) -> None:
        """Except pass violations should generate recommendation."""
        violations = [
            CrashViolation(
                file="test.py", line=1, violation_type="except_pass",
                message="test", severity="error",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("SILENT FAILURE" in r for r in recs)

    def test_swallowed_recommendation(self) -> None:
        """Swallowed exception violations should generate recommendation."""
        violations = [
            CrashViolation(
                file="test.py", line=1, violation_type="exception_swallowed",
                message="test", severity="warning",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("SWALLOWED EXCEPTION" in r for r in recs)

    def test_nested_recommendation(self) -> None:
        """Nested try/except violations should generate recommendation."""
        violations = [
            CrashViolation(
                file="test.py", line=1, violation_type="nested_try_except",
                message="test", severity="warning",
            )
        ]
        recs = generate_recommendations(violations)
        assert any("NESTED TRY/EXCEPT" in r for r in recs)

    def test_empty_violations_no_recommendations(self) -> None:
        """No violations should produce no recommendations."""
        recs = generate_recommendations([])
        assert recs == []


class TestValidateCrashOrchestration:
    """Tests for validate_crash orchestration (lines 257-303)."""

    def test_blocked_on_errors(self, tmp_path: Path) -> None:
        """Errors should block validation."""
        code = """
def bad():
    try:
        risky()
    except:
        pass
"""
        test_file = tmp_path / "bad.py"
        test_file.write_text(code)

        result = validate_crash(str(tmp_path), all_files=True)
        assert result.allowed is False
        assert result.summary["errors"] > 0
        assert result.summary["blocked"] is True

    def test_strict_mode_blocks_warnings(self, tmp_path: Path) -> None:
        """Strict mode should block on warnings."""
        # Place in core path to get exception_swallowed warning
        core_dir = tmp_path / "domain"
        core_dir.mkdir()
        code = """
def handler():
    try:
        risky()
    except Exception as e:
        return None
"""
        test_file = core_dir / "swallow.py"
        test_file.write_text(code)

        result = validate_crash(str(tmp_path), strict=True, all_files=True)
        assert result.summary["warnings"] > 0
        assert result.allowed is False

    def test_by_type_summary(self, tmp_path: Path) -> None:
        """Summary should include by_type breakdown."""
        code = """
def bad():
    try:
        risky()
    except:
        pass
"""
        test_file = tmp_path / "bad.py"
        test_file.write_text(code)

        result = validate_crash(str(tmp_path), all_files=True)
        assert "by_type" in result.summary
        assert "bare_except" in result.summary["by_type"]
        assert "except_pass" in result.summary["by_type"]


class TestCrashCLI:
    """Tests for main() CLI entrypoint (lines 306-384)."""

    def test_json_output(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch", capsys: "pytest.CaptureFixture") -> None:
        """--json flag should produce JSON output."""
        import json as json_mod

        test_file = tmp_path / "simple.py"
        test_file.write_text("x = 1\n")
        monkeypatch.setattr(
            "sys.argv",
            ["validate_crash", "--scope-root", str(tmp_path), "--all", "--json"],
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
            ["validate_crash", "--scope-root", str(tmp_path), "--all"],
        )

        try:
            main()
        except SystemExit:
            pass

        captured = capsys.readouterr()
        assert "Let It Crash Validation:" in captured.out
        assert "Files analyzed:" in captured.out

    def test_exit_code_zero_on_pass(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Clean code should exit with code 0."""
        import pytest

        test_file = tmp_path / "clean.py"
        test_file.write_text("x = 1\n")
        monkeypatch.setattr(
            "sys.argv",
            ["validate_crash", "--scope-root", str(tmp_path), "--all"],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_exit_code_two_on_block(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch") -> None:
        """Blocked validation should exit with code 2."""
        import pytest

        test_file = tmp_path / "bad.py"
        test_file.write_text(
            """
def bad():
    try:
        x()
    except:
        pass
"""
        )
        monkeypatch.setattr(
            "sys.argv",
            ["validate_crash", "--scope-root", str(tmp_path), "--all"],
        )

        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 2

    def test_text_output_with_violations_shows_by_type(self, tmp_path: Path, monkeypatch: "pytest.MonkeyPatch", capsys: "pytest.CaptureFixture") -> None:
        """Text output with violations should show By Type section."""
        test_file = tmp_path / "bad.py"
        test_file.write_text(
            """
def bad():
    try:
        x()
    except:
        pass
"""
        )
        monkeypatch.setattr(
            "sys.argv",
            ["validate_crash", "--scope-root", str(tmp_path), "--all"],
        )

        try:
            main()
        except SystemExit:
            pass

        captured = capsys.readouterr()
        assert "By Type:" in captured.out
        assert "Violations:" in captured.out
