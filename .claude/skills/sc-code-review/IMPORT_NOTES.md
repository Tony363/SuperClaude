# Code Review Skill Import from Ocelot

**Date**: 2026-03-08
**Source**: `~/Desktop/Ocelot/.claude/commands/code-review.md`
**Target**: `.claude/skills/sc-code-review/SKILL.md`

## Import Summary

Successfully imported and adapted the code-review skill from Ocelot to SuperClaude framework with significant enhancements.

## Key Enhancements Imported

### 1. Interactive Philosophy - "Ask Early, Ask Often"
- Liberally uses `AskUserQuestion` at every decision point
- User directs the review flow instead of receiving fire-and-forget report
- Interactive checkpoints throughout the review process

### 2. Scope Confirmation (Phase 1b)
- Presents summary before review starts
- Options to narrow, expand, or change focus
- User can select specific files/directories to review
- Prevents wasted effort reviewing wrong scope

### 3. Large Diff Handling (Phase 5)
- Interactive strategy selection for diffs > 1000 lines
- Options: chunked review, high-risk only, full pass, or user selection
- Prevents context overflow and improves review quality

### 4. Model Disagreement Resolution (Phase 6a)
- Surfaces disagreements between models
- User adjudicates severity conflicts
- Option to dismiss false positives
- Up to 4 disagreements per question

### 5. Critical/High Findings Validation (Phase 6b)
- User confirms critical/high severity items before finalizing
- Prevents false positives that erode trust
- Uses `mcp__pal__challenge` for adversarial validation
- Unselected items downgraded to Medium with note

### 6. Post-Review Follow-Up (Phase 8)
- Always asks user what to do next
- Options: auto-fix, deep-dive, post to PR, re-review, done
- Auto-fix with severity selection (critical, high, medium, all)
- File-specific deep-dive with max context (-U20)
- Re-review with different model selection

## Structural Changes

### From Ocelot Format
```
.claude/commands/code-review.md
- description: (in frontmatter)
- allowed-tools: (in frontmatter)
- argument-hint: (in frontmatter)
```

### To SuperClaude Format
```
.claude/skills/sc-code-review/SKILL.md
- name: sc-code-review (in frontmatter)
- description: (enhanced in frontmatter)
- allowed-tools: (added AskUserQuestion, Edit, Glob)
```

## Tool Additions

### New Tools Added
- `AskUserQuestion` - Interactive decision points
- `Edit` - Auto-fix issues based on findings
- `Glob` - File discovery for large diffs
- `mcp__pal__challenge` - Adversarial validation of critical findings

### Existing Tools Retained
- `Bash` - Git operations
- `Read` - Source file inspection
- `Grep` - Pattern search
- `mcp__pal__consensus` - Multi-model consensus
- `mcp__pal__codereview` - Single-model fallback
- `mcp__pal__listmodels` - Model discovery

## Behavioral Flow Comparison

### Ocelot (10 steps)
1. Parse Arguments
2. Validate Git State
3. Discover Available Models
4. Gather Git Context
5. Categorize Changed Files
6. Handle Large Diffs
7. Run PAL MCP Consensus
8. Format Output
9. Optional: Post to PR
10. Post-Review Follow-Up

### SuperClaude (13 steps)
1. Parse Arguments
2. Validate Git State
3. **Confirm Scope** (new - interactive)
4. Discover Available Models
5. Gather Git Context
6. Categorize Changed Files
7. **Handle Large Diffs** (enhanced - interactive)
8. Run PAL MCP Consensus
9. **Resolve Disagreements** (new - interactive)
10. **Validate Findings** (new - interactive)
11. Format Output
12. **Follow-up** (enhanced - interactive)
13. Optional: Post to PR

## Philosophy Alignment

Both versions emphasize user direction, but SuperClaude implementation adds:
- More explicit `AskUserQuestion` patterns
- Clearer decision tree for each checkpoint
- Adversarial validation with `mcp__pal__challenge`
- Multi-select for granular control (fix scope, focus areas)

## Compatibility

### Backward Compatible
- All original flags work: `commits`, `--staged`, `--branch`, `--focus`, `--post-pr`
- All original modes: Commits, Staged, Branch comparison
- All original focus areas: security, performance, quality, architecture, full

### New Features
- `--models` flag to control consensus size (2-5 models)
- Interactive scope refinement before review
- User validation of critical/high findings
- Post-review action menu with auto-fix

## Testing Recommendations

1. **Basic flow**: `/sc:code-review` with default 5 commits
2. **Scope confirmation**: Test "Too much" and "Too little" paths
3. **Large diff**: Create 1500+ line diff, test chunking options
4. **Model disagreement**: Review code with known edge cases
5. **Critical findings**: Test validation and challenge workflow
6. **Auto-fix**: Test fix scope selection and Edit integration
7. **PR posting**: Test with and without `--post-pr` flag

## Migration Notes

### For Ocelot Users
If migrating from Ocelot to SuperClaude:
1. Replace `/code-review` with `/sc:code-review`
2. All flags work the same
3. Expect more interactive prompts (can skip with "Looks good — proceed")
4. New auto-fix capability in follow-up menu

### For SuperClaude Users
If you were using the old `sc-code-review`:
1. Same invocation: `/sc:code-review`
2. Much more interactive — be prepared to answer questions
3. Better false positive prevention on critical findings
4. New post-review auto-fix workflow

## Future Enhancements

Potential additions based on Ocelot patterns:
- [ ] Add `--notify` flag for Rube MCP integrations (Slack, Jira)
- [ ] Save review templates for recurring review patterns
- [ ] Multi-repo review support (review changes across multiple repos)
- [ ] Review history tracking and comparison
- [ ] Custom severity definitions per project
- [ ] Integration with issue trackers (auto-create issues from findings)

## Credits

- **Original Author**: Ocelot framework code-review command
- **Adapted By**: SuperClaude framework integration
- **Key Innovation**: Interactive, user-directed review flow with adversarial validation
