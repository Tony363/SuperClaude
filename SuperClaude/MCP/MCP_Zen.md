# Zen MCP Multi-Model Orchestration

**Purpose**: Orchestrate multiple AI models for consensus, deep thinking, and validation

## Model Preferences

### Tool-Specific Configuration

**thinkdeep**
- **Preferred Model**: GPT-5 (50K tokens) / Gemini-2.5-pro (>400K tokens)
- **Primary Fallback**: Claude Opus 4.1
- **Context Routing**: Auto-switches to Gemini-2.5-pro for long context scenarios
- **Purpose**: Multi-angle analysis and hypothesis testing
- **Usage**: `--thinkdeep` or via mcp__zen__thinkdeep

**consensus**
- **Ensemble**: [GPT-5, Claude Opus 4.1, GPT-4.1] / [Gemini-2.5-pro, GPT-4.1, GPT-5] (>400K tokens)
- **Quorum**: 2 models must agree
- **Token Budget**: 30K per model (90K total) / 200K per model for long context
- **Context Routing**: Switches ensemble composition for long context scenarios
- **Purpose**: Multi-model validation and agreement
- **Usage**: `--consensus` or via mcp__zen__consensus

**planner**
- **Preferred Model**: GPT-5 (50K tokens)
- **Primary Fallback**: Claude Opus 4.1
- **Purpose**: Strategic multi-step planning
- **Usage**: `--plan` or via mcp__zen__planner

**debug**
- **Preferred Model**: GPT-5 (50K tokens)
- **Primary Fallback**: Claude Opus 4.1
- **Purpose**: Root cause analysis and debugging
- **Usage**: `--debug` or via mcp__zen__debug

**codereview**
- **Preferred Model**: GPT-5 (50K tokens)
- **Primary Fallback**: Claude Opus 4.1
- **Purpose**: Comprehensive code quality analysis
- **Usage**: `--zen-review` or via mcp__zen__codereview

**precommit**
- **Preferred Model**: GPT-5 (50K tokens)
- **Primary Fallback**: Claude Opus 4.1
- **Purpose**: Pre-commit validation and checks
- **Usage**: `--precommit` or via mcp__zen__precommit

**challenge**
- **Preferred Model**: GPT-5
- **Primary Fallback**: Claude Opus 4.1
- **Purpose**: Critical thinking and assumption challenging
- **Usage**: Automatically triggered on disagreement

## Token Budgets

| Operation | Default | Maximum | Per Model (Ensemble) |
|-----------|---------|---------|---------------------|
| thinkdeep | 50K | 50K | N/A |
| consensus | 90K total | 150K | 30K-50K |
| planner | 50K | 50K | N/A |
| debug | 50K | 50K | N/A |
| codereview | 50K | 50K | N/A |
| chat | 30K | 50K | N/A |

## Fallback Strategy

### Primary Chain
1. **GPT-5**: First choice for all deep thinking operations
2. **Claude Opus 4.1**: Primary fallback with equivalent depth
3. **GPT-4.1**: Secondary fallback when both unavailable
4. **Degradation**: Reduce to single model if ensemble unavailable

### Availability Checking
- TTL-based backoff: 60 seconds for failed models
- Rate limit detection: Auto-switch on 429 errors
- Cost monitoring: Fallback when approaching limits

### Degradation Modes
- **Full Ensemble**: All 3 models available
- **Partial Ensemble**: 2 models available (maintain quorum)
- **Single Model**: Fallback to best available with increased depth
- **Emergency Mode**: Claude Opus 4.1 as ultimate fallback

## Usage Examples

### Deep Thinking with GPT-5
```bash
# Automatic GPT-5 selection
--thinkdeep --think 3

# Force specific model
--thinkdeep --model gpt-5

# With fallback disabled
SC_DISABLE_GPT5=true --thinkdeep  # Uses Opus 4.1
```

### Multi-Model Consensus
```bash
# Standard consensus (3 models)
--consensus

# Extended consensus with custom ensemble
--consensus --models "gpt-5,claude-opus-4.1,gpt-4o,gpt-4.1"

# Consensus with specific quorum
--consensus --quorum 3
```

