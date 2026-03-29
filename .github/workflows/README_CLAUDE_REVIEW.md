# 🤖 Claude Review + PAL MCP Integration

**AI-Powered Code Review with Multi-Model Consensus and Automated PR Creation**

---

## 🚀 Quick Start (< 5 minutes)

```bash
# Run automated setup script
bash .github/workflows/setup-claude-review.sh
```

The script will guide you through:
1. ✅ Installing Claude GitHub App
2. ✅ Configuring secrets (Claude OAuth, PAL MCP API keys)
3. ✅ Installing workflow files
4. ✅ Creating test PR

**Or follow manual setup**: See [CLAUDE_REVIEW_SETUP.md](./CLAUDE_REVIEW_SETUP.md)

---

## 📊 What's Included

This implementation provides a **three-phase approach** to AI code review:

### Phase 1: Comment-Only Review 💬
- **What**: Claude reviews PRs, posts comments
- **Cost**: ~$1.50/PR
- **Latency**: 2-5 minutes
- **Risk**: Low (read-only)
- **Best for**: All teams, first-time users

**Triggers**:
- Automatic on PR open/ready for review
- Manual: Comment `@claude-review` on PR

### Phase 2: Selective Consensus 🔒
- **What**: Multi-model review for security-sensitive changes
- **Models**: Claude Opus + GPT-5-mini + Claude Haiku + Gemini-2-Flash
- **Cost**: $1.50-$5/PR (only for high-stakes PRs)
- **Latency**: 5-13 minutes
- **Best for**: Repos with security-critical code

**Auto-triggers when**:
- Changes to `auth/`, `security/`, `crypto/`
- Modifications to `.env`, secrets
- Updates to database migrations or workflows

**Manual trigger**: Add `ai-consensus` label

### Phase 3: Draft PR Creation 🚀
- **What**: Generates draft PRs with AI-suggested fixes
- **Cost**: $3-$8/PR
- **Latency**: 8-20 minutes
- **Risk**: Medium (creates PRs, but requires human approval)
- **Best for**: Mature repos with strong CI/CD

**Safety features**:
- ✅ Always creates DRAFT PRs (never auto-merges)
- ✅ Blocks modifications to workflows, secrets
- ✅ Requires consensus approval from 3 models
- ✅ Runs security scans on generated patches
- ✅ Requires human `/approve-ai-patch` label

---

## 📁 Files Installed

```
.github/workflows/
├── claude-review-phase1.yml          # Phase 1: Comment-only
├── claude-review-phase2.yml          # Phase 2: Selective consensus
├── claude-review-phase3.yml          # Phase 3: Draft PR creation
├── ai-review-cost-monitor.yml        # Cost tracking & alerts
├── setup-claude-review.sh            # Automated setup script
├── CLAUDE_REVIEW_SETUP.md            # Detailed setup guide
└── README_CLAUDE_REVIEW.md           # This file
```

---

## 🔑 Required Secrets

