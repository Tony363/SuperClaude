# SuperClaude Rules Directory

Rules are **always-on project knowledge** automatically loaded into Claude Code's context. Unlike skills (invoked on-demand), rules are persistent — Claude reads them at the start of every conversation without being asked.

## How Rules Work

Files in `.claude/rules/` are:
- Automatically loaded into Claude Code context at session start
- Always available without explicit invocation
- Ideal for project-specific knowledge that should inform every interaction
- Complementary to `CLAUDE.md` (rules handle domain knowledge; CLAUDE.md handles behavior)

## When to Use Rules vs Other Mechanisms

| Mechanism | Use For | Loaded |
|-----------|---------|--------|
| **Rules** (`.claude/rules/`) | Project architecture, conventions, operational knowledge | Always (auto) |
| **CLAUDE.md** | Agent behavior, commands, design principles | Always (auto) |
| **Skills** (`.claude/skills/`) | Structured workflows invoked via `/sc:` commands | On-demand |
| **Agents** (`agents/`) | Persona-based expertise and traits | On-demand |

## Template Rules

This directory ships with template rules. Copy and customize them for your project:

| Template | Purpose | Customize For |
|----------|---------|---------------|
| `architecture-reference.md` | Key components, API routes, data layer | Your project's file structure and endpoints |
| `logging.md` | Log locations, formats, debugging commands | Your logging infrastructure |
| `project-conventions.md` | Team conventions, naming, patterns | Your team's standards |

## Creating Custom Rules

Create a markdown file in `.claude/rules/` with project-specific knowledge:

```markdown
# Rule Title

## Section
- Key facts Claude should always know
- File paths, conventions, patterns
- Operational commands and their purposes
```

**Guidelines:**
- Keep rules concise — they consume context window on every session
- Focus on stable, rarely-changing knowledge (architecture, conventions)
- Avoid duplicating CLAUDE.md content
- Use tables and bullet points for scanability
- Update rules when architecture changes

## Examples of Good Rules

- Database schema and ORM model locations
- API route mount points and key endpoints
- Environment variable documentation
- CI/CD pipeline structure
- External service dependencies and their configs
- Team naming conventions and code patterns
