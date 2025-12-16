"""Tests for CommandExecutor utility methods."""

from __future__ import annotations

from SuperClaude.Commands.parser import ParsedCommand


class TestSlugify:
    """Tests for _slugify method."""

    def test_slugify_basic_string(self, executor):
        """Slugify converts spaces to hyphens."""
        assert executor._slugify("Hello World") == "hello-world"

    def test_slugify_special_characters(self, executor):
        """Slugify removes special characters."""
        assert executor._slugify("test!@#$%feature") == "test-feature"

    def test_slugify_multiple_hyphens(self, executor):
        """Slugify collapses multiple hyphens."""
        assert executor._slugify("test---feature") == "test-feature"

    def test_slugify_preserves_underscores(self, executor):
        """Slugify keeps underscores."""
        assert executor._slugify("test_feature") == "test_feature"

    def test_slugify_empty_string(self, executor):
        """Slugify returns default for empty input."""
        assert executor._slugify("") == "implementation"

    def test_slugify_only_special_chars(self, executor):
        """Slugify returns default for only special characters."""
        assert executor._slugify("!@#$%") == "implementation"

    def test_slugify_unicode(self, executor):
        """Slugify handles unicode characters."""
        result = executor._slugify("caf\u00e9 feature")
        assert "caf" in result  # cafe with accent
        assert "-" in result or "feature" in result


class TestDeduplicate:
    """Tests for _deduplicate method."""

    def test_deduplicate_removes_duplicates(self, executor):
        """Deduplicate removes duplicate entries."""
        result = executor._deduplicate(["a", "b", "a", "c", "b"])
        assert result == ["a", "b", "c"]

    def test_deduplicate_preserves_order(self, executor):
        """Deduplicate maintains first occurrence order."""
        result = executor._deduplicate(["c", "b", "a", "c", "b"])
        assert result == ["c", "b", "a"]

    def test_deduplicate_empty_list(self, executor):
        """Deduplicate handles empty list."""
        assert executor._deduplicate([]) == []

    def test_deduplicate_strips_whitespace(self, executor):
        """Deduplicate strips whitespace from entries."""
        result = executor._deduplicate(["  a  ", "a", " a"])
        assert result == ["a"]

    def test_deduplicate_removes_empty_strings(self, executor):
        """Deduplicate removes empty strings."""
        result = executor._deduplicate(["a", "", "  ", "b"])
        assert result == ["a", "b"]

    def test_deduplicate_single_item(self, executor):
        """Deduplicate handles single item list."""
        assert executor._deduplicate(["only"]) == ["only"]


class TestIsTruthy:
    """Tests for _is_truthy method."""

    def test_is_truthy_bool_true(self, executor):
        """is_truthy returns True for boolean True."""
        assert executor._is_truthy(True) is True

    def test_is_truthy_bool_false(self, executor):
        """is_truthy returns False for boolean False."""
        assert executor._is_truthy(False) is False

    def test_is_truthy_int_nonzero(self, executor):
        """is_truthy returns True for non-zero int."""
        assert executor._is_truthy(1) is True
        assert executor._is_truthy(42) is True

    def test_is_truthy_int_zero(self, executor):
        """is_truthy returns False for zero."""
        assert executor._is_truthy(0) is False

    def test_is_truthy_string_true(self, executor):
        """is_truthy returns True for truthy strings."""
        for val in ["true", "True", "TRUE", "yes", "Yes", "1", "on", "enabled"]:
            assert executor._is_truthy(val) is True, f"Failed for {val}"

    def test_is_truthy_string_false(self, executor):
        """is_truthy returns False for non-truthy strings."""
        for val in ["false", "False", "no", "0", "off", "disabled", "random"]:
            assert executor._is_truthy(val) is False, f"Failed for {val}"

    def test_is_truthy_none(self, executor):
        """is_truthy returns False for None."""
        assert executor._is_truthy(None) is False


