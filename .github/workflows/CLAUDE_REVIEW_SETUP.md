# Claude Review + PAL MCP Integration Setup Guide

Complete setup instructions for the three-phase AI code review system.

## 📋 Table of Contents

- [Overview](#overview)
- [Phase Selection](#phase-selection)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Cost Management](#cost-management)
- [Security Configuration](#security-configuration)
- [Usage Guide](#usage-guide)
- [Troubleshooting](#troubleshooting)

## Overview

This repository implements a phased approach to AI-powered code review:

| Phase | Features | Cost/PR | Latency | Risk |
|-------|----------|---------|---------|------|
| **Phase 1** | Claude review comments only | ~$1.50 | 2-5 min | Low |
| **Phase 2** | + PAL MCP consensus for high-stakes changes | $1.50-$5 | 5-13 min | Medium |
| **Phase 3** | + Draft PR creation with AI suggestions | $3-$8 | 8-20 min | Medium-High |

**Recommendation**: Start with Phase 1, graduate to Phase 2 after 2-4 weeks, consider Phase 3 only for mature repos with strong CI.

## Phase Selection

### Use Phase 1 If:
- ✅ First time using AI code review
- ✅ Want low cost and fast feedback
- ✅ Prefer manual implementation of suggestions
- ✅ High PR volume (>50/day)

### Use Phase 2 If:
- ✅ Have security-critical code
- ✅ Want multi-model validation for important changes
- ✅ Willing to pay premium for high-stakes PRs
- ✅ Medium PR volume (20-50/day)

### Use Phase 3 If:
- ✅ Want automated fix PRs
- ✅ Have mature CI/CD with comprehensive tests
- ✅ Strong branch protection rules in place
- ✅ Low-medium PR volume (<20/day)

## Prerequisites

### 1. Claude Code Setup

**Required**:
- Claude Pro or Claude for Work subscription
- Repository admin access

**Steps**:
1. Install Claude GitHub App: https://github.com/apps/claude
2. Grant permissions:
   - ✅ Read: Contents, Issues, Pull Requests
   - ✅ Write: Contents (Phase 3 only), Issues, Pull Requests
3. Generate OAuth token:
   - Visit https://claude.com/console
   - Navigate to API Keys
   - Create new OAuth token
   - Copy token (you won't see it again)

### 2. GitHub Secrets Configuration

Add these secrets in repository Settings → Secrets → Actions:

#### Phase 1 (Required):
```
CLAUDE_CODE_OAUTH_TOKEN=<your-oauth-token-from-claude-console>
```

#### Phase 2 (Additional):
```
PAL_MCP_API_KEY=<your-pal-mcp-api-key>
PAL_MCP_ENDPOINT=https://your-pal-mcp-server.com/api/tools/consensus
```

#### Phase 3 (Additional):
```
# PAT_TOKEN is no longer required — GITHUB_TOKEN is used for all operations
```

### 3. PAL MCP Setup (Phase 2 & 3)

**Option A: Hosted Service** (Recommended)
- Contact PAL MCP provider for API key
- Use provided endpoint URL

**Option B: Self-Hosted** (Advanced)
```bash
# Clone PAL MCP server
git clone https://github.com/BeehiveInnovations/pal-mcp-server
cd pal-mcp-server

# Configure environment
cp .env.example .env
# Add your model API keys:
# - OPENAI_API_KEY
# - ANTHROPIC_API_KEY
# - GOOGLE_API_KEY

# Run server
docker-compose up -d

# Your endpoint: http://localhost:8080/api/tools/consensus
```

### 4. Branch Protection Rules (Phase 3)

**Critical for safety**:
1. Go to Settings → Branches → Branch protection rules
2. Add rule for `main` (or default branch):
   - ✅ Require pull request reviews before merging
   - ✅ Require status checks to pass before merging
   - ✅ Require branches to be up to date before merging
   - ✅ Do not allow bypassing the above settings
   - ❌ Do NOT enable "Allow auto-merge" for bot accounts

## Setup Instructions

### Step 1: Choose Your Phase

Copy the desired workflow file:

```bash
# Phase 1: Comment-only review
cp .github/workflows/claude-review-phase1.yml .github/workflows/claude-review.yml

# Phase 2: Selective consensus
cp .github/workflows/claude-review-phase2.yml .github/workflows/claude-review.yml

# Phase 3: Draft PR creation
cp .github/workflows/claude-review-phase3.yml .github/workflows/claude-review.yml
```

### Step 2: Add Secrets

```bash
# Add Claude OAuth token
gh secret set CLAUDE_CODE_OAUTH_TOKEN

# Phase 2/3: Add PAL MCP credentials
gh secret set PAL_MCP_API_KEY
gh secret set PAL_MCP_ENDPOINT --body "https://your-endpoint.com/api/tools/consensus"

# Phase 3: PAT_TOKEN no longer required (GITHUB_TOKEN is used)
```

### Step 3: Create CLAUDE.md (Optional but Recommended)

Create a `CLAUDE.md` file in your repository root with coding guidelines:

```markdown
# Code Review Guidelines

## Project Standards
- Language: [Python/TypeScript/Go/etc.]
- Style Guide: [PEP 8/Airbnb/Google/etc.]
- Test Coverage: Minimum 80%

## Security Rules
- No hardcoded secrets
- All user input must be validated
- Use parameterized queries (no SQL injection)

## Architectural Principles
- [Your team's principles]

## Review Focus Areas
1. Security vulnerabilities
2. Performance issues
3. Code maintainability
4. Test coverage
```

### Step 4: Test the Integration

Create a test PR:

```bash
git checkout -b test/ai-review
echo "# Test AI Review" >> test-file.md
git add test-file.md
git commit -m "test: trigger AI review"
git push origin test/ai-review

# Create PR
gh pr create --title "Test: AI Review System" --body "Testing Phase X integration"
```

For Phase 1: Check for review comment
For Phase 2: Add `ai-consensus` label to trigger multi-model
For Phase 3: Wait for draft PR to be created

## Cost Management

### Budget Controls

Create `.github/workflows/cost-monitor.yml`:

```yaml
name: AI Review Cost Monitor

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:

jobs:
  cost-check:
    runs-on: ubuntu-latest
    steps:
      - name: Check daily spend
        run: |
          # Query your cost tracking system
          # This is a placeholder - implement based on your setup

          DAILY_SPEND=50  # Example: Query from logs/metrics
          MONTHLY_BUDGET=1000
          DAILY_LIMIT=$((MONTHLY_BUDGET / 30))

          if [ $DAILY_SPEND -gt $DAILY_LIMIT ]; then
            echo "::error::Daily AI review spend ($${DAILY_SPEND}) exceeds limit ($${DAILY_LIMIT})"
            # Disable workflows or notify team
          fi
```

### Cost Optimization Tips

1. **Use size limits** (already in Phase 1):
   ```yaml
   if: |
     steps.pr_size.outputs.lines_changed < 1000
   ```

2. **Selective triggering** (Phase 2):
   - Only run on `ready_for_review`, not every `synchronize`
   - Use labels: `ai-review`, `ai-consensus`

3. **Cheaper models** for consensus:
   ```json
   {
     "models": [
       {"model": "gpt-5-mini", "stance": "for"},       // $0.10/1M tokens
       {"model": "claude-haiku-4.5", "stance": "against"},  // $0.25/1M tokens
       {"model": "gemini-2-flash", "stance": "neutral"}     // $0.15/1M tokens
     ]
   }
   ```

## Security Configuration

### Sensitive File Protection

The workflows automatically block AI modifications to:
- `.github/workflows/*` - Workflow files
- `secrets/`, `.env*` - Secrets and config
- `*.key`, `*.pem` - Cryptographic keys
- `auth/`, `security/` - Auth/security modules

### Fork PR Safety

Phase 3 automatically disables for fork PRs:
```yaml
if: |
  github.event.pull_request.head.repo.full_name == github.repository
```

### Prompt Injection Defense

The workflows:
- Never pass PR descriptions directly to models
- Treat all user input as untrusted
- Use strict system prompts

### Manual Override

For emergency review bypass:
```bash
# Skip AI review for this PR
gh pr edit <pr-number> --add-label "skip-ai-review"
```

## Usage Guide

### Phase 1: Comment-Only Review

**Automatic**: Triggers on PR open/ready_for_review

**Manual trigger**: Comment `@claude-review` on PR

**Expected output**:
```
🤖 Claude Review Summary

Issues Found: 3
- [High] Potential SQL injection in query builder
- [Medium] Missing error handling in API endpoint
- [Low] Consider using const instead of let

Suggestions: 2
- Add input validation
- Extract magic numbers to constants

Estimated cost: ~$1.50
```

### Phase 2: Selective Consensus

**Automatic high-stakes detection**:
- Modifies `auth/`, `security/`, `crypto/`
- Changes `.env` or secrets
- Alters database migrations
- Updates workflows

**Manual trigger**: Add `ai-consensus` label

**Expected output**:
```
🔒 Multi-Model Security Consensus

Trigger: Security-sensitive files detected

Consensus Recommendation:
✅ Safe to proceed with following conditions:
- Add unit tests for new auth logic
- Update security documentation
- Require two reviewers

Models: GPT-5-mini (approve), Claude Haiku (concerns noted), Gemini-2-Flash (approved with conditions)

Cost: ~$4.20
```

### Phase 3: Draft PR Creation

**Automatic**: Creates draft PR when:
1. Claude generates valid patch
2. Consensus approves changes
3. Security checks pass

**Expected output**:
1. Comment on original PR with link to draft PR
2. Draft PR created with:
   - 🤖 Prefix in title
   - `ai-generated`, `needs-human-review` labels
   - Detailed explanation of changes
   - Link back to original PR

**Next steps**:
1. Review draft PR changes
2. Run full CI suite
3. If approved, apply `/approve-ai-patch` label
4. Merge normally (requires human approval)

## Troubleshooting

### Issue: Workflow doesn't trigger

**Check**:
1. Workflow file in `.github/workflows/` folder?
2. Proper YAML syntax? Run: `yamllint .github/workflows/*.yml`
3. Secrets configured? Check Settings → Secrets
4. PR from fork? Phase 3 disabled for forks (security)

**Debug**:
```bash
# Check workflow status
gh run list --workflow=claude-review.yml

# View workflow logs
gh run view <run-id> --log
```

### Issue: "CLAUDE_CODE_OAUTH_TOKEN not found"

**Solution**:
1. Verify token in Claude Console: https://claude.com/console
2. Add to GitHub Secrets:
   ```bash
   gh secret set CLAUDE_CODE_OAUTH_TOKEN
   ```
3. Token must start with `sk-ant-`

### Issue: PAL MCP API returns 401 Unauthorized

**Check**:
1. `PAL_MCP_API_KEY` secret is set
2. API key is valid (test with curl):
   ```bash
   curl -H "Authorization: Bearer $PAL_MCP_API_KEY" \
        https://your-endpoint.com/api/health
   ```
3. Endpoint URL is correct

### Issue: Draft PR not created (Phase 3)

**Common causes**:
1. **Protected branch**: GITHUB_TOKEN can't push to protected branches directly
3. **Consensus rejected changes**: Check workflow logs for recommendation
4. **Security block**: Modifying protected files (`.github/`, secrets)

**Debug**:
```bash
# Check PAT permissions
gh auth status

# Verify branch protection
gh api repos/:owner/:repo/branches/main/protection
```

### Issue: Cost too high

**Solutions**:
1. **Enable size limits** (Phase 1 default):
   ```yaml
   if: steps.pr_size.outputs.lines_changed < 500
   ```

2. **Use cheaper models** (Phase 2/3):
   - Replace `gpt-5.2` → `gpt-5-mini`
   - Replace `claude-opus` → `claude-haiku`
   - Replace `gemini-3-pro` → `gemini-2-flash`

3. **Selective triggering**:
   - Only on `ready_for_review`, not `synchronize`
   - Use labels: `ai-review` for opt-in

4. **Monitor daily spend**:
   ```bash
   # Add cost tracking workflow
   cp .github/workflows/examples/cost-monitor.yml .github/workflows/
   ```

### Issue: Infinite loop (bot reviewing own PRs)

**Should never happen** - workflows have guards:
```yaml
if: |
  github.actor != 'claude[bot]' &&
  github.actor != 'dependabot[bot]' &&
  github.actor != 'github-actions[bot]'
```

**If it does**:
1. Cancel running workflows: Actions → Cancel all
2. Check workflow file for missing `if` condition
3. Verify bot username matches filter

## Support & Resources

- **Claude Code Docs**: https://code.claude.com/docs
- **PAL MCP GitHub**: https://github.com/BeehiveInnovations/pal-mcp-server
- **GitHub Actions**: https://docs.github.com/actions
- **This Research**: See `.github/workflows/RESEARCH_REPORT.md`

## Contributing

Found a bug or have suggestions? Open an issue or PR!

## License

See repository LICENSE file.

---

**Generated by**: Claude Code Research + Implementation
**Last Updated**: 2026-03-04
**Version**: 1.0.0
