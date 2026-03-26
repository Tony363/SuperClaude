#!/bin/bash
# Claude Review + PAL MCP Integration Setup Script
# Automates the setup process for AI code review workflows

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

prompt() {
    echo -e "${BLUE}?${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    info "Checking prerequisites..."

    # Check if gh CLI is installed
    if ! command -v gh &> /dev/null; then
        error "GitHub CLI (gh) is not installed"
        echo "Install from: https://cli.github.com"
        exit 1
    fi
    success "GitHub CLI found"

    # Check if logged in
    if ! gh auth status &> /dev/null; then
        error "Not logged into GitHub CLI"
        echo "Run: gh auth login"
        exit 1
    fi
    success "GitHub CLI authenticated"

    # Check if in git repo
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        error "Not in a git repository"
        exit 1
    fi
    success "Git repository detected"

    # Check if GitHub remote exists
    if ! git remote get-url origin &> /dev/null; then
        error "No GitHub remote 'origin' found"
        exit 1
    fi
    success "GitHub remote found"
}

# Select phase
select_phase() {
    echo ""
    prompt "Select which phase to install:"
    echo "  1) Phase 1 - Comment Only (Safest, $1.50/PR, 2-5 min)"
    echo "  2) Phase 2 - Selective Consensus ($1.50-$5/PR, 5-13 min)"
    echo "  3) Phase 3 - Draft PR Creation ($3-$8/PR, 8-20 min)"
    echo "  4) All phases (for evaluation)"
    echo ""
    read -p "Enter choice [1-4]: " phase_choice

    case $phase_choice in
        1)
            PHASE="phase1"
            PHASE_NAME="Phase 1 (Comment Only)"
            ;;
        2)
            PHASE="phase2"
            PHASE_NAME="Phase 2 (Selective Consensus)"
            ;;
        3)
            PHASE="phase3"
            PHASE_NAME="Phase 3 (Draft PR Creation)"
            ;;
        4)
            PHASE="all"
            PHASE_NAME="All Phases"
            ;;
        *)
            error "Invalid choice"
            exit 1
            ;;
    esac

    success "Selected: $PHASE_NAME"
}

# Configure secrets
configure_secrets() {
    echo ""
    info "Configuring GitHub Secrets..."

    # Claude OAuth Token (required for all phases)
    if ! gh secret list | grep -q "CLAUDE_CODE_OAUTH_TOKEN"; then
        warning "CLAUDE_CODE_OAUTH_TOKEN not found"
        echo ""
        echo "📋 Steps to get Claude OAuth token:"
        echo "  1. Visit https://claude.com/console"
        echo "  2. Go to API Keys section"
        echo "  3. Create new OAuth token"
        echo "  4. Copy the token"
        echo ""
        read -p "Paste your Claude OAuth token: " claude_token

        if [ -z "$claude_token" ]; then
            error "Token cannot be empty"
            exit 1
        fi

        echo "$claude_token" | gh secret set CLAUDE_CODE_OAUTH_TOKEN
        success "CLAUDE_CODE_OAUTH_TOKEN configured"
    else
        success "CLAUDE_CODE_OAUTH_TOKEN already configured"
    fi

    # PAL MCP credentials (required for Phase 2 & 3)
    if [ "$PHASE" == "phase2" ] || [ "$PHASE" == "phase3" ] || [ "$PHASE" == "all" ]; then
        if ! gh secret list | grep -q "PAL_MCP_API_KEY"; then
            warning "PAL_MCP_API_KEY not found"
            read -p "Do you have a PAL MCP API key? [y/n]: " has_pal

            if [ "$has_pal" == "y" ]; then
                read -p "Paste your PAL MCP API key: " pal_key
                echo "$pal_key" | gh secret set PAL_MCP_API_KEY
                success "PAL_MCP_API_KEY configured"

                read -p "Enter PAL MCP endpoint URL (or press Enter for default): " pal_endpoint
                if [ -n "$pal_endpoint" ]; then
                    echo "$pal_endpoint" | gh secret set PAL_MCP_ENDPOINT
                    success "PAL_MCP_ENDPOINT configured"
                fi
            else
                warning "PAL MCP not configured - Phase 2/3 consensus features will not work"
                echo "See setup guide for PAL MCP setup instructions"
            fi
        else
            success "PAL_MCP_API_KEY already configured"
        fi
    fi

    # PAT Token (required for Phase 3)
    if [ "$PHASE" == "phase3" ] || [ "$PHASE" == "all" ]; then
        if ! gh secret list | grep -q "PAT_TOKEN"; then
            warning "PAT_TOKEN not found (required for PR creation)"
            echo ""
            echo "📋 Steps to create PAT token:"
            echo "  1. Visit https://github.com/settings/tokens"
            echo "  2. Generate new token (classic)"
            echo "  3. Required scopes: repo, workflow"
            echo "  4. Copy the token"
            echo ""
            read -p "Paste your PAT token (or press Enter to skip): " pat_token

            if [ -n "$pat_token" ]; then
                echo "$pat_token" | gh secret set PAT_TOKEN
                success "PAT_TOKEN configured"
            else
                warning "PAT_TOKEN not configured - Phase 3 PR creation will not work"
            fi
        else
            success "PAT_TOKEN already configured"
        fi
    fi
}

