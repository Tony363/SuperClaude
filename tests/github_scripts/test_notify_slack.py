"""Tests for .github/scripts/notify_slack.py message builders."""

import sys
from pathlib import Path

scripts_dir = str(Path(__file__).parent.parent.parent / ".github" / "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

from notify_slack import (  # noqa: E402
    build_commit_message,
    build_docs_update_message,
    build_issue_fix_message,
    build_scanner_message,
)


class TestBuildCommitMessage:
    """Tests for build_commit_message."""

    def test_basic_commit(self):
        msg = build_commit_message(
            branch="main",
            commit_short_sha="abc1234",
            author="Alice",
            committer="Bob",
            message_subject="feat: add login",
            message_body="Details here",
            files_changed=3,
            commit_url="https://github.com/repo/commit/abc",
        )
        assert "main" in msg
        assert "abc1234" in msg
        assert "Alice" in msg
        assert "Bob" in msg
        assert "feat: add login" in msg
        assert "3" in msg

    def test_truncates_long_body(self):
        long_body = "x" * 300
        msg = build_commit_message(
            branch="main",
            commit_short_sha="abc",
            author="A",
            committer="B",
            message_subject="subj",
            message_body=long_body,
            files_changed=1,
            commit_url="url",
        )
        assert "..." in msg
        # Should not contain the full 300-char body
        assert "x" * 200 not in msg

    def test_empty_body(self):
        msg = build_commit_message(
            branch="dev",
            commit_short_sha="def",
            author="A",
            committer="A",
            message_subject="fix: typo",
            message_body="",
            files_changed=1,
            commit_url="url",
        )
        assert "fix: typo" in msg


class TestBuildScannerMessage:
    """Tests for build_scanner_message."""

    def test_success_status(self):
        msg = build_scanner_message(
            status="success",
            prs_created=2,
            pr_details=["PR #1: formatting", "PR #2: security"],
            workflow_run_url="https://run",
            prs_url="https://prs",
        )
        assert "SUCCESS" in msg
        assert "2" in msg
        assert "PR #1: formatting" in msg

    def test_no_prs(self):
        msg = build_scanner_message(
            status="failure",
            prs_created=0,
            pr_details=[],
            workflow_run_url="url",
            prs_url="url",
        )
        assert "No PRs created" in msg

    def test_budget_info(self):
        msg = build_scanner_message(
            status="success",
            prs_created=1,
            pr_details=["PR #1"],
            workflow_run_url="url",
            prs_url="url",
            budget_used=45.50,
            budget_remaining=54.50,
        )
        assert "$45.50" in msg
        assert "$54.50" in msg


class TestBuildIssueFiXMessage:
    """Tests for build_issue_fix_message."""

    def test_success_with_pr(self):
        msg = build_issue_fix_message(
            status="success",
            issue_number="42",
            issue_title="Fix bug",
            issue_url="https://issue",
            workflow_run_url="https://run",
            pr_number="99",
            pr_url="https://pr",
        )
        assert "PR CREATED" in msg
        assert "#42" in msg
        assert "Fix bug" in msg
        assert "#99" in msg

    def test_no_changes(self):
        msg = build_issue_fix_message(
            status="no-changes",
            issue_number="1",
            issue_title="T",
            issue_url="u",
            workflow_run_url="u",
        )
        assert "NO CHANGES" in msg


class TestBuildDocsUpdateMessage:
    """Tests for build_docs_update_message."""

    def test_success_with_docs(self):
        msg = build_docs_update_message(
            status="success",
            affected_docs="README.md, CHANGELOG.md",
            workflow_run_url="url",
        )
        assert "SUCCESS" in msg
        assert "README.md" in msg
        assert "CHANGELOG.md" in msg

    def test_no_affected_docs(self):
        msg = build_docs_update_message(
            status="skipped",
            affected_docs="",
            workflow_run_url="url",
        )
        assert "No documentation affected" in msg

    def test_with_pr_url(self):
        msg = build_docs_update_message(
            status="success",
            affected_docs="README.md",
            workflow_run_url="url",
            pr_url="https://pr",
        )
        assert "View Draft PR" in msg


# ---------------------------------------------------------------------------
# Tests for send_slack_notification (lines 173-236)
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, patch  # noqa: E402

from notify_slack import main, send_slack_notification  # noqa: E402


class TestSendSlackNotification:
    """Tests for send_slack_notification."""

    def test_missing_token_returns_false(self, monkeypatch):
        monkeypatch.delenv("RUBE_API_TOKEN", raising=False)
        assert send_slack_notification("hello") is False

    def test_successful_send(self, monkeypatch):
        monkeypatch.setenv("RUBE_API_TOKEN", "tok-123")
        monkeypatch.delenv("SLACK_CONNECTED_ACCOUNT_ID", raising=False)

        mock_response = MagicMock()
        mock_response.json.return_value = {"successful": True}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            result = send_slack_notification("test message")

        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]["json"]["entityId"] == "default"
        assert call_kwargs[1]["json"]["input"]["markdown_text"] == "test message"

    def test_successful_send_with_connected_account(self, monkeypatch):
        monkeypatch.setenv("RUBE_API_TOKEN", "tok-123")
        monkeypatch.setenv("SLACK_CONNECTED_ACCOUNT_ID", "acct-456")

        mock_response = MagicMock()
        mock_response.json.return_value = {"successful": True}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response) as mock_post:
            result = send_slack_notification("msg")

        assert result is True
        payload = mock_post.call_args[1]["json"]
        assert payload["connectedAccountId"] == "acct-456"
        assert "entityId" not in payload

    def test_api_returns_error(self, monkeypatch):
        monkeypatch.setenv("RUBE_API_TOKEN", "tok-123")
        monkeypatch.delenv("SLACK_CONNECTED_ACCOUNT_ID", raising=False)

        mock_response = MagicMock()
        mock_response.json.return_value = {"successful": False, "error": "channel_not_found"}
        mock_response.raise_for_status = MagicMock()

        with patch("requests.post", return_value=mock_response):
            result = send_slack_notification("msg")

        assert result is False

    def test_http_request_exception(self, monkeypatch):
        monkeypatch.setenv("RUBE_API_TOKEN", "tok-123")
        monkeypatch.delenv("SLACK_CONNECTED_ACCOUNT_ID", raising=False)

        import requests as req_mod

        exc = req_mod.exceptions.RequestException("timeout")
        exc.response = None

        with patch("requests.post", side_effect=exc):
            result = send_slack_notification("msg")

        assert result is False

    def test_http_exception_with_response_body(self, monkeypatch):
        monkeypatch.setenv("RUBE_API_TOKEN", "tok-123")
        monkeypatch.delenv("SLACK_CONNECTED_ACCOUNT_ID", raising=False)

        import requests as req_mod

        mock_resp = MagicMock()
        mock_resp.text = "Internal Server Error"
        exc = req_mod.exceptions.RequestException("500")
        exc.response = mock_resp

        with patch("requests.post", side_effect=exc):
            result = send_slack_notification("msg")

        assert result is False

    def test_unexpected_exception(self, monkeypatch):
        monkeypatch.setenv("RUBE_API_TOKEN", "tok-123")
        monkeypatch.delenv("SLACK_CONNECTED_ACCOUNT_ID", raising=False)

        with patch("requests.post", side_effect=RuntimeError("boom")):
            result = send_slack_notification("msg")

        assert result is False


