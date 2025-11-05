# Behavioural Flags

Flags customise how the executor routes work, selects agents, and enforces
guardrails. Combine them to match the risk profile of your change.

## Core Flags

| Flag | Usage | Effect |
| ---- | ----- | ------ |
| `--think <1-3>` | `/sc:implement --think 3` | Expands the context window and instructs the router to favour deeper reasoning models. |
| `--consensus` | `/sc:workflow --consensus` | Forces multi-model voting even if the command does not require it by default. |
| `--fast-codex` | `/sc:implement --fast-codex` | Switches to the codex-implementer persona for quick diffs. Requires live Codex/OpenAI credentials. |
| `--safe` | `/sc:implement --safe` | Disables risky shortcuts (fast-codex, auto-apply) and raises the quality gate threshold. |
| `--delegate <agent>` | `/sc:reflect --delegate technical-writer` | Pins execution to a specific agent when you know who should lead. |
| `--loop` | `/sc:improve --loop` | Allows the executor to re-plan with additional agents until success criteria are met. |
| `--cwd <path>` | Pass on CLI | Run commands against a different repository without changing your working directory. |

## Consensus Controls

- `--vote-type <majority|quorum|unanimous|weighted>` overrides the policy in
  `SuperClaude/Config/consensus_policies.yaml`.
- `--quorum-size <n>` pairs with `--vote-type quorum` to define the minimum
  approvals needed.

## Telemetry & Debugging

- `--verbose` prints additional execution details.
- `--export-plan` writes the final change plan to STDOUT for scripting.
- Set environment variable `SUPERCLAUDE_LOG_LEVEL=DEBUG` to enable verbose logs
  for the current command.

These flags can be combined. For example, `/sc:implement --fast-codex --think 2
--consensus --safe` requests a fast plan but insists on consensus and safety, so
the executor will auto-fallback to the standard persona stack if any guardrail
objects.
