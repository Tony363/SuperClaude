#!/usr/bin/env python3
"""
Generate Docstring Suggestions using Claude Haiku 4.5.

Reads a JSON array of {file, function, line} entries for functions missing
docstrings, sends source context to Claude, and produces a suggestions JSON
with Google-style docstrings.

Output contract (consumed by scripts/apply_docstrings.py):
  {
    "functions_documented": [
      {"file": "...", "function": "...", "docstring": "..."}
    ]
  }
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

try:
    import anthropic
except ImportError:
    print("::error::anthropic package not installed", file=sys.stderr)
    print("Install with: pip install anthropic", file=sys.stderr)
    sys.exit(1)

PROTECTED_PATTERNS = [
    ".github/workflows/",
    "secrets/",
    ".env",
    "agents/core/",
    "agents/traits/",
    "agents/extensions/",
    ".claude/skills/",
    ".claude/rules/",
    "CLAUDE.md",
    "benchmarks/",
]

# Haiku 4.5 pricing: $0.80 per MTok input, $4.00 per MTok output
HAIKU_INPUT_COST_PER_MTOK = 0.80
HAIKU_OUTPUT_COST_PER_MTOK = 4.00


def is_protected(file_path: str) -> bool:
    """Check if a file matches protected patterns."""
    for pattern in PROTECTED_PATTERNS:
        if file_path.startswith(pattern) or f"/{pattern}" in file_path:
            return True
    return False


def load_missing_docs(input_path: Path) -> list[dict[str, Any]]:
    """Load the list of functions missing docstrings."""
    try:
        with open(input_path, "r") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"::error::Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"::error::Invalid JSON in input file: {input_path}", file=sys.stderr)
        sys.exit(1)


def read_file_source(file_path: str) -> str | None:
    """Read source code from a file, returning None if unreadable."""
    try:
        return Path(file_path).read_text()
    except (OSError, UnicodeDecodeError):
        return None


def group_by_file(functions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group function entries by file path, filtering protected files."""
    by_file: dict[str, list[dict[str, Any]]] = {}
    for func in functions:
        file_path = func.get("file", "")
        if not file_path or is_protected(file_path):
            continue
        by_file.setdefault(file_path, []).append(func)
    return by_file


def build_prompt(file_path: str, source: str, functions: list[dict[str, Any]]) -> str:
    """Build the prompt for generating docstrings for functions in a file."""
    func_list = "\n".join(
        f"- `{f['function']}` (line {f.get('line', '?')})"
        for f in functions
    )

    return f"""You are a Python documentation expert. Analyze the following source file and write Google-style docstrings for the specified functions.

## Source File: `{file_path}`

```python
{source}
```

## Functions Needing Docstrings

{func_list}

## Requirements

1. Use Google-style docstrings (Args/Returns/Raises sections)
2. Start with a concise summary line in imperative mood ("Parse the input" not "Parses the input")
3. Include Args section if the function has parameters (excluding self/cls)
4. Include Returns section if the function returns a value
5. Include Raises section only if the function explicitly raises exceptions
6. Keep docstrings concise but informative
7. Do NOT include type annotations in the docstring (they belong in the signature)

## Output Format

Respond with a JSON object:

```json
{{
  "functions_documented": [
    {{
      "file": "{file_path}",
      "function": "function_name",
      "docstring": "Summary line.\\n\\nArgs:\\n    param: Description.\\n\\nReturns:\\n    Description."
    }}
  ]
}}
```

Only include functions you can write meaningful docstrings for. Use \\n for newlines within the docstring."""


def generate_docs_for_file(
    client: anthropic.Anthropic,
    file_path: str,
    source: str,
    functions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int, int]:
    """Call Claude to generate docstrings for functions in one file.

    Returns (documented_functions, input_tokens, output_tokens).
    """
    prompt = build_prompt(file_path, source, functions)

    response = client.messages.create(
        model="claude-haiku-4-5-20250514",
        max_tokens=8000,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    response_text = ""
    for block in response.content:
        if block.type == "text":
            response_text += block.text

    # Extract JSON from response
    json_start = response_text.find("```json")
    if json_start != -1:
        json_start = response_text.find("\n", json_start) + 1
        json_end = response_text.find("```", json_start)
        json_str = response_text[json_start:json_end].strip()
    else:
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start != -1 and json_end > json_start:
            json_str = response_text[json_start:json_end]
        else:
            json_str = ""

    documented = []
    if json_str:
        parsed = json.loads(json_str)
        documented = parsed.get("functions_documented", [])

    return documented, response.usage.input_tokens, response.usage.output_tokens


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate cost based on Claude Haiku 4.5 pricing."""
    input_cost = (input_tokens / 1_000_000) * HAIKU_INPUT_COST_PER_MTOK
    output_cost = (output_tokens / 1_000_000) * HAIKU_OUTPUT_COST_PER_MTOK
    return round(input_cost + output_cost, 4)


def main():
    input_path = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/missing-docs.json")
    output_path = Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/documentation-suggestions.json")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("::error::ANTHROPIC_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)

    print(f"Loading missing docstrings from {input_path}...")
    functions = load_missing_docs(input_path)

    # Handle empty input
    if not functions:
        print("No functions to document. Writing empty output.")
        result = {"functions_documented": [], "_metadata": {"model": "N/A", "input_tokens": 0, "output_tokens": 0, "total_tokens": 0}}
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        print("\n::set-output name=docstring_cost::0.00")
        return

    # Limit to 40 functions
    functions = functions[:40]
    by_file = group_by_file(functions)

    print(f"Processing {len(functions)} functions across {len(by_file)} files...")

    client = anthropic.Anthropic(api_key=api_key)
    all_documented: list[dict[str, Any]] = []
    total_input_tokens = 0
    total_output_tokens = 0

    for file_path, file_funcs in by_file.items():
        source = read_file_source(file_path)
        if source is None:
            print(f"  Skipping unreadable file: {file_path}")
            continue

        print(f"  Generating docstrings for {file_path} ({len(file_funcs)} functions)...")

        try:
            documented, in_tok, out_tok = generate_docs_for_file(
                client, file_path, source, file_funcs
            )
            all_documented.extend(documented)
            total_input_tokens += in_tok
            total_output_tokens += out_tok
            print(f"    Got {len(documented)} docstrings ({in_tok + out_tok} tokens)")
        except anthropic.APIError as e:
            print(f"  ::warning::API error for {file_path}: {e}")
            continue
        except json.JSONDecodeError:
            print(f"  ::warning::Failed to parse JSON response for {file_path}")
            continue

    result = {
        "functions_documented": all_documented,
        "_metadata": {
            "model": "claude-haiku-4-5-20250514",
            "input_tokens": total_input_tokens,
            "output_tokens": total_output_tokens,
            "total_tokens": total_input_tokens + total_output_tokens,
        },
    }

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    cost = estimate_cost(total_input_tokens, total_output_tokens)

    print(f"\nDocstring generation complete. Results saved to {output_path}")
    print("\n## Docstring Generation Results\n")
    print(f"- **Functions documented**: {len(all_documented)}")
    print(f"- **Files processed**: {len(by_file)}")
    print(f"- **Cost**: ${cost}")
    print(f"- **Tokens**: {total_input_tokens + total_output_tokens:,} ({total_input_tokens:,} in + {total_output_tokens:,} out)")

    print(f"\n::set-output name=docstring_cost::{cost}")


if __name__ == "__main__":
    main()
