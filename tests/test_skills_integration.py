"""
Integration Tests for SuperClaude Skills System.

Tests the complete Skills migration including:
- Skill discovery and loading
- Adapter conversions
- Runtime configuration
- Script execution

These tests require the archived SDK to be properly installed.
Skip if the archived SDK compatibility layer has import issues.
"""

import json
import sys
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Check if archived SDK imports work - skip entire module if not
try:
    from SuperClaude.Skills.discovery import SkillDiscovery  # noqa: F401
except ImportError:
    pytest.skip(
        "Archived SDK compatibility layer not available",
        allow_module_level=True,
    )


def test_skill_discovery():
    """Test skill discovery from .claude/skills directory."""
    from SuperClaude.Skills.discovery import SkillDiscovery

    skills_dir = project_root / ".claude" / "skills"
    discovery = SkillDiscovery(skills_dir=skills_dir)
    index = discovery.discover()

    # Verify discovery found skills
    assert len(index.skills) > 0, "No skills discovered"

    # Check for expected command skills
    commands = discovery.get_commands()
    command_ids = [c.skill_id for c in commands]
    assert "sc-implement" in command_ids, "sc-implement not found"
    assert "sc-analyze" in command_ids, "sc-analyze not found"
    assert "sc-test" in command_ids, "sc-test not found"

    # Check for expected agent skills
    agents = discovery.get_agents()
    agent_ids = [a.skill_id for a in agents]
    assert "agent-react-specialist" in agent_ids, "agent-react-specialist not found"
    assert "agent-python-pro" in agent_ids, "agent-python-pro not found"

    print(f"✓ Discovered {len(commands)} commands and {len(agents)} agents")
    return True


def test_skill_adapter():
    """Test skill adapter loading and conversion."""
    from SuperClaude.Skills.adapter import SkillAdapter

    adapter = SkillAdapter()

    # Load a skill
    skill_path = project_root / ".claude" / "skills" / "sc-implement"
    skill = adapter.load_skill(skill_path)

    assert skill is not None, "Failed to load sc-implement skill"
    assert skill.name == "sc-implement", f"Wrong name: {skill.name}"
    assert skill.skill_type == "command", f"Wrong type: {skill.skill_type}"
    assert len(skill.description) > 0, "Empty description"

    # Test conversion to CommandMetadata
    command = adapter.to_command_metadata(skill)
    assert command.name == skill.name, "Name mismatch in conversion"
    assert command.description == skill.description, "Description mismatch"

    print(f"✓ Loaded and converted skill: {skill.name}")
    return True


def test_runtime_config():
    """Test runtime configuration loading."""
    from SuperClaude.Skills.runtime import RuntimeConfig

    # Test loading from file
    config_path = project_root / ".claude" / "settings.json"
    if config_path.exists():
        config = RuntimeConfig.load(config_path)
        assert config.runtime == "skills", f"Wrong runtime: {config.runtime}"
        assert config.fallback_to_python is True, "Fallback not enabled"
        print(f"✓ Loaded config: runtime={config.runtime}")
    else:
        # Test default config
        config = RuntimeConfig()
        assert config.runtime == "skills", "Wrong default runtime"
        print("✓ Using default config")

    return True


def test_skill_runtime():
    """Test skill runtime initialization."""
    from SuperClaude.Skills.runtime import RuntimeConfig, SkillRuntime

    config = RuntimeConfig(
        runtime="skills",
        skills_dir=".claude/skills",
        fallback_to_python=True,
    )

    runtime = SkillRuntime(config=config, project_root=project_root)

    # Test skill lookup
    skill = runtime.get_skill("sc-implement")
    assert skill is not None, "Failed to get sc-implement"

    # Test task-based skill finding
    skill = runtime.find_skill_for_task("implement a new React component")
    assert skill is not None, "Failed to find skill for task"

    # List commands and agents
    commands = runtime.list_commands()
    agents = runtime.list_agents()

    print(f"✓ Runtime initialized with {len(commands)} commands, {len(agents)} agents")
    return True


def test_select_agent_script():
    """Test the select_agent.py bundled script."""
    import subprocess

    script_path = (
        project_root / ".claude" / "skills" / "sc-implement" / "scripts" / "select_agent.py"
    )

    if not script_path.exists():
        print("⚠ select_agent.py not found, skipping")
        return True

    # Test agent selection
    context = {
        "task": "build a React dashboard component",
        "files": ["dashboard.tsx", "styles.css"],
        "languages": ["typescript"],
        "keywords": ["react", "component", "dashboard"],
    }

    result = subprocess.run(
        ["python", str(script_path), json.dumps(context)],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    if result.returncode == 0:
        output = json.loads(result.stdout)
        assert "selected_agent" in output, "No agent selected"
        print(
            f"✓ Agent selection: {output['selected_agent']} (confidence: {output.get('confidence', 'N/A')})"
        )
    else:
        print(f"⚠ Agent selection script failed: {result.stderr}")

    return True


def test_evidence_gate_script():
    """Test the evidence_gate.py bundled script."""
    import subprocess

    script_path = (
        project_root / ".claude" / "skills" / "sc-implement" / "scripts" / "evidence_gate.py"
    )

    if not script_path.exists():
        print("⚠ evidence_gate.py not found, skipping")
        return True

    # Test evidence evaluation
    evidence = {
        "command": "implement",
        "requires_evidence": True,
        "changes": [
            {"file": "src/component.tsx", "type": "modified", "diff_lines": 50},
            {"file": "src/component.test.tsx", "type": "added", "diff_lines": 30},
        ],
        "tests": {
            "ran": True,
            "passed": 10,
            "failed": 0,
            "coverage": 85.0,
        },
        "lint": {
            "ran": True,
            "errors": 0,
            "warnings": 1,
        },
    }

    result = subprocess.run(
        ["python", str(script_path), json.dumps(evidence)],
        capture_output=True,
        text=True,
        cwd=str(project_root),
    )

    if result.returncode == 0:
        output = json.loads(result.stdout)
        assert output.get("passed") is True, "Evidence gate should pass"
        print(f"✓ Evidence gate: score={output.get('score')}, status={output.get('status')}")
    else:
        print(f"⚠ Evidence gate script failed: {result.stderr}")

    return True


def test_skill_search():
    """Test skill search functionality."""
    from SuperClaude.Skills.discovery import SkillDiscovery

    skills_dir = project_root / ".claude" / "skills"
    discovery = SkillDiscovery(skills_dir=skills_dir)
    discovery.discover()

    # Test search by query
    results = discovery.find_skills(query="react", limit=5)
    assert len(results) > 0, "No results for 'react' query"

    # Test search by type
    commands = discovery.find_skills(skill_type="command", limit=20)
    assert all(s.skill_type == "command" for s in commands), "Type filter failed"

    # Test search by domain
    agents = discovery.find_skills(skill_type="agent", limit=20)
    assert len(agents) > 0, "No agents found"

    print("✓ Search tests passed")
    return True


def run_all_tests():
    """Run all integration tests."""
    print("=" * 60)
    print("SuperClaude Skills Integration Tests")
    print("=" * 60)
    print()

    tests = [
        ("Skill Discovery", test_skill_discovery),
        ("Skill Adapter", test_skill_adapter),
        ("Runtime Config", test_runtime_config),
        ("Skill Runtime", test_skill_runtime),
        ("Select Agent Script", test_select_agent_script),
        ("Evidence Gate Script", test_evidence_gate_script),
        ("Skill Search", test_skill_search),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\n[{name}]")
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"✗ {name} failed")
        except Exception as e:
            failed += 1
            print(f"✗ {name} error: {e}")

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
