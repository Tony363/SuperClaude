"""Tests for scripts/run_stochastic_local.py pure functions."""

from pathlib import Path

from scripts.run_stochastic_local import (
    find_agent_file,
    find_recent_files,
    load_test_config,
    validate_response,
)


class TestLoadTestConfig:
    """Tests for load_test_config."""

    def test_loads_yaml(self, tmp_path: Path):
        config = tmp_path / "tests.yaml"
        config.write_text("agents:\n  python-expert:\n    prompt: 'test'\n")

        result = load_test_config(config)
        assert "agents" in result
        assert "python-expert" in result["agents"]


class TestFindAgentFile:
    """Tests for find_agent_file."""

    def test_finds_in_core(self, tmp_path: Path):
        core = tmp_path / "agents" / "core"
        core.mkdir(parents=True)
        (core / "architect.md").write_text("# Architect")

        result = find_agent_file("architect", tmp_path)
        assert result is not None
        assert result.name == "architect.md"

    def test_finds_in_extensions(self, tmp_path: Path):
        ext = tmp_path / "agents" / "extensions"
        ext.mkdir(parents=True)
        (ext / "python-expert.md").write_text("# Python")

        result = find_agent_file("python-expert", tmp_path)
        assert result is not None

    def test_returns_none_if_not_found(self, tmp_path: Path):
        (tmp_path / "agents" / "core").mkdir(parents=True)
        (tmp_path / "agents" / "extensions").mkdir(parents=True)

        result = find_agent_file("nonexistent", tmp_path)
        assert result is None


class TestFindRecentFiles:
    """Tests for find_recent_files."""

    def test_finds_recent_py(self, tmp_path: Path):
        f = tmp_path / "new.py"
        f.write_text("x = 1")

        results = find_recent_files(tmp_path, [".py"], minutes=5)
        assert len(results) >= 1
        assert any(r.name == "new.py" for r in results)

    def test_skips_node_modules(self, tmp_path: Path):
        nm = tmp_path / "node_modules"
        nm.mkdir()
        (nm / "pkg.py").write_text("x = 1")

        results = find_recent_files(tmp_path, [".py"], minutes=5)
        assert all("node_modules" not in str(r) for r in results)

    def test_empty_dir(self, tmp_path: Path):
        results = find_recent_files(tmp_path, [".py"], minutes=5)
        assert results == []


class TestValidateResponse:
    """Tests for validate_response."""

    def test_passes_with_keywords_and_length(self):
        response = "This is a python implementation using pytest framework with async support."
        passed, reason = validate_response(response, ["python", "pytest"])
        assert passed is True
        assert "Matched keywords" in reason

    def test_fails_short_response(self):
        passed, reason = validate_response("short", ["python"])
        assert passed is False
        assert "too short" in reason

    def test_fails_no_keywords(self):
        response = "x" * 100
        passed, reason = validate_response(response, ["python", "react"])
        assert passed is False
        assert "No keywords" in reason

    def test_custom_min_length(self):
        passed, _ = validate_response("hi keyword", ["keyword"], min_length=5)
        assert passed is True

    def test_case_insensitive(self):
        response = "This PYTHON implementation is great and well tested."
        passed, _ = validate_response(response, ["python"])
        assert passed is True

    def test_fallback_file_check(self, tmp_path: Path):
        """Test the fallback path when response mentions 'max turns'."""
        # Create a recent file with a keyword
        py_file = tmp_path / "test_output.py"
        py_file.write_text("# Implementation using python with pytest")

        response = "Reached max turns limit"
        passed, reason = validate_response(
            response, ["python", "pytest"], min_length=50, base_dir=tmp_path
        )
        assert passed is True
        assert "found work in files" in reason


# --- Tests for run_claude_evaluation, run_single_test, and main ---

from unittest.mock import MagicMock, patch  # noqa: E402


class TestRunClaudeEvaluation:
    """Tests for run_claude_evaluation."""

    def test_successful_run(self, tmp_path: Path):
        from scripts.run_stochastic_local import run_claude_evaluation

        mock_result = MagicMock()
        mock_result.stdout = "Agent response with detailed output"
        mock_result.stderr = ""
        mock_result.returncode = 0

        agent_file = tmp_path / "agents" / "core" / "architect.md"
        agent_file.parent.mkdir(parents=True)
        agent_file.write_text("# Architect")

        with patch("scripts.run_stochastic_local.subprocess.run", return_value=mock_result):
            response, success = run_claude_evaluation(
                "architect", agent_file, "test prompt", timeout=30
            )

        assert success is True
        assert "Agent response" in response

    def test_timeout(self, tmp_path: Path):
        import subprocess

        from scripts.run_stochastic_local import run_claude_evaluation

        agent_file = tmp_path / "agent.md"
        agent_file.write_text("# Agent")

        with patch(
            "scripts.run_stochastic_local.subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="claude", timeout=30),
        ):
            response, success = run_claude_evaluation("test", agent_file, "prompt", timeout=30)

        assert success is False
        assert "TIMEOUT" in response

    def test_cli_not_found(self, tmp_path: Path):
        from scripts.run_stochastic_local import run_claude_evaluation

        agent_file = tmp_path / "agent.md"
        agent_file.write_text("# Agent")

        with patch(
            "scripts.run_stochastic_local.subprocess.run",
            side_effect=FileNotFoundError(),
        ):
            response, success = run_claude_evaluation("test", agent_file, "prompt")

        assert success is False
        assert "Claude CLI not found" in response

    def test_empty_stdout_with_stderr(self, tmp_path: Path):
        from scripts.run_stochastic_local import run_claude_evaluation

        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = "Some error output"
        mock_result.returncode = 1

        agent_file = tmp_path / "agent.md"
        agent_file.write_text("# Agent")

        with patch("scripts.run_stochastic_local.subprocess.run", return_value=mock_result):
            response, success = run_claude_evaluation("test", agent_file, "prompt")

        assert success is False

    def test_empty_stdout_no_stderr(self, tmp_path: Path):
        from scripts.run_stochastic_local import run_claude_evaluation

        mock_result = MagicMock()
        mock_result.stdout = ""
        mock_result.stderr = ""
        mock_result.returncode = 0

        agent_file = tmp_path / "agent.md"
        agent_file.write_text("# Agent")

        with patch("scripts.run_stochastic_local.subprocess.run", return_value=mock_result):
            response, success = run_claude_evaluation("test", agent_file, "prompt")

        assert success is False
        assert "No response" in response