# Install workflow files
install_workflows() {
    echo ""
    info "Installing workflow files..."

    # Create workflows directory if it doesn't exist
    mkdir -p .github/workflows

    case $PHASE in
        phase1)
            cp .github/workflows/claude-review-phase1.yml .github/workflows/claude-review.yml
            success "Installed Phase 1 workflow"
            ;;
        phase2)
            cp .github/workflows/claude-review-phase2.yml .github/workflows/claude-review.yml
            success "Installed Phase 2 workflow"
            ;;
        phase3)
            cp .github/workflows/claude-review-phase3.yml .github/workflows/claude-review.yml
            success "Installed Phase 3 workflow"
            ;;
        all)
            # Keep all phase files with their original names
            success "All phase workflows available"
            ;;
    esac

    # Install cost monitor
    if [ -f .github/workflows/ai-review-cost-monitor.yml ]; then
        success "Cost monitor workflow available"
    else
        warning "Cost monitor workflow not found"
    fi
}

# Install Claude GitHub App
install_github_app() {
    echo ""
    info "Installing Claude GitHub App..."

    REPO_FULL=$(gh repo view --json nameWithOwner -q .nameWithOwner)

    echo ""
    echo "📱 Install Claude GitHub App:"
    echo "  1. Visit: https://github.com/apps/claude/installations/new"
    echo "  2. Select repository: $REPO_FULL"
    echo "  3. Grant permissions:"
    echo "     - Read: Contents, Issues, Pull Requests"
    echo "     - Write: Contents (Phase 3), Issues, Pull Requests"
    echo ""
    read -p "Press Enter after installing the app..."

    success "Claude GitHub App installation complete"
}

