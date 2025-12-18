"""
Skill Runtime System for SuperClaude Framework.

Configures and manages Skills-first runtime with Python fallback.
Enables dual runtime support for both native Skills and Python orchestration.
"""

import json
import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ModuleNotFoundError:
    yaml = None  # type: ignore

from .adapter import SkillAdapter, SkillMetadata
from .discovery import SkillDiscovery

logger = logging.getLogger(__name__)


@dataclass
class RuntimeConfig:
    """
    Configuration for Skills runtime.

    Attributes:
        runtime: Primary runtime mode ('skills' or 'python')
        skills_dir: Path to skills directory
        fallback_to_python: Whether to fallback to Python on skill failures
        enforced_guardrails: Guardrails that always run via Python
        script_timeout: Timeout for bundled script execution (seconds)
        progressive_loading: Enable progressive content loading
        cache_skills: Cache skill metadata in memory
    """

    runtime: str = "skills"  # 'skills' or 'python'
    skills_dir: str = ".claude/skills"
    fallback_to_python: bool = True

    # Guardrails that ALWAYS run regardless of runtime
    enforced_guardrails: list[str] = field(
        default_factory=lambda: [
            "evidence_gating",
            "quality_loop_limits",
            "safe_apply",
            "path_traversal_prevention",
        ]
    )

    script_timeout: int = 300  # 5 minutes
    progressive_loading: bool = True
    cache_skills: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RuntimeConfig":
        """Create config from dictionary."""
        default_guardrails = [
            "evidence_gating",
            "quality_loop_limits",
            "safe_apply",
            "path_traversal_prevention",
        ]
        return cls(
            runtime=data.get("runtime", "skills"),
            skills_dir=data.get("skills_dir", ".claude/skills"),
            fallback_to_python=data.get("fallback_to_python", True),
            enforced_guardrails=data.get("enforced_guardrails", default_guardrails),
            script_timeout=data.get("script_timeout", 300),
            progressive_loading=data.get("progressive_loading", True),
            cache_skills=data.get("cache_skills", True),
        )

    @classmethod
    def load(cls, config_path: str | Path | None = None) -> "RuntimeConfig":
        """
        Load configuration from file.

        Args:
            config_path: Path to config file (JSON or YAML)

        Returns:
            RuntimeConfig instance
        """
        if config_path is None:
            # Try default locations
            for default_path in [
                ".claude/settings.json",
                ".claude/settings.yaml",
                ".claude/config.json",
            ]:
                if Path(default_path).exists():
                    config_path = default_path
                    break

        if config_path is None:
            return cls()

        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return cls()

        try:
            content = path.read_text(encoding="utf-8")

            if path.suffix in [".yaml", ".yml"]:
                if yaml is None:
                    logger.warning("PyYAML not installed; using defaults")
                    return cls()
                data = yaml.safe_load(content)
            else:
                data = json.loads(content)

            # Extract superclaude section if present
            if "superclaude" in data:
                data = data["superclaude"]

            return cls.from_dict(data)

        except Exception as e:
            logger.error(f"Error loading config from {config_path}: {e}")
            return cls()

    def to_dict(self) -> dict[str, Any]:
        """Export config to dictionary."""
        return {
            "runtime": self.runtime,
            "skills_dir": self.skills_dir,
            "fallback_to_python": self.fallback_to_python,
            "enforced_guardrails": self.enforced_guardrails,
            "script_timeout": self.script_timeout,
            "progressive_loading": self.progressive_loading,
            "cache_skills": self.cache_skills,
        }


@dataclass
class ScriptResult:
    """Result from executing a bundled script."""

    success: bool
    output: dict[str, Any]
    error: str | None = None
    exit_code: int = 0


