"""
Integration Tests: Agent Frontmatter Validator

Tests the scripts/validate_agents.py validator that enforces
the tiered agent architecture schema.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pytest
import yaml

# =============================================================================
# Test Configuration
# =============================================================================

# Find repository root
REPO_ROOT = Path(__file__).parent.parent.parent
VALIDATOR_SCRIPT = REPO_ROOT / "scripts" / "validate_agents.py"
AGENTS_DIR = REPO_ROOT / "agents"


def run_validator(
    args: Optional[List[str]] = None, repo_root: Optional[Path] = None
) -> subprocess.CompletedProcess:
    """Run the validator script and return result."""
    cmd = [sys.executable, str(VALIDATOR_SCRIPT)]
    if args:
        cmd.extend(args)
    if repo_root:
        cmd.extend(["--repo-root", str(repo_root)])

    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )


def create_agent_file(tmp_path: Path, name: str, frontmatter: Dict) -> Path:
    """Create a temporary agent file with given frontmatter."""
    content = "---\n"
    content += yaml.dump(frontmatter, default_flow_style=False)
    content += "---\n\n"
    content += f"# {name.replace('-', ' ').title()}\n\n"
    content += "Agent description goes here.\n"

    filepath = tmp_path / f"{name}.md"
    filepath.write_text(content)
    return filepath


def setup_test_repo(tmp_path: Path) -> Path:
    """Set up a minimal test repository structure."""
    # Create required directories
    (tmp_path / "agents" / "core").mkdir(parents=True)
    (tmp_path / "agents" / "traits").mkdir(parents=True)
    (tmp_path / "agents" / "extensions").mkdir(parents=True)

    # Create pyproject.toml marker file (validator checks for this)
    (tmp_path / "pyproject.toml").write_text('[project]\nname = "test-superclaude"\n')

    return tmp_path


# =============================================================================
# Validator Script Tests
# =============================================================================


class TestValidatorScript:
    """Test the validator script execution."""

    def test_script_exists(self):
        """Verify validator script exists."""
        assert VALIDATOR_SCRIPT.exists(), f"Validator script not found at {VALIDATOR_SCRIPT}"

    def test_script_runs_successfully(self):
        """Test validator runs on actual repo."""
        result = run_validator()

        assert result.returncode == 0, f"Validator failed: {result.stderr}"
        assert "Validation PASSED" in result.stdout

    def test_verbose_flag(self):
        """Test --verbose flag shows warnings."""
        result = run_validator(["--verbose"])

        assert result.returncode == 0

    def test_strict_mode(self):
        """Test --strict mode treats warnings as errors."""
        result = run_validator(["--strict"])

        # Should pass since we have clean agents
        assert result.returncode == 0


class TestValidatorWithTestRepo:
    """Test validator behavior with temporary test repositories."""

    def test_valid_core_agent(self, tmp_path):
        """Test validation of a valid core agent."""
        repo = setup_test_repo(tmp_path)

        create_agent_file(
            repo / "agents" / "core",
            "test-agent",
            {
                "name": "test-agent",
                "description": "A test agent for validation",
                "tier": "core",
                "category": "testing",
                "triggers": ["test", "validate"],
                "tools": ["Read", "Write", "Bash"],
            },
        )

        result = run_validator(repo_root=repo)

        assert result.returncode == 0
        assert "Validation PASSED" in result.stdout

    def test_valid_trait(self, tmp_path):
        """Test validation of a valid trait."""
        repo = setup_test_repo(tmp_path)

        create_agent_file(
            repo / "agents" / "traits",
            "test-trait",
            {
                "name": "test-trait",
                "description": "A test trait modifier",
                "tier": "trait",
                "category": "modifier",
            },
        )

        result = run_validator(repo_root=repo)

        assert result.returncode == 0

    def test_valid_extension(self, tmp_path):
        """Test validation of a valid extension agent."""
        repo = setup_test_repo(tmp_path)

        create_agent_file(
            repo / "agents" / "extensions",
            "test-extension",
            {
                "name": "test-extension",
                "description": "A test extension agent",
                "tier": "extension",
                "category": "language",
                "triggers": ["testlang"],
                "tools": ["Read", "Edit"],
            },
        )

        result = run_validator(repo_root=repo)

        assert result.returncode == 0

    def test_missing_required_name(self, tmp_path):
        """Test error when name field is missing."""
        repo = setup_test_repo(tmp_path)

        create_agent_file(
            repo / "agents" / "core",
            "no-name-agent",
            {
                # "name": missing!
                "description": "Agent without name",
                "tier": "core",
            },
        )

        result = run_validator(repo_root=repo)

        assert result.returncode == 1
        assert "Missing required field: 'name'" in result.stdout

    def test_missing_required_description(self, tmp_path):
        """Test error when description field is missing."""
        repo = setup_test_repo(tmp_path)

        create_agent_file(
            repo / "agents" / "core",
            "no-desc-agent",
            {
                "name": "no-desc-agent",
                # "description": missing!
                "tier": "core",
            },
        )

        result = run_validator(repo_root=repo)

        assert result.returncode == 1
        assert "Missing required field: 'description'" in result.stdout

    def test_missing_required_tier(self, tmp_path):
        """Test error when tier field is missing."""
        repo = setup_test_repo(tmp_path)

        create_agent_file(
            repo / "agents" / "core",
            "no-tier-agent",
            {
                "name": "no-tier-agent",
                "description": "Agent without tier",
                # "tier": missing!
            },
        )

        result = run_validator(repo_root=repo)

        assert result.returncode == 1
        assert "Missing required field: 'tier'" in result.stdout

    def test_invalid_tier_value(self, tmp_path):
        """Test error on invalid tier value."""
        repo = setup_test_repo(tmp_path)

        create_agent_file(
            repo / "agents" / "core",
            "bad-tier-agent",
            {
                "name": "bad-tier-agent",
                "description": "Agent with invalid tier",
                "tier": "invalid-tier-value",
            },
        )

        result = run_validator(repo_root=repo)

        assert result.returncode == 1
        assert "'tier' must be one of" in result.stdout

    def test_invalid_name_format(self, tmp_path):
        """Test error on invalid name format (special characters)."""
        repo = setup_test_repo(tmp_path)

        create_agent_file(
            repo / "agents" / "core",
            "bad_name",
            {
                "name": "bad_name_with_underscores",  # Underscores not allowed
                "description": "Agent with invalid name format",
                "tier": "core",
            },
        )

        result = run_validator(repo_root=repo)

        # Invalid name format is an error
        assert result.returncode == 1
        assert "lowercase alphanumeric with hyphens" in result.stdout

    def test_duplicate_names(self, tmp_path):
        """Test error when two agents have the same name."""
        repo = setup_test_repo(tmp_path)

        # Create first agent
        create_agent_file(
            repo / "agents" / "core",
            "duplicate-agent",
            {
                "name": "duplicate-agent",
                "description": "First agent with this name",
                "tier": "core",
            },
        )

        # Create second agent with same name
        create_agent_file(
            repo / "agents" / "extensions",
            "duplicate-agent-ext",
            {
                "name": "duplicate-agent",  # Same name!
                "description": "Second agent with same name",
                "tier": "extension",
            },
        )

        result = run_validator(repo_root=repo)

        assert result.returncode == 1
        assert "Duplicate agent name" in result.stdout

    def test_unknown_tool_warning(self, tmp_path):
        """Test warning for unknown tool in verbose mode."""
        repo = setup_test_repo(tmp_path)

        create_agent_file(
            repo / "agents" / "core",
            "unknown-tool-agent",
            {
                "name": "unknown-tool-agent",
                "description": "Agent with unknown tool",
                "tier": "core",
                "tools": ["Read", "UnknownMagicTool"],
            },
        )

        result = run_validator(["--verbose"], repo_root=repo)

        # Should pass but with warning
        assert result.returncode == 0
        assert "Unknown tool" in result.stdout or "unknown tool" in result.stdout.lower()

    def test_strict_mode_fails_on_warning(self, tmp_path):
        """Test that strict mode treats warnings as errors."""
        repo = setup_test_repo(tmp_path)

        create_agent_file(
            repo / "agents" / "core",
            "warning-agent",
            {
                "name": "warning-agent",
                "description": "Agent that triggers a warning",
                "tier": "core",
                "tools": ["Read", "UnknownMagicTool"],  # Unknown tool = warning
            },
        )

        result = run_validator(["--strict"], repo_root=repo)

        # Should fail in strict mode
        assert result.returncode == 1
        assert "warnings treated as errors" in result.stdout.lower()

    def test_trait_should_not_have_triggers(self, tmp_path):
        """Test warning when trait has triggers defined."""
        repo = setup_test_repo(tmp_path)

        create_agent_file(
            repo / "agents" / "traits",
            "trait-with-triggers",
            {
                "name": "trait-with-triggers",
                "description": "Trait that incorrectly has triggers",
                "tier": "trait",
                "triggers": ["trigger1", "trigger2"],  # Traits shouldn't have this
            },
        )

        result = run_validator(["--verbose"], repo_root=repo)

        # Should pass but with warning
        assert result.returncode == 0
        assert "should not define 'triggers'" in result.stdout.lower()

    def test_referenced_trait_exists(self, tmp_path):
        """Test error when agent references non-existent trait."""
        repo = setup_test_repo(tmp_path)

        create_agent_file(
            repo / "agents" / "core",
            "agent-with-traits",
            {
                "name": "agent-with-traits",
                "description": "Agent referencing traits",
                "tier": "core",
                "traits": ["nonexistent-trait"],  # This trait doesn't exist
            },
        )

        result = run_validator(repo_root=repo)

        assert result.returncode == 1
        assert "unknown trait" in result.stdout.lower()


class TestActualAgents:
    """Test validation of actual agents in the repository."""

    def test_all_core_agents_valid(self):
        """Verify all core agents pass validation."""
        result = run_validator()

        assert result.returncode == 0
        assert "Errors: 0" in result.stdout

    def test_all_traits_valid(self):
        """Verify all traits pass validation."""
        result = run_validator()

        assert result.returncode == 0

    def test_all_extensions_valid(self):
        """Verify all extensions pass validation."""
        result = run_validator()

        assert result.returncode == 0

    def test_agent_count(self):
        """Verify expected number of agents are validated."""
        result = run_validator()

        # We should have 33 active agents (16 core + 10 traits + 7 extensions)
        assert "Files validated: 33" in result.stdout

    def test_no_deprecated_agents_in_active_paths(self):
        """Verify deprecated agents are not in active directories."""
        for active_path in ["core", "traits", "extensions"]:
            active_dir = AGENTS_DIR / active_path
            if active_dir.exists():
                for agent_file in active_dir.glob("*.md"):
                    assert "DEPRECATED" not in str(agent_file), (
                        f"Found deprecated agent in active path: {agent_file}"
                    )


class TestTraitConflictDetection:
    """Test trait conflict detection in select_agent.py."""

    def test_hard_conflict_detected(self):
        """Verify conflicting traits are detected."""
        select_script = (
            REPO_ROOT / ".claude" / "skills" / "sc-implement" / "scripts" / "select_agent.py"
        )

        if not select_script.exists():
            pytest.skip("select_agent.py not found")

        result = subprocess.run(
            [
                sys.executable,
                str(select_script),
                '{"task": "test", "traits": ["minimal-changes", "rapid-prototype"]}',
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )

        assert result.returncode == 0

        import json

        output = json.loads(result.stdout)

        assert "trait_conflicts" in output
        assert len(output["trait_conflicts"]) == 1
        assert output["trait_conflicts"][0]["severity"] == "error"
        assert "conflict_warning" in output

    def test_soft_tension_detected(self):
        """Verify trait tensions are detected and warned."""
        select_script = (
            REPO_ROOT / ".claude" / "skills" / "sc-implement" / "scripts" / "select_agent.py"
        )

        if not select_script.exists():
            pytest.skip("select_agent.py not found")

        result = subprocess.run(
            [
                sys.executable,
                str(select_script),
                '{"task": "test", "traits": ["legacy-friendly", "cloud-native"]}',
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )

        assert result.returncode == 0

        import json

        output = json.loads(result.stdout)

        assert "trait_tensions" in output
        assert len(output["trait_tensions"]) == 1
        assert output["trait_tensions"][0]["severity"] == "warning"
        assert "tension_note" in output

    def test_no_conflict_when_compatible(self):
        """Verify no conflicts for compatible traits."""
        select_script = (
            REPO_ROOT / ".claude" / "skills" / "sc-implement" / "scripts" / "select_agent.py"
        )

        if not select_script.exists():
            pytest.skip("select_agent.py not found")

        result = subprocess.run(
            [
                sys.executable,
                str(select_script),
                '{"task": "test", "traits": ["security-first", "test-driven"]}',
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )

        assert result.returncode == 0

        import json

        output = json.loads(result.stdout)

        assert "trait_conflicts" not in output
        assert "trait_tensions" not in output
        assert "security-first" in output["traits_applied"]
        assert "test-driven" in output["traits_applied"]


class TestSelectAgentIntegration:
    """Test integration between validator and select_agent.py."""

    def test_all_validated_agents_loadable(self):
        """Verify all validated agents can be loaded by select_agent.py."""
        select_script = (
            REPO_ROOT / ".claude" / "skills" / "sc-implement" / "scripts" / "select_agent.py"
        )

        if not select_script.exists():
            pytest.skip("select_agent.py not found")

        # Run select_agent with a simple task
        result = subprocess.run(
            [sys.executable, str(select_script), '{"task": "test task"}'],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )

        # Should run without errors
        assert result.returncode == 0, f"select_agent failed: {result.stderr}"

        # Should return valid JSON with expected fields
        import json

        output = json.loads(result.stdout)
        assert "selected_agent" in output
        assert "agent_path" in output

    def test_trait_composition_works(self):
        """Verify trait composition works with validated traits."""
        select_script = (
            REPO_ROOT / ".claude" / "skills" / "sc-implement" / "scripts" / "select_agent.py"
        )

        if not select_script.exists():
            pytest.skip("select_agent.py not found")

        # Run with trait specified
        result = subprocess.run(
            [
                sys.executable,
                str(select_script),
                '{"task": "secure api", "traits": ["security-first"]}',
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )

        assert result.returncode == 0

        import json

        output = json.loads(result.stdout)

        # Should have trait applied
        assert "traits_applied" in output
        assert "security-first" in output["traits_applied"]
        assert len(output["trait_paths"]) > 0
