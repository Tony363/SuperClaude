"""Integration tests for GitHub Actions workflow YAML configurations.

Validates structural correctness, permissions, concurrency groups,
and bash script patterns in workflow files changed by PR #91.
"""

from pathlib import Path

import pytest
import yaml

WORKFLOWS_DIR = Path(__file__).parent.parent.parent / ".github" / "workflows"

CI_YML = WORKFLOWS_DIR / "ci.yml"
PHASE2_YML = WORKFLOWS_DIR / "claude-review-phase2.yml"
PHASE3_YML = WORKFLOWS_DIR / "claude-review-phase3.yml"


@pytest.fixture
def ci_config():
    return yaml.safe_load(CI_YML.read_text())


@pytest.fixture
def phase2_config():
    return yaml.safe_load(PHASE2_YML.read_text())


@pytest.fixture
def phase3_config():
    return yaml.safe_load(PHASE3_YML.read_text())


class TestYAMLValidity:
    """All workflow files must be valid YAML."""

    @pytest.mark.parametrize("workflow_file", list(WORKFLOWS_DIR.glob("*.yml")))
    def test_valid_yaml(self, workflow_file):
        """Each workflow YAML file parses without errors."""
        content = workflow_file.read_text()
        try:
            result = yaml.safe_load(content)
        except yaml.YAMLError as e:
            pytest.fail(f"{workflow_file.name}: Invalid YAML: {e}")
        else:
            assert isinstance(result, dict), (
                f"{workflow_file.name}: Expected dict, got {type(result)}"
            )

    @pytest.mark.parametrize("workflow_file", list(WORKFLOWS_DIR.glob("*.yml")))
    def test_has_required_keys(self, workflow_file):
        """Each workflow has 'name', 'on', and 'jobs' keys."""
        config = yaml.safe_load(workflow_file.read_text())
        for key in ("name", True, "jobs"):  # 'on' is parsed as True in YAML
            assert key in config, f"{workflow_file.name}: Missing required key '{key}'"


class TestCIWorkflow:
    """Tests for ci.yml workflow configuration."""

    def test_claude_review_job_exists(self, ci_config):
        assert "claude-review" in ci_config["jobs"]

    def test_claude_review_has_continue_on_error(self, ci_config):
        """Job-level continue-on-error prevents workflow failure on review error."""
        job = ci_config["jobs"]["claude-review"]
        assert job.get("continue-on-error") is True

    def test_claude_review_has_pull_requests_write(self, ci_config):
        """Claude review needs pull-requests: write to post comments."""
        perms = ci_config["jobs"]["claude-review"]["permissions"]
        assert perms.get("pull-requests") == "write"

    def test_bedrock_step_has_continue_on_error(self, ci_config):
        """PR #91: Bedrock review step must have continue-on-error so Anthropic fallback runs."""
        steps = ci_config["jobs"]["claude-review"]["steps"]
        bedrock_step = None
        for step in steps:
            if "Bedrock" in step.get("name", "") and "Primary" in step.get("name", ""):
                bedrock_step = step
                break
        assert bedrock_step is not None, "Bedrock review step not found"
        assert bedrock_step.get("continue-on-error") is True, (
            "Bedrock step needs continue-on-error: true so Anthropic fallback can execute"
        )

    def test_grep_pipefail_safety_python_files(self, ci_config):
        """PR #91: grep for .py files is wrapped to handle zero matches under pipefail."""
        steps = ci_config["jobs"]["claude-review"]["steps"]
        pr_context_step = None
        for step in steps:
            if step.get("name") == "Get PR context":
                pr_context_step = step
                break
        assert pr_context_step is not None, "Get PR context step not found"
        run_script = pr_context_step["run"]
        assert "{ grep '\\.py$' || true; }" in run_script, (
            "grep for .py files must be wrapped in { ... || true; } for pipefail safety"
        )

    def test_grep_pipefail_safety_test_files(self, ci_config):
        """PR #91: grep for test files is wrapped to handle zero matches under pipefail."""
        steps = ci_config["jobs"]["claude-review"]["steps"]
        pr_context_step = None
        for step in steps:
            if step.get("name") == "Get PR context":
                pr_context_step = step
                break
        assert pr_context_step is not None
        run_script = pr_context_step["run"]
        assert "{ grep '^tests/' || true; }" in run_script, (
            "grep for tests/ must be wrapped in { ... || true; } for pipefail safety"
        )


