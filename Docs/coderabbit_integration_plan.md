# SuperClaude + CodeRabbit Integration Plan

## Overview
- Integrate CodeRabbit MCP as an automated reviewer while maintaining resilience, consistent scoring, and evidence tracking.
- Work is organized into four tracks: Integration, Quality & Scoring, Agent Loop, and CI/CD + Compliance, each with testing and telemetry deliverables.

## 1. CodeRabbit MCP Integration Layer (`SuperClaude/MCP/coderabbit.py`)
- [x] Implement `CodeRabbitClient` wrapping MCP calls with configurable timeouts, exponential backoff (max 3 retries with jitter), and cached-last-known-score fallbacks per PR.
- [x] Emit typed errors (`NetworkError`, `AuthError`, `RateLimitError`) so callers can degrade gracefully.
- [x] Sanitize and log telemetry to `.superclaude_metrics/` with API payloads redacted; add helper to scrub secrets before persistence.
- [x] **Tests**: `tests/mcp/test_coderabbit_client.py` covering happy path, retry logic, fallback cache, and secret redaction.

## 2. Quality Scorer & Threshold Alignment (`SuperClaude/Quality/quality_scorer.py`, `Config/coderabbit.yaml`)
- [x] Single scoring formula:
  ```python
  quality_score = (
      superclaude_correctness * weights.superclaude +
      coderabbit_score * weights.coderabbit +
      completeness * weights.completeness +
      test_coverage * weights.test_coverage
  )
  ```
- [x] Default weights: 0.35 / 0.35 / 0.15 / 0.15; override via config to keep one source of truth.
- [x] Introduce `QualityThresholds` struct: `production_ready >= 90`, `needs_attention 75-89`, `iterate < 75`; shared by agent loop and CI gate.
- [x] When CodeRabbit data missing, renormalize remaining weights automatically and log `coderabbit_status = degraded` in telemetry.
- [x] **Tests**: `tests/quality/test_quality_scorer.py` for weighted math, threshold mapping, and degraded-mode renormalization.

## 3. Agentic Loop & Routing Enhancements (`SuperClaude/Commands/executor.py`, `Core/AGENTS.md`)
- [x] Loop sequence: Execution → SuperClaude scoring → (if available) CodeRabbit review fetch → telemetry merge → unified score → iterate/accept decision.
- [x] Define deterministic issue taxonomy (security, performance, style, logic) derived from CodeRabbit comment tags and stored in config.
- [x] On score < threshold: aggregate comments per taxonomy, compose improvement briefs with line numbers and rationale, delegate-ready routing metadata mapped to each specialist agent, then re-evaluate after fixes.
- [x] If CodeRabbit unavailable, fall back to SuperClaude-only flow, log degraded status, and skip routing adjustments to avoid stale guidance.
- [x] Document loop, taxonomy, and fallback rules in `AGENTS.md`.
- [x] **Tests**: `tests/commands/test_executor_coderabbit_loop.py` with mocked MCP responses and degraded scenarios.

## 4. Validation Pipeline (`SuperClaude/Quality/validation_pipeline.py`)
- [x] Build modular stages (syntax, security, style, tests, performance) that short-circuit on fatal errors yet continue collecting non-fatal findings where possible.
- [x] Security stage consumes CodeRabbit insights but also runs local static checks so security coverage persists when MCP fails.
- [x] Emit structured evidence artifacts per stage to `.superclaude_metrics/validation/`.
- [x] **Tests**: stage unit tests plus integration test ensuring evidence emission and graceful handling of stage failures.

## 5. CI/CD Workflow (`.github/workflows/ci-tests.yml`, `SuperClaude/Quality/coderabbit_gate.py`)
- [x] Create `coderabbit_gate.py` CLI with `--pr-number`, `--threshold`, `--allow-degraded`, reusing `CodeRabbitClient` and threshold config.
- [x] Workflow safeguards:
  - Run only on `pull_request` events; skip forks lacking secrets.
  - Export `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1` wherever pytest runs.
  - On MCP outage, gate exits neutral if `allow_degraded=true`; otherwise blocks with actionable messaging.
- [x] Upload sanitized gate results to `.superclaude_metrics/ci/`.
- [x] **Tests**: CLI unit tests for pass/fail/degraded plus workflow dry-run docs.

## 6. Configuration & Security (`Config/coderabbit.yaml`, Docs)
- [x] Config keys: `enabled`, `api_key_env`, `weights`, `thresholds`, `retry_policy`, `cache_ttl`, `issue_taxonomy`, `ci.allow_degraded`.
- [x] Document secret handling: prefer `CODERABBIT_API_KEY` env in prod, `.env` overrides for local (gitignored). Include rotation guidance and logging redaction rules.
- [x] Update Docs/README to explain setup, local testing, degraded-mode indicators, and telemetry outputs.

## 7. Testing & Evidence Coverage
- Ensure every new module has mirrored tests under `tests/<domain>/…`, including fixtures validating `.superclaude_metrics` artifacts.
- Extend benchmarks or smoke tests if CodeRabbit inputs affect performance-sensitive flows.
- Update telemetry specs with `coderabbit_status`, `coderabbit_score`, `degraded_reason`, ensuring evidence alignment with repository guidelines.

## Implementation Phasing
- **Week 1 (Integration)**: Client, config scaffolding, retry/caching tests.
- **Week 2 (Quality)**: Scorer refactor, thresholds, validation pipeline, associated tests.
- **Week 3 (Agent Loop)**: Routing logic, AGENTS.md updates, degraded handling fixtures.
- **Week 4 (CI/CD & Compliance)**: Gate CLI, workflow updates, docs, security hardening.
