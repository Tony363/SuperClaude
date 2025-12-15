#!/bin/bash
# SuperClaude Branch Protection Setup Script
# Run this script after installing GitHub CLI: brew install gh (macOS) or see https://cli.github.com/
# Prerequisites: gh auth login

set -e

OWNER="Tony363"
REPO="SuperClaude"

echo "🔒 Setting up branch protection for $OWNER/$REPO..."

# Protect main branch
echo "📌 Protecting main branch..."
gh api "repos/$OWNER/$REPO/branches/main/protection" \
  -X PUT \
  -H "Accept: application/vnd.github+json" \
  --input - << 'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Quality Gate",
      "Test (Python 3.11)",
      "Coverage Gate (80%)",
      "CI Status"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF

echo "✅ Main branch protected!"

# Optionally protect develop branch (less strict)
if gh api "repos/$OWNER/$REPO/branches/develop" &>/dev/null; then
  echo "📌 Protecting develop branch..."
  gh api "repos/$OWNER/$REPO/branches/develop/protection" \
    -X PUT \
    -H "Accept: application/vnd.github+json" \
    --input - << 'EOF'
{
  "required_status_checks": {
    "strict": false,
    "contexts": [
      "Quality Gate",
      "Test (Python 3.11)"
    ]
  },
  "enforce_admins": false,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false
}
EOF
  echo "✅ Develop branch protected!"
else
  echo "ℹ️  No develop branch found, skipping..."
fi

echo ""
echo "🎉 Branch protection setup complete!"
echo ""
echo "Summary of protections on main:"
echo "  • PRs required for all changes (no direct pushes)"
echo "  • 1 approval required"
echo "  • Stale reviews dismissed on new commits"
echo "  • Code owner review required"
echo "  • Status checks required: Quality Gate, Test (3.11), Coverage Gate"
echo "  • Branches must be up-to-date before merging"
echo "  • Admins ARE included (no bypass)"
echo "  • Linear history enforced"
echo "  • Force pushes blocked"
echo ""
echo "⚠️  Emergency bypass procedure:"
echo "  1. Go to Settings → Branches → main → Edit"
echo "  2. Temporarily uncheck 'Include administrators'"
echo "  3. Make emergency fix"
echo "  4. Re-enable 'Include administrators'"
echo "  5. Document the bypass in an issue"
