name: select-tool
description: "Intelligent MCP tool selection across Sequential, Zen, and Deepwiki integrations"
category: special
complexity: high
mcp-servers: []
personas: []
---

# /sc:select-tool - Intelligent MCP Tool Selection

## Triggers
- Operations requiring optimal MCP tool selection across Sequential, Zen, and Deepwiki
- Meta-system decisions needing complexity analysis and capability matching
- Tool routing decisions requiring performance vs accuracy trade-offs
- Operations benefiting from intelligent tool capability assessment

## Usage
```
/sc:select-tool [operation] [--analyze] [--explain]
```

## Behavioral Flow
1. **Parse**: Analyze operation type, scope, file count, and complexity indicators
2. **Score**: Apply multi-dimensional complexity scoring across various operation factors
3. **Match**: Compare operation requirements against Sequential, Zen, and Deepwiki capabilities
4. **Select**: Choose optimal tool based on scoring matrix and performance requirements
5. **Validate**: Verify selection accuracy and provide confidence metrics

Key behaviors:
- Complexity scoring based on file count, operation type, language, and framework requirements
- Performance assessment evaluating speed vs accuracy trade-offs for optimal selection
- Decision logic matrix with direct mappings and threshold-based routing rules
- Tool capability matching for Sequential (deep reasoning), Zen (multi-model consensus),
  and Deepwiki (documentation intelligence)

## MCP Integration
- **Sequential MCP**: Optimal for deep analysis, hypothesis testing, and multi-step reasoning
- **Zen MCP**: Optimal for consensus building, cross-model validation, and high-confidence reviews
- **Deepwiki MCP**: Optimal for documentation lookup, framework guidance, and API research
- **Decision Matrix**: Intelligent routing based on complexity scoring and capability coverage

## Tool Coordination
- **get_current_config**: System configuration analysis for tool capability assessment
- **execute_sketched_edit**: Operation testing and validation for selection accuracy
- **Read/Grep**: Operation context analysis and complexity factor identification
- **Integration**: Automatic selection logic used by refactor, edit, implement, and improve commands

## Key Patterns
- **Direct Mapping**: Architecture analysis → Sequential, Validation → Zen, Documentation → Deepwiki
- **Complexity Thresholds**: Score >0.6 → Sequential, Score 0.4-0.6 → Zen, Score <0.4 → Deepwiki
- **Performance Trade-offs**: Consensus confidence needs → Zen, Rapid insights → Sequential,
  Documentation depth → Deepwiki
- **Fallback Strategy**: Sequential → Zen → Native tools degradation chain

## Examples

### Complex Refactoring Operation
```
/sc:select-tool "rename function across 10 files" --analyze
# Analysis: High complexity (multi-file, reasoning heavy)
# Selection: Sequential MCP (iterative reasoning and dependency tracing)
```

### Consensus Review
```
/sc:select-tool "verify architectural decision against multiple viewpoints" --explain
# Analysis: Requires cross-model agreement and confidence scoring
# Selection: Zen MCP (multi-model consensus and validation)
```

### Documentation Research
```
/sc:select-tool "determine latest React server component guidance"
# Direct mapping: Documentation research → Deepwiki MCP
# Rationale: Leverage curated framework documentation and examples
```

## Boundaries

**Will:**
- Analyze operations and provide optimal tool selection across Sequential, Zen, and Deepwiki
- Apply complexity scoring based on file count, operation type, and requirements
- Provide sub-100ms decision time with >95% selection accuracy

**Will Not:**
- Override explicit tool specifications when user has clear preference
- Select tools without proper complexity analysis and capability matching
- Compromise performance requirements for convenience or speed
