"""Tests for data sanitization in MCP fixture capture.

These tests ensure sensitive data is properly sanitized before being
written to fixture files.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from tests.mcp.live_mcp_client import (
    _apply_global_sanitization,
    _sanitize_dict_strings,
    check_fixture_staleness,
    register_tool_sanitizer,
    sanitize_capture,
)


class TestGlobalSanitization:
    """Tests for global regex-based sanitization."""

    def test_sanitize_email_addresses(self):
        """Email addresses should be replaced."""
        text = "Contact john.doe@company.com for details"
        result = _apply_global_sanitization(text)
        assert "john.doe@company.com" not in result
        assert "user@example.com" in result

    def test_sanitize_multiple_emails(self):
        """Multiple emails in same text should all be replaced."""
        text = "From: alice@test.org To: bob@other.net"
        result = _apply_global_sanitization(text)
        assert "@test.org" not in result
        assert "@other.net" not in result
        assert result.count("user@example.com") == 2

    def test_sanitize_bearer_token(self):
        """Bearer tokens should be redacted."""
        text = (
            "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0"
        )
        result = _apply_global_sanitization(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "Bearer [REDACTED]" in result

    def test_sanitize_aws_key(self):
        """AWS-style keys should be redacted."""
        text = "key: AKIAIOSFODNN7EXAMPLE"
        result = _apply_global_sanitization(text)
        assert "AKIAIOSFODNN7EXAMPLE" not in result
        assert "[REDACTED_AWS_KEY]" in result

    def test_sanitize_phone_numbers(self):
        """Phone numbers should be replaced."""
        text = "Call me at 555-123-4567"
        result = _apply_global_sanitization(text)
        assert "555-123-4567" not in result
        assert "555-000-0000" in result

    def test_sanitize_phone_with_dots(self):
        """Phone numbers with dot separators should be replaced."""
        text = "Phone: 555.123.4567"
        result = _apply_global_sanitization(text)
        assert "555.123.4567" not in result

    def test_sanitize_credit_card(self):
        """Credit card numbers should be redacted."""
        text = "Card: 4111-1111-1111-1111"
        result = _apply_global_sanitization(text)
        assert "4111-1111-1111-1111" not in result
        assert "[REDACTED_CC]" in result

    def test_sanitize_public_ip(self):
        """Public IP addresses should be sanitized."""
        text = "Server at 8.8.8.8"
        result = _apply_global_sanitization(text)
        assert "8.8.8.8" not in result
        assert "203.0.113.1" in result

    def test_preserve_private_ip(self):
        """Private IP addresses should be preserved."""
        text = "Internal: 192.168.1.100 and 10.0.0.1 and 172.16.0.1"
        result = _apply_global_sanitization(text)
        assert "192.168.1.100" in result
        assert "10.0.0.1" in result
        assert "172.16.0.1" in result

    def test_sanitize_long_token(self):
        """Long alphanumeric tokens should be redacted."""
        text = 'api_key = "abcdefghijklmnopqrstuvwxyz123456789012"'
        result = _apply_global_sanitization(text)
        assert "abcdefghijklmnopqrstuvwxyz123456789012" not in result


class TestDictSanitization:
    """Tests for recursive dict sanitization."""

    def test_sanitize_nested_dict(self):
        """Nested dicts should be recursively sanitized."""
        data = {
            "user": {
                "email": "secret@company.com",
                "profile": {
                    "contact": "call 555-123-4567",
                },
            }
        }
        result = _sanitize_dict_strings(data)
        assert result["user"]["email"] == "user@example.com"
        assert "555-123-4567" not in result["user"]["profile"]["contact"]

    def test_sanitize_list_of_strings(self):
        """Lists of strings should be sanitized."""
        data = {
            "emails": ["alice@test.com", "bob@test.com"],
        }
        result = _sanitize_dict_strings(data)
        assert all(email == "user@example.com" for email in result["emails"])

    def test_sanitize_list_of_dicts(self):
        """Lists of dicts should be recursively sanitized."""
        data = {
            "users": [
                {"email": "user1@test.com"},
                {"email": "user2@test.com"},
            ]
        }
        result = _sanitize_dict_strings(data)
        assert all(u["email"] == "user@example.com" for u in result["users"])

    def test_preserve_non_string_values(self):
        """Non-string values should be preserved."""
        data = {
            "count": 42,
            "active": True,
            "ratio": 3.14,
            "empty": None,
        }
        result = _sanitize_dict_strings(data)
        assert result["count"] == 42
        assert result["active"] is True
        assert result["ratio"] == 3.14
        assert result["empty"] is None


class TestToolSpecificSanitization:
    """Tests for tool-specific sanitizer registration."""

    def test_register_and_apply_tool_sanitizer(self):
        """Tool-specific sanitizer should be applied."""

        def custom_sanitizer(data: dict) -> dict:
            import copy

            data = copy.deepcopy(data)
            if "custom_field" in data:
                data["custom_field"] = "[CUSTOM_REDACTED]"
            return data

        register_tool_sanitizer("mcp__test__tool", custom_sanitizer)

        data = {"custom_field": "sensitive_value", "other": "keep"}
        result = sanitize_capture("mcp__test__tool", data)

        assert result["custom_field"] == "[CUSTOM_REDACTED]"
        assert result["other"] == "keep"

    def test_tool_sanitizer_runs_after_global(self):
        """Tool-specific sanitizer receives globally-sanitized data."""

        def check_sanitizer(data: dict) -> dict:
            # Email should already be sanitized by global pass
            assert data.get("email") == "user@example.com"
            return data

        register_tool_sanitizer("mcp__test__check", check_sanitizer)

        data = {"email": "original@company.com"}
        sanitize_capture("mcp__test__check", data)

    def test_tool_sanitizer_error_handled(self):
        """Tool-specific sanitizer errors should not crash."""

        def failing_sanitizer(data: dict) -> dict:
            raise ValueError("Intentional failure")

        register_tool_sanitizer("mcp__test__fail", failing_sanitizer)

        data = {"field": "value"}
        # Should not raise, just log warning
        result = sanitize_capture("mcp__test__fail", data)
        assert result["field"] == "value"


class TestFixtureStaleness:
    """Tests for fixture staleness checking."""

    def test_empty_directory(self, tmp_path):
        """Empty directory should report 0 fixtures."""
        report = check_fixture_staleness(tmp_path)
        assert report.total_fixtures == 0
        assert report.stale_fixtures == 0
        assert len(report.stale_files) == 0

    def test_nonexistent_directory(self, tmp_path):
        """Nonexistent directory should report warning."""
        report = check_fixture_staleness(tmp_path / "nonexistent")
        assert report.total_fixtures == 0
        assert len(report.warnings) == 1
        assert "does not exist" in report.warnings[0]

    def test_fresh_fixture(self, tmp_path):
        """Recent fixtures should not be flagged as stale."""
        fixture = {
            "tool_name": "test",
            "request": {},
            "response": {},
            "metadata": {
                "captured_at": datetime.utcnow().isoformat() + "Z",
            },
        }
        with open(tmp_path / "fresh.json", "w") as f:
            json.dump(fixture, f)

        report = check_fixture_staleness(tmp_path, max_age_days=30)
        assert report.total_fixtures == 1
        assert report.stale_fixtures == 0

    def test_stale_fixture(self, tmp_path):
        """Old fixtures should be flagged as stale."""
        old_date = datetime.utcnow() - timedelta(days=45)
        fixture = {
            "tool_name": "test",
            "request": {},
            "response": {},
            "metadata": {
                "captured_at": old_date.isoformat() + "Z",
            },
        }
        with open(tmp_path / "stale.json", "w") as f:
            json.dump(fixture, f)

        report = check_fixture_staleness(tmp_path, max_age_days=30)
        assert report.total_fixtures == 1
        assert report.stale_fixtures == 1
        assert len(report.stale_files) == 1
        assert report.stale_files[0][1] >= 45  # age in days

    def test_jsonl_staleness_check(self, tmp_path):
        """JSONL files should have each line checked."""
        now = datetime.utcnow()
        old_date = now - timedelta(days=60)

        fixtures = [
            {
                "tool_name": "t1",
                "request": {},
                "response": {},
                "metadata": {"captured_at": now.isoformat() + "Z"},
            },
            {
                "tool_name": "t2",
                "request": {},
                "response": {},
                "metadata": {"captured_at": old_date.isoformat() + "Z"},
            },
        ]

        with open(tmp_path / "mixed.jsonl", "w") as f:
            for fixture in fixtures:
                f.write(json.dumps(fixture) + "\n")

        report = check_fixture_staleness(tmp_path, max_age_days=30)
        assert report.total_fixtures == 2
        assert report.stale_fixtures == 1

    def test_missing_captured_at_warning(self, tmp_path):
        """Missing captured_at metadata should generate warning."""
        fixture = {
            "tool_name": "test",
            "request": {},
            "response": {},
            "metadata": {},  # No captured_at
        }
        with open(tmp_path / "no_date.json", "w") as f:
            json.dump(fixture, f)

        report = check_fixture_staleness(tmp_path)
        assert report.total_fixtures == 1
        assert len(report.warnings) == 1
        assert "No captured_at" in report.warnings[0]

    def test_custom_threshold(self, tmp_path):
        """Custom age threshold should be respected."""
        old_date = datetime.utcnow() - timedelta(days=10)
        fixture = {
            "tool_name": "test",
            "request": {},
            "response": {},
            "metadata": {"captured_at": old_date.isoformat() + "Z"},
        }
        with open(tmp_path / "test.json", "w") as f:
            json.dump(fixture, f)

        # With 30-day threshold, should not be stale
        report_30 = check_fixture_staleness(tmp_path, max_age_days=30)
        assert report_30.stale_fixtures == 0

        # With 7-day threshold, should be stale
        report_7 = check_fixture_staleness(tmp_path, max_age_days=7)
        assert report_7.stale_fixtures == 1
