"""Integration tests for GitHub Actions workflow YAML configurations.

Validates structural correctness, permissions, concurrency groups,
and bash script patterns in workflow files changed by PR #91.
"""

from pathlib import Path

import pytest
import yaml

WORKFLOWS_DIR = Path(__file__).parent.parent.parent / ".github" / "workflows"

CI_YML = WORKFLOWS_DIR / "ci.yml"
AI_CODE_REVIEW_YML = WORKFLOWS_DIR / "ai-code-review.yml"


@pytest.fixture
def ci_config():
    return yaml.safe_load(CI_YML.read_text())


@pytest.fixture
def ai_code_review_config():
    """Consolidated AI code review workflow (replaces phase1/2/3)."""
    return yaml.safe_load(AI_CODE_REVIEW_YML.read_text())


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


class TestAICodeReviewWorkflow:
    """Tests for consolidated ai-code-review.yml workflow (replaces phase1/2/3)."""

    def test_has_preflight_job(self, ai_code_review_config):
        """Preflight job gates all downstream work."""
        assert "preflight" in ai_code_review_config["jobs"]

    def test_has_review_job(self, ai_code_review_config):
        """Review job performs comment-only review + consensus."""
        assert "review" in ai_code_review_config["jobs"]

    def test_has_autofix_job(self, ai_code_review_config):
        """Autofix job creates draft PRs with fixes."""
        assert "autofix" in ai_code_review_config["jobs"]

    def test_review_depends_on_preflight(self, ai_code_review_config):
        """Review job needs preflight to complete first."""
        job = ai_code_review_config["jobs"]["review"]
        needs = job.get("needs")
        assert needs == "preflight" or "preflight" in needs

    def test_autofix_depends_on_preflight_and_review(self, ai_code_review_config):
        """Autofix job depends on both preflight and review."""
        job = ai_code_review_config["jobs"]["autofix"]
        needs = job.get("needs", [])
        if isinstance(needs, str):
            needs = [needs]
        assert "preflight" in needs, "autofix must depend on preflight"
        assert "review" in needs, "autofix must depend on review"

    def test_triggers_on_pull_request_and_issue_comment(self, ai_code_review_config):
        """Workflow triggers on both pull_request and issue_comment events."""
        triggers = ai_code_review_config[True]  # 'on' key is True in YAML
        assert "pull_request" in triggers
        assert "issue_comment" in triggers

    def test_has_concurrency_control(self, ai_code_review_config):
        """Workflow has concurrency group to prevent parallel runs."""
        assert "concurrency" in ai_code_review_config
        concurrency = ai_code_review_config["concurrency"]
        assert concurrency.get("cancel-in-progress") is True
        # Should include PR or issue number in group
        group = concurrency["group"]
        assert "pull_request.number" in group or "issue.number" in group

    def test_preflight_checks_high_stakes_files(self, ai_code_review_config):
        """Preflight job detects high-stakes files for consensus."""
        steps = ai_code_review_config["jobs"]["preflight"]["steps"]
        gate_step = None
        for step in steps:
            if step.get("id") == "gate" or "evaluate" in step.get("name", "").lower():
                gate_step = step
                break
        assert gate_step is not None, "Evaluate gates step not found"
        run_script = gate_step["run"]
        # Should check for workflow files in high-stakes patterns
        assert ".github/workflows/" in run_script
        # Should output should_consensus
        assert "should_consensus" in run_script.lower()

    def test_autofix_blocks_protected_files(self, ai_code_review_config):
        """Autofix job prevents modifications to protected files."""
        job = ai_code_review_config["jobs"]["autofix"]
        steps = job["steps"]
        validation_step = None
        for step in steps:
            if (
                "protect" in step.get("name", "").lower()
                or "validate" in step.get("name", "").lower()
            ):
                validation_step = step
                break
        assert validation_step is not None, "Protected file validation not found"
        run_script = validation_step["run"]
        # Should block workflow files, secrets, env files
        assert ".github/workflows/" in run_script
        assert "secrets/" in run_script or ".env" in run_script

    def test_autofix_has_write_permissions(self, ai_code_review_config):
        """Autofix job needs write permissions to create PRs."""
        job = ai_code_review_config["jobs"]["autofix"]
        perms = job.get("permissions", {})
        assert perms.get("contents") == "write", "autofix needs contents:write"
        assert perms.get("pull-requests") == "write", "autofix needs pull-requests:write"

    def test_review_has_read_and_pr_write_permissions(self, ai_code_review_config):
        """Review job needs pull-requests: write to comment."""
        job = ai_code_review_config["jobs"]["review"]
        perms = job.get("permissions", {})
        assert perms.get("pull-requests") == "write", "review needs pull-requests:write"
        assert perms.get("contents") == "read", "review should only read contents"

    def test_uses_github_token_not_pat(self, ai_code_review_config):
        """Autofix uses GITHUB_TOKEN to prevent recursive triggers."""
        job = ai_code_review_config["jobs"]["autofix"]
        steps = job["steps"]
        pr_create_step = None
        for step in steps:
            if "create-pull-request" in step.get("uses", ""):
                pr_create_step = step
                break
        assert pr_create_step is not None, "create-pull-request step not found"
        # Should use GITHUB_TOKEN, not PAT
        with_block = pr_create_step.get("with", {})
        token = with_block.get("token", "")
        assert "GITHUB_TOKEN" in token, "Must use GITHUB_TOKEN not PAT for recursive safety"
        assert "PAT" not in token, "Must not use PAT_TOKEN"

    def test_creates_draft_prs_only(self, ai_code_review_config):
        """Autofix creates draft PRs, never auto-merges."""
        job = ai_code_review_config["jobs"]["autofix"]
        steps = job["steps"]
        pr_create_step = None
        for step in steps:
            if "create-pull-request" in step.get("uses", ""):
                pr_create_step = step
                break
        assert pr_create_step is not None
        with_block = pr_create_step.get("with", {})
        # Should explicitly set draft: true
        assert with_block.get("draft") == "true" or with_block.get("draft") is True
