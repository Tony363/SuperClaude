#!/usr/bin/env python3
"""
Slack notification script using Composio SDK (Rube MCP) for GitHub Actions.
Sends formatted notifications to Slack for workflow runs and individual commits.
"""

import os
import sys


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

**Status**: {status.upper()} ({status_emoji})

---

### Workflow Summary
- **PRs Created**: {prs_created}
- **Scanners Run**: Security, Quality, Performance{budget_info}

### PR Details
{pr_lines}

---

[View PRs]({prs_url}) | [View Workflow Run]({workflow_run_url})

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
    _emoji, label = status_map.get(status, ("unknown", status.upper()))

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

**Status**: {label}

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

    Crashes on missing required env vars (Let It Crash).
    Returns True on success, False on API-level failure.
    """
    # Let It Crash: required env vars crash if missing
    api_token = os.environ["RUBE_API_TOKEN"]
    channel_id = os.environ["SLACK_CHANNEL_ID"]
    entity_id = os.environ["RUBE_ENTITY_ID"]

    # LET-IT-CRASH-EXCEPTION: API_BOUNDARY - HTTP call to external Slack API
    import requests

    print(f"Sending notification to Slack channel {channel_id}...")

    api_url = "https://backend.composio.dev/api/v2/actions/SLACK_SEND_MESSAGE/execute"

    headers = {
        "X-API-Key": api_token,
        "Content-Type": "application/json",
    }

    payload = {
        "entityId": entity_id,
        "appName": "slack",
        "input": {
            "channel": channel_id,
            "markdown_text": message,
        },
    }

    response = requests.post(api_url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    result = response.json()

    if result.get("successful"):
        print("Slack notification sent successfully!")
        return True

    error = result.get("error", "Unknown error")
    print(f"Slack API error: {error}", file=sys.stderr)
    print(f"Full response: {result}", file=sys.stderr)
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
        status = os.environ.get("WORKFLOW_STATUS", "unknown")
        prs_created = int(os.environ.get("PRS_CREATED", "0"))
        workflow_run_url = os.environ.get("WORKFLOW_RUN_URL", "")
        prs_url = os.environ.get("PRS_URL", "")

        pr_details_str = os.environ.get("PR_DETAILS", "")
        pr_details = [d.strip() for d in pr_details_str.split(",") if d.strip()]

        budget_used = None
        budget_remaining = None
        if os.environ.get("BUDGET_USED"):
            budget_used = float(os.environ["BUDGET_USED"])
        if os.environ.get("BUDGET_REMAINING"):
            budget_remaining = float(os.environ["BUDGET_REMAINING"])

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
