#!/usr/bin/env python3
"""
Slack notification script using Composio SDK (Rube MCP) for GitHub Actions.
Sends formatted notifications to Slack for scanner runs and individual commits.
"""

import os
import sys

# Configuration
SLACK_CHANNEL_ID = "C02UJAFKRRC"  # qa-testing channel


def build_commit_message(
    branch: str,
    commit_short_sha: str,
    author: str,
    committer: str,
    message_subject: str,
    message_body: str,
    files_changed: int,
    commit_url: str,
) -> str:
    """Build Slack message for individual commit notification."""
    # Truncate long commit messages
    if len(message_body) > 200:
        message_body = message_body[:197] + "..."

    full_message = f"{message_subject}\n{message_body}" if message_body else message_subject

    return f"""## New Commit to `{branch}`

**Commit**: [`{commit_short_sha}`]({commit_url})
**Author**: {author}
**Committer**: {committer}
**Files Changed**: {files_changed}

### Message
```
{full_message}
```

---

[View Commit]({commit_url})

_Automated notification from GitHub Actions_"""


def build_scanner_message(
    status: str,
    prs_created: int,
    pr_details: list[str],
    workflow_run_url: str,
    prs_url: str,
    budget_used: float | None = None,
    budget_remaining: float | None = None,
) -> str:
    """Build Slack message for scanner notification."""
    status_emoji = "pass" if status == "success" else "fail"

    pr_lines = (
        "\n".join(f"- {detail}" for detail in pr_details) if pr_details else "- No PRs created"
    )

    budget_info = ""
    if budget_used is not None:
        budget_info = f"\n- **Budget Used**: ${budget_used:.2f}"
    if budget_remaining is not None:
        budget_info += f"\n- **Budget Remaining**: ${budget_remaining:.2f}"

    return f"""## SuperClaude Autonomous Code Scanner

**Status**: {status_emoji} {status.upper()}

---

### Workflow Summary
- **PRs Created**: {prs_created}
- **Scanners Run**: P0 (Formatting), P1 (Security){budget_info}

### PR Details
{pr_lines}

---

[View PRs]({prs_url}) | [View Workflow Run]({workflow_run_url})

_Automated notification from GitHub Actions_"""


def build_issue_fix_message(
    status: str,
    issue_number: str,
    issue_title: str,
    issue_url: str,
    workflow_run_url: str,
    pr_number: str | None = None,
    pr_url: str | None = None,
) -> str:
    """Build Slack message for issue-to-PR workflow notification."""
    status_map = {
        "success": ("pass", "PR CREATED"),
        "no-changes": ("skip", "NO CHANGES"),
        "failure": ("fail", "FAILURE"),
        "skipped": ("skip", "SKIPPED"),
    }
    emoji, label = status_map.get(status, ("?", status.upper()))

    pr_section = ""
    if pr_number and pr_url:
        pr_section = f"\n\n### Pull Request\n[Draft PR #{pr_number}]({pr_url})"

    return f"""## Issue to PR

**Status**: {emoji} {label}

---

### Issue
[#{issue_number}: {issue_title}]({issue_url})
{pr_section}

---

[View Workflow Run]({workflow_run_url})

_Automated notification from GitHub Actions_"""


def build_docs_update_message(
    status: str,
    affected_docs: str,
    workflow_run_url: str,
    pr_url: str | None = None,
) -> str:
    """Build Slack message for nightly docs update notification."""
    status_map = {
        "success": ("pass", "SUCCESS"),
        "failure": ("fail", "FAILURE"),
        "skipped": ("skip", "SKIPPED"),
    }
    emoji, label = status_map.get(status, ("?", status.upper()))

    if affected_docs:
        docs_lines = "\n".join(
            f"- `{doc.strip()}`" for doc in affected_docs.split(",") if doc.strip()
        )
    else:
        docs_lines = "- No documentation affected"

    pr_section = ""
    if pr_url:
        pr_section = f"\n[View Draft PR]({pr_url})"

    return f"""## Nightly Docs Update

**Status**: {emoji} {label}

---

### Affected Documentation
{docs_lines}
{pr_section}

---

[View Workflow Run]({workflow_run_url})

_Automated notification from GitHub Actions_"""