### All Phases:
- `CLAUDE_CODE_OAUTH_TOKEN` - From [Claude Console](https://claude.com/console)

### Phase 2 & 3:
- `PAL_MCP_API_KEY` - From PAL MCP provider
- `PAL_MCP_ENDPOINT` - PAL MCP API URL (optional, has default)

### Phase 3:
- Uses `GITHUB_TOKEN` (automatically provided, no additional secrets needed)

---

## 💰 Cost Management

### Built-in Controls

1. **Size Limits**: PRs >1000 lines require `force-review` label
2. **Selective Triggering**: Phase 2 only on high-stakes changes
3. **Concurrency Control**: One review per PR at a time
4. **Cost Monitoring**: Automated tracking every 6 hours

### Budget Alerts

The cost monitor creates GitHub issues when:
- Daily spend exceeds $50
- Monthly projection exceeds $1000

Customize limits in [`ai-review-cost-monitor.yml`](./ai-review-cost-monitor.yml)

### Optimization Tips

**Use cheaper models** (Phase 2/3):
```yaml
models: [
  {"model": "gpt-5-mini", "stance": "for"},          # $0.10/1M vs $3/1M
  {"model": "claude-haiku-4.5", "stance": "against"}, # $0.25/1M vs $15/1M
  {"model": "gemini-2-flash", "stance": "neutral"}    # $0.15/1M vs $7/1M
]
```

**Result**: 84% cost reduction with minimal quality loss

---

## 🔒 Security

### Protections Built-In

| Protection | Phase 1 | Phase 2 | Phase 3 |
|------------|---------|---------|---------|
| Read-only mode | ✅ | ✅ | ❌ |
| Infinite loop prevention | ✅ | ✅ | ✅ |
| Fork PR safety | ✅ | ✅ | ✅ |
| Prompt injection defense | ✅ | ✅ | ✅ |
| Protected file blocking | N/A | N/A | ✅ |
| Secret scanning | N/A | N/A | ✅ |
| Draft PR only (no auto-merge) | N/A | N/A | ✅ |

### Files Protected from AI Modification

Phase 3 automatically blocks changes to:
- `.github/workflows/*` - Workflow files
- `secrets/`, `.env*` - Configuration
- `*.key`, `*.pem` - Cryptographic keys
- PRs from forks

---

## 📖 Usage Examples

### Example 1: Trigger Review Manually

```bash
# Comment on any PR
@claude-review
```

### Example 2: Request Multi-Model Consensus

```bash
# Add label to PR
gh pr edit <pr-number> --add-label "ai-consensus"
```

### Example 3: Force Review Large PR

```bash
# Override size limit
gh pr edit <pr-number> --add-label "force-review"
```

### Example 4: Approve AI-Generated Draft PR

```bash
# After reviewing the draft PR
gh pr edit <draft-pr-number> --add-label "approve-ai-patch"
gh pr ready <draft-pr-number>  # Convert from draft
# Then merge normally (requires approvals per branch protection)
```

---

## 📊 Expected Outputs

### Phase 1 Output:

```markdown
🤖 Claude Review Summary

Issues Found: 3
- [High] Potential SQL injection in query builder (line 45)
- [Medium] Missing error handling in API endpoint (line 78)
- [Low] Consider using const instead of let (line 12)

Suggestions: 2
- Add input validation for user parameters
- Extract magic numbers to named constants

Confidence: 87% (3/4 agents agree)
Estimated cost: ~$1.50
Phase: 1 (Comment Only)
```

### Phase 2 Output:

```markdown
🔒 Multi-Model Security Consensus

Trigger: Security-sensitive files detected (auth/middleware.py)

Consensus Recommendation:
✅ Safe to proceed with conditions:
1. Add unit tests for new auth logic
2. Update security documentation
3. Require two reviewers minimum

Model Perspectives:
- GPT-5-mini (for): Improvements are valid
- Claude Haiku (against): Noted concerns about edge cases
- Gemini-2-Flash (neutral): Approved with testing requirements

Estimated cost: ~$4.20
Phase: 2 (Selective Consensus)
```

### Phase 3 Output:

```markdown
🤖 AI Suggestions Available

I've analyzed this PR and created draft PR #147 with suggested improvements.

🔗 View Draft PR: #147

What's included:
✅ Multi-model consensus validation (3 models)
✅ Security checks passed
✅ Patch applied cleanly
✅ Linters/formatters run

Next steps:
1. Review the suggested changes in draft PR #147
2. If approved, add `/approve-ai-patch` label
3. Merge normally (requires human approval)

⚠️ The draft PR requires human review - do not auto-merge.

Estimated cost: ~$6.80
Phase: 3 (Draft PR Creation)
```

---

## 🐛 Troubleshooting

### Workflow doesn't trigger

**Check**:
1. Workflow file exists in `.github/workflows/`
2. YAML syntax is valid: `yamllint .github/workflows/*.yml`
3. Secrets are configured: `gh secret list`
4. PR is not from a fork (Phase 3 disabled for forks)

**Debug**:
```bash
# View workflow runs
gh run list --workflow=claude-review.yml --limit 5

# View specific run logs
gh run view <run-id> --log
```

### "CLAUDE_CODE_OAUTH_TOKEN not found"

```bash
# Verify token in Claude Console: https://claude.com/console
# Add to GitHub:
gh secret set CLAUDE_CODE_OAUTH_TOKEN
# Paste token when prompted
```

### PAL MCP returns 401 Unauthorized

```bash
# Test API key
curl -H "Authorization: Bearer YOUR_KEY" \
     https://your-pal-endpoint.com/api/health

# If invalid, generate new key and update secret:
gh secret set PAL_MCP_API_KEY
```

### Cost too high

1. **Reduce frequency**: Only trigger on `ready_for_review`, not `synchronize`
2. **Use cheaper models**: Edit Phase 2/3 to use mini/haiku/flash variants
3. **Increase size limits**: Only review PRs <500 lines
4. **Enable label-based triggering**: Remove automatic triggers, require `ai-review` label

See [CLAUDE_REVIEW_SETUP.md](./CLAUDE_REVIEW_SETUP.md#cost-optimization-tips) for details.

---

## 📚 Additional Resources

- **Full Setup Guide**: [CLAUDE_REVIEW_SETUP.md](./CLAUDE_REVIEW_SETUP.md)
- **Research Report**: [RESEARCH_REPORT.md](../../RESEARCH_REPORT.md) (if available)
- **Claude Code Docs**: https://code.claude.com/docs
- **PAL MCP GitHub**: https://github.com/BeehiveInnovations/pal-mcp-server
- **GitHub Actions**: https://docs.github.com/actions

---

## 🎯 Recommended Adoption Path

### Week 1-2: Phase 1 Only
- Get familiar with Claude review comments
- Calibrate CLAUDE.md guidelines
- Monitor accuracy and usefulness

### Week 3-4: Add Phase 2
- Enable selective consensus for high-stakes
- Test multi-model validation
- Adjust sensitivity thresholds

### Week 5+: Consider Phase 3
- Only if Phase 1-2 quality is high
- Strong CI/CD with comprehensive tests required
- Start with label-based triggering, not automatic

---

## 🤝 Support

**Issues with this integration?**
1. Check [CLAUDE_REVIEW_SETUP.md](./CLAUDE_REVIEW_SETUP.md) troubleshooting section
2. Review workflow run logs: `gh run view --log`
3. Open an issue in this repository

**Questions about Claude Code?**
- Docs: https://code.claude.com/docs
- Support: support@anthropic.com

**Questions about PAL MCP?**
- GitHub: https://github.com/BeehiveInnovations/pal-mcp-server
- Issues: https://github.com/BeehiveInnovations/pal-mcp-server/issues

---

## 📄 License

See repository LICENSE file.

---

**🎉 Happy reviewing with AI!**

Generated by: Claude Code Research + Implementation
Version: 1.0.0
Last Updated: 2026-03-04
