"""Integration test for the Codex client.

This test only runs when an OpenAI key is available. It exercises the
``CodexClient`` end-to-end so CI environments with network access can verify
that the fast-codex path works against a real backend.
"""

from __future__ import annotations

import os

import pytest

from SuperClaude.APIClients.codex_client import CodexClient, CodexUnavailable


@pytest.mark.integration
def test_codex_client_live_completion(tmp_path):
    """Hit the live Codex endpoint and ensure we receive structured JSON."""

    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("CODEX_API_KEY")
    if not api_key:
        pytest.skip("OPENAI_API_KEY not configured; skipping live Codex test")

    output_path = tmp_path / "codex-live-demo.txt"

    system_prompt = (
        "You are a JSON-only code assistant. Respond with an object containing "
        "'summary' and 'changes'. Each entry in 'changes' must include 'path', "
        "'content', and 'mode'. Use the provided path verbatim."
    )

    user_prompt = (
        "Add a greeting line to the demo file. Use the relative path "
        f"'{output_path.name}' and set mode to 'replace'."
    )

    client = CodexClient()

    try:
        payload = client.complete_structured(system_prompt, user_prompt)
    except CodexUnavailable as exc:  # pragma: no cover - defensive guard
        pytest.skip(f"Codex backend unavailable: {exc}")

    assert isinstance(payload, dict), "Codex response must be a dict"
    assert payload.get("summary"), "Codex response missing summary"

    changes = payload.get("changes")
    assert isinstance(changes, list) and changes, "Codex response missing changes"

    first = changes[0]
    assert first.get("path") == output_path.name
    assert first.get("mode") in {"replace", "append"}
    assert isinstance(first.get("content"), str) and first["content"].strip()