def send_slack_notification(message: str) -> bool:
    """
    Send notification to Slack via Composio API (Rube MCP endpoint).

    Args:
        message: Pre-formatted markdown message to send

    Returns:
        True if notification sent successfully, False otherwise
    """
    api_token = os.environ.get("RUBE_API_TOKEN")
    if not api_token:
        print("ERROR: RUBE_API_TOKEN not set", file=sys.stderr)
        return False

    try:
        import requests

        print(f"Sending notification to Slack channel {SLACK_CHANNEL_ID}...")

        api_url = "https://backend.composio.dev/api/v2/actions/SLACK_SEND_MESSAGE/execute"

        headers = {
            "X-API-Key": api_token,
            "Content-Type": "application/json",
        }

        payload = {
            "entityId": os.environ.get(
                "SLACK_CONNECTED_ACCOUNT_ID",
                "default",
            ),
            "appName": "slack",
            "input": {
                "channel": SLACK_CHANNEL_ID,
                "markdown_text": message,
            },
        }

        response = requests.post(api_url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()

        if result.get("successful"):
            print("Slack notification sent successfully!")
            return True
        else:
            error = result.get("error", "Unknown error")
            print(f"Slack API error: {error}", file=sys.stderr)
            print(f"Full response: {result}", file=sys.stderr)
            return False

    except requests.exceptions.RequestException as e:
        print(f"HTTP request failed: {e}", file=sys.stderr)
        if hasattr(e, "response") and e.response is not None:
            print(f"Response: {e.response.text}", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Failed to send Slack notification: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main entry point - reads environment variables and sends notification."""
    notify_kind = os.environ.get("NOTIFY_KIND", "scanner")

    if notify_kind == "docs-update":
        status = os.environ.get("WORKFLOW_STATUS", "unknown")
        affected_docs = os.environ.get("AFFECTED_DOCS", "")
        workflow_run_url = os.environ.get("WORKFLOW_RUN_URL", "")
        pr_url = os.environ.get("PR_URL") or None

        message = build_docs_update_message(
            status,
            affected_docs,
            workflow_run_url,
            pr_url,
        )
    elif notify_kind == "issue-fix":
        status = os.environ.get("WORKFLOW_STATUS", "unknown")
        issue_number = os.environ.get("ISSUE_NUMBER", "")
        issue_title = os.environ.get("ISSUE_TITLE", "")
        issue_url = os.environ.get("ISSUE_URL", "")
        workflow_run_url = os.environ.get("WORKFLOW_RUN_URL", "")
        pr_number = os.environ.get("PR_NUMBER") or None
        pr_url = os.environ.get("PR_URL") or None

        message = build_issue_fix_message(
            status,
            issue_number,
            issue_title,
            issue_url,
            workflow_run_url,
            pr_number,
            pr_url,
        )
    elif notify_kind == "commit":
        branch = os.environ.get("COMMIT_BRANCH", "unknown")
        commit_sha = os.environ.get("COMMIT_SHA", "")
        commit_short_sha = os.environ.get("COMMIT_SHORT_SHA", commit_sha[:7])
        author = os.environ.get("COMMIT_AUTHOR", "Unknown")
        committer = os.environ.get("COMMIT_COMMITTER", author)
        message_subject = os.environ.get("COMMIT_MESSAGE_SUBJECT", "")
        message_body = os.environ.get("COMMIT_MESSAGE_BODY", "")
        files_changed = int(os.environ.get("FILES_CHANGED", "0"))
        commit_url = os.environ.get("COMMIT_URL", "")

        message = build_commit_message(
            branch,
            commit_short_sha,
            author,
            committer,
            message_subject,
            message_body,
            files_changed,
            commit_url,
        )
    else:
        # Scanner notification mode
        status = os.environ.get("WORKFLOW_STATUS", "unknown")
        prs_created = int(os.environ.get("PRS_CREATED", "0"))
        workflow_run_url = os.environ.get("WORKFLOW_RUN_URL", "")
        prs_url = os.environ.get("PRS_URL", "")

        pr_details_str = os.environ.get("PR_DETAILS", "")
        pr_details = [d.strip() for d in pr_details_str.split(",") if d.strip()]

        budget_used = None
        budget_remaining = None
        if os.environ.get("BUDGET_USED"):
            try:
                budget_used = float(os.environ["BUDGET_USED"])
            except ValueError:
                pass
        if os.environ.get("BUDGET_REMAINING"):
            try:
                budget_remaining = float(os.environ["BUDGET_REMAINING"])
            except ValueError:
                pass

        message = build_scanner_message(
            status,
            prs_created,
            pr_details,
            workflow_run_url,
            prs_url,
            budget_used,
            budget_remaining,
        )

    success = send_slack_notification(message)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