class TestFlagPresent:
    """Tests for _flag_present method."""

    def test_flag_present_in_flags(self, executor):
        """flag_present finds flag in flags dict."""
        parsed = ParsedCommand(
            name="test",
            raw_string="/sc:test --safe",
            flags={"safe": True},
            parameters={},
        )
        assert executor._flag_present(parsed, "safe") is True

    def test_flag_present_with_underscore_alias(self, executor):
        """flag_present handles underscore/hyphen aliases."""
        parsed = ParsedCommand(
            name="test",
            raw_string="/sc:test --with-tests",
            flags={"with_tests": True},
            parameters={},
        )
        assert executor._flag_present(parsed, "with-tests") is True

    def test_flag_present_in_parameters(self, executor):
        """flag_present checks parameters too."""
        parsed = ParsedCommand(
            name="test",
            raw_string="/sc:test",
            flags={},
            parameters={"safe": True},
        )
        assert executor._flag_present(parsed, "safe") is True

    def test_flag_present_string_true(self, executor):
        """flag_present handles string 'true' in parameters."""
        parsed = ParsedCommand(
            name="test",
            raw_string="/sc:test",
            flags={},
            parameters={"force": "true"},
        )
        assert executor._flag_present(parsed, "force") is True

    def test_flag_absent(self, executor):
        """flag_present returns False when flag not found."""
        parsed = ParsedCommand(
            name="test",
            raw_string="/sc:test",
            flags={},
            parameters={},
        )
        assert executor._flag_present(parsed, "missing") is False


class TestCoerceFloat:
    """Tests for _coerce_float method."""

    def test_coerce_float_from_int(self, executor):
        """coerce_float converts int to float."""
        assert executor._coerce_float(42, None) == 42.0

    def test_coerce_float_from_string(self, executor):
        """coerce_float converts numeric string."""
        assert executor._coerce_float("3.14", None) == 3.14

    def test_coerce_float_from_bool_true(self, executor):
        """coerce_float converts True to 1.0."""
        assert executor._coerce_float(True, None) == 1.0

    def test_coerce_float_from_bool_false(self, executor):
        """coerce_float converts False to 0.0."""
        assert executor._coerce_float(False, None) == 0.0

    def test_coerce_float_invalid_returns_default(self, executor):
        """coerce_float returns default for invalid input."""
        assert executor._coerce_float("not-a-number", 0.5) == 0.5

    def test_coerce_float_none_returns_default(self, executor):
        """coerce_float returns default for None."""
        assert executor._coerce_float(None, 1.0) == 1.0


class TestClampInt:
    """Tests for _clamp_int method."""

    def test_clamp_int_within_bounds(self, executor):
        """clamp_int keeps value within bounds."""
        assert executor._clamp_int(5, 0, 10, 0) == 5

    def test_clamp_int_below_minimum(self, executor):
        """clamp_int clamps to minimum."""
        assert executor._clamp_int(-5, 0, 10, 0) == 0

    def test_clamp_int_above_maximum(self, executor):
        """clamp_int clamps to maximum."""
        assert executor._clamp_int(15, 0, 10, 0) == 10

    def test_clamp_int_at_boundary(self, executor):
        """clamp_int handles boundary values."""
        assert executor._clamp_int(0, 0, 10, 5) == 0
        assert executor._clamp_int(10, 0, 10, 5) == 10

    def test_clamp_int_from_string(self, executor):
        """clamp_int converts string to int."""
        assert executor._clamp_int("7", 0, 10, 0) == 7

    def test_clamp_int_invalid_returns_default(self, executor):
        """clamp_int returns default for invalid input."""
        assert executor._clamp_int("invalid", 0, 10, 5) == 5

    def test_clamp_int_from_bool(self, executor):
        """clamp_int converts bool to int."""
        assert executor._clamp_int(True, 0, 10, 5) == 1
        assert executor._clamp_int(False, 0, 10, 5) == 0


