---
name: sc-research
description: Deep research on any topic combining real-time web search (Rube MCP) with multi-model consensus analysis (PAL MCP). Produces structured reports with sourced findings and confidence assessments.
---

# Deep Research Skill

Conduct comprehensive research on any topic by combining real-time web search (via Rube MCP) with multi-model deep analysis and consensus synthesis (via PAL MCP). Produces structured research reports with sourced findings, cross-validated analysis, and confidence assessments.

## Quick Start

```bash
# Quick overview
/sc:research "quantum computing developments" --depth shallow

# Balanced research (default)
/sc:research "Impact of AI regulation on open-source development"

# Exhaustive deep dive saved to file
/sc:research "carbon capture technologies" --depth deep --output reports/carbon.md

# More models for consensus
/sc:research "PostgreSQL vs CockroachDB for write-heavy workloads" --models 4
```

## Behavioral Flow

1. **Parse** - Extract topic, depth, output path, model count
2. **Decompose** - Break topic into 3-7 sub-questions for comprehensive coverage
3. **Discover** - Find web search tools via Rube MCP
4. **Search** - Execute web research in parallel batches
5. **Analyze** - Deep analysis of findings via PAL ThinkDeep
6. **Validate** - Multi-model consensus via PAL Consensus
7. **Report** - Generate structured markdown report
8. **Output** - Save to file or display in console

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--depth` | string | medium | Research depth: shallow, medium, deep |
| `--output` | string | - | Save report to file path |
| `--models` | int | 3 | Number of models for consensus (2-5) |

## Depth Levels

| Depth | Sub-questions | Searches/question | Follow-ups |
|-------|--------------|-------------------|------------|
| shallow | 2-3 | 1 | 0 |
| medium | 3-5 | 1-2 | 1 per gap |
| deep | 5-7 | 2-3 | 2-3 per gap |

## Phase 1: Parse and Plan

Extract topic from arguments. Decompose into sub-questions that provide comprehensive coverage when answered together.

Present research plan before proceeding:

```
Research Topic: <topic>
Depth: <level>
Sub-questions:
  1. <sub-question>
  2. <sub-question>
  ...
Estimated searches: ~N
```

## Phase 2: Discover Search Tools

Use `mcp__rube__RUBE_SEARCH_TOOLS` to find web search and URL extraction tools:

```
RUBE_SEARCH_TOOLS:
  session: { generate_id: true }
  queries:
    - use_case: "search the web for information about a topic"
    - use_case: "scrape and extract content from a web page URL"
```

From the response:
1. **Record session_id** — reuse for all subsequent Rube calls
2. **Check connection status** for returned toolkits
3. If no active connection, call `RUBE_MANAGE_CONNECTIONS` and present auth link
4. **Identify best tools** for web search and URL content extraction
5. If tools return `schemaRef`, call `RUBE_GET_TOOL_SCHEMAS` for full schemas

## Phase 3: Execute Web Research

Batch independent searches in parallel (up to 5 per call) via `RUBE_MULTI_EXECUTE_TOOL`:

**Search query formulation:**
- Rephrase sub-questions as effective search queries
- Use specific, factual language
- For controversial topics, search multiple perspectives explicitly
- Include date qualifiers if recency matters

**After initial searches:**
1. Parse and collect all results
2. Identify most relevant URLs
3. For medium/deep: extract full content from top 3-5 URLs
4. Identify information gaps

**For medium/deep — follow-up searches:**
- Generate refined queries targeting gaps
- Execute follow-up searches
- Extract additional URL content

**Organize raw findings:**

```
Sub-question 1: <question>
  Sources:
    - [Source Title](URL) - Key finding: <summary>
  Gaps: <what's still unclear>

Sub-question 2: <question>
  Sources:
    - ...
```

## Phase 4: Deep Analysis (PAL ThinkDeep)

Use `mcp__pal__thinkdeep` for systematic analysis:

**Step 1 — Analyze:**
- Identify key themes and patterns across sources
- Flag contradictions between sources
- Assess source credibility and biases
- Identify well-supported vs. poorly-supported claims
- Note significant information gaps
- Synthesize preliminary narrative

**Step 2 — Refine:**
- Resolve contradictions with evidence-based reasoning
- Rank findings by confidence (high/medium/low)
- Produce structured outline for final report
- Identify 3-5 most important takeaways

## Phase 5: Multi-Model Consensus (PAL Consensus)

### 5a. Discover Models

Call `mcp__pal__listmodels`. Select top N by score, preferring different providers for diversity.

### 5b. Run Consensus

Use `mcp__pal__consensus` with for/against/neutral stances:

| Stance | Purpose |
|--------|---------|
| for | Evaluate findings charitably, look for strengths |
| against | Critically evaluate, look for weaknesses and gaps |
| neutral | Balanced evaluation, weigh strengths and weaknesses |

### 5c. Incorporate Consensus

Synthesize:
- **Areas of agreement** — high confidence findings
- **Areas of disagreement** — flag for nuance
- **Missing perspectives** — gaps identified by any model
- **Confidence adjustments** — raise/lower based on feedback

## Phase 6: Generate Report

```markdown
# Deep Research Report: <Topic>

