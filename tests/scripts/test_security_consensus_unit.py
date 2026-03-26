"""Unit tests for scripts/security_consensus.py pure functions.

Complements the existing integration/test_security_consensus.py by testing
via direct import instead of subprocess.
"""

import json
from pathlib import Path

from scripts.security_consensus import (
    build_consensus_prompt,
    estimate_cost,
    format_finding_for_prompt,
    load_high_severity_findings,
)


class TestLoadHighSeverityFindings:
    """Tests for load_high_severity_findings."""

    def test_loads_valid_findings(self, tmp_path: Path):
        data = [{"test_id": "B101"}, {"test_id": "B102"}]
        p = tmp_path / "findings.json"
        p.write_text(json.dumps(data))

        result = load_high_severity_findings(p)
        assert len(result) == 2

    def test_empty_array(self, tmp_path: Path):
        p = tmp_path / "empty.json"
        p.write_text("[]")

        result = load_high_severity_findings(p)
        assert result == []


class TestFormatFindingForPrompt:
    """Tests for format_finding_for_prompt."""

    def test_all_fields_present(self):
        finding = {
            "test_id": "B501",
            "filename": "app/auth.py",
            "line_number": 15,
            "issue_severity": "HIGH",
            "issue_confidence": "MEDIUM",
            "issue_text": "Request with no cert verification",
            "code": "requests.get(url, verify=False)",
        }
        result = format_finding_for_prompt(finding)
        assert "B501" in result
        assert "app/auth.py" in result
        assert "15" in result
        assert "verify=False" in result

    def test_missing_optional_fields(self):
        result = format_finding_for_prompt({})
        assert "UNKNOWN" in result


class TestBuildConsensusPrompt:
    """Tests for build_consensus_prompt."""

    def test_single_finding(self):
        findings = [{"test_id": "B101", "filename": "t.py"}]
        prompt = build_consensus_prompt(findings)
        assert "1 total" in prompt
        assert "security expert" in prompt.lower()

    def test_caps_at_20(self):
        findings = [{"test_id": f"B{i:03d}"} for i in range(30)]
        prompt = build_consensus_prompt(findings)
        assert "20 total" in prompt


class TestEstimateCost:
    """Tests for estimate_cost."""

    def test_zero(self):
        assert estimate_cost(0, 0) == 0.0

    def test_million_tokens(self):
        # $15 in + $75 out = $90
        assert estimate_cost(1_000_000, 1_000_000) == 90.0

    def test_typical_run(self):
        # ~30K input, ~10K output
        cost = estimate_cost(30000, 10000)
        expected = round((30000 / 1e6) * 15 + (10000 / 1e6) * 75, 2)
        assert cost == expected


# --- Tests for run_consensus and main ---

from unittest.mock import MagicMock, patch  # noqa: E402


class TestRunConsensus:
    """Tests for run_consensus."""

    def _make_mock_anthropic(self, response_text, in_tok=100, out_tok=50):
        """Create a mock anthropic module with a client that returns the given text."""
        mock_block = MagicMock()
        mock_block.type = "text"
        mock_block.text = response_text

        mock_response = MagicMock()
        mock_response.content = [mock_block]
        mock_response.usage.input_tokens = in_tok
        mock_response.usage.output_tokens = out_tok

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        mock_mod = MagicMock()
        mock_mod.Anthropic.return_value = mock_client
        return mock_mod

    def test_run_consensus_parses_json_response(self):
        from scripts.security_consensus import run_consensus

        mock_anthropic = self._make_mock_anthropic(
            '```json\n{"findings_validated": [], "summary": {"total_reviewed": 0}}\n```',
            100,
            50,
        )

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = run_consensus([{"test_id": "B101"}], "fake-key")

        assert "findings_validated" in result
        assert result["_metadata"]["input_tokens"] == 100
        assert result["_metadata"]["output_tokens"] == 50

    def test_run_consensus_raw_json_no_codeblock(self):
        from scripts.security_consensus import run_consensus

        mock_anthropic = self._make_mock_anthropic(
            '{"findings_validated": [], "summary": {"total_reviewed": 0}}',
            200,
            100,
        )

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = run_consensus([{"test_id": "B101"}], "fake-key")

        assert result["_metadata"]["total_tokens"] == 300


class TestSecurityConsensusMain:
    """Tests for main()."""

    def test_main_no_findings(self, tmp_path: Path, monkeypatch):
        from scripts.security_consensus import main

        findings_file = tmp_path / "findings.json"
        findings_file.write_text("[]")
        output_file = tmp_path / "results.json"

        monkeypatch.setattr("sys.argv", ["prog", str(findings_file), str(output_file)])
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

        main()

        result = json.loads(output_file.read_text())
        assert result["summary"]["total_reviewed"] == 0
        assert result["overall_recommendation"] == "No high severity findings detected."

    def test_main_with_findings(self, tmp_path: Path, monkeypatch):
        from scripts.security_consensus import main

        findings_file = tmp_path / "findings.json"
        findings_file.write_text(json.dumps([{"test_id": "B101", "filename": "t.py"}]))
        output_file = tmp_path / "results.json"

        monkeypatch.setattr("sys.argv", ["prog", str(findings_file), str(output_file)])
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

        mock_result = {
            "findings_validated": [{"finding_id": "B101"}],
            "summary": {
                "total_reviewed": 1,
                "true_positives": 1,
                "false_positives": 0,
                "critical_count": 0,
                "high_count": 1,
                "medium_count": 0,
                "low_count": 0,
            },
            "overall_recommendation": "Fix it",
            "_metadata": {
                "model": "claude-opus-4-20250514",
                "input_tokens": 1000,
                "output_tokens": 500,
                "total_tokens": 1500,
            },
        }

        with patch("scripts.security_consensus.run_consensus", return_value=mock_result):
            main()

        result = json.loads(output_file.read_text())
        assert result["summary"]["true_positives"] == 1