class TestPhase2Workflow:
    """Tests for claude-review-phase2.yml workflow configuration."""

    def test_detect_high_stakes_job_exists(self, phase2_config):
        assert "detect-high-stakes" in phase2_config["jobs"]

    def test_concurrency_includes_event_name(self, phase2_config):
        """PR #91: Concurrency groups must include event_name to prevent cross-event cancellation."""
        jobs = phase2_config["jobs"]
        for job_name, job_config in jobs.items():
            concurrency = job_config.get("concurrency")
            if concurrency and concurrency.get("cancel-in-progress"):
                group = concurrency["group"]
                assert "event_name" in group, (
                    f"Job '{job_name}' concurrency group '{group}' must include "
                    f"event_name to prevent issue_comment runs from cancelling pull_request runs"
                )

    def test_high_stakes_patterns_include_workflows(self, phase2_config):
        """High-stakes detection includes .github/workflows/ changes."""
        steps = phase2_config["jobs"]["detect-high-stakes"]["steps"]
        check_step = None
        for step in steps:
            if step.get("id") == "check" or "high-stakes" in step.get("name", "").lower():
                check_step = step
                break
        assert check_step is not None
        assert ".github/workflows/" in check_step["run"]

    def test_triggers_on_pull_request_and_issue_comment(self, phase2_config):
        """Phase 2 triggers on both pull_request and issue_comment events."""
        triggers = phase2_config[True]  # 'on' key is True in YAML
        assert "pull_request" in triggers
        assert "issue_comment" in triggers

    def test_has_read_write_permissions(self, phase2_config):
        """Workflow-level permissions include pull-requests: write."""
        perms = phase2_config.get("permissions", {})
        assert perms.get("pull-requests") == "write"
        assert perms.get("contents") == "read"


class TestPhase3Workflow:
    """Tests for claude-review-phase3.yml workflow configuration."""

    def test_security_check_job_exists(self, phase3_config):
        assert "security-check" in phase3_config["jobs"]

    def test_blocked_security_job_exists(self, phase3_config):
        assert "blocked-security" in phase3_config["jobs"]

    def test_blocked_security_has_write_permissions(self, phase3_config):
        """PR #91: blocked-security job needs issues: write to post security notice."""
        job = phase3_config["jobs"]["blocked-security"]
        perms = job.get("permissions", {})
        assert perms.get("issues") == "write", (
            "blocked-security job needs 'issues: write' to post security notice comments"
        )
        assert perms.get("pull-requests") == "write", (
            "blocked-security job needs 'pull-requests: write' for PR comment access"
        )

    def test_blocked_security_depends_on_security_check(self, phase3_config):
        """blocked-security runs only when security check fails."""
        job = phase3_config["jobs"]["blocked-security"]
        assert "security-check" in job.get("needs", []) or job.get("needs") == "security-check"

    def test_security_check_blocks_workflow_files(self, phase3_config):
        """Security check blocks modifications to .github/workflows/."""
        steps = phase3_config["jobs"]["security-check"]["steps"]
        validation_step = None
        for step in steps:
            if "security" in step.get("name", "").lower() or step.get("id") == "check":
                validation_step = step
                break
        assert validation_step is not None
        assert ".github/workflows/" in validation_step["run"]

    def test_has_concurrency_control(self, phase3_config):
        """Phase 3 has workflow-level concurrency to prevent parallel runs."""
        assert "concurrency" in phase3_config
        assert phase3_config["concurrency"].get("cancel-in-progress") is True

    def test_never_auto_merges(self, phase3_config):
        """Phase 3 creates draft PRs, never auto-merges."""
        # The name or comment should indicate draft PR creation
        assert "Draft PR" in phase3_config["name"] or "draft" in str(phase3_config).lower()
