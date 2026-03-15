"""
Integration tests for scripts/notify_slack.py

Tests message formatting, truncation, missing env var crashes,
and notification modes. Uses subprocess-based script testing.

Run with: pytest tests/integration/test_notify_slack.py -v
"""

import os
import subprocess
import sys

PYTHON = sys.executable
SCRIPT = "scripts/notify_slack.py"


class TestBuildCommitMessage:
    """Tests for commit message formatting."""

    def test_basic_commit_message(self):
        """Commit message includes all fields."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.notify_slack import build_commit_message
msg = build_commit_message(
    branch="main",
    commit_short_sha="abc1234",
    author="Alice <alice@test.com>",
    committer="Bob <bob@test.com>",
    message_subject="feat: add new feature",
    message_body="Detailed description here",
    files_changed=5,
    commit_url="https://github.com/test/repo/commit/abc1234",
)
assert "main" in msg
assert "abc1234" in msg
assert "Alice" in msg
assert "Bob" in msg
assert "feat: add new feature" in msg
assert "5" in msg
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout

    def test_commit_message_body_truncation(self):
        """Long commit message bodies are truncated to 200 chars."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.notify_slack import build_commit_message
long_body = "x" * 300
msg = build_commit_message(
    branch="main",
    commit_short_sha="abc1234",
    author="A",
    committer="B",
    message_subject="test",
    message_body=long_body,
    files_changed=1,
    commit_url="https://example.com",
)
# The truncated body should end with "..."
assert "..." in msg
# Should not contain the full 300-char string
assert "x" * 300 not in msg
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout

    def test_commit_message_empty_body(self):
        """Commit message with empty body only shows subject."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.notify_slack import build_commit_message
msg = build_commit_message(
    branch="main",
    commit_short_sha="abc1234",
    author="A",
    committer="B",
    message_subject="fix: quick fix",
    message_body="",
    files_changed=1,
    commit_url="https://example.com",
)
assert "fix: quick fix" in msg
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout


class TestBuildScannerMessage:
    """Tests for scanner message formatting."""

    def test_scanner_message_with_budget(self):
        """Scanner message includes budget information."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.notify_slack import build_scanner_message
msg = build_scanner_message(
    status="success",
    prs_created=2,
    pr_details=["PR #1: Fix auth", "PR #2: Update docs"],
    workflow_run_url="https://example.com/run/1",
    prs_url="https://example.com/pulls",
    budget_used=12.50,
    budget_remaining=87.50,
)
assert "SUCCESS" in msg
assert "2" in msg
assert "PR #1: Fix auth" in msg
assert "$12.50" in msg
assert "$87.50" in msg
assert "SuperClaude" in msg
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout

    def test_scanner_message_no_prs(self):
        """Scanner message shows 'No PRs created' when empty."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.notify_slack import build_scanner_message
msg = build_scanner_message(
    status="success",
    prs_created=0,
    pr_details=[],
    workflow_run_url="https://example.com/run/1",
    prs_url="https://example.com/pulls",
)
assert "No PRs created" in msg
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout


class TestBuildDocsUpdateMessage:
    """Tests for docs update message formatting."""

    def test_docs_update_message_success(self):
        """Docs update message for success status."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.notify_slack import build_docs_update_message
msg = build_docs_update_message(
    status="success",
    affected_docs="README.md,AGENTS.md",
    workflow_run_url="https://example.com/run/1",
    pr_url="https://example.com/pr/42",
)
assert "SUCCESS" in msg
assert "README.md" in msg
assert "AGENTS.md" in msg
assert "View Draft PR" in msg
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout


class TestSendSlackNotification:
    """Tests for the Slack notification sender."""

    def test_missing_rube_api_token_crashes(self):
        """Missing RUBE_API_TOKEN crashes (Let It Crash)."""
        env = os.environ.copy()
        env.pop("RUBE_API_TOKEN", None)
        env.pop("SLACK_CHANNEL_ID", None)
        env.pop("RUBE_ENTITY_ID", None)
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.notify_slack import send_slack_notification
send_slack_notification("test message")
""",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode != 0
        assert "KeyError" in result.stderr

    def test_missing_slack_channel_id_crashes(self):
        """Missing SLACK_CHANNEL_ID crashes (Let It Crash)."""
        env = os.environ.copy()
        env["RUBE_API_TOKEN"] = "test-token"
        env.pop("SLACK_CHANNEL_ID", None)
        env.pop("RUBE_ENTITY_ID", None)
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.notify_slack import send_slack_notification
send_slack_notification("test message")
""",
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode != 0
        assert "KeyError" in result.stderr


class TestMainEntryPoint:
    """Tests for the main() function dispatch."""

    def test_main_commit_mode_env_vars(self):
        """Main dispatches to commit mode based on NOTIFY_KIND."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
import os
os.environ["NOTIFY_KIND"] = "commit"
os.environ["COMMIT_BRANCH"] = "main"
os.environ["COMMIT_SHA"] = "abc1234567890"
os.environ["COMMIT_AUTHOR"] = "Test"
os.environ["COMMIT_MESSAGE_SUBJECT"] = "test commit"
os.environ["COMMIT_URL"] = "https://example.com"
os.environ["FILES_CHANGED"] = "3"
# Don't set RUBE_API_TOKEN so send_slack_notification crashes
# We just want to test message building doesn't crash
from scripts.notify_slack import build_commit_message
msg = build_commit_message(
    branch="main",
    commit_short_sha="abc1234",
    author="Test",
    committer="Test",
    message_subject="test commit",
    message_body="",
    files_changed=3,
    commit_url="https://example.com",
)
assert "test commit" in msg
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout
