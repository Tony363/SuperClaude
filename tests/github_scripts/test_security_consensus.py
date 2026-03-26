"""Tests for .github/scripts/security-consensus.py pure functions."""

import importlib
import json
import sys
from pathlib import Path

scripts_dir = str(Path(__file__).parent.parent.parent / ".github" / "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

mod = importlib.import_module("security-consensus")

load_high_severity_findings = mod.load_high_severity_findings
format_finding_for_prompt = mod.format_finding_for_prompt
build_consensus_prompt = mod.build_consensus_prompt
estimate_cost = mod.estimate_cost


class TestLoadHighSeverityFindings:
    """Tests for load_high_severity_findings."""

    def test_loads_valid_json(self, tmp_path: Path):
        findings = [{"test_id": "B101", "filename": "test.py"}]
        p = tmp_path / "findings.json"
        p.write_text(json.dumps(findings))

        result = load_high_severity_findings(p)
        assert len(result) == 1
        assert result[0]["test_id"] == "B101"

    def test_missing_file_exits(self, tmp_path: Path):
        import pytest

        with pytest.raises(SystemExit):
            load_high_severity_findings(tmp_path / "nope.json")

    def test_invalid_json_exits(self, tmp_path: Path):
        import pytest

        p = tmp_path / "bad.json"
        p.write_text("not json")
        with pytest.raises(SystemExit):
            load_high_severity_findings(p)


class TestFormatFindingForPrompt:
    """Tests for format_finding_for_prompt."""

    def test_formats_all_fields(self):
        finding = {
            "test_id": "B101",
            "filename": "auth.py",
            "line_number": 42,
            "issue_severity": "HIGH",
            "issue_confidence": "HIGH",
            "issue_text": "Use of exec detected",
            "code": "exec(user_input)",
        }
        result = format_finding_for_prompt(finding)

        assert "B101" in result
        assert "auth.py" in result
        assert "42" in result
        assert "HIGH" in result
        assert "exec(user_input)" in result

    def test_handles_missing_fields(self):
        finding = {}
        result = format_finding_for_prompt(finding)
        assert "UNKNOWN" in result
        assert "N/A" in result


class TestBuildConsensusPrompt:
    """Tests for build_consensus_prompt."""

    def test_includes_all_findings(self):
        findings = [{"test_id": f"B{i}", "filename": f"f{i}.py"} for i in range(5)]
        prompt = build_consensus_prompt(findings)
        assert "5 total" in prompt
        assert "B0" in prompt
        assert "B4" in prompt

    def test_limits_to_20(self):
        findings = [{"test_id": f"B{i}", "filename": f"f{i}.py"} for i in range(25)]
        prompt = build_consensus_prompt(findings)
        assert "20 total" in prompt
        assert "f24.py" not in prompt

    def test_includes_json_format(self):
        prompt = build_consensus_prompt([{"test_id": "B1"}])
        assert "findings_validated" in prompt
        assert "risk_level" in prompt


class TestEstimateCost:
    """Tests for estimate_cost."""

    def test_zero_tokens(self):
        assert estimate_cost(0, 0) == 0.0

    def test_opus_pricing(self):
        # Opus: $15/MTok in, $75/MTok out
        cost = estimate_cost(1_000_000, 1_000_000)
        assert cost == 90.0

    def test_small_usage(self):
        cost = estimate_cost(10000, 5000)
        expected = round((10000 / 1_000_000) * 15 + (5000 / 1_000_000) * 75, 2)
        assert cost == expected


# ---------------------------------------------------------------------------
# Tests for run_consensus (lines 137-191)
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, patch  # noqa: E402

run_consensus = mod.run_consensus


class TestRunConsensus:
    """Tests for run_consensus."""

    def _make_mock_response(self, text_content: str, input_tokens=100, output_tokens=200):
        """Helper to build a mock Anthropic response."""
        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = text_content

        response = MagicMock()
        response.content = [text_block]
        response.usage.input_tokens = input_tokens
        response.usage.output_tokens = output_tokens
        return response

    def test_extracts_json_from_code_fence(self):
        result_json = json.dumps(
            {
                "findings_validated": [],
                "summary": {"total_reviewed": 0},
                "overall_recommendation": "All clear.",
            }
        )
        response_text = f"Here is the analysis:\n```json\n{result_json}\n```\nDone."
        mock_response = self._make_mock_response(response_text, 500, 1000)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            result = run_consensus([{"test_id": "B101"}], "fake-key")

        assert result["findings_validated"] == []
        assert result["overall_recommendation"] == "All clear."
        assert result["_metadata"]["model"] == "claude-opus-4-20250514"
        assert result["_metadata"]["input_tokens"] == 500
        assert result["_metadata"]["output_tokens"] == 1000
        assert result["_metadata"]["total_tokens"] == 1500

    def test_extracts_json_without_code_fence(self):
        result_json = json.dumps(
            {
                "findings_validated": [{"finding_id": "B102"}],
                "summary": {"total_reviewed": 1},
                "overall_recommendation": "Fix it.",
            }
        )
        response_text = f"Analysis: {result_json}"
        mock_response = self._make_mock_response(response_text, 300, 600)

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            result = run_consensus([{"test_id": "B102"}], "fake-key")

        assert len(result["findings_validated"]) == 1
        assert result["findings_validated"][0]["finding_id"] == "B102"

    def test_skips_thinking_blocks(self):
        """Only text blocks contribute to response_text."""
        thinking_block = MagicMock()
        thinking_block.type = "thinking"
        thinking_block.text = "Let me think about this..."

        text_block = MagicMock()
        text_block.type = "text"
        text_block.text = json.dumps(
            {
                "findings_validated": [],
                "summary": {},
                "overall_recommendation": "None.",
            }
        )

        response = MagicMock()
        response.content = [thinking_block, text_block]
        response.usage.input_tokens = 100
        response.usage.output_tokens = 200

        mock_client = MagicMock()
        mock_client.messages.create.return_value = response

        with patch("anthropic.Anthropic", return_value=mock_client):
            result = run_consensus([{"test_id": "B103"}], "fake-key")

        # Should succeed; thinking block content not included
        assert result["overall_recommendation"] == "None."

    def test_api_error_exits(self):
        import anthropic as anthropic_mod
        import pytest

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = anthropic_mod.APIError("rate limited")

        with patch("anthropic.Anthropic", return_value=mock_client):
            with pytest.raises(SystemExit):
                run_consensus([{"test_id": "B104"}], "fake-key")

    def test_invalid_json_in_response_exits(self):
        import pytest

        mock_response = self._make_mock_response("This is not JSON at all")

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response

        with patch("anthropic.Anthropic", return_value=mock_client):
            with pytest.raises(SystemExit):
                run_consensus([{"test_id": "B105"}], "fake-key")

    def test_unexpected_exception_exits(self):
        import pytest

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = RuntimeError("unexpected")

        with patch("anthropic.Anthropic", return_value=mock_client):
            with pytest.raises(SystemExit):
                run_consensus([{"test_id": "B106"}], "fake-key")


# ---------------------------------------------------------------------------
# Tests for main (lines 201-273)
# ---------------------------------------------------------------------------

main_fn = mod.main


class TestSecurityConsensusMain:
    """Tests for the main() entry point."""

    def test_missing_api_key_exits(self, monkeypatch):
        import pytest

        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.setattr("sys.argv", ["security-consensus.py"])

        with pytest.raises(SystemExit) as exc_info:
            main_fn()
        assert exc_info.value.code == 1

    def test_empty_findings_skips_consensus(self, monkeypatch, tmp_path):

        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

        findings_file = tmp_path / "findings.json"
        findings_file.write_text("[]")
        output_file = tmp_path / "results.json"

        monkeypatch.setattr(
            "sys.argv",
            [
                "security-consensus.py",
                str(findings_file),
                str(output_file),
            ],
        )

        # main() does not call sys.exit on success path, so it should return normally
        main_fn()

        result = json.loads(output_file.read_text())
        assert result["findings_validated"] == []
        assert result["summary"]["total_reviewed"] == 0
        assert result["_metadata"]["model"] == "N/A"

    def test_runs_consensus_and_writes_output(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

        findings_file = tmp_path / "findings.json"
        findings_file.write_text(
            json.dumps(
                [
                    {"test_id": "B101", "filename": "app.py"},
                ]
            )
        )
        output_file = tmp_path / "results.json"

        monkeypatch.setattr(
            "sys.argv",
            [
                "security-consensus.py",
                str(findings_file),
                str(output_file),
            ],
        )

        mock_result = {
            "findings_validated": [{"finding_id": "B101", "is_true_positive": True}],
            "summary": {
                "total_reviewed": 1,
                "true_positives": 1,
                "false_positives": 0,
                "critical_count": 0,
                "high_count": 1,
                "medium_count": 0,
                "low_count": 0,
            },
            "overall_recommendation": "Fix high-risk issue.",
            "_metadata": {
                "model": "claude-opus-4-20250514",
                "input_tokens": 5000,
                "output_tokens": 2000,
                "total_tokens": 7000,
            },
        }

        with patch.object(mod, "run_consensus", return_value=mock_result):
            main_fn()

        result = json.loads(output_file.read_text())
        assert result["summary"]["true_positives"] == 1
        assert result["_metadata"]["total_tokens"] == 7000

    def test_warns_on_critical_findings(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

        findings_file = tmp_path / "findings.json"
        findings_file.write_text(
            json.dumps(
                [
                    {"test_id": "B102", "filename": "vuln.py"},
                ]
            )
        )
        output_file = tmp_path / "results.json"

        monkeypatch.setattr(
            "sys.argv",
            [
                "security-consensus.py",
                str(findings_file),
                str(output_file),
            ],
        )

        mock_result = {
            "findings_validated": [],
            "summary": {
                "total_reviewed": 1,
                "true_positives": 1,
                "false_positives": 0,
                "critical_count": 1,
                "high_count": 0,
                "medium_count": 0,
                "low_count": 0,
            },
            "overall_recommendation": "Critical vuln found.",
            "_metadata": {
                "model": "claude-opus-4-20250514",
                "input_tokens": 3000,
                "output_tokens": 1000,
                "total_tokens": 4000,
            },
        }

        with patch.object(mod, "run_consensus", return_value=mock_result):
            main_fn()

        captured = capsys.readouterr()
        assert "::warning::" in captured.out
        assert "Critical or high-risk" in captured.out

    def test_default_argv_paths(self, monkeypatch, tmp_path):
        """When no argv given, defaults to /tmp paths."""
        import pytest

        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
        monkeypatch.setattr("sys.argv", ["security-consensus.py"])

        # The default findings path (/tmp/high-severity.json) won't exist,
        # so load_high_severity_findings calls sys.exit(1)
        with pytest.raises(SystemExit) as exc_info:
            main_fn()
        assert exc_info.value.code == 1

    def test_cost_output_printed(self, monkeypatch, tmp_path, capsys):
        """When metadata contains tokens, cost and token summary are printed."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")

        findings_file = tmp_path / "findings.json"
        findings_file.write_text(
            json.dumps(
                [
                    {"test_id": "B110", "filename": "x.py"},
                ]
            )
        )
        output_file = tmp_path / "results.json"

        monkeypatch.setattr(
            "sys.argv",
            [
                "security-consensus.py",
                str(findings_file),
                str(output_file),
            ],
        )

        mock_result = {
            "findings_validated": [],
            "summary": {
                "total_reviewed": 1,
                "true_positives": 0,
                "false_positives": 1,
                "critical_count": 0,
                "high_count": 0,
                "medium_count": 0,
                "low_count": 0,
            },
            "overall_recommendation": "All false positives.",
            "_metadata": {
                "model": "claude-opus-4-20250514",
                "input_tokens": 10000,
                "output_tokens": 5000,
                "total_tokens": 15000,
            },
        }

        with patch.object(mod, "run_consensus", return_value=mock_result):
            main_fn()

        captured = capsys.readouterr()
        assert "**Cost**:" in captured.out
        assert "**Tokens**:" in captured.out
        assert "::set-output name=consensus_cost::" in captured.out