class TestRunSingleTest:
    """Tests for run_single_test."""

    def test_agent_not_found(self, tmp_path: Path):
        from scripts.run_stochastic_local import run_single_test

        base = tmp_path / "project"
        (base / "agents" / "core").mkdir(parents=True)
        (base / "agents" / "extensions").mkdir(parents=True)
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = run_single_test(
            "nonexistent",
            {"prompt": "test", "keywords": ["python"]},
            1,
            base,
            output_dir,
        )

        assert result["passed"] is False
        assert "not found" in result["reason"]

    def test_dry_run(self, tmp_path: Path):
        from scripts.run_stochastic_local import run_single_test

        base = tmp_path / "project"
        core = base / "agents" / "core"
        core.mkdir(parents=True)
        (base / "agents" / "extensions").mkdir(parents=True)
        (core / "architect.md").write_text("# Architect")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        result = run_single_test(
            "architect",
            {"prompt": "test", "keywords": ["python"], "type": "standard", "threshold": 0.8},
            1,
            base,
            output_dir,
            dry_run=True,
        )

        assert result["passed"] is True
        assert result["reason"] == "DRY RUN"

    def test_real_run_success(self, tmp_path: Path):
        from scripts.run_stochastic_local import run_single_test

        base = tmp_path / "project"
        core = base / "agents" / "core"
        core.mkdir(parents=True)
        (base / "agents" / "extensions").mkdir(parents=True)
        (core / "architect.md").write_text("# Architect")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch(
            "scripts.run_stochastic_local.run_claude_evaluation",
            return_value=("Detailed python implementation with comprehensive testing", True),
        ):
            result = run_single_test(
                "architect",
                {"prompt": "test", "keywords": ["python"], "type": "standard", "threshold": 0.8},
                1,
                base,
                output_dir,
            )

        assert result["passed"] is True

    def test_real_run_execution_failure(self, tmp_path: Path):
        from scripts.run_stochastic_local import run_single_test

        base = tmp_path / "project"
        core = base / "agents" / "core"
        core.mkdir(parents=True)
        (base / "agents" / "extensions").mkdir(parents=True)
        (core / "architect.md").write_text("# Architect")
        output_dir = tmp_path / "output"
        output_dir.mkdir()

        with patch(
            "scripts.run_stochastic_local.run_claude_evaluation",
            return_value=("TIMEOUT", False),
        ):
            result = run_single_test(
                "architect",
                {"prompt": "test", "keywords": ["python"]},
                1,
                base,
                output_dir,
            )

        assert result["passed"] is False


class TestStochasticMain:
    """Tests for main()."""

    def test_main_missing_config(self, monkeypatch, tmp_path: Path):
        """main() returns 1 when config file doesn't exist."""
        import scripts.run_stochastic_local as mod

        monkeypatch.setattr(
            "sys.argv",
            ["prog", "--config", "nonexistent.yaml"],
        )

        # Override __file__ location so base_dir resolves to tmp_path
        original_file = mod.__file__
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        monkeypatch.setattr(mod, "__file__", str(scripts_dir / "run_stochastic_local.py"))

        result = mod.main()
        monkeypatch.setattr(mod, "__file__", original_file)
        assert result == 1

    def test_main_dry_run(self, monkeypatch, tmp_path: Path):
        """main() succeeds in dry-run mode."""
        import scripts.run_stochastic_local as mod

        # Setup: config file, agent files
        config_file = tmp_path / "evals" / "tests.yaml"
        config_file.parent.mkdir(parents=True)
        config_file.write_text(
            "agents:\n  architect:\n    prompt: test\n    keywords:\n      - python\n"
        )

        core = tmp_path / "agents" / "core"
        core.mkdir(parents=True)
        (tmp_path / "agents" / "extensions").mkdir(parents=True)
        (core / "architect.md").write_text("# Architect")

        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()
        original_file = mod.__file__
        monkeypatch.setattr(mod, "__file__", str(scripts_dir / "run_stochastic_local.py"))

        monkeypatch.setattr(
            "sys.argv",
            ["prog", "--dry-run", "--runs", "1"],
        )

        result = mod.main()
        monkeypatch.setattr(mod, "__file__", original_file)
        assert result == 0
