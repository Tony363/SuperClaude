# Claude Review + PAL MCP Integration

**AI-Powered Code Review with Multi-Model Consensus and Automated Draft PRs**

---

## Quick Start

See [CLAUDE_REVIEW_SETUP.md](./CLAUDE_REVIEW_SETUP.md) for detailed setup, or
run the setup script:

```bash
bash .github/workflows/setup-claude-review.sh
```

---

## What's Included

A **single consolidated workflow** (`ai-code-review.yml`) with three jobs:

### Review (always runs)
- Claude reviews PRs and posts advisory comments
- Dual provider: AWS Bedrock (primary) + Anthropic API (fallback)
- Cost: ~$1.50/PR | Latency: 2-5 minutes

### Consensus (conditional)
- Multi-model review for security-sensitive changes
- Models: GPT-5-mini, Claude Haiku 4.5, Gemini-2-Flash
- Triggers automatically for high-stakes files or `ai-consensus` label
- Cost: ~$3-5 additional | Latency: +5-8 minutes

### Autofix (opt-in via `ai-patch` label)
- Generates draft PRs with AI-suggested fixes
- Blocked for protected files and fork PRs
- Always creates DRAFT PRs (never auto-merges)
- Cost: ~$3 additional | Latency: +8-15 minutes

---

## Files

```
.github/workflows/
├── ai-code-review.yml                # Consolidated review workflow
├── ai-review-cost-monitor.yml        # Cost tracking & alerts
├── setup-claude-review.sh            # Automated setup script
├── CLAUDE_REVIEW_SETUP.md            # Detailed setup guide
└── README_CLAUDE_REVIEW.md           # This file
```

---

## Required Secrets

### Review (required — at least one):
- `ANTHROPIC_API_KEY` - Anthropic API key
- `AWS_BEARER_TOKEN_BEDROCK` + `AWS_REGION` - AWS Bedrock credentials

### Consensus (optional):
- `PAL_MCP_API_KEY` - From PAL MCP provider
- `PAL_MCP_ENDPOINT` - PAL MCP API URL (optional, has default)

### Autofix:
- Uses `GITHUB_TOKEN` (automatically provided, no additional secrets needed)

---

## Cost Management

### Built-in Controls

1. **Size Limits**: PRs >1000 lines require `force-review` label
2. **Draft Skip**: Draft PRs skip review unless `force-review` label
3. **Concurrency Control**: One review per PR at a time
4. **Cost Monitoring**: Automated tracking every 6 hours

### Budget Alerts

The cost monitor creates GitHub issues when:
- Daily spend exceeds $50
- Monthly projection exceeds $1000

Customize limits in [`ai-review-cost-monitor.yml`](./ai-review-cost-monitor.yml)

---

## Security

### Protections Built-In

| Protection | Review | Consensus | Autofix |
|------------|--------|-----------|---------|
| Bot loop prevention | Yes | Yes | Yes |
| Fork PR safety | Yes | Yes | Yes (blocked) |
| Protected file blocking | N/A | N/A | Yes |
| Secret scanning | N/A | N/A | Yes |
| Draft PR only (no auto-merge) | N/A | N/A | Yes |

### Files Protected from AI Modification (Autofix)

- `.github/workflows/*`, `secrets/`, `.env*`
- `CLAUDE.md`, `.claude/skills/*`
- `agents/core/*`, `agents/traits/*`
- PRs from forks

---

## Usage

### Trigger Review Manually
Comment `@claude-review` on any PR.

### Request Multi-Model Consensus
```bash
gh pr edit <pr-number> --add-label "ai-consensus"
```

### Force Review (draft or large PR)
```bash
gh pr edit <pr-number> --add-label "force-review"
```

### Enable Autofix Draft PR
```bash
gh pr edit <pr-number> --add-label "ai-patch"
```

### Skip Review
```bash
gh pr edit <pr-number> --add-label "skip-ci-review"
```

---

## Labels Reference

| Label | Effect |
|-------|--------|
| `skip-ci-review` | Skip AI review entirely |
| `force-review` | Override draft/size gates |
| `ai-consensus` | Force multi-model consensus |
| `ai-patch` | Enable autofix draft PR creation |

---

## Troubleshooting

### Workflow doesn't trigger
1. Check `ai-code-review.yml` exists in `.github/workflows/`
2. Verify YAML syntax: `yamllint .github/workflows/ai-code-review.yml`
3. Confirm secrets are configured: `gh secret list`

### Debug
```bash
gh run list --workflow=ai-code-review.yml --limit 5
gh run view <run-id> --log
```

---

## Resources

- **Setup Guide**: [CLAUDE_REVIEW_SETUP.md](./CLAUDE_REVIEW_SETUP.md)
- **Claude Code Docs**: https://code.claude.com/docs
- **PAL MCP GitHub**: https://github.com/BeehiveInnovations/pal-mcp-server

---

Last Updated: 2026-04-01
