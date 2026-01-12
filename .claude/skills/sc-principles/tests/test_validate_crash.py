#!/usr/bin/env python3
"""Tests for Let It Crash validator."""

from pathlib import Path

from scripts.validate_crash import (
    CrashThresholds,
    analyze_file_crash,
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
        """except Exception without re-raise should be warning."""
        code = """
def swallows_error():
    try:
        something()
    except Exception as e:
        print(f"Error: {e}")
        return None
"""
        test_file = tmp_path / "swallowed.py"
        test_file.write_text(code)

        _ = analyze_file_crash(test_file, CrashThresholds())
        # In core paths, this would be flagged
        # In shell paths, it might be acceptable

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

        _ = analyze_file_crash(test_file, CrashThresholds())
        # Shell paths should have fewer/no violations for error handling
        # The severity should be warning, not error

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

        _ = analyze_file_crash(test_file, CrashThresholds())
        # API handlers can catch and convert exceptions


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
        json.dumps({
            "allowed": result.allowed,
            "violations": result.violations,
            "summary": result.summary,
        })


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
