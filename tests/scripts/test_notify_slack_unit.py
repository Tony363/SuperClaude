"""Unit tests for scripts/notify_slack.py message builders."""

from scripts.notify_slack import (
    build_commit_message,
    build_docs_update_message,
    build_scanner_message,
)


class TestBuildCommitMessage:
    """Tests for build_commit_message."""

    def test_formats_correctly(self):
        msg = build_commit_message(
            branch="main",
            commit_short_sha="abc1234",
            author="Alice",
            committer="Bob",
            message_subject="feat: add auth",
            message_body="Body text",
            files_changed=5,
            commit_url="https://github.com/commit/abc",
        )
        assert "main" in msg
        assert "abc1234" in msg
        assert "Alice" in msg
        assert "feat: add auth" in msg

    def test_truncates_long_body(self):
        long_body = "a" * 300
        msg = build_commit_message(
            branch="dev",
            commit_short_sha="x",
            author="A",
            committer="A",
            message_subject="s",
            message_body=long_body,
            files_changed=1,
            commit_url="u",
        )
        assert "..." in msg

    def test_empty_body(self):
        msg = build_commit_message(
            branch="dev",
            commit_short_sha="x",
            author="A",
            committer="A",
            message_subject="fix: typo",
            message_body="",
            files_changed=1,
            commit_url="u",
        )
        assert "fix: typo" in msg


class TestBuildScannerMessage:
    """Tests for build_scanner_message."""

    def test_with_budget(self):
        msg = build_scanner_message(
            status="success",
            prs_created=2,
            pr_details=["PR #1", "PR #2"],
            workflow_run_url="url",
            prs_url="url",
            budget_used=42.0,
            budget_remaining=58.0,
        )
        assert "$42.00" in msg
        assert "$58.00" in msg

    def test_no_details(self):
        msg = build_scanner_message(
            status="failure",
            prs_created=0,
            pr_details=[],
            workflow_run_url="u",
            prs_url="u",
        )
        assert "No PRs created" in msg


class TestBuildDocsUpdateMessage:
    """Tests for build_docs_update_message."""

    def test_success(self):
        msg = build_docs_update_message(
            status="success",
            affected_docs="README.md",
            workflow_run_url="url",
        )
        assert "SUCCESS" in msg
        assert "README.md" in msg

    def test_skipped(self):
        msg = build_docs_update_message(
            status="skipped",
            affected_docs="",
            workflow_run_url="url",
        )
        assert "SKIPPED" in msg

    def test_unknown_status(self):
        msg = build_docs_update_message(
            status="weird",
            affected_docs="",
            workflow_run_url="url",
        )
        assert "WEIRD" in msg


# --- Tests for send_slack_notification and main ---

from unittest.mock import MagicMock, patch  # noqa: E402


class TestSendSlackNotification:
    """Tests for send_slack_notification."""

    def test_missing_env_vars_crashes(self, monkeypatch):
        """Let It Crash: missing required env vars raise KeyError."""
        monkeypatch.delenv("RUBE_API_TOKEN", raising=False)
        monkeypatch.delenv("SLACK_CHANNEL_ID", raising=False)
        monkeypatch.delenv("RUBE_ENTITY_ID", raising=False)

        import pytest

        from scripts.notify_slack import send_slack_notification

        with pytest.raises(KeyError):
            send_slack_notification("test message")

    def test_success(self, monkeypatch):
        monkeypatch.setenv("RUBE_API_TOKEN", "fake-token")
        monkeypatch.setenv("SLACK_CHANNEL_ID", "C123")
        monkeypatch.setenv("RUBE_ENTITY_ID", "default")

        mock_response = MagicMock()
        mock_response.json.return_value = {"successful": True}
        mock_response.raise_for_status = MagicMock()

        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response

        with patch.dict("sys.modules", {"requests": mock_requests}):
            from scripts.notify_slack import send_slack_notification

            result = send_slack_notification("test")

        assert result is True

    def test_api_error(self, monkeypatch):
        monkeypatch.setenv("RUBE_API_TOKEN", "fake-token")
        monkeypatch.setenv("SLACK_CHANNEL_ID", "C123")
        monkeypatch.setenv("RUBE_ENTITY_ID", "default")

        mock_response = MagicMock()
        mock_response.json.return_value = {"successful": False, "error": "channel not found"}
        mock_response.raise_for_status = MagicMock()

        mock_requests = MagicMock()
        mock_requests.post.return_value = mock_response

        with patch.dict("sys.modules", {"requests": mock_requests}):
            from scripts.notify_slack import send_slack_notification

            result = send_slack_notification("test")

        assert result is False


