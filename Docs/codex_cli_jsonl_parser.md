# Codex CLI JSONL Parser Update

Date: 2025-11-09

## Summary
- Updated `SuperClaude/APIClients/codex_cli.py` so fast-codex runs can ingest the JSONL stream emitted by newer Codex CLI builds.

## Changes
1. **`_extract_json` overhaul**
   - Keeps the legacy single-JSON fast path.
   - Iterates through each stdout line, decoding JSONL events, and tracks them for a final reverse pass.
   - Returns the first record (or nested payload) containing both `summary` and `changes`; raises a descriptive error if none are found.

2. **New helpers**
   - `_parse_payload_from_record(record)` recursively inspects event dictionaries, including nested `text`, `message`, `content`, `item`, `payload`, or `data` fields, to find the Codex diff payload.
   - `_safe_json_loads(blob)` trims fences/whitespace, strips ```json blocks, and safely attempts `json.loads`, returning `None` on failure.

## Impact
- `/sc:implement --fast-codex …` now succeeds even when the Codex CLI wraps the desired diff inside JSONL `agent_message` events, eliminating the previous “Codex CLI output did not contain valid JSON” failure.
- No behavior change for older Codex builds that already emitted a single JSON document.
