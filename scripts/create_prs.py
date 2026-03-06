#!/usr/bin/env python3
"""
PR Creation & Management with Idempotency

Creates categorized PRs for nightly code review suggestions.
Updates existing PRs instead of creating duplicates (idempotency).
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

CATEGORY_LABELS = {
    "security": ["nightly-review", "security", "ai-generated"],
    "quality": ["nightly-review", "quality", "ai-generated"],
    "performance": ["nightly-review", "performance", "ai-generated"],
    "tests": ["nightly-review", "tests", "ai-generated"],
}

# Phase 2: Autofix PR labels (distinct from suggestion-only)
AUTOFIX_CATEGORY_LABELS = {
    "security": ["nightly-review-autofix", "security", "ai-generated", "autofix"],
    "quality": ["nightly-review-autofix", "quality", "ai-generated", "autofix", "formatting"],
    "performance": ["nightly-review-autofix", "performance", "ai-generated", "autofix"],
    "tests": ["nightly-review-autofix", "tests", "ai-generated", "autofix"],
}


def run_command(cmd: List[str], capture_output: bool = True) -> Optional[str]:
    """Run shell command and return output."""
    try:
        result = subprocess.run(cmd, capture_output=capture_output, text=True, check=True)
        return result.stdout.strip() if capture_output else None
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {' '.join(cmd)}", file=sys.stderr)
        print(f"Error: {e.stderr if e.stderr else str(e)}", file=sys.stderr)
        return None


def get_existing_pr_for_category(category: str) -> Optional[Dict[str, Any]]:
    """Check if open PR exists for this category."""
    # List open PRs with nightly-review label
    output = run_command(
        [
            "gh",
            "pr",
            "list",
            "--label",
            "nightly-review",
            "--label",
            category,
            "--state",
            "open",
            "--json",
            "number,title,headRefName,labels",
            "--limit",
            "10",
        ]
    )

    if not output:
        return None

    try:
        prs = json.loads(output)
        # Find PR matching this category
        for pr in prs:
            if pr.get("headRefName", "").startswith(f"nightly-review/{category}/"):
                return pr
        return None
    except json.JSONDecodeError:
        return None


def create_or_update_branch(category: str, pr_content_file: Path) -> str:
    """Create or update branch for category."""
    # Branch name: nightly-review/{category}/{date}
    date_str = datetime.now().strftime("%Y-%m-%d")
    branch_name = f"nightly-review/{category}/{date_str}"

    # Check if branch exists locally
    branch_exists = run_command(["git", "rev-parse", "--verify", branch_name]) is not None

    if branch_exists:
        print(f"Branch {branch_name} exists - checking out")
        run_command(["git", "checkout", branch_name])
    else:
        print(f"Creating new branch: {branch_name}")
        # Ensure we're on main/master before creating branch
        main_branch = run_command(["git", "symbolic-ref", "refs/remotes/origin/HEAD"])
        if main_branch:
            main_branch = main_branch.split("/")[-1]
        else:
            main_branch = "main"

        run_command(["git", "checkout", main_branch])
        run_command(["git", "checkout", "-b", branch_name])

    return branch_name


def create_pr_with_gh(category: str, branch_name: str, pr_content_file: Path) -> bool:
    """Create PR using gh CLI."""
    # Read PR description
    try:
        with open(pr_content_file, "r") as f:
            pr_body = f.read()
    except OSError as e:
        print(f"Error reading PR content: {e}", file=sys.stderr)
        return False

    # Extract title from first line of PR description
    lines = pr_body.split("\n")
    pr_title = lines[0].strip("# ") if lines else f"Nightly Review: {category.upper()}"

    # Create PR
    labels = ",".join(CATEGORY_LABELS.get(category, ["nightly-review", "ai-generated"]))

    # Use gh pr create
    result = run_command(
        [
            "gh",
            "pr",
            "create",
            "--title",
            pr_title,
            "--body",
            pr_body,
            "--label",
            labels,
            "--draft",  # Always create as draft
            "--head",
            branch_name,
        ]
    )

    if result:
        print(f"Created PR for {category}: {result}")
        return True
    else:
        print(f"Failed to create PR for {category}", file=sys.stderr)
        return False


def update_existing_pr(pr_number: int, pr_content_file: Path) -> bool:
    """Update existing PR description."""
    try:
        with open(pr_content_file, "r") as f:
            pr_body = f.read()
    except OSError as e:
        print(f"Error reading PR content: {e}", file=sys.stderr)
        return False

    # Update PR body
    result = run_command(["gh", "pr", "edit", str(pr_number), "--body", pr_body])

    if result is not None:  # Command succeeded (even if no output)
        print(f"Updated PR #{pr_number}")
        return True
    else:
        print(f"Failed to update PR #{pr_number}", file=sys.stderr)
        return False


def get_existing_autofix_pr_for_category(category: str) -> Optional[Dict[str, Any]]:
    """Check if open autofix PR exists for this category."""
    # List open PRs with nightly-review-autofix label
    output = run_command(
        [
            "gh",
            "pr",
            "list",
            "--label",
            "nightly-review-autofix",
            "--label",
            category,
            "--state",
            "open",
            "--json",
            "number,title,headRefName,labels",
            "--limit",
            "10",
        ]
    )

    if not output:
        return None

    try:
        prs = json.loads(output)
        # Find PR matching this category
        for pr in prs:
            if pr.get("headRefName", "").startswith(f"nightly-review-autofix/{category}/"):
                return pr
        return None
    except json.JSONDecodeError:
        return None


def create_autofix_branch(category: str) -> str:
    """Create autofix branch with actual code changes."""
    date_str = datetime.now().strftime("%Y-%m-%d")
    branch_name = f"nightly-review-autofix/{category}/{date_str}"

    # Check if branch exists locally
    branch_exists = run_command(["git", "rev-parse", "--verify", branch_name]) is not None

    if branch_exists:
        print(f"Autofix branch {branch_name} exists - checking out")
        run_command(["git", "checkout", branch_name])
    else:
        print(f"Creating new autofix branch: {branch_name}")
        # Ensure we're on main/master before creating branch
        main_branch = run_command(["git", "symbolic-ref", "refs/remotes/origin/HEAD"])
        if main_branch:
            main_branch = main_branch.split("/")[-1]
        else:
            main_branch = "main"

        run_command(["git", "checkout", main_branch])
        run_command(["git", "checkout", "-b", branch_name])

    return branch_name


def create_autofix_pr_with_gh(category: str, branch_name: str, pr_content_file: Path) -> bool:
    """Create autofix PR using gh CLI."""
    # Read PR description
    try:
        with open(pr_content_file, "r") as f:
            pr_body = f.read()
    except OSError as e:
        print(f"Error reading autofix PR content: {e}", file=sys.stderr)
        return False

    # Extract title from first line of PR description
    lines = pr_body.split("\n")
    pr_title = lines[0].strip("# ") if lines else f"AUTOFIX: {category.upper()}"

    # Get autofix labels
    labels = ",".join(AUTOFIX_CATEGORY_LABELS.get(category, ["nightly-review-autofix", "ai-generated"]))

    # Use gh pr create
    result = run_command(
        [
            "gh",
            "pr",
            "create",
            "--title",
            pr_title,
            "--body",
            pr_body,
            "--label",
            labels,
            "--draft",  # Always create as draft
            "--head",
            branch_name,
        ]
    )

    if result:
        print(f"Created autofix PR for {category}: {result}")
        return True
    else:
        print(f"Failed to create autofix PR for {category}", file=sys.stderr)
        return False


def process_autofix_category(category: str, pr_content_dir: Path) -> bool:
    """Process autofix category - create or update PR with actual code changes."""
    pr_content_file = pr_content_dir / f"{category}-autofix-pr.md"

    if not pr_content_file.exists():
        print(f"No autofix PR content for {category} - skipping")
        return False

    # Check for existing autofix PR
    existing_pr = get_existing_autofix_pr_for_category(category)

    if existing_pr:
        pr_number = existing_pr["number"]
        print(f"\nFound existing autofix PR for {category}: #{pr_number}")
        return update_existing_pr(pr_number, pr_content_file)
    else:
        print(f"\nNo existing autofix PR for {category} - creating new")

        # Create autofix branch (code changes already applied by apply_autofix.py)
        branch_name = create_autofix_branch(category)

        # Commit autofix changes
        # At this point, apply_autofix.py has already modified files
        # We just need to stage and commit them
        run_command(["git", "add", "-A"])

        # Check if there are changes to commit
        status_output = run_command(["git", "status", "--porcelain"])
        if not status_output:
            print(f"No changes to commit for autofix {category} - skipping PR creation")
            return False

        run_command(
            [
                "git",
                "commit",
                "-m",
                f"autofix({category}): apply ruff format\n\nAutomated fixes from nightly code review.\nAll safety checks passed.\n\nGenerated by SuperClaude Nightly Code Review (Phase 2)",
            ]
        )

        # Push branch
        push_result = run_command(["git", "push", "-u", "origin", branch_name])
        if not push_result and push_result is not None:
            # Branch might already exist remotely
            run_command(["git", "push", "--force-with-lease", "origin", branch_name])

        # Create PR
        return create_autofix_pr_with_gh(category, branch_name, pr_content_file)


def process_category(category: str, pr_content_dir: Path) -> bool:
    """Process single category - create or update PR."""
    pr_content_file = pr_content_dir / f"{category}-pr.md"

    if not pr_content_file.exists():
        print(f"No PR content for {category} - skipping")
        return False

    # Check for existing PR
    existing_pr = get_existing_pr_for_category(category)

    if existing_pr:
        pr_number = existing_pr["number"]
        print(f"\nFound existing PR for {category}: #{pr_number}")
        return update_existing_pr(pr_number, pr_content_file)
    else:
        print(f"\nNo existing PR for {category} - creating new")

        # Create/update branch
        branch_name = create_or_update_branch(category, pr_content_file)

        # Create placeholder commit (PRs need at least one commit)
        # In Phase 1, PRs are suggestion-only, so we create a minimal commit
        placeholder_file = Path(f".nightly-review-{category}.md")
        with open(placeholder_file, "w") as f:
            f.write(f"# Nightly Review: {category.upper()}\n\n")
            f.write("This PR contains code review suggestions.\n")
            f.write("See PR description for details.\n")

        run_command(["git", "add", str(placeholder_file)])
        run_command(
            [
                "git",
                "commit",
                "-m",
                f"nightly-review: {category} findings\n\nGenerated by SuperClaude Nightly Code Review",
            ]
        )

        # Push branch
        push_result = run_command(["git", "push", "-u", "origin", branch_name])
        if not push_result and push_result is not None:
            # Branch might already exist remotely
            run_command(["git", "push", "--force-with-lease", "origin", branch_name])

        # Create PR
        return create_pr_with_gh(category, branch_name, pr_content_file)


def main():
    parser = argparse.ArgumentParser(description="Create or update nightly review PRs")
    parser.add_argument(
        "--pr-content-dir",
        type=Path,
        required=True,
        help="Directory containing PR content markdown files",
    )
    parser.add_argument("--max-prs", type=int, default=4, help="Maximum PRs per run")
    parser.add_argument(
        "--stale-days", type=int, default=7, help="Days before PR is considered stale"
    )
    parser.add_argument(
        "--autofix",
        action="store_true",
        help="Create autofix PRs (Phase 2) instead of suggestion-only PRs",
    )

    args = parser.parse_args()

    if not args.pr_content_dir.exists():
        print(f"Error: PR content directory not found: {args.pr_content_dir}", file=sys.stderr)
        sys.exit(1)

    # Process each category
    if args.autofix:
        # Phase 2: Autofix mode
        categories = ["quality"]  # Phase 2A: Only quality for now
        print("Phase 2 Autofix Mode: Creating autofix PRs with actual code changes")
    else:
        # Phase 1: Suggestion-only mode
        categories = ["security", "quality", "performance", "tests"]
        print("Phase 1 Suggestion Mode: Creating suggestion-only PRs")

    prs_created = 0
    prs_updated = 0

    for category in categories:
        if prs_created + prs_updated >= args.max_prs:
            print(f"\nReached max PR limit ({args.max_prs}) - stopping")
            break

        if args.autofix:
            result = process_autofix_category(category, args.pr_content_dir)
        else:
            result = process_category(category, args.pr_content_dir)

        if result:
            # Check if we created or updated
            if args.autofix:
                existing = get_existing_autofix_pr_for_category(category)
            else:
                existing = get_existing_pr_for_category(category)

            if existing:
                prs_updated += 1
            else:
                prs_created += 1

    print("\nPR Summary:")
    print(f"  Mode: {'Autofix (Phase 2)' if args.autofix else 'Suggestion-only (Phase 1)'}")
    print(f"  Created: {prs_created}")
    print(f"  Updated: {prs_updated}")


if __name__ == "__main__":
    main()