class SkillRuntime:
    """
    Runtime for executing Agent Skills.

    Features:
    - Skills-first execution with Python fallback
    - Bundled script execution
    - Enforced guardrails (evidence gating, quality loop)
    - Progressive content loading
    """

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        project_root: str | Path | None = None,
    ):
        """
        Initialize skill runtime.

        Args:
            config: Runtime configuration
            project_root: Project root directory
        """
        self.config = config or RuntimeConfig.load()
        self.project_root = Path(project_root) if project_root else Path.cwd()

        # Initialize components
        skills_path = self.project_root / self.config.skills_dir
        self.discovery = SkillDiscovery(skills_dir=skills_path)
        self.adapter = SkillAdapter()

        # Discover skills
        self.discovery.discover()

    def is_skills_first(self) -> bool:
        """Check if running in Skills-first mode."""
        return self.config.runtime == "skills"

    def get_skill(self, skill_id: str) -> SkillMetadata | None:
        """
        Get skill by ID with progressive loading.

        Args:
            skill_id: Skill identifier (e.g., 'sc-implement', 'agent-react-specialist')

        Returns:
            SkillMetadata or None
        """
        return self.discovery.get_skill(
            skill_id, load_content=self.config.progressive_loading
        )

    def find_skill_for_task(
        self,
        task: str,
        files: list[str] | None = None,
        languages: list[str] | None = None,
    ) -> SkillMetadata | None:
        """
        Find appropriate skill for a task.

        Args:
            task: Task description
            files: Files involved
            languages: Programming languages

        Returns:
            Best matching skill or None
        """
        return self.discovery.get_skill_for_task(task, files, languages)

    def execute_script(
        self,
        script_path: str | Path,
        args: dict[str, Any] | None = None,
    ) -> ScriptResult:
        """
        Execute a bundled Python script.

        Args:
            script_path: Path to Python script
            args: Arguments to pass as JSON

        Returns:
            ScriptResult with output and status
        """
        script_path = Path(script_path)
        if not script_path.exists():
            return ScriptResult(
                success=False,
                output={},
                error=f"Script not found: {script_path}",
                exit_code=1,
            )

        # Prepare arguments
        args_json = json.dumps(args or {})

        try:
            result = subprocess.run(
                ["python", str(script_path), args_json],
                capture_output=True,
                text=True,
                timeout=self.config.script_timeout,
                cwd=str(self.project_root),
            )

            # Parse JSON output
            try:
                output = json.loads(result.stdout) if result.stdout else {}
            except json.JSONDecodeError:
                output = {"raw_output": result.stdout}

            return ScriptResult(
                success=result.returncode == 0,
                output=output,
                error=result.stderr if result.returncode != 0 else None,
                exit_code=result.returncode,
            )

        except subprocess.TimeoutExpired:
            return ScriptResult(
                success=False,
                output={},
                error=f"Script timed out after {self.config.script_timeout}s",
                exit_code=-1,
            )
        except Exception as e:
            return ScriptResult(
                success=False,
                output={},
                error=str(e),
                exit_code=-1,
            )

    def run_select_agent(
        self,
        task: str,
        files: list[str] | None = None,
        languages: list[str] | None = None,
        keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Run agent selection script.

        Args:
            task: Task description
            files: Files involved
            languages: Programming languages
            keywords: Task keywords

        Returns:
            Agent selection result
        """
        script_path = (
            self.project_root
            / self.config.skills_dir
            / "sc-implement"
            / "scripts"
            / "select_agent.py"
        )

        args = {
            "task": task,
            "files": files or [],
            "languages": languages or [],
            "keywords": keywords or [],
        }

        result = self.execute_script(script_path, args)
        return result.output if result.success else {"error": result.error}

    def run_evidence_gate(
        self,
        command: str,
        changes: list[dict[str, Any]],
        tests: dict[str, Any] | None = None,
        lint: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Run evidence gate validation.

        This is an enforced guardrail that always runs.

        Args:
            command: Command being executed
            changes: List of file changes
            tests: Test results
            lint: Lint results

        Returns:
            Evidence gate result
        """
        script_path = (
            self.project_root
            / self.config.skills_dir
            / "sc-implement"
            / "scripts"
            / "evidence_gate.py"
        )

        args = {
            "command": command,
            "requires_evidence": True,
            "changes": changes,
            "tests": tests or {},
            "lint": lint or {},
        }

        result = self.execute_script(script_path, args)
        return (
            result.output
            if result.success
            else {"passed": False, "error": result.error}
        )

    def run_tests(
        self,
        target: str | None = None,
        test_type: str = "all",
        coverage: bool = False,
    ) -> dict[str, Any]:
        """
        Run test execution script.

        Args:
            target: Test target path
            test_type: Type of tests (unit, integration, e2e, all)
            coverage: Generate coverage report

        Returns:
            Test execution result
        """
        script_path = (
            self.project_root
            / self.config.skills_dir
            / "sc-implement"
            / "scripts"
            / "run_tests.py"
        )

        args = {
            "target": target or "",
            "type": test_type,
            "coverage": coverage,
            "project_root": str(self.project_root),
        }

        result = self.execute_script(script_path, args)
        return (
            result.output
            if result.success
            else {"success": False, "error": result.error}
        )

    def should_enforce_guardrail(self, guardrail: str) -> bool:
        """Check if a guardrail should be enforced."""
        return guardrail in self.config.enforced_guardrails

    def get_skill_content(self, skill: SkillMetadata) -> str:
        """
        Get full content for a skill.

        Implements progressive loading - returns cached content
        or loads from file.

        Args:
            skill: Skill to get content for

        Returns:
            Skill content string
        """
        if skill.content:
            return skill.content

        # Load content from file
        full_skill = self.adapter.load_skill(Path(skill.skill_dir))
        if full_skill:
            skill.content = full_skill.content
            return skill.content

        return ""

    def get_skill_resources(self, skill: SkillMetadata) -> dict[str, str]:
        """
        Get additional resources for a skill.

        Args:
            skill: Skill to get resources for

        Returns:
            Dictionary of resource name -> content
        """
        resources = {}

        for name, path in skill.resources.items():
            try:
                content = Path(path).read_text(encoding="utf-8")
                resources[name] = content
            except Exception as e:
                logger.warning(f"Failed to load resource {name}: {e}")

        return resources

    def list_commands(self) -> list[str]:
        """List all available command skills."""
        commands = self.discovery.get_commands()
        return [cmd.skill_id for cmd in commands]

    def list_agents(self) -> list[str]:
        """List all available agent skills."""
        agents = self.discovery.get_agents()
        return [agent.skill_id for agent in agents]

    def get_stats(self) -> dict[str, Any]:
        """Get runtime statistics."""
        return {
            "config": self.config.to_dict(),
            "skills": self.discovery.index.stats(),
            "project_root": str(self.project_root),
        }


def create_runtime(
    project_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> SkillRuntime:
    """
    Factory function to create SkillRuntime.

    Args:
        project_root: Project root directory
        config_path: Path to configuration file

    Returns:
        Configured SkillRuntime instance
    """
    config = RuntimeConfig.load(config_path)
    return SkillRuntime(config=config, project_root=project_root)
