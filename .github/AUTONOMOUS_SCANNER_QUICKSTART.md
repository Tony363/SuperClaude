# Autonomous Code Scanner - Quick Start Guide

## 🚀 What It Does

The autonomous code scanner runs nightly at 2 AM UTC and:
1. Scans the entire codebase (~505 files)
2. Finds issues: formatting, security, type hints, documentation
3. Creates separate draft PRs for each issue type
4. Enforces $100/night budget with priority system

## 🎯 Quick Commands

### Manual Trigger (Dry Run)
```bash
# Test without creating PRs
gh workflow run autonomous-code-scanner.yml \
  --field dry_run=true
```

### Manual Trigger (Full Scan)
```bash
# Run full scan with PR creation
gh workflow run autonomous-code-scanner.yml
```

### Manual Trigger (Skip Expensive Scanners)
```bash
# Only run P0/P1 (formatting + security)
gh workflow run autonomous-code-scanner.yml \
  --field skip_expensive=true
```

### View Recent Runs
```bash
# List recent workflow runs
gh run list --workflow=autonomous-code-scanner.yml --limit 5

# View specific run details
gh run view <run-id>

# Download artifacts from run
gh run download <run-id>
```

## 📋 Understanding the Output

### GitHub Step Summary (Main Results Page)

After each run, view the step summary:
```bash
gh run view <run-id> --web
# Click "Summary" tab
```

**Example output**:
```markdown
# Autonomous Code Scanner Results

**Scan date**: 2026-03-04 02:15 UTC
**Run ID**: 12345678

## PRs Created

- ✅ **Formatting**: #1234 (23 files)
- ⚠️ **Security**: #1235 (12 findings - NEEDS REVIEW)
- ✅ **Type Hints**: #1236 (42 functions)
- ✅ **Documentation**: #1237 (35 functions)

**Total PRs**: 4 / 10 (budget)

## Cost Summary

| Scanner | Files | Issues | Cost |
|---------|-------|--------|------|
| Formatting | 450 | 23 | $0.50 |
| Security | 450 | 12 | $38.45 |
| Type Hints | 100 | 42 | $18.67 |
| Docs | 80 | 35 | $9.61 |

- **Total spend**: $67.23
- **Budget**: $100
- **Remaining**: $32.77
```

### Artifacts (7-day retention)

Download artifacts for detailed results:
```bash
gh run download <run-id>

# Artifacts available:
# - scannable-files/         (file lists)
# - formatting-changes/      (diff summary)
# - security-findings/       (Bandit results)
# - type-hints-suggestions/  (missing hints)
# - documentation-suggestions/ (missing docs)
```

## 🔍 Reviewing PRs

### 1. Formatting PRs (Low Risk)

**Label**: `auto-formatting`

**Review steps**:
```bash
# 1. Check out PR branch
gh pr checkout <pr-number>

# 2. Review changes
git diff main...HEAD

# 3. Run tests
pytest

# 4. Approve and merge if tests pass
gh pr review <pr-number> --approve
gh pr merge <pr-number> --squash
```

**Expected changes**: Indentation, line length, import sorting, unused imports removed

### 2. Security PRs (High Risk)

**Label**: `needs-human-review`, `critical`

**⚠️ CRITICAL**: Manual review required

**Review steps**:
```bash
# 1. Check out PR branch
gh pr checkout <pr-number>

# 2. Review Bandit findings
cat security-findings/bandit-results.json | jq

# 3. Review high severity findings
cat security-findings/high-severity.json | jq

# 4. For each finding:
#    - Verify it's a true positive
#    - Assess actual risk level
#    - Test suggested fix doesn't break functionality

# 5. Run security tests
pytest tests/test_security/ -v

# 6. Request second reviewer
gh pr review <pr-number> --request-reviewers @username

# 7. Only merge after:
#    - Manual validation of each finding
#    - Security testing
#    - Second reviewer approval
```

**DO NOT auto-merge security PRs**

### 3. Type Hints PRs (Medium Risk)

**Label**: `auto-type-hints`

**Review steps**:
```bash
# 1. Check out PR branch
gh pr checkout <pr-number>

# 2. Review type hints for accuracy
git diff main...HEAD

# 3. Run type checker
mypy app/

# 4. Run tests
pytest

# 5. Approve and merge if checks pass
gh pr review <pr-number> --approve
gh pr merge <pr-number> --squash
```

**Watch for**: Incorrect types, over-specified types, missing imports

### 4. Documentation PRs (Low Risk)

**Label**: `auto-documentation`

**Review steps**:
```bash
# 1. Check out PR branch
gh pr checkout <pr-number>

# 2. Review docstrings for accuracy
git diff main...HEAD

# 3. Check formatting (Google style)
# - Summary line present?
# - Args section correct?
# - Returns section present?

# 4. Approve and merge if documentation clear
gh pr review <pr-number> --approve
gh pr merge <pr-number> --squash
```

