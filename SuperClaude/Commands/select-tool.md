name: select-tool
description: "Intelligent MCP tool selection across Zen, Deepwiki, and optional Rube integrations"
category: special
complexity: high
mcp-servers: []
personas: []
---

# /sc:select-tool - Intelligent MCP Tool Selection

## Triggers
- Operations requiring optimal MCP tool selection across Zen, Deepwiki, and Rube (optional)
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
3. **Match**: Compare operation requirements against Zen, Deepwiki, and Rube capabilities
4. **Select**: Choose optimal tool based on scoring matrix and performance requirements
5. **Validate**: Verify selection accuracy and provide confidence metrics

Key behaviors:
- Complexity scoring based on file count, operation type, language, and framework requirements
- Performance assessment evaluating speed vs accuracy trade-offs for optimal selection
- Decision logic matrix with direct mappings and threshold-based routing rules
- Tool capability matching for Zen (multi-model consensus), Deepwiki (documentation intelligence),
  and Rube (cross-application automation)

## MCP Integration
- **Zen MCP**: Optimal for consensus building, cross-model validation, and high-confidence reviews
- **Deepwiki MCP**: Optimal for documentation lookup, framework guidance, and API research
- **Rube MCP (optional)**: Optimal for cross-application automation and SaaS integrations
- **Decision Matrix**: Intelligent routing based on complexity scoring and capability coverage

## Tool Coordination
- **get_current_config**: System configuration analysis for tool capability assessment
- **execute_sketched_edit**: Operation testing and validation for selection accuracy
- **Read/Grep**: Operation context analysis and complexity factor identification
- **Integration**: Automatic selection logic used by refactor, edit, implement, and improve commands

## Key Patterns
- **Direct Mapping**: Architecture analysis → Zen, Automation workflows → Rube, Documentation → Deepwiki
- **Complexity Thresholds**: Score >0.6 → Zen, Score 0.4-0.6 → Rube (when enabled), Score <0.4 → Deepwiki
- **Performance Trade-offs**: Consensus confidence needs → Zen, Automation depth → Rube,
  Documentation depth → Deepwiki
- **Fallback Strategy**: Zen → Rube (if available) → Native tools degradation chain

## Examples

### Complex Refactoring Operation
```
/sc:select-tool "rename function across 10 files" --analyze
# Analysis: High complexity (multi-file, reasoning heavy)
# Selection: Zen MCP (multi-model reasoning and dependency tracing)
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
- Analyze operations and provide optimal tool selection across Zen, Deepwiki, and optional Rube
- Apply complexity scoring based on file count, operation type, and requirements
- Provide sub-100ms decision time with >95% selection accuracy

**Will Not:**
- Override explicit tool specifications when user has clear preference
- Select tools without proper complexity analysis and capability matching
- Compromise performance requirements for convenience or speed