### Planning Mode
```bash
# Auto-selects GPT-5 with 50K tokens
--plan --think 3

# Strategic planning with introspection
--plan --introspect --think 3
```

### Code Review
```bash
# Comprehensive review with GPT-5
--zen-review --think 3

# Quick review with standard depth
--zen-review --think 2

# Large codebase review with Gemini-2.5-pro (auto-triggered)
--zen-review --extended-context --bulk-analysis
```

### Long Context Operations
```bash
# Bulk file analysis (auto-switches to Gemini-2.5-pro)
--thinkdeep --bulk-analysis src/ docs/ tests/

# Extended documentation processing
--consensus --extended-context --think 3

# Large codebase architecture review
--zen-review --extended-context "Analyze entire codebase architecture"

# Force Gemini for long context
--model gemini-2.5-pro --thinkdeep
```

## Integration with Modes

### Introspection Mode
- Auto-activates GPT-5 for meta-cognitive analysis
- Uses full 50K token budget for deep reflection
- Falls back to Opus 4.1 for comparable depth

### Plan Mode
- Triggers GPT-5 for strategic thinking
- Leverages planner tool with 50K tokens
- Validates plans through consensus when critical

### Task Management
- Uses GPT-5 for complex task breakdown
- Delegates to appropriate models based on task type
- Maintains model preferences across delegation

## Configuration Override

### Environment Variables
```bash
# Force specific model globally
export SC_FORCE_MODEL=gpt-5

# Disable GPT-5 (force fallback)
export SC_DISABLE_GPT5=true

# Override token limit
export SC_MAX_TOKENS=50000

# Set default think level
export SC_DEFAULT_THINK_LEVEL=3
```

### CLI Flags
```bash
# Force model for session
--model gpt-5

# Exclude specific models
--deny-model gpt-4o --deny-model gpt-4o-mini

# Override token budget
--tokens 50000
```

## Best Practices

1. **Use --think 3** for maximum GPT-5 utilization
2. **Let auto-routing handle model selection** unless specific needs
3. **Monitor costs** with consensus operations (3x model usage)
4. **Leverage fallbacks** - Opus 4.1 provides excellent alternative
5. **Batch operations** when using consensus for efficiency

## Context-Aware Model Routing

The framework intelligently routes requests based on context size and complexity:

### Standard Operations (≤400K tokens)
**Primary Chain**: GPT-5 → Claude Opus 4.1 → GPT-4.1
- Most deep thinking, planning, and analysis operations
- Optimized for reasoning quality and response speed

### Long Context Ingestion (>400K tokens)
**Primary Chain**: Gemini-2.5-pro → GPT-4.1 → GPT-5 (chunked)
- Bulk file analysis (>50 files)
- Large codebase reviews
- Extended documentation processing
- Multi-file batch operations

### Automatic Triggers for Long Context Mode
- Total token count exceeds 400K
- File count exceeds 50 in single operation
- Explicit flags: `--extended-context`, `--bulk-analysis`
- Large document processing (single files >200K tokens)

## Model Capabilities Matrix

| Model | Reasoning | Speed | Cost | Context | Best For |
|-------|-----------|-------|------|---------|----------|
| GPT-5 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | $$$ | 400K | Deep thinking, planning |
| Gemini-2.5-pro | ⭐⭐⭐⭐ | ⭐⭐⭐ | $$ | 2M | **Long context ingestion, bulk analysis** |
| Claude Opus 4.1 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | $$ | 200K | Fallback, validation |
| GPT-4.1 | ⭐⭐⭐⭐ | ⭐⭐⭐ | $$ | 1M | Large context tasks |
| GPT-4o | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | $ | 128K | Standard operations |

## Troubleshooting

**GPT-5 not selecting**
- Check availability: `mcp__zen__listmodels`
- Verify not disabled: `echo $SC_DISABLE_GPT5`
- Check rate limits and backoff status

**Fallback to unexpected model**
- Review models.yaml configuration
- Check deny list and overrides
- Verify model availability status

**Token limit issues**
- Ensure request under 50K limit
- Check model's context window
- Consider chunking for large operations