"""Tests for .github/scripts/generate-docstrings.py pure functions."""

import importlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

scripts_dir = str(Path(__file__).parent.parent.parent / ".github" / "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

mod = importlib.import_module("generate-docstrings")

is_protected = mod.is_protected
load_missing_docs = mod.load_missing_docs
read_file_source = mod.read_file_source
group_by_file = mod.group_by_file
build_prompt = mod.build_prompt
estimate_cost = mod.estimate_cost
generate_docs_for_file = mod.generate_docs_for_file
main = mod.main


class TestIsProtected:
    """Tests for is_protected."""

    def test_workflow_protected(self):
        assert is_protected(".github/workflows/ci.yml") is True

    def test_benchmarks_protected(self):
        assert is_protected("benchmarks/test.py") is True

    def test_regular_file_ok(self):
        assert is_protected("src/service.py") is False

    def test_skills_protected(self):
        assert is_protected(".claude/skills/test/SKILL.md") is True


class TestLoadMissingDocs:
    """Tests for load_missing_docs."""

    def test_loads_valid_json(self, tmp_path: Path):
        import json

        data = [{"file": "test.py", "function": "foo", "line": 1}]
        p = tmp_path / "docs.json"
        p.write_text(json.dumps(data))

        result = load_missing_docs(p)
        assert len(result) == 1

    def test_missing_file_exits(self, tmp_path: Path):
        import pytest

        with pytest.raises(SystemExit):
            load_missing_docs(tmp_path / "nope.json")


class TestGroupByFile:
    """Tests for group_by_file."""

    def test_groups_correctly(self):
        functions = [
            {"file": "a.py", "function": "f1"},
            {"file": "b.py", "function": "f2"},
            {"file": "a.py", "function": "f3"},
        ]
        result = group_by_file(functions)
        assert len(result["a.py"]) == 2
        assert len(result["b.py"]) == 1

    def test_filters_protected(self):
        functions = [{"file": "CLAUDE.md", "function": "f1"}]
        result = group_by_file(functions)
        assert result == {}


class TestBuildPrompt:
    """Tests for build_prompt."""

    def test_includes_google_style_instructions(self):
        prompt = build_prompt("test.py", "def foo(): pass", [{"function": "foo", "line": 1}])
        assert "Google-style" in prompt
        assert "test.py" in prompt
        assert "`foo`" in prompt

    def test_includes_json_format(self):
        prompt = build_prompt("t.py", "code", [{"function": "f", "line": 1}])
        assert "functions_documented" in prompt


class TestEstimateCost:
    """Tests for estimate_cost."""

    def test_zero(self):
        assert estimate_cost(0, 0) == 0.0

    def test_known_pricing(self):
        # Same Haiku pricing as type hints
        cost = estimate_cost(1_000_000, 1_000_000)
        assert cost == 4.8


def _make_mock_response(text: str, input_tokens: int = 100, output_tokens: int = 200):
    """Build a mock anthropic response object."""
    block = MagicMock()
    block.type = "text"
    block.text = text

    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens

    response = MagicMock()
    response.content = [block]
    response.usage = usage
    return response


class TestGenerateDocsForFile:
    """Tests for generate_docs_for_file."""

    def test_parses_json_from_code_fence(self):
        payload = json.dumps(
            {
                "functions_documented": [
                    {"file": "a.py", "function": "foo", "docstring": "Do something."}
                ]
            }
        )
        response_text = f"Here are the results:\n```json\n{payload}\n```"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(response_text, 50, 80)

        documented, in_tok, out_tok = generate_docs_for_file(
            mock_client, "a.py", "def foo(): pass", [{"function": "foo", "line": 1}]
        )

        assert len(documented) == 1
        assert documented[0]["function"] == "foo"
        assert documented[0]["docstring"] == "Do something."
        assert in_tok == 50
        assert out_tok == 80

    def test_parses_json_without_code_fence(self):
        payload = json.dumps(
            {"functions_documented": [{"file": "b.py", "function": "bar", "docstring": "Bar it."}]}
        )
        response_text = f"Sure, here you go: {payload}"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(response_text)

        documented, _, _ = generate_docs_for_file(
            mock_client, "b.py", "def bar(): pass", [{"function": "bar", "line": 1}]
        )

        assert len(documented) == 1
        assert documented[0]["function"] == "bar"

    def test_returns_empty_on_no_json(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response("No JSON here at all.")

        documented, _, _ = generate_docs_for_file(
            mock_client, "c.py", "def baz(): pass", [{"function": "baz", "line": 1}]
        )

        assert documented == []

    def test_returns_empty_on_missing_key(self):
        payload = json.dumps({"other_key": []})
        response_text = f"```json\n{payload}\n```"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(response_text)

        documented, _, _ = generate_docs_for_file(
            mock_client, "d.py", "def qux(): pass", [{"function": "qux", "line": 1}]
        )

        assert documented == []

    def test_multiple_text_blocks_concatenated(self):
        payload = json.dumps(
            {"functions_documented": [{"file": "e.py", "function": "multi", "docstring": "Multi."}]}
        )
        block1 = MagicMock()
        block1.type = "text"
        block1.text = f"```json\n{payload}"

        block2 = MagicMock()
        block2.type = "text"
        block2.text = "\n```"

        usage = MagicMock()
        usage.input_tokens = 10
        usage.output_tokens = 20

        response = MagicMock()
        response.content = [block1, block2]
        response.usage = usage

        mock_client = MagicMock()
        mock_client.messages.create.return_value = response

        documented, in_tok, out_tok = generate_docs_for_file(
            mock_client, "e.py", "def multi(): pass", [{"function": "multi", "line": 1}]
        )

        assert len(documented) == 1
        assert in_tok == 10
        assert out_tok == 20


class TestMain:
    """Tests for main() CLI entrypoint."""

    def test_exits_without_api_key(self, monkeypatch, tmp_path):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        input_file = tmp_path / "input.json"
        input_file.write_text("[]")
        monkeypatch.setattr(sys, "argv", ["prog", str(input_file)])

        with pytest.raises(SystemExit):
            main()

    def test_empty_functions_writes_empty_output(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        input_file = tmp_path / "input.json"
        input_file.write_text("[]")
        output_file = tmp_path / "output.json"
        monkeypatch.setattr(sys, "argv", ["prog", str(input_file), str(output_file)])

        main()

        result = json.loads(output_file.read_text())
        assert result["functions_documented"] == []
        assert result["_metadata"]["model"] == "N/A"
        assert result["_metadata"]["total_tokens"] == 0

    def test_processes_functions_and_writes_output(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        # Create a source file that read_file_source can find
        src_file = tmp_path / "mymod.py"
        src_file.write_text("def greet(name):\n    return f'Hello {name}'\n")

        input_data = [{"file": str(src_file), "function": "greet", "line": 1}]
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(input_data))
        output_file = tmp_path / "output.json"
        monkeypatch.setattr(sys, "argv", ["prog", str(input_file), str(output_file)])

        api_response_payload = json.dumps(
            {
                "functions_documented": [
                    {
                        "file": str(src_file),
                        "function": "greet",
                        "docstring": "Greet a person by name.",
                    }
                ]
            }
        )
        mock_response = _make_mock_response(
            f"```json\n{api_response_payload}\n```", input_tokens=150, output_tokens=300
        )
        mock_client_instance = MagicMock()
        mock_client_instance.messages.create.return_value = mock_response

        with patch.object(mod, "anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value = mock_client_instance
            mock_anthropic.APIError = type("APIError", (Exception,), {})
            main()

        result = json.loads(output_file.read_text())
        assert len(result["functions_documented"]) == 1
        assert result["functions_documented"][0]["function"] == "greet"
        assert result["_metadata"]["input_tokens"] == 150
        assert result["_metadata"]["output_tokens"] == 300
        assert result["_metadata"]["total_tokens"] == 450

    def test_skips_unreadable_files(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        input_data = [{"file": "/nonexistent/fake.py", "function": "nope", "line": 1}]
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(input_data))
        output_file = tmp_path / "output.json"
        monkeypatch.setattr(sys, "argv", ["prog", str(input_file), str(output_file)])

        mock_client_instance = MagicMock()

        with patch.object(mod, "anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value = mock_client_instance
            mock_anthropic.APIError = type("APIError", (Exception,), {})
            main()

        result = json.loads(output_file.read_text())
        assert result["functions_documented"] == []
        # Client should never have been called since the file was unreadable
        mock_client_instance.messages.create.assert_not_called()

    def test_handles_api_error_gracefully(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        src_file = tmp_path / "fail.py"
        src_file.write_text("def fail(): pass\n")

        input_data = [{"file": str(src_file), "function": "fail", "line": 1}]
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(input_data))
        output_file = tmp_path / "output.json"
        monkeypatch.setattr(sys, "argv", ["prog", str(input_file), str(output_file)])

        MockAPIError = type("APIError", (Exception,), {})

        mock_client_instance = MagicMock()
        mock_client_instance.messages.create.side_effect = MockAPIError("rate limited")

        with patch.object(mod, "anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value = mock_client_instance
            mock_anthropic.APIError = MockAPIError
            main()

        result = json.loads(output_file.read_text())
        assert result["functions_documented"] == []

    def test_handles_json_decode_error_from_api(self, monkeypatch, tmp_path):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        src_file = tmp_path / "badjson.py"
        src_file.write_text("def badjson(): pass\n")

        input_data = [{"file": str(src_file), "function": "badjson", "line": 1}]
        input_file = tmp_path / "input.json"
        input_file.write_text(json.dumps(input_data))
        output_file = tmp_path / "output.json"
        monkeypatch.setattr(sys, "argv", ["prog", str(input_file), str(output_file)])

        # Return response with invalid JSON that will trigger json.JSONDecodeError
        mock_response = _make_mock_response("{not valid json at all!!!", 10, 20)
        mock_client_instance = MagicMock()
        mock_client_instance.messages.create.return_value = mock_response

        with patch.object(mod, "anthropic") as mock_anthropic:
            mock_anthropic.Anthropic.return_value = mock_client_instance
            mock_anthropic.APIError = type("APIError", (Exception,), {})
            main()

        result = json.loads(output_file.read_text())
        assert result["functions_documented"] == []