# ---------------------------------------------------------------------------
# Tests for main (lines 239-336)
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for the main() entry point."""

    def test_exits_0_when_no_token(self, monkeypatch):
        import pytest

        monkeypatch.delenv("RUBE_API_TOKEN", raising=False)
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_docs_update_path(self, monkeypatch):
        import pytest

        monkeypatch.setenv("RUBE_API_TOKEN", "tok")
        monkeypatch.setenv("NOTIFY_KIND", "docs-update")
        monkeypatch.setenv("WORKFLOW_STATUS", "success")
        monkeypatch.setenv("AFFECTED_DOCS", "README.md")
        monkeypatch.setenv("WORKFLOW_RUN_URL", "https://run")
        monkeypatch.delenv("PR_URL", raising=False)

        with patch("notify_slack.send_slack_notification", return_value=True) as mock_send:
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        msg = mock_send.call_args[0][0]
        assert "Nightly Docs Update" in msg
        assert "README.md" in msg

    def test_docs_update_with_pr_url(self, monkeypatch):
        import pytest

        monkeypatch.setenv("RUBE_API_TOKEN", "tok")
        monkeypatch.setenv("NOTIFY_KIND", "docs-update")
        monkeypatch.setenv("WORKFLOW_STATUS", "success")
        monkeypatch.setenv("AFFECTED_DOCS", "CHANGELOG.md")
        monkeypatch.setenv("WORKFLOW_RUN_URL", "https://run")
        monkeypatch.setenv("PR_URL", "https://pr/1")

        with patch("notify_slack.send_slack_notification", return_value=True) as mock_send:
            with pytest.raises(SystemExit):
                main()

        msg = mock_send.call_args[0][0]
        assert "View Draft PR" in msg

    def test_issue_fix_path(self, monkeypatch):
        import pytest

        monkeypatch.setenv("RUBE_API_TOKEN", "tok")
        monkeypatch.setenv("NOTIFY_KIND", "issue-fix")
        monkeypatch.setenv("WORKFLOW_STATUS", "success")
        monkeypatch.setenv("ISSUE_NUMBER", "42")
        monkeypatch.setenv("ISSUE_TITLE", "Fix login bug")
        monkeypatch.setenv("ISSUE_URL", "https://issue/42")
        monkeypatch.setenv("WORKFLOW_RUN_URL", "https://run")
        monkeypatch.setenv("PR_NUMBER", "99")
        monkeypatch.setenv("PR_URL", "https://pr/99")

        with patch("notify_slack.send_slack_notification", return_value=True) as mock_send:
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        msg = mock_send.call_args[0][0]
        assert "#42" in msg
        assert "Fix login bug" in msg
        assert "#99" in msg

    def test_issue_fix_path_no_pr(self, monkeypatch):
        import pytest

        monkeypatch.setenv("RUBE_API_TOKEN", "tok")
        monkeypatch.setenv("NOTIFY_KIND", "issue-fix")
        monkeypatch.setenv("WORKFLOW_STATUS", "no-changes")
        monkeypatch.setenv("ISSUE_NUMBER", "10")
        monkeypatch.setenv("ISSUE_TITLE", "Some issue")
        monkeypatch.setenv("ISSUE_URL", "https://issue/10")
        monkeypatch.setenv("WORKFLOW_RUN_URL", "https://run")
        monkeypatch.delenv("PR_NUMBER", raising=False)
        monkeypatch.delenv("PR_URL", raising=False)

        with patch("notify_slack.send_slack_notification", return_value=True) as mock_send:
            with pytest.raises(SystemExit):
                main()

        msg = mock_send.call_args[0][0]
        assert "NO CHANGES" in msg

    def test_commit_path(self, monkeypatch):
        import pytest

        monkeypatch.setenv("RUBE_API_TOKEN", "tok")
        monkeypatch.setenv("NOTIFY_KIND", "commit")
        monkeypatch.setenv("COMMIT_BRANCH", "feature/x")
        monkeypatch.setenv("COMMIT_SHA", "abc1234567890")
        monkeypatch.setenv("COMMIT_SHORT_SHA", "abc1234")
        monkeypatch.setenv("COMMIT_AUTHOR", "Alice")
        monkeypatch.setenv("COMMIT_COMMITTER", "Bob")
        monkeypatch.setenv("COMMIT_MESSAGE_SUBJECT", "feat: new thing")
        monkeypatch.setenv("COMMIT_MESSAGE_BODY", "body text")
        monkeypatch.setenv("FILES_CHANGED", "5")
        monkeypatch.setenv("COMMIT_URL", "https://commit/abc")

        with patch("notify_slack.send_slack_notification", return_value=True) as mock_send:
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        msg = mock_send.call_args[0][0]
        assert "feature/x" in msg
        assert "abc1234" in msg
        assert "Alice" in msg
        assert "feat: new thing" in msg

    def test_scanner_default_path(self, monkeypatch):
        import pytest

        monkeypatch.setenv("RUBE_API_TOKEN", "tok")
        monkeypatch.setenv("NOTIFY_KIND", "scanner")
        monkeypatch.setenv("WORKFLOW_STATUS", "success")
        monkeypatch.setenv("PRS_CREATED", "2")
        monkeypatch.setenv("WORKFLOW_RUN_URL", "https://run")
        monkeypatch.setenv("PRS_URL", "https://prs")
        monkeypatch.setenv("PR_DETAILS", "PR #1: fmt, PR #2: sec")
        monkeypatch.setenv("BUDGET_USED", "10.50")
        monkeypatch.setenv("BUDGET_REMAINING", "89.50")

        with patch("notify_slack.send_slack_notification", return_value=True) as mock_send:
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        msg = mock_send.call_args[0][0]
        assert "SUCCESS" in msg
        assert "$10.50" in msg
        assert "$89.50" in msg

    def test_scanner_default_no_explicit_kind(self, monkeypatch):
        """When NOTIFY_KIND is unset, falls through to scanner default."""
        import pytest

        monkeypatch.setenv("RUBE_API_TOKEN", "tok")
        monkeypatch.delenv("NOTIFY_KIND", raising=False)
        monkeypatch.setenv("WORKFLOW_STATUS", "failure")
        monkeypatch.setenv("PRS_CREATED", "0")
        monkeypatch.setenv("WORKFLOW_RUN_URL", "https://run")
        monkeypatch.setenv("PRS_URL", "https://prs")
        monkeypatch.delenv("PR_DETAILS", raising=False)
        monkeypatch.delenv("BUDGET_USED", raising=False)
        monkeypatch.delenv("BUDGET_REMAINING", raising=False)

        with patch("notify_slack.send_slack_notification", return_value=True) as mock_send:
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 0
        msg = mock_send.call_args[0][0]
        assert "FAILURE" in msg
        assert "No PRs created" in msg

    def test_scanner_invalid_budget_values(self, monkeypatch):
        """Invalid budget strings are silently ignored (budget stays None)."""
        import pytest

        monkeypatch.setenv("RUBE_API_TOKEN", "tok")
        monkeypatch.setenv("NOTIFY_KIND", "scanner")
        monkeypatch.setenv("WORKFLOW_STATUS", "success")
        monkeypatch.setenv("PRS_CREATED", "0")
        monkeypatch.setenv("WORKFLOW_RUN_URL", "url")
        monkeypatch.setenv("PRS_URL", "url")
        monkeypatch.delenv("PR_DETAILS", raising=False)
        monkeypatch.setenv("BUDGET_USED", "not-a-number")
        monkeypatch.setenv("BUDGET_REMAINING", "also-bad")

        with patch("notify_slack.send_slack_notification", return_value=True) as mock_send:
            with pytest.raises(SystemExit):
                main()

        msg = mock_send.call_args[0][0]
        # Budget lines should NOT appear since values are invalid
        assert "Budget Used" not in msg

    def test_send_failure_exits_1(self, monkeypatch):
        import pytest

        monkeypatch.setenv("RUBE_API_TOKEN", "tok")
        monkeypatch.setenv("NOTIFY_KIND", "commit")
        monkeypatch.setenv("COMMIT_BRANCH", "main")
        monkeypatch.setenv("COMMIT_SHA", "abc1234567890")
        monkeypatch.setenv("COMMIT_SHORT_SHA", "abc1234")
        monkeypatch.setenv("COMMIT_AUTHOR", "A")
        monkeypatch.setenv("COMMIT_COMMITTER", "A")
        monkeypatch.setenv("COMMIT_MESSAGE_SUBJECT", "fix")
        monkeypatch.setenv("COMMIT_MESSAGE_BODY", "")
        monkeypatch.setenv("FILES_CHANGED", "1")
        monkeypatch.setenv("COMMIT_URL", "url")

        with patch("notify_slack.send_slack_notification", return_value=False):
            with pytest.raises(SystemExit) as exc_info:
                main()

        assert exc_info.value.code == 1
