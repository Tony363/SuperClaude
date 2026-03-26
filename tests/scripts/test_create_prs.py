"""Tests for scripts/create_prs.py - PR creation and management with idempotency."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from scripts.create_prs import (
    AUTOFIX_CATEGORY_LABELS,
    CATEGORY_LABELS,
    create_autofix_branch,
    create_autofix_pr_with_gh,
    create_or_update_branch,
    create_pr_with_gh,
    get_existing_autofix_pr_for_category,
    get_existing_pr_for_category,
    main,
    process_autofix_category,
    process_category,
    run_command,
    update_existing_pr,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


class TestModuleConstants:
    """Verify module-level label dictionaries."""

    def test_category_labels_has_expected_keys(self):
        assert set(CATEGORY_LABELS.keys()) == {"security", "quality", "performance", "tests"}

    def test_category_labels_all_include_nightly_review(self):
        for category, labels in CATEGORY_LABELS.items():
            assert "nightly-review" in labels, f"{category} missing 'nightly-review'"
            assert "ai-generated" in labels, f"{category} missing 'ai-generated'"

    def test_autofix_category_labels_has_expected_keys(self):
        assert set(AUTOFIX_CATEGORY_LABELS.keys()) == {
            "security",
            "quality",
            "performance",
            "tests",
        }

    def test_autofix_category_labels_all_include_autofix(self):
        for category, labels in AUTOFIX_CATEGORY_LABELS.items():
            assert "nightly-review-autofix" in labels
            assert "autofix" in labels
            assert "ai-generated" in labels


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------


class TestRunCommand:
    """Tests for run_command subprocess wrapper."""

    def test_returns_stdout_stripped(self):
        # Arrange
        mock_result = subprocess.CompletedProcess(
            args=["echo", "hello"], returncode=0, stdout="  hello world  \n", stderr=""
        )

        # Act
        with patch("scripts.create_prs.subprocess.run", return_value=mock_result) as mock_run:
            result = run_command(["echo", "hello"])

        # Assert
        mock_run.assert_called_once_with(
            ["echo", "hello"], capture_output=True, text=True, check=True
        )
        assert result == "hello world"

    def test_returns_none_when_capture_output_false(self):
        # Arrange
        mock_result = subprocess.CompletedProcess(
            args=["git", "checkout", "main"], returncode=0, stdout="", stderr=""
        )

        # Act
        with patch("scripts.create_prs.subprocess.run", return_value=mock_result):
            result = run_command(["git", "checkout", "main"], capture_output=False)

        # Assert
        assert result is None

    def test_returns_none_on_failure_when_check_false(self):
        # Arrange
        mock_result = subprocess.CompletedProcess(
            args=["git", "rev-parse"], returncode=1, stdout="", stderr="error"
        )

        # Act
        with patch("scripts.create_prs.subprocess.run", return_value=mock_result):
            result = run_command(["git", "rev-parse", "--verify", "branch"], check=False)

        # Assert
        assert result is None

    def test_raises_on_failure_when_check_true(self):
        # Arrange / Act / Assert
        with patch(
            "scripts.create_prs.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "git"),
        ):
            with pytest.raises(subprocess.CalledProcessError):
                run_command(["git", "bad-command"], check=True)

    def test_returns_empty_string_for_empty_stdout(self):
        # Arrange
        mock_result = subprocess.CompletedProcess(args=["cmd"], returncode=0, stdout="", stderr="")

        # Act
        with patch("scripts.create_prs.subprocess.run", return_value=mock_result):
            result = run_command(["cmd"])

        # Assert
        assert result == ""


# ---------------------------------------------------------------------------
# get_existing_pr_for_category
# ---------------------------------------------------------------------------


class TestGetExistingPrForCategory:
    """Tests for get_existing_pr_for_category."""

    def test_returns_matching_pr(self):
        # Arrange
        prs = [
            {
                "number": 42,
                "title": "Nightly Review: Security",
                "headRefName": "nightly-review/security/2026-03-25",
                "labels": [{"name": "nightly-review"}, {"name": "security"}],
            }
        ]

        # Act
        with patch("scripts.create_prs.run_command", return_value=json.dumps(prs)):
            result = get_existing_pr_for_category("security")

        # Assert
        assert result is not None
        assert result["number"] == 42

    def test_returns_none_when_no_matching_branch(self):
        # Arrange
        prs = [
            {
                "number": 10,
                "title": "Some other PR",
                "headRefName": "nightly-review/quality/2026-03-25",
                "labels": [],
            }
        ]

        # Act
        with patch("scripts.create_prs.run_command", return_value=json.dumps(prs)):
            result = get_existing_pr_for_category("security")

        # Assert
        assert result is None

    def test_returns_none_when_run_command_returns_none(self):
        # Arrange / Act
        with patch("scripts.create_prs.run_command", return_value=None):
            result = get_existing_pr_for_category("security")

        # Assert
        assert result is None

    def test_returns_none_on_invalid_json(self):
        # Arrange / Act
        with patch("scripts.create_prs.run_command", return_value="not-json{"):
            result = get_existing_pr_for_category("quality")

        # Assert
        assert result is None

    def test_returns_none_for_empty_list(self):
        # Arrange / Act
        with patch("scripts.create_prs.run_command", return_value="[]"):
            result = get_existing_pr_for_category("performance")

        # Assert
        assert result is None

    def test_passes_correct_gh_command(self):
        # Arrange / Act
        with patch("scripts.create_prs.run_command", return_value="[]") as mock_cmd:
            get_existing_pr_for_category("tests")

        # Assert
        mock_cmd.assert_called_once_with(
            [
                "gh",
                "pr",
                "list",
                "--label",
                "nightly-review",
                "--label",
                "tests",
                "--state",
                "open",
                "--json",
                "number,title,headRefName,labels",
                "--limit",
                "10",
            ],
            check=False,
        )


# ---------------------------------------------------------------------------
# create_or_update_branch
# ---------------------------------------------------------------------------


class TestCreateOrUpdateBranch:
    """Tests for create_or_update_branch."""

    @patch("scripts.create_prs.datetime")
    @patch("scripts.create_prs.run_command")
    def test_checks_out_existing_branch(self, mock_cmd, mock_dt):
        # Arrange
        mock_dt.now.return_value.strftime.return_value = "2026-03-25"
        # First call: rev-parse succeeds (branch exists), second: checkout
        mock_cmd.side_effect = ["some-sha", None]

        # Act
        result = create_or_update_branch("security", Path("/tmp/pr.md"))

        # Assert
        assert result == "nightly-review/security/2026-03-25"
        assert mock_cmd.call_count == 2
        mock_cmd.assert_any_call(
            ["git", "rev-parse", "--verify", "nightly-review/security/2026-03-25"],
            check=False,
        )
        mock_cmd.assert_any_call(["git", "checkout", "nightly-review/security/2026-03-25"])

    @patch("scripts.create_prs.datetime")
    @patch("scripts.create_prs.run_command")
    def test_creates_new_branch_from_main(self, mock_cmd, mock_dt):
        # Arrange
        mock_dt.now.return_value.strftime.return_value = "2026-03-25"
        # rev-parse fails (branch not exist), symbolic-ref returns origin/HEAD,
        # checkout main, checkout -b new branch
        mock_cmd.side_effect = [None, "refs/remotes/origin/main", None, None]

        # Act
        result = create_or_update_branch("quality", Path("/tmp/pr.md"))

        # Assert
        assert result == "nightly-review/quality/2026-03-25"
        mock_cmd.assert_any_call(["git", "checkout", "main"])
        mock_cmd.assert_any_call(["git", "checkout", "-b", "nightly-review/quality/2026-03-25"])

    @patch("scripts.create_prs.datetime")
    @patch("scripts.create_prs.run_command")
    def test_defaults_to_main_when_symbolic_ref_fails(self, mock_cmd, mock_dt):
        # Arrange
        mock_dt.now.return_value.strftime.return_value = "2026-03-25"
        # rev-parse fails, symbolic-ref fails (returns None), checkout main, checkout -b
        mock_cmd.side_effect = [None, None, None, None]

        # Act
        result = create_or_update_branch("tests", Path("/tmp/pr.md"))

        # Assert
        assert result == "nightly-review/tests/2026-03-25"
        mock_cmd.assert_any_call(["git", "checkout", "main"])


# ---------------------------------------------------------------------------
# create_pr_with_gh
# ---------------------------------------------------------------------------


class TestCreatePrWithGh:
    """Tests for create_pr_with_gh."""

    def test_creates_pr_successfully(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "security-pr.md"
        pr_file.write_text("# Security Findings\n\nSome issues found.")

        # Act
        with patch("scripts.create_prs.run_command", return_value="https://github.com/repo/pull/1"):
            result = create_pr_with_gh("security", "nightly-review/security/2026-03-25", pr_file)

        # Assert
        assert result is True

    def test_extracts_title_from_first_line(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "quality-pr.md"
        pr_file.write_text("# Quality Report\n\nDetails here.")

        # Act
        with patch("scripts.create_prs.run_command", return_value="url") as mock_cmd:
            create_pr_with_gh("quality", "nightly-review/quality/2026-03-25", pr_file)

        # Assert - title extracted from first line
        cmd_args = mock_cmd.call_args[0][0]
        title_idx = cmd_args.index("--title") + 1
        assert cmd_args[title_idx] == "Quality Report"

    def test_empty_content_gives_empty_title(self, tmp_path):
        # Arrange - empty file split gives [""] which is truthy, no fallback
        pr_file = tmp_path / "performance-pr.md"
        pr_file.write_text("")

        # Act
        with patch("scripts.create_prs.run_command", return_value="url") as mock_cmd:
            create_pr_with_gh("performance", "nightly-review/performance/2026-03-25", pr_file)

        # Assert - "".strip("# ") is ""
        cmd_args = mock_cmd.call_args[0][0]
        title_idx = cmd_args.index("--title") + 1
        assert cmd_args[title_idx] == ""

    def test_returns_false_when_file_missing(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "nonexistent.md"

        # Act
        result = create_pr_with_gh("security", "branch-name", pr_file)

        # Assert
        assert result is False

    def test_returns_false_when_gh_returns_none(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "tests-pr.md"
        pr_file.write_text("# Test Findings\n\nContent.")

        # Act
        with patch("scripts.create_prs.run_command", return_value=None):
            result = create_pr_with_gh("tests", "branch", pr_file)

        # Assert
        assert result is False

    def test_returns_false_when_gh_returns_empty(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "tests-pr.md"
        pr_file.write_text("# Test Findings\n\nContent.")

        # Act
        with patch("scripts.create_prs.run_command", return_value=""):
            result = create_pr_with_gh("tests", "branch", pr_file)

        # Assert
        assert result is False

    def test_uses_correct_labels(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "security-pr.md"
        pr_file.write_text("# Title\nBody")

        # Act
        with patch("scripts.create_prs.run_command", return_value="url") as mock_cmd:
            create_pr_with_gh("security", "branch", pr_file)

        # Assert
        cmd_args = mock_cmd.call_args[0][0]
        label_idx = cmd_args.index("--label") + 1
        expected_labels = ",".join(CATEGORY_LABELS["security"])
        assert cmd_args[label_idx] == expected_labels

    def test_creates_as_draft(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "security-pr.md"
        pr_file.write_text("# Title\nBody")

        # Act
        with patch("scripts.create_prs.run_command", return_value="url") as mock_cmd:
            create_pr_with_gh("security", "branch", pr_file)

        # Assert
        cmd_args = mock_cmd.call_args[0][0]
        assert "--draft" in cmd_args

    def test_uses_fallback_labels_for_unknown_category(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "unknown-pr.md"
        pr_file.write_text("# Title\nBody")

        # Act
        with patch("scripts.create_prs.run_command", return_value="url") as mock_cmd:
            create_pr_with_gh("unknown", "branch", pr_file)

        # Assert
        cmd_args = mock_cmd.call_args[0][0]
        label_idx = cmd_args.index("--label") + 1
        assert cmd_args[label_idx] == "nightly-review,ai-generated"


# ---------------------------------------------------------------------------
# update_existing_pr
# ---------------------------------------------------------------------------


class TestUpdateExistingPr:
    """Tests for update_existing_pr."""

    def test_updates_pr_successfully(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "security-pr.md"
        pr_file.write_text("# Updated content\n\nNew findings.")

        # Act
        with patch("scripts.create_prs.run_command", return_value="") as mock_cmd:
            result = update_existing_pr(42, pr_file)

        # Assert
        assert result is True
        mock_cmd.assert_called_once_with(
            ["gh", "pr", "edit", "42", "--body", "# Updated content\n\nNew findings."]
        )

    def test_returns_false_when_file_missing(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "nonexistent.md"

        # Act
        result = update_existing_pr(42, pr_file)

        # Assert
        assert result is False

    def test_lets_crash_propagate_from_gh(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "security-pr.md"
        pr_file.write_text("body")

        # Act / Assert
        with patch(
            "scripts.create_prs.run_command",
            side_effect=subprocess.CalledProcessError(1, "gh"),
        ):
            with pytest.raises(subprocess.CalledProcessError):
                update_existing_pr(42, pr_file)


# ---------------------------------------------------------------------------
# get_existing_autofix_pr_for_category
# ---------------------------------------------------------------------------


class TestGetExistingAutofixPrForCategory:
    """Tests for get_existing_autofix_pr_for_category."""

    def test_returns_matching_autofix_pr(self):
        # Arrange
        prs = [
            {
                "number": 99,
                "title": "AUTOFIX: Quality",
                "headRefName": "nightly-review-autofix/quality/2026-03-25",
                "labels": [],
            }
        ]

        # Act
        with patch("scripts.create_prs.run_command", return_value=json.dumps(prs)):
            result = get_existing_autofix_pr_for_category("quality")

        # Assert
        assert result is not None
        assert result["number"] == 99

    def test_returns_none_when_no_matching_branch(self):
        # Arrange
        prs = [
            {
                "number": 10,
                "headRefName": "nightly-review-autofix/security/2026-03-25",
                "labels": [],
            }
        ]

        # Act
        with patch("scripts.create_prs.run_command", return_value=json.dumps(prs)):
            result = get_existing_autofix_pr_for_category("quality")

        # Assert
        assert result is None

    def test_returns_none_when_output_is_none(self):
        # Arrange / Act
        with patch("scripts.create_prs.run_command", return_value=None):
            result = get_existing_autofix_pr_for_category("quality")

        # Assert
        assert result is None

    def test_returns_none_on_invalid_json(self):
        # Arrange / Act
        with patch("scripts.create_prs.run_command", return_value="<html>error</html>"):
            result = get_existing_autofix_pr_for_category("quality")

        # Assert
        assert result is None

    def test_passes_correct_gh_command(self):
        # Arrange / Act
        with patch("scripts.create_prs.run_command", return_value="[]") as mock_cmd:
            get_existing_autofix_pr_for_category("security")

        # Assert
        mock_cmd.assert_called_once_with(
            [
                "gh",
                "pr",
                "list",
                "--label",
                "nightly-review-autofix",
                "--label",
                "security",
                "--state",
                "open",
                "--json",
                "number,title,headRefName,labels",
                "--limit",
                "10",
            ],
            check=False,
        )


# ---------------------------------------------------------------------------
# create_autofix_branch
# ---------------------------------------------------------------------------


class TestCreateAutofixBranch:
    """Tests for create_autofix_branch."""

    @patch("scripts.create_prs.datetime")
    @patch("scripts.create_prs.run_command")
    def test_checks_out_existing_branch(self, mock_cmd, mock_dt):
        # Arrange
        mock_dt.now.return_value.strftime.return_value = "2026-03-25"
        mock_cmd.side_effect = ["some-sha", None]

        # Act
        result = create_autofix_branch("quality")

        # Assert
        assert result == "nightly-review-autofix/quality/2026-03-25"
        mock_cmd.assert_any_call(
            ["git", "rev-parse", "--verify", "nightly-review-autofix/quality/2026-03-25"],
            check=False,
        )
        mock_cmd.assert_any_call(["git", "checkout", "nightly-review-autofix/quality/2026-03-25"])

    @patch("scripts.create_prs.datetime")
    @patch("scripts.create_prs.run_command")
    def test_creates_new_branch_from_main(self, mock_cmd, mock_dt):
        # Arrange
        mock_dt.now.return_value.strftime.return_value = "2026-03-25"
        mock_cmd.side_effect = [None, "refs/remotes/origin/main", None, None]

        # Act
        result = create_autofix_branch("quality")

        # Assert
        assert result == "nightly-review-autofix/quality/2026-03-25"
        mock_cmd.assert_any_call(["git", "checkout", "main"])
        mock_cmd.assert_any_call(
            ["git", "checkout", "-b", "nightly-review-autofix/quality/2026-03-25"]
        )

    @patch("scripts.create_prs.datetime")
    @patch("scripts.create_prs.run_command")
    def test_defaults_to_main_when_symbolic_ref_fails(self, mock_cmd, mock_dt):
        # Arrange
        mock_dt.now.return_value.strftime.return_value = "2026-03-25"
        mock_cmd.side_effect = [None, None, None, None]

        # Act
        result = create_autofix_branch("security")

        # Assert
        assert result == "nightly-review-autofix/security/2026-03-25"
        mock_cmd.assert_any_call(["git", "checkout", "main"])


# ---------------------------------------------------------------------------
# create_autofix_pr_with_gh
# ---------------------------------------------------------------------------


class TestCreateAutofixPrWithGh:
    """Tests for create_autofix_pr_with_gh."""

    def test_creates_autofix_pr_successfully(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "quality-autofix-pr.md"
        pr_file.write_text("# AUTOFIX: Quality\n\nFormatting fixes.")

        # Act
        with patch("scripts.create_prs.run_command", return_value="https://github.com/repo/pull/5"):
            result = create_autofix_pr_with_gh(
                "quality", "nightly-review-autofix/quality/2026-03-25", pr_file
            )

        # Assert
        assert result is True

    def test_extracts_title_from_first_line(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "quality-autofix-pr.md"
        pr_file.write_text("# AUTOFIX: Quality Formatting\n\nDetails.")

        # Act
        with patch("scripts.create_prs.run_command", return_value="url") as mock_cmd:
            create_autofix_pr_with_gh("quality", "branch", pr_file)

        # Assert
        cmd_args = mock_cmd.call_args[0][0]
        title_idx = cmd_args.index("--title") + 1
        assert cmd_args[title_idx] == "AUTOFIX: Quality Formatting"

    def test_empty_content_gives_empty_title(self, tmp_path):
        # Arrange — empty file splits to [""] which is truthy, so no fallback
        pr_file = tmp_path / "quality-autofix-pr.md"
        pr_file.write_text("")

        # Act
        with patch("scripts.create_prs.run_command", return_value="url") as mock_cmd:
            create_autofix_pr_with_gh("quality", "branch", pr_file)

        # Assert
        cmd_args = mock_cmd.call_args[0][0]
        title_idx = cmd_args.index("--title") + 1
        assert cmd_args[title_idx] == ""

    def test_returns_false_when_file_missing(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "nonexistent.md"

        # Act
        result = create_autofix_pr_with_gh("quality", "branch", pr_file)

        # Assert
        assert result is False

    def test_returns_false_when_gh_returns_empty(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "quality-autofix-pr.md"
        pr_file.write_text("# Title\nBody")

        # Act
        with patch("scripts.create_prs.run_command", return_value=""):
            result = create_autofix_pr_with_gh("quality", "branch", pr_file)

        # Assert
        assert result is False

    def test_uses_autofix_labels(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "quality-autofix-pr.md"
        pr_file.write_text("# Title\nBody")

        # Act
        with patch("scripts.create_prs.run_command", return_value="url") as mock_cmd:
            create_autofix_pr_with_gh("quality", "branch", pr_file)

        # Assert
        cmd_args = mock_cmd.call_args[0][0]
        label_idx = cmd_args.index("--label") + 1
        expected = ",".join(AUTOFIX_CATEGORY_LABELS["quality"])
        assert cmd_args[label_idx] == expected

    def test_uses_fallback_labels_for_unknown_category(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "unknown-autofix-pr.md"
        pr_file.write_text("# Title\nBody")

        # Act
        with patch("scripts.create_prs.run_command", return_value="url") as mock_cmd:
            create_autofix_pr_with_gh("unknown", "branch", pr_file)

        # Assert
        cmd_args = mock_cmd.call_args[0][0]
        label_idx = cmd_args.index("--label") + 1
        assert cmd_args[label_idx] == "nightly-review-autofix,ai-generated"

    def test_creates_as_draft(self, tmp_path):
        # Arrange
        pr_file = tmp_path / "quality-autofix-pr.md"
        pr_file.write_text("# Title\nBody")

        # Act
        with patch("scripts.create_prs.run_command", return_value="url") as mock_cmd:
            create_autofix_pr_with_gh("quality", "branch", pr_file)

        # Assert
        cmd_args = mock_cmd.call_args[0][0]
        assert "--draft" in cmd_args


# ---------------------------------------------------------------------------
# process_autofix_category
# ---------------------------------------------------------------------------


class TestProcessAutofixCategory:
    """Tests for process_autofix_category."""

    def test_skips_when_no_content_file(self, tmp_path):
        # Arrange - no file created

        # Act
        result = process_autofix_category("quality", tmp_path)

        # Assert
        assert result is False

    @patch("scripts.create_prs.update_existing_pr", return_value=True)
    @patch(
        "scripts.create_prs.get_existing_autofix_pr_for_category",
        return_value={"number": 55, "headRefName": "nightly-review-autofix/quality/2026-03-25"},
    )
    def test_updates_existing_pr(self, mock_get, mock_update, tmp_path):
        # Arrange
        pr_file = tmp_path / "quality-autofix-pr.md"
        pr_file.write_text("# Autofix content")

        # Act
        result = process_autofix_category("quality", tmp_path)

        # Assert
        assert result is True
        mock_update.assert_called_once_with(55, pr_file)

    @patch("scripts.create_prs.create_autofix_pr_with_gh", return_value=True)
    @patch("scripts.create_prs.run_command")
    @patch(
        "scripts.create_prs.create_autofix_branch",
        return_value="nightly-review-autofix/quality/2026-03-25",
    )
    @patch("scripts.create_prs.get_existing_autofix_pr_for_category", return_value=None)
    def test_creates_new_pr_when_changes_exist(
        self, mock_get, mock_branch, mock_cmd, mock_create_pr, tmp_path
    ):
        # Arrange
        pr_file = tmp_path / "quality-autofix-pr.md"
        pr_file.write_text("# Autofix Quality\n\nChanges applied.")
        # run_command calls: git add, git status (has changes), git commit, git push
        mock_cmd.side_effect = [None, "M some_file.py", None, None]

        # Act
        result = process_autofix_category("quality", tmp_path)

        # Assert
        assert result is True
        mock_branch.assert_called_once_with("quality")
        mock_create_pr.assert_called_once_with(
            "quality", "nightly-review-autofix/quality/2026-03-25", pr_file
        )

    @patch("scripts.create_prs.run_command")
    @patch(
        "scripts.create_prs.create_autofix_branch",
        return_value="nightly-review-autofix/quality/2026-03-25",
    )
    @patch("scripts.create_prs.get_existing_autofix_pr_for_category", return_value=None)
    def test_skips_pr_when_no_changes(self, mock_get, mock_branch, mock_cmd, tmp_path):
        # Arrange
        pr_file = tmp_path / "quality-autofix-pr.md"
        pr_file.write_text("# Autofix Quality\n")
        # run_command calls: git add, git status (empty = no changes)
        mock_cmd.side_effect = [None, ""]

        # Act
        result = process_autofix_category("quality", tmp_path)

        # Assert
        assert result is False


# ---------------------------------------------------------------------------
# process_category
# ---------------------------------------------------------------------------


class TestProcessCategory:
    """Tests for process_category."""

    def test_skips_when_no_content_file(self, tmp_path):
        # Arrange - no file created

        # Act
        result = process_category("security", tmp_path)

        # Assert
        assert result is False

    @patch("scripts.create_prs.update_existing_pr", return_value=True)
    @patch(
        "scripts.create_prs.get_existing_pr_for_category",
        return_value={"number": 10, "headRefName": "nightly-review/security/2026-03-25"},
    )
    def test_updates_existing_pr(self, mock_get, mock_update, tmp_path):
        # Arrange
        pr_file = tmp_path / "security-pr.md"
        pr_file.write_text("# Security findings")

        # Act
        result = process_category("security", tmp_path)

        # Assert
        assert result is True
        mock_update.assert_called_once_with(10, pr_file)

    @patch("scripts.create_prs.create_pr_with_gh", return_value=True)
    @patch("scripts.create_prs.run_command")
    @patch(
        "scripts.create_prs.create_or_update_branch",
        return_value="nightly-review/security/2026-03-25",
    )
    @patch("scripts.create_prs.get_existing_pr_for_category", return_value=None)
    def test_creates_new_pr(self, mock_get, mock_branch, mock_cmd, mock_create_pr, tmp_path):
        # Arrange
        pr_file = tmp_path / "security-pr.md"
        pr_file.write_text("# Security\n\nFindings here.")
        # run_command calls: git add, git commit, git push
        mock_cmd.return_value = None

        # Act
        result = process_category("security", tmp_path)

        # Assert
        assert result is True
        mock_branch.assert_called_once_with("security", pr_file)
        mock_create_pr.assert_called_once_with(
            "security", "nightly-review/security/2026-03-25", pr_file
        )

    @patch("scripts.create_prs.create_pr_with_gh", return_value=True)
    @patch("scripts.create_prs.run_command")
    @patch(
        "scripts.create_prs.create_or_update_branch",
        return_value="nightly-review/quality/2026-03-25",
    )
    @patch("scripts.create_prs.get_existing_pr_for_category", return_value=None)
    def test_creates_placeholder_file(
        self, mock_get, mock_branch, mock_cmd, mock_pr, tmp_path, monkeypatch
    ):
        # Arrange
        pr_file = tmp_path / "quality-pr.md"
        pr_file.write_text("# Quality\n\nContent.")
        mock_cmd.return_value = None
        # Change cwd so placeholder file is created in tmp_path
        monkeypatch.chdir(tmp_path)

        # Act
        process_category("quality", tmp_path)

        # Assert - placeholder file was created
        placeholder = tmp_path / ".nightly-review-quality.md"
        assert placeholder.exists()
        content = placeholder.read_text()
        assert "QUALITY" in content
        assert "code review suggestions" in content


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


class TestMain:
    """Tests for main CLI entry point."""

    def test_exits_when_dir_not_found(self, monkeypatch, tmp_path):
        # Arrange
        nonexistent = tmp_path / "no-such-dir"
        monkeypatch.setattr("sys.argv", ["create_prs.py", "--pr-content-dir", str(nonexistent)])

        # Act / Assert
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 1

    @patch("scripts.create_prs.get_existing_pr_for_category", return_value=None)
    @patch("scripts.create_prs.process_category", return_value=False)
    def test_suggestion_mode_processes_all_categories(
        self, mock_process, mock_get, monkeypatch, tmp_path
    ):
        # Arrange
        monkeypatch.setattr("sys.argv", ["create_prs.py", "--pr-content-dir", str(tmp_path)])

        # Act
        main()

        # Assert - processes all 4 categories in suggestion mode
        assert mock_process.call_count == 4
        categories_called = [c[0][0] for c in mock_process.call_args_list]
        assert set(categories_called) == {"security", "quality", "performance", "tests"}

    @patch("scripts.create_prs.get_existing_autofix_pr_for_category", return_value=None)
    @patch("scripts.create_prs.process_autofix_category", return_value=False)
    def test_autofix_mode_processes_quality_only(
        self, mock_process, mock_get, monkeypatch, tmp_path
    ):
        # Arrange
        monkeypatch.setattr(
            "sys.argv",
            ["create_prs.py", "--pr-content-dir", str(tmp_path), "--autofix"],
        )

        # Act
        main()

        # Assert - only processes quality in autofix mode (Phase 2A)
        assert mock_process.call_count == 1
        mock_process.assert_called_once_with("quality", tmp_path)

    @patch("scripts.create_prs.get_existing_pr_for_category", return_value={"number": 1})
    @patch("scripts.create_prs.process_category", return_value=True)
    def test_respects_max_prs_limit(self, mock_process, mock_get, monkeypatch, tmp_path):
        # Arrange
        monkeypatch.setattr(
            "sys.argv",
            ["create_prs.py", "--pr-content-dir", str(tmp_path), "--max-prs", "2"],
        )

        # Act
        main()

        # Assert - stops after max_prs
        assert mock_process.call_count == 2

    @patch("scripts.create_prs.get_existing_pr_for_category", return_value=None)
    @patch("scripts.create_prs.process_category", return_value=True)
    def test_counts_created_prs(self, mock_process, mock_get, monkeypatch, tmp_path, capsys):
        # Arrange
        monkeypatch.setattr("sys.argv", ["create_prs.py", "--pr-content-dir", str(tmp_path)])

        # Act
        main()

        # Assert
        captured = capsys.readouterr()
        assert "Created:" in captured.out

    @patch("scripts.create_prs.get_existing_pr_for_category", return_value={"number": 1})
    @patch("scripts.create_prs.process_category", return_value=True)
    def test_counts_updated_prs(self, mock_process, mock_get, monkeypatch, tmp_path, capsys):
        # Arrange
        monkeypatch.setattr("sys.argv", ["create_prs.py", "--pr-content-dir", str(tmp_path)])

        # Act
        main()

        # Assert
        captured = capsys.readouterr()
        assert "Updated:" in captured.out

    def test_autofix_flag_prints_phase2_mode(self, monkeypatch, tmp_path, capsys):
        # Arrange
        monkeypatch.setattr(
            "sys.argv",
            ["create_prs.py", "--pr-content-dir", str(tmp_path), "--autofix"],
        )

        # Act
        with patch("scripts.create_prs.process_autofix_category", return_value=False):
            with patch(
                "scripts.create_prs.get_existing_autofix_pr_for_category", return_value=None
            ):
                main()

        # Assert
        captured = capsys.readouterr()
        assert "Autofix" in captured.out

    def test_suggestion_mode_prints_phase1(self, monkeypatch, tmp_path, capsys):
        # Arrange
        monkeypatch.setattr("sys.argv", ["create_prs.py", "--pr-content-dir", str(tmp_path)])

        # Act
        with patch("scripts.create_prs.process_category", return_value=False):
            with patch("scripts.create_prs.get_existing_pr_for_category", return_value=None):
                main()

        # Assert
        captured = capsys.readouterr()
        assert "Suggestion" in captured.out