**Generated**: <date>
**Depth**: <shallow|medium|deep>
**Sources consulted**: <N>
**Models consulted**: <list>

---

## Executive Summary

<3-5 paragraph synthesis for general audience>

---

## Research Question

<Original topic and how it was decomposed>

---

## Key Findings

### Finding 1: <Title>
**Confidence**: High | Medium | Low
**Consensus**: Agreed | Mixed | Disputed

<Detailed finding with inline source citations>

**Sources**: [Source 1](url), [Source 2](url)

---

## Analysis

### Themes and Patterns
<Cross-cutting themes across sources>

### Contradictions and Debates
<Where sources/models disagreed>

### Information Gaps
<What remains unclear>

---

## Model Consensus

| Model | Stance | Confidence | Key Feedback |
|-------|--------|------------|--------------|
| <model_1> | For | X/10 | <summary> |
| <model_2> | Against | X/10 | <summary> |
| <model_3> | Neutral | X/10 | <summary> |

**Agreement Areas**: <where all models agreed>
**Divergent Views**: <where models differed>

---

## Sources

| # | Title | URL | Relevance |
|---|-------|-----|-----------|
| 1 | <title> | <url> | <contribution> |

---

## Methodology

1. **Web search** via Rube MCP (<N> searches)
2. **Deep analysis** via PAL ThinkDeep
3. **Multi-model consensus** via PAL Consensus (<N> models)
```

## Phase 7: Output

- If `--output <filepath>`: Write report to file, confirm path
- Otherwise: Display full report in console

End with summary:

```
Research complete:
- Topic: <topic>
- Sources: <N> web sources
- Models: <N> reached consensus
- Confidence: <overall assessment>
- Key takeaway: <1-sentence summary>
```

## MCP Integration

### PAL MCP

| Tool | Phase | Purpose |
|------|-------|---------|
| `mcp__pal__thinkdeep` | Analysis | Multi-stage hypothesis testing |
| `mcp__pal__consensus` | Validation | Multi-model cross-validation |
| `mcp__pal__listmodels` | Discovery | Available models for consensus |
| `mcp__pal__challenge` | Validation | Critical thinking on controversial claims |

### Rube MCP

| Tool | Phase | Purpose |
|------|-------|---------|
| `mcp__rube__RUBE_SEARCH_TOOLS` | Discovery | Find search/scraping tools |
| `mcp__rube__RUBE_GET_TOOL_SCHEMAS` | Discovery | Load full schemas if needed |
| `mcp__rube__RUBE_MULTI_EXECUTE_TOOL` | Search | Parallel web searches |
| `mcp__rube__RUBE_MANAGE_CONNECTIONS` | Auth | Connect search integrations |
| `mcp__rube__RUBE_REMOTE_BASH_TOOL` | Processing | Handle large response data |

## Error Handling

| Scenario | Action |
|----------|--------|
| No search tools found | Fall back to `WebFetch` for direct URLs |
| Connection not active | Call `RUBE_MANAGE_CONNECTIONS`, present auth link |
| Search returns no results | Reformulate with broader terms |
| Tool schema missing | Call `RUBE_GET_TOOL_SCHEMAS` first |
| PAL MCP unavailable | Skip consensus, report from web research only |
| ThinkDeep fails | Continue with raw findings |
| Rate limiting | Reduce parallel batch size to 2-3 |

## Guardrails

- Present research plan before executing searches
- Preserve all source URLs for verifiability
- Search multiple perspectives for controversial topics
- `--depth deep` can make 15-25+ API calls — use judiciously
- If Rube unavailable but PAL available, degrade to analysis-only via `WebFetch`

## Tool Coordination

- **WebFetch** - Fallback URL fetching when Rube unavailable
- **Write** - Save report to file
- **Bash** - File operations
- **PAL MCP** - Analysis, consensus, challenge
- **Rube MCP** - Web search, URL extraction
