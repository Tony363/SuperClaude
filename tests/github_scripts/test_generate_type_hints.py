"""Tests for .github/scripts/generate-type-hints.py pure functions."""

import importlib
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add .github/scripts to path for import
scripts_dir = str(Path(__file__).parent.parent.parent / ".github" / "scripts")
if scripts_dir not in sys.path:
    sys.path.insert(0, scripts_dir)

mod = importlib.import_module("generate-type-hints")

is_protected = mod.is_protected
load_missing_hints = mod.load_missing_hints
read_file_source = mod.read_file_source
group_by_file = mod.group_by_file
build_prompt = mod.build_prompt
estimate_cost = mod.estimate_cost
generate_hints_for_file = mod.generate_hints_for_file
main = mod.main


class TestIsProtected:
    """Tests for is_protected."""

    def test_workflow_path_is_protected(self):
        assert is_protected(".github/workflows/ci.yml") is True

    def test_secrets_dir_is_protected(self):
        assert is_protected("secrets/api_key.txt") is True

    def test_env_file_is_protected(self):
        assert is_protected(".env") is True

    def test_agents_core_is_protected(self):
        assert is_protected("agents/core/architect.md") is True

    def test_regular_file_is_not_protected(self):
        assert is_protected("src/utils/helpers.py") is False

    def test_scripts_dir_not_protected(self):
        assert is_protected("scripts/validate.py") is False

    def test_claude_md_is_protected(self):
        assert is_protected("CLAUDE.md") is True


class TestLoadMissingHints:
    """Tests for load_missing_hints."""

    def test_loads_valid_json(self, tmp_path: Path):
        import json

        data = [{"file": "test.py", "function": "foo", "line": 1}]
        p = tmp_path / "hints.json"
        p.write_text(json.dumps(data))

        result = load_missing_hints(p)
        assert len(result) == 1
        assert result[0]["function"] == "foo"

    def test_missing_file_exits(self, tmp_path: Path):
        import pytest

        with pytest.raises(SystemExit):
            load_missing_hints(tmp_path / "nonexistent.json")

    def test_invalid_json_exits(self, tmp_path: Path):
        import pytest

        p = tmp_path / "bad.json"
        p.write_text("not json {{{")
        with pytest.raises(SystemExit):
            load_missing_hints(p)


class TestReadFileSource:
    """Tests for read_file_source."""

    def test_reads_existing_file(self, tmp_path: Path):
        p = tmp_path / "test.py"
        p.write_text("def foo(): pass")
        result = read_file_source(str(p))
        assert result == "def foo(): pass"

    def test_returns_none_for_missing(self):
        result = read_file_source("/nonexistent/path.py")
        assert result is None


class TestGroupByFile:
    """Tests for group_by_file."""

    def test_groups_by_file_path(self):
        functions = [
            {"file": "a.py", "function": "foo"},
            {"file": "a.py", "function": "bar"},
            {"file": "b.py", "function": "baz"},
        ]
        result = group_by_file(functions)
        assert len(result) == 2
        assert len(result["a.py"]) == 2
        assert len(result["b.py"]) == 1

    def test_filters_protected_files(self):
        functions = [
            {"file": "agents/core/test.md", "function": "foo"},
            {"file": "src/utils.py", "function": "bar"},
        ]
        result = group_by_file(functions)
        assert "agents/core/test.md" not in result
        assert "src/utils.py" in result

    def test_skips_empty_file_path(self):
        functions = [{"file": "", "function": "foo"}]
        result = group_by_file(functions)
        assert result == {}


class TestBuildPrompt:
    """Tests for build_prompt."""

    def test_contains_source_and_functions(self):
        source = "def foo(): pass\ndef bar(): return 1"
        functions = [
            {"function": "foo", "line": 1},
            {"function": "bar", "line": 2},
        ]
        prompt = build_prompt("test.py", source, functions)

        assert "test.py" in prompt
        assert "def foo(): pass" in prompt
        assert "`foo`" in prompt
        assert "`bar`" in prompt
        assert "JSON" in prompt


class TestEstimateCost:
    """Tests for estimate_cost."""

    def test_zero_tokens(self):
        assert estimate_cost(0, 0) == 0.0

    def test_known_pricing(self):
        # Haiku: $0.80/MTok in, $4.00/MTok out
        cost = estimate_cost(1_000_000, 1_000_000)
        assert cost == 4.8  # 0.80 + 4.00

    def test_small_usage(self):
        cost = estimate_cost(10000, 5000)
        expected = round((10000 / 1_000_000) * 0.80 + (5000 / 1_000_000) * 4.00, 4)
        assert cost == expected


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


class TestGenerateHintsForFile:
    """Tests for generate_hints_for_file."""

    def test_parses_json_from_code_fence(self):
        payload = json.dumps(
            {
                "functions_annotated": [
                    {
                        "file": "a.py",
                        "function": "foo",
                        "typed_signature": "def foo(x: int) -> str:",
                        "imports_needed": [],
                    }
                ]
            }
        )
        response_text = f"Here are the results:\n```json\n{payload}\n```"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(response_text, 50, 80)

        annotations, in_tok, out_tok = generate_hints_for_file(
            mock_client, "a.py", "def foo(x): return str(x)", [{"function": "foo", "line": 1}]
        )

        assert len(annotations) == 1
        assert annotations[0]["function"] == "foo"
        assert annotations[0]["typed_signature"] == "def foo(x: int) -> str:"
        assert in_tok == 50
        assert out_tok == 80

    def test_parses_json_without_code_fence(self):
        payload = json.dumps(
            {
                "functions_annotated": [
                    {
                        "file": "b.py",
                        "function": "bar",
                        "typed_signature": "def bar() -> None:",
                        "imports_needed": [],
                    }
                ]
            }
        )
        response_text = f"Sure, here you go: {payload}"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(response_text)

        annotations, _, _ = generate_hints_for_file(
            mock_client, "b.py", "def bar(): pass", [{"function": "bar", "line": 1}]
        )

        assert len(annotations) == 1
        assert annotations[0]["function"] == "bar"

    def test_returns_empty_on_no_json(self):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response("No JSON here at all.")

        annotations, _, _ = generate_hints_for_file(
            mock_client, "c.py", "def baz(): pass", [{"function": "baz", "line": 1}]
        )

        assert annotations == []

    def test_returns_empty_on_missing_key(self):
        payload = json.dumps({"other_key": []})
        response_text = f"```json\n{payload}\n```"
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _make_mock_response(response_text)

        annotations, _, _ = generate_hints_for_file(
            mock_client, "d.py", "def qux(): pass", [{"function": "qux", "line": 1}]
        )

        assert annotations == []

    def test_multiple_text_blocks_concatenated(self):
        payload = json.dumps(
            {
                "functions_annotated": [
                    {
                        "file": "e.py",
                        "function": "multi",
                        "typed_signature": "def multi() -> None:",
                        "imports_needed": [],
                    }
                ]
            }
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

        annotations, in_tok, out_tok = generate_hints_for_file(
            mock_client, "e.py", "def multi(): pass", [{"function": "multi", "line": 1}]
        )

        assert len(annotations) == 1
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
        assert result["functions_annotated"] == []
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
                "functions_annotated": [
                    {
                        "file": str(src_file),
                        "function": "greet",
                        "typed_signature": "def greet(name: str) -> str:",
                        "imports_needed": [],
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
        assert len(result["functions_annotated"]) == 1
        assert result["functions_annotated"][0]["function"] == "greet"
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
        assert result["functions_annotated"] == []
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
        assert result["functions_annotated"] == []

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
        assert result["functions_annotated"] == []