## 🛡️ Safety Features

### 1. Protected Files (Never Modified)

These files are **absolutely blocked** from scanning:
- `.github/workflows/*` - Workflow self-modification
- `secrets/*`, `.env*` - Credentials
- `app/auth.py`, `app/auth/*` - Authentication
- `app/pipeline/chat_pipeline.py` - Core pipeline
- `prompts/*` - Proprietary prompts
- `migrations/*` - Database schema

### 2. Draft PRs (Manual Approval Required)

**All PRs created as drafts** - no auto-merge possible

To merge a PR:
```bash
# 1. Review changes
gh pr view <pr-number> --web

# 2. Mark as ready for review
gh pr ready <pr-number>

# 3. Approve
gh pr review <pr-number> --approve

# 4. Merge
gh pr merge <pr-number> --squash
```

### 3. Pre-PR Validation

Before creating any PR, the scanner validates:
- ✅ No secrets in diff (API keys, passwords, tokens)
- ✅ Python syntax valid
- ✅ Diff size reasonable (<5000 lines)

### 4. Budget Enforcement

**Priority system** ensures critical scanners always run:
- **P0** (Formatting): Always runs ($0.50)
- **P1** (Security): Always runs ($2-40)
- **P2** (Type Hints): Conditional ($27-47, needs >$40 remaining)
- **P3** (Documentation): Conditional ($20-35, needs >$30 remaining)

**Maximum cost**: $90 (P0 + P1 + P2, no P3)

## 📊 Monitoring

### Check Workflow Status

```bash
# View recent runs
gh run list --workflow=autonomous-code-scanner.yml --limit 10

# Check if workflow is enabled
gh workflow view autonomous-code-scanner.yml

# View workflow file
gh workflow view autonomous-code-scanner.yml --yaml
```

### View Cost Trends

```bash
# Download all run summaries
for run_id in $(gh run list --workflow=autonomous-code-scanner.yml --json databaseId -q '.[].databaseId' --limit 30); do
  gh run view $run_id --json conclusion,createdAt,displayTitle > "run-$run_id.json"
done

# Parse cost data (requires jq)
# Cost data is in step summary, would need API scraping
```

### Alert on Failures

```bash
# Check if last run failed
LAST_RUN=$(gh run list --workflow=autonomous-code-scanner.yml --limit 1 --json conclusion,databaseId -q '.[0]')
CONCLUSION=$(echo $LAST_RUN | jq -r '.conclusion')

if [ "$CONCLUSION" != "success" ]; then
  echo "⚠️ Last scanner run failed!"
  gh run view $(echo $LAST_RUN | jq -r '.databaseId')
fi
```

## 🔧 Troubleshooting

### "Required secrets missing" Error

**Solution**: Add secrets to repository
```bash
# GITHUB_TOKEN is automatic — no PAT needed for PR creation

# Add ANTHROPIC_API_KEY (for AI features)
gh secret set ANTHROPIC_API_KEY
# Paste key from console.anthropic.com
```

### Budget Exceeded Warning

**Symptom**: P2/P3 scanners skipped, total cost >$90

**Solution**: Expected behavior if security consensus runs. Review step summary:
```bash
gh run view <run-id> --web
# Check "Cost Summary" section
# Verify total cost <$100
```

### No PRs Created

**Symptom**: Workflow completes but no PRs appear

**Solutions**:
1. Check dry run mode: `--field dry_run=false`
2. Check if changes detected: View step summary
3. Check GITHUB_TOKEN write permissions in repo Settings > Actions

### Protected Files Modified

**Symptom**: Workflow attempts to modify `.github/workflows/` or other protected files

**Solution**: Report as critical bug - protected files should be filtered in Job 1
```bash
# Verify protected file filtering
gh run download <run-id> -n scannable-files
grep "\.github/workflows" scannable_python.txt
# Should return NOTHING
```

## 📞 Support

### View Full Workflow Logs

```bash
# View all job logs
gh run view <run-id> --log

# View specific job log
gh run view <run-id> --log --job <job-id>
```

### Report Issues

```bash
# File GitHub issue
gh issue create \
  --title "[Auto-Scanner] Issue description" \
  --label "scanner,bug" \
  --body "Run ID: <run-id>\nIssue: ..."
```

### Disable Scanner (Emergency)

```bash
# Disable cron schedule
gh workflow disable autonomous-code-scanner.yml

# Re-enable later
gh workflow enable autonomous-code-scanner.yml
```

## 📚 Reference

- **Full implementation status**: `.github/AUTONOMOUS_SCANNER_STATUS.md`
- **Workflow file**: `.github/workflows/autonomous-code-scanner.yml`
- **Protected files list**: Job 1 (security-check) in workflow file

---

**Last updated**: 2026-03-03