class TestToList:
    """Tests for _to_list method."""

    def test_to_list_from_list(self, executor):
        """to_list passes through list."""
        assert executor._to_list(["a", "b", "c"]) == ["a", "b", "c"]

    def test_to_list_from_string(self, executor):
        """to_list wraps string in list."""
        assert executor._to_list("single") == ["single"]

    def test_to_list_from_comma_separated(self, executor):
        """to_list splits comma-separated string."""
        assert executor._to_list("a,b,c") == ["a", "b", "c"]

    def test_to_list_from_tuple(self, executor):
        """to_list converts tuple to list."""
        assert executor._to_list(("a", "b")) == ["a", "b"]

    def test_to_list_from_set(self, executor):
        """to_list converts set to list."""
        result = executor._to_list({"a", "b"})
        assert sorted(result) == ["a", "b"]

    def test_to_list_none(self, executor):
        """to_list returns empty list for None."""
        assert executor._to_list(None) == []

    def test_to_list_empty_string(self, executor):
        """to_list returns empty list for empty string."""
        assert executor._to_list("") == []

    def test_to_list_strips_whitespace(self, executor):
        """to_list strips whitespace from items."""
        assert executor._to_list("  a  ,  b  ") == ["a", "b"]


class TestTruncateOutput:
    """Tests for _truncate_output method."""

    def test_truncate_short_text(self, executor):
        """truncate_output returns short text unchanged."""
        text = "short text"
        assert executor._truncate_output(text, 100) == text

    def test_truncate_long_text(self, executor):
        """truncate_output truncates long text."""
        text = "a" * 1000
        result = executor._truncate_output(text, 100)
        assert len(result) < len(text)
        assert "[truncated]" in result

    def test_truncate_preserves_head_and_tail(self, executor):
        """truncate_output keeps beginning and end."""
        text = "START" + ("x" * 1000) + "END"
        result = executor._truncate_output(text, 100)
        assert result.startswith("START")
        assert result.endswith("END")

    def test_truncate_empty_string(self, executor):
        """truncate_output handles empty string."""
        assert executor._truncate_output("", 100) == ""

    def test_truncate_none(self, executor):
        """truncate_output handles None."""
        assert executor._truncate_output(None, 100) is None


class TestNormalizeEvidenceValue:
    """Tests for _normalize_evidence_value method."""

    def test_normalize_string(self, executor):
        """normalize_evidence_value handles string."""
        assert executor._normalize_evidence_value("test") == ["test"]

    def test_normalize_list(self, executor):
        """normalize_evidence_value flattens list."""
        assert executor._normalize_evidence_value(["a", "b"]) == ["a", "b"]

    def test_normalize_nested_list(self, executor):
        """normalize_evidence_value flattens nested list."""
        result = executor._normalize_evidence_value([["a", "b"], "c"])
        assert result == ["a", "b", "c"]

    def test_normalize_dict(self, executor):
        """normalize_evidence_value formats dict entries."""
        result = executor._normalize_evidence_value({"key": "value"})
        assert "key: value" in result

    def test_normalize_none(self, executor):
        """normalize_evidence_value returns empty for None."""
        assert executor._normalize_evidence_value(None) == []

    def test_normalize_empty_string(self, executor):
        """normalize_evidence_value returns empty for empty string."""
        assert executor._normalize_evidence_value("") == []


class TestEnsureList:
    """Tests for _ensure_list method."""

    def test_ensure_list_existing_list(self, executor):
        """ensure_list returns existing list."""
        container = {"key": ["a", "b"]}
        result = executor._ensure_list(container, "key")
        assert result == ["a", "b"]

    def test_ensure_list_none_value(self, executor):
        """ensure_list creates empty list for None."""
        container = {"key": None}
        result = executor._ensure_list(container, "key")
        assert result == []
        assert container["key"] == []

    def test_ensure_list_string_value(self, executor):
        """ensure_list wraps string in list."""
        container = {"key": "value"}
        result = executor._ensure_list(container, "key")
        assert result == ["value"]
        assert container["key"] == ["value"]

    def test_ensure_list_missing_key(self, executor):
        """ensure_list creates entry for missing key."""
        container = {}
        result = executor._ensure_list(container, "key")
        assert result == []
        assert container["key"] == []
