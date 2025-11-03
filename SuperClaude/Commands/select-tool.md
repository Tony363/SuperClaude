---
name: select-tool
description: "Archived /sc:select-tool command retained for historical reference"
category: legacy
complexity: deprecated
archived: true
requires_evidence: false
personas: []
---
# /sc:select-tool (Archived)

> The modern tool routing flow now lives in `/sc:workflow --delegate`. This
> entry remains for teams auditing historical playbooks.

## Triggers
- Operations requiring optimal MCP tool selection across Zen and optional Rube integrations
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
3. **Match**: Compare operation requirements against Zen and Rube capabilities
4. **Select**: Choose optimal tool based on scoring matrix and performance requirements
5. **Validate**: Verify selection accuracy and provide confidence metrics

Key behaviors:
- Complexity scoring based on file count, operation type, language, and framework requirements
- Performance assessment evaluating speed vs accuracy trade-offs for optimal selection
- Decision logic matrix with direct mappings and threshold-based routing rules
- Tool capability matching for Zen (multi-model consensus) and Rube (cross-application automation)

## Integration Landscape
- **Zen MCP**: Optimal for consensus building, cross-model validation, and high-confidence reviews
- **Rube MCP (optional)**: Optimal for cross-application automation and SaaS integrations when network access is available
- **Repository Knowledge Base**: Default source for framework guidance, documentation lookup, and API research
- **Decision Matrix**: Intelligent routing based on complexity scoring and capability coverage

## Tool Coordination
- **get_current_config**: System configuration analysis for tool capability assessment
- **execute_sketched_edit**: Operation testing and validation for selection accuracy
- **Read/Grep**: Operation context analysis and complexity factor identification
- **Integration**: Automatic selection logic used by refactor, edit, implement, and improve commands

## Key Patterns
- **Direct Mapping**: Architecture analysis → Zen, Automation workflows → Rube, Documentation → Repository knowledge
- **Complexity Thresholds**: Score >0.6 → Zen, Score 0.4-0.6 → Rube (when enabled), Score <0.4 → Native tooling
- **Performance Trade-offs**: Consensus confidence needs → Zen, Automation depth → Rube,
  Documentation depth → Repository knowledge and native analysis
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
# Direct mapping: Documentation research → Repository knowledge base
# Rationale: Leverage curated framework documentation and examples stored locally
```

## Boundaries

**Will:**
- Analyze operations and provide optimal tool selection across Zen and optional Rube
- Apply complexity scoring based on file count, operation type, and requirements
- Provide sub-100ms decision time with >95% selection accuracy

**Will Not:**
- Override explicit tool specifications when user has clear preference
- Select tools without proper complexity analysis and capability matching
- Compromise performance requirements for convenience or speed
