"""
Integration tests for scripts/security_consensus.py

Tests JSON loading, prompt building, cost estimation,
and max 20 findings limit. Uses subprocess-based testing.

Run with: pytest tests/integration/test_security_consensus.py -v
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

PYTHON = sys.executable


class TestLoadHighSeverityFindings:
    """Tests for finding file loading."""

    def test_load_valid_findings(self):
        """Valid JSON findings file loads correctly."""
        findings = [
            {
                "test_id": "B101",
                "filename": "scripts/auth.py",
                "line_number": 10,
                "issue_severity": "HIGH",
                "issue_confidence": "HIGH",
                "issue_text": "Use of exec detected",
                "code": "exec(user_input)",
            }
        ]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(findings, f)
            f.flush()
            result = subprocess.run(
                [
                    PYTHON,
                    "-c",
                    f"""
import sys; sys.path.insert(0, '.')
from pathlib import Path
from scripts.security_consensus import load_high_severity_findings
findings = load_high_severity_findings(Path("{f.name}"))
assert len(findings) == 1
assert findings[0]["test_id"] == "B101"
print("PASS")
""",
                ],
                capture_output=True,
                text=True,
            )
        Path(f.name).unlink()
        assert result.returncode == 0
        assert "PASS" in result.stdout

    def test_load_missing_file_crashes(self):
        """Missing findings file crashes (Let It Crash)."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from pathlib import Path
from scripts.security_consensus import load_high_severity_findings
load_high_severity_findings(Path("/tmp/nonexistent-findings-99999.json"))
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0
        assert "FileNotFoundError" in result.stderr

    def test_load_invalid_json_crashes(self):
        """Invalid JSON file crashes (Let It Crash)."""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("not valid json {{{")
            f.flush()
            result = subprocess.run(
                [
                    PYTHON,
                    "-c",
                    f"""
import sys; sys.path.insert(0, '.')
from pathlib import Path
from scripts.security_consensus import load_high_severity_findings
load_high_severity_findings(Path("{f.name}"))
""",
                ],
                capture_output=True,
                text=True,
            )
        Path(f.name).unlink()
        assert result.returncode != 0
        assert "JSONDecodeError" in result.stderr


class TestBuildConsensusPrompt:
    """Tests for prompt construction."""

    def test_prompt_contains_findings(self):
        """Prompt includes finding details."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.security_consensus import build_consensus_prompt
findings = [
    {
        "test_id": "B101",
        "filename": "scripts/auth.py",
        "line_number": 10,
        "issue_severity": "HIGH",
        "issue_confidence": "HIGH",
        "issue_text": "Use of exec detected",
        "code": "exec(user_input)",
    }
]
prompt = build_consensus_prompt(findings)
assert "B101" in prompt
assert "scripts/auth.py" in prompt
assert "exec(user_input)" in prompt
assert "1 total" in prompt
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout

    def test_prompt_limits_to_20_findings(self):
        """Prompt caps at 20 findings even if more provided."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.security_consensus import build_consensus_prompt
findings = [
    {
        "test_id": f"B{i:03d}",
        "filename": f"file_{i}.py",
        "line_number": i,
        "issue_severity": "HIGH",
        "issue_confidence": "HIGH",
        "issue_text": f"Issue {i}",
        "code": f"code_{i}()",
    }
    for i in range(25)
]
prompt = build_consensus_prompt(findings)
assert "20 total" in prompt
# Should not contain finding #21 (0-indexed: B020 through B024)
assert "file_24.py" not in prompt
# Should contain finding #19 (0-indexed: B019)
assert "file_19.py" in prompt
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout


class TestEstimateCost:
    """Tests for cost estimation."""

    def test_cost_calculation(self):
        """Cost calculation follows Opus 4.6 pricing."""
        result = subprocess.run(
            [
                PYTHON,
                "-c",
                """
import sys; sys.path.insert(0, '.')
from scripts.security_consensus import estimate_cost
# 1M input tokens = $15, 1M output tokens = $75
cost = estimate_cost(1_000_000, 1_000_000)
assert cost == 90.0, f"Expected 90.0, got {cost}"
# Small usage
cost = estimate_cost(10000, 5000)
expected = round((10000 / 1_000_000) * 15 + (5000 / 1_000_000) * 75, 2)
assert cost == expected, f"Expected {expected}, got {cost}"
print("PASS")
""",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "PASS" in result.stdout


class TestMainMissingApiKey:
    """Tests for missing API key."""

    def test_missing_api_key_crashes(self):
        """Missing ANTHROPIC_API_KEY crashes (Let It Crash)."""
        import os

        env = os.environ.copy()
        env.pop("ANTHROPIC_API_KEY", None)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump([{"test_id": "B101"}], f)
            f.flush()
            result = subprocess.run(
                [PYTHON, "scripts/security_consensus.py", f.name],
                capture_output=True,
                text=True,
                env=env,
            )
        Path(f.name).unlink()
        assert result.returncode != 0
        assert "KeyError" in result.stderr