class TestNotifySlackMain:
    """Tests for main() with different NOTIFY_KIND values."""

    def test_main_scanner_mode(self, monkeypatch):
        monkeypatch.setenv("NOTIFY_KIND", "scanner")
        monkeypatch.setenv("WORKFLOW_STATUS", "success")
        monkeypatch.setenv("PRS_CREATED", "2")
        monkeypatch.setenv("WORKFLOW_RUN_URL", "https://example.com")
        monkeypatch.setenv("PRS_URL", "https://example.com/prs")
        monkeypatch.setenv("PR_DETAILS", "PR #1,PR #2")
        monkeypatch.setenv("RUBE_API_TOKEN", "fake")
        monkeypatch.setenv("SLACK_CHANNEL_ID", "C123")
        monkeypatch.setenv("RUBE_ENTITY_ID", "default")

        with patch("scripts.notify_slack.send_slack_notification", return_value=True) as mock_send:
            with patch("sys.exit"):
                from scripts.notify_slack import main

                main()

            mock_send.assert_called_once()
            msg = mock_send.call_args[0][0]
            assert "success" in msg.lower() or "SUCCESS" in msg

    def test_main_commit_mode(self, monkeypatch):
        monkeypatch.setenv("NOTIFY_KIND", "commit")
        monkeypatch.setenv("COMMIT_BRANCH", "main")
        monkeypatch.setenv("COMMIT_SHA", "abc1234567890")
        monkeypatch.setenv("COMMIT_SHORT_SHA", "abc1234")
        monkeypatch.setenv("COMMIT_AUTHOR", "Alice")
        monkeypatch.setenv("COMMIT_COMMITTER", "Bob")
        monkeypatch.setenv("COMMIT_MESSAGE_SUBJECT", "fix: typo")
        monkeypatch.setenv("COMMIT_MESSAGE_BODY", "")
        monkeypatch.setenv("FILES_CHANGED", "3")
        monkeypatch.setenv("COMMIT_URL", "https://example.com/commit")
        monkeypatch.setenv("RUBE_API_TOKEN", "fake")
        monkeypatch.setenv("SLACK_CHANNEL_ID", "C123")
        monkeypatch.setenv("RUBE_ENTITY_ID", "default")

        with patch("scripts.notify_slack.send_slack_notification", return_value=True) as mock_send:
            with patch("sys.exit"):
                from scripts.notify_slack import main

                main()

            msg = mock_send.call_args[0][0]
            assert "main" in msg
            assert "abc1234" in msg

    def test_main_docs_update_mode(self, monkeypatch):
        monkeypatch.setenv("NOTIFY_KIND", "docs-update")
        monkeypatch.setenv("WORKFLOW_STATUS", "success")
        monkeypatch.setenv("AFFECTED_DOCS", "README.md,CLAUDE.md")
        monkeypatch.setenv("WORKFLOW_RUN_URL", "https://example.com")
        monkeypatch.setenv("RUBE_API_TOKEN", "fake")
        monkeypatch.setenv("SLACK_CHANNEL_ID", "C123")
        monkeypatch.setenv("RUBE_ENTITY_ID", "default")

        with patch("scripts.notify_slack.send_slack_notification", return_value=True) as mock_send:
            with patch("sys.exit"):
                from scripts.notify_slack import main

                main()

            msg = mock_send.call_args[0][0]
            assert "README.md" in msg