# Create CLAUDE.md template
create_claude_md() {
    echo ""
    prompt "Create CLAUDE.md file with coding guidelines? [y/n]: "
    read create_md

    if [ "$create_md" == "y" ]; then
        if [ -f CLAUDE.md ]; then
            warning "CLAUDE.md already exists, skipping"
        else
            cat > CLAUDE.md <<'EOF'
# Code Review Guidelines

## Project Standards

- **Language**: [Specify primary language]
- **Style Guide**: [PEP 8, Airbnb, Google Style Guide, etc.]
- **Test Coverage**: Minimum 80%
- **Documentation**: All public APIs must be documented

## Security Requirements

- ❌ No hardcoded secrets or API keys
- ✅ All user input must be validated
- ✅ Use parameterized queries (prevent SQL injection)
- ✅ Follow OWASP Top 10 guidelines
- ✅ Implement proper error handling (no stack traces to users)

## Code Quality Standards

- **Functions**: Max 50 lines, single responsibility
- **Complexity**: Cyclomatic complexity < 10
- **Naming**: Clear, descriptive, consistent with codebase
- **Comments**: Focus on "why", not "what"

## Testing Requirements

- **Unit tests**: Required for all new functions
- **Integration tests**: Required for API endpoints
- **Edge cases**: Test boundary conditions
- **Error cases**: Test error handling paths

## Review Focus Areas

When reviewing code, prioritize:

1. **Security vulnerabilities** (highest priority)
2. **Correctness and logic errors**
3. **Performance issues**
4. **Code maintainability**
5. **Test coverage**

## Architectural Principles

[Add your team's specific architectural principles here]

- Separation of concerns
- DRY (Don't Repeat Yourself)
- SOLID principles
- [Add more as needed]

## Common Issues to Flag

- Missing error handling
- Potential null pointer exceptions
- Race conditions in concurrent code
- Memory leaks
- Inefficient algorithms
- Overly complex logic

## Exemptions

The following files/patterns should not be modified by AI:

- `.github/workflows/*` - Workflow files
- `secrets/` - Secret management
- `.env*` - Environment configuration
- Critical authentication logic

---

**Note**: These guidelines help AI code review focus on what matters most to your team.
Update this file as your standards evolve.
EOF
            success "Created CLAUDE.md template"
            info "Edit CLAUDE.md to match your team's standards"
        fi
    fi
}

# Test the setup
test_setup() {
    echo ""
    prompt "Create a test PR to verify the setup? [y/n]: "
    read create_test

    if [ "$create_test" == "y" ]; then
        info "Creating test PR..."

        # Create test branch
        TEST_BRANCH="test/ai-review-setup-$(date +%s)"
        git checkout -b "$TEST_BRANCH"

        # Create test file
        echo "# AI Review Test" > test-ai-review.md
        echo "This is a test file to verify AI review integration." >> test-ai-review.md
        echo "Created: $(date)" >> test-ai-review.md

        git add test-ai-review.md
        git commit -m "test: verify AI review integration"
        git push origin "$TEST_BRANCH"

        # Create PR
        PR_URL=$(gh pr create \
            --title "Test: AI Review Integration" \
            --body "Automated test PR to verify AI review setup. Should trigger Claude review workflow." \
            --head "$TEST_BRANCH")

        success "Test PR created: $PR_URL"
        info "Check the PR for AI review comment"
        info "You can delete the PR after verification"
    fi
}

# Print summary
print_summary() {
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    success "Setup Complete! 🎉"
    echo ""
    echo "📋 What's been configured:"
    echo "  - Workflow files installed"
    echo "  - GitHub secrets configured"
    echo "  - Claude GitHub App installed"
    echo ""
    echo "📚 Next steps:"
    echo "  1. Review .github/workflows/CLAUDE_REVIEW_SETUP.md"
    echo "  2. Customize CLAUDE.md for your team"
    echo "  3. Create a test PR to verify integration"
    echo "  4. Monitor costs with cost-monitor workflow"
    echo ""
    echo "💡 Usage:"
    if [ "$PHASE" == "phase1" ] || [ "$PHASE" == "all" ]; then
        echo "  - Phase 1: Automatic on PR open/ready_for_review"
        echo "    Comment '@claude-review' for manual trigger"
    fi
    if [ "$PHASE" == "phase2" ] || [ "$PHASE" == "all" ]; then
        echo "  - Phase 2: Add 'ai-consensus' label for multi-model review"
    fi
    if [ "$PHASE" == "phase3" ] || [ "$PHASE" == "all" ]; then
        echo "  - Phase 3: Draft PRs created automatically (requires approval)"
    fi
    echo ""
    echo "🔗 Resources:"
    echo "  - Setup guide: .github/workflows/CLAUDE_REVIEW_SETUP.md"
    echo "  - Cost monitoring: Actions → AI Review Cost Monitor"
    echo "  - Claude docs: https://code.claude.com/docs"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

# Main execution
main() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Claude Review + PAL MCP Integration Setup"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    check_prerequisites
    select_phase
    install_github_app
    configure_secrets
    install_workflows
    create_claude_md
    test_setup
    print_summary
}

# Run main function
main
