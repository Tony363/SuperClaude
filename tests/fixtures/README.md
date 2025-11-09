# Test Fixtures

This directory contains reusable data assets that exercise the live code paths
for high-signal tests:

- `consensus/approve.json` and `consensus/split.json` capture recorded multi-model
  consensus payloads. Tests load these fixtures to register deterministic
  executors while still preserving realistic metadata, token counts, and
  provider annotations.

When adding new fixtures, prefer JSON or YAML formats so tests can load them
without custom parsers. Keep the payloads representative of real-world
responses to ensure the suite surfaces behavioural regressions instead of
artificial mock failures.
