---
name: sc-evaluate
description: LLM pipeline evaluation with oracle judge scoring. Runs prompts against gold standard datasets, evaluates output quality via LLM-as-judge, and generates scored reports with improvement recommendations.
---

# LLM Evaluation Skill

Run LLM pipeline evaluation against gold standard datasets using oracle LLM-as-judge scoring. Measures output quality across weighted dimensions, identifies weak steps, and suggests prompt improvements.

## Quick Start

```bash
# Full evaluation (all test cases, all steps)
/sc:evaluate

# Quick spot check
/sc:evaluate --cases=case_1,case_2 --steps=1,2,3

# Re-evaluate existing results without re-running pipeline
/sc:evaluate --skip-pipeline

# Generate outputs only (no evaluation)
/sc:evaluate --skip-eval

# Specify judge model
/sc:evaluate --judge-model=gpt-4o

# Dry run to preview plan
/sc:evaluate --dry-run
```

## Behavioral Flow

1. **Discover** - Find evaluation script, gold standards, and prompt files
2. **Configure** - Parse scope (cases, steps, model overrides)
3. **Execute** - Run pipeline on gold standard inputs
4. **Evaluate** - Score outputs against gold standards via LLM-as-judge
5. **Analyze** - Identify weak steps, dimension breakdowns, patterns
6. **Recommend** - Suggest specific prompt improvements for low-scoring steps
7. **Report** - Generate JSON + Markdown evaluation reports

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--cases` | string | all | Comma-separated test case IDs to evaluate |
| `--steps` | string | all | Comma-separated step numbers to evaluate |
| `--model` | string | env default | Override pipeline model |
| `--judge-model` | string | env default | Override judge/oracle model |
| `--skip-pipeline` | bool | false | Skip pipeline execution, evaluate existing results |
| `--skip-eval` | bool | false | Run pipeline only, skip evaluation |
| `--dry-run` | bool | false | Preview execution plan without API calls |
| `--output` | string | `eval_runs/YYYYMMDD_HHMMSS/` | Output directory |
| `--concurrency` | int | 5 | Parallel judge calls |
| `--threshold` | int | 70 | Score threshold for "needs improvement" |

## Phase 1: Discover Project Structure

Locate evaluation components:

| Component | Common Locations | Purpose |
|-----------|-----------------|---------|
| Evaluation script | `scripts/run_eval.py`, `eval/run.py` | Orchestrates pipeline + scoring |
| Gold standards | `gold_standards/`, `test_data/`, `fixtures/` | Expected outputs |
| Prompts | `prompts/`, `templates/` | Pipeline prompt templates |
| Rubrics | `eval/rubrics.py`, `config/rubrics.yaml` | Scoring dimensions and weights |

If no standard structure found, ask the user to specify paths.

## Phase 2: Configure Scope

Parse arguments to determine:
- Which test cases to run (default: all discovered)
- Which pipeline steps to evaluate (default: all)
- Model overrides for pipeline and judge
- Output directory (default: timestamped)

Create output directory:
```bash
OUTPUT_DIR="${output:-eval_runs/$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$OUTPUT_DIR"
```

## Phase 3: Execute Pipeline

Run the pipeline on gold standard inputs:

```bash
python <eval_script> \
  --output "$OUTPUT_DIR" \
  --verbose \
  [--cases CASES] \
  [--steps STEPS] \
  [--model MODEL] \
  [--skip-pipeline] \
  [--skip-eval]
```

**API call estimation:**
- Pipeline: steps x cases API calls
- Evaluation: scored_dimensions x cases judge calls

For quick validation, suggest running on 1-2 cases with 2-3 steps first.

## Phase 4: Evaluate with LLM-as-Judge

For each step output, compare against gold standard using oracle LLM-as-judge:

**Evaluation dimensions (customizable per project):**

| Dimension | What It Measures |
|-----------|-----------------|
| Content Agreement | Do outputs cover the same key points? |
| Structure Match | Is the organization/format similar? |
| Detail Accuracy | Are specific claims and data correct? |
| Completeness | Are all expected elements present? |

Each dimension has a weight (0.0-1.0) summing to 1.0 per step.

## Phase 5: Analyze Results

Read and analyze evaluation report:

1. **Overall similarity score** across all cases and steps
2. **Per-step scores** — highlight any below threshold (default: 70/100)
3. **Per-case scores** — identify consistently weak test cases
4. **Dimension breakdowns** for weak steps

**Score interpretation:**

| Score Range | Assessment | Action |
|-------------|-----------|--------|
| 85-100 | Excellent | No changes needed |
| 70-84 | Good | Minor tuning possible |
| 60-69 | Needs improvement | Prompt revision recommended |
| Below 60 | Poor | Prompt likely needs rewrite |

## Phase 6: Recommend Improvements

For each step scoring below threshold:

1. **Read the current prompt** template
2. **Read the gold standard output** (expected)
3. **Read the pipeline output** (actual)
4. **Compare and identify gaps:**
   - Missing instructions that gold standard captures
   - Overly broad instructions causing divergent output
   - Format/structure differences
   - Specificity gaps

Present actionable suggestions:
```markdown
### Step N: <step_name> (Score: XX/100)

**Weakest Dimension**: <dimension> (XX/100)

**Gap Analysis**:
- Gold standard includes <X> but prompt doesn't instruct it
- Output format diverges: gold uses <format>, output uses <other>

**Suggested Prompt Changes**:
1. Add instruction: "<specific instruction>"
2. Clarify format: "<format guidance>"
3. Add example: "<example output snippet>"
```

## Output Structure

```
eval_runs/YYYYMMDD_HHMMSS/
  results/                    # Pipeline outputs
    case_1/
      step_01_<name>.md
      step_02_<name>.md
      ...
    case_2/
      ...
  evaluation/                 # Judge scores
    evaluation_report.json
    evaluation_report.md
    per_step_scores.csv
    per_case_scores.csv
```

## MCP Integration

### PAL MCP (Optional)

| Tool | When | Purpose |
|------|------|---------|
| `mcp__pal__thinkdeep` | Low-scoring steps | Deep analysis of why outputs diverge |
| `mcp__pal__consensus` | Prompt revision | Multi-model validation of proposed changes |
| `mcp__pal__codereview` | Eval script | Review evaluation pipeline code |

### Rube MCP (Optional)

| Tool | When | Purpose |
|------|------|---------|
| `mcp__rube__RUBE_REMOTE_WORKBENCH` | Large eval runs | Process results in Python sandbox |
| `mcp__rube__RUBE_MULTI_EXECUTE_TOOL` | Notifications | Report results to Slack/email |

## Error Handling

| Scenario | Action |
|----------|--------|
| No eval script found | Ask user for script path |
| No gold standards found | Ask user for gold standard directory |
| API rate limit | Reduce concurrency, add delays |
| Pipeline step fails | Log error, continue with remaining steps |
| Judge returns invalid score | Retry once, then flag for manual review |
| Output directory exists | Append timestamp suffix |

## Guardrails

- Always pass `--verbose` for progress visibility
- Warn about API call counts before full runs
- Suggest quick validation on subset before full evaluation
- Preserve all intermediate outputs for debugging
- Never modify gold standard files

## Tool Coordination

- **Bash** - Run evaluation scripts
- **Read** - Inspect prompts, gold standards, outputs, reports
- **Write** - Generate reports
- **Grep** - Search for patterns in outputs
- **PAL MCP** - Deep analysis of score gaps
