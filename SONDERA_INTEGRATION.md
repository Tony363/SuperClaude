# Sondera Security Layer Integration

## Overview

Sondera is an **optional** security harness for SuperClaude that provides LLM-powered policy enforcement for Claude Code tool executions. It operates as a separate service that validates tool calls before they execute.

## Architecture

```
┌─────────────────┐
│  Claude Code    │
│  + SuperClaude  │
└────────┬────────┘
         │ Tool call
         ▼
┌─────────────────┐
│  Hook (Rust)    │ ◄─── .claude/settings.local.json
│  Claude Code    │
└────────┬────────┘
         │ Unix Socket
         ▼
┌─────────────────┐
│ Sondera Harness │
│   - Intent LLM  │ (ministral-3:14b-cloud)
│   - Safety LLM  │ (gpt-oss-safeguard:20b)
│   - Cedar       │ (policy enforcement)
└────────┬────────┘
         │
         ▼
    Allow/Deny
```

## Design Philosophy: Why Optional?

### Current Approach: Modular Security

SuperClaude treats Sondera as an **optional plugin** rather than a bundled component. This design choice reflects several key principles:

#### 1. Flexibility Over Security-by-Default

**Rationale:**
- Different users have different trust models and security requirements
- Development environments often need unrestricted access
- Research and experimentation benefit from low-friction workflows

**Tradeoff:** Users must explicitly opt-in to security, which means some deployments may lack protection.

#### 2. Simplicity Over Comprehensiveness

**Rationale:**
- Sondera has complex dependencies (Rust, Ollama, 2 LLM models, Cedar)
- Adding ~30GB of model dependencies to every installation is excessive
- Not all platforms support Unix sockets (Windows limitations)

**Tradeoff:** Production deployments require additional setup steps.

#### 3. Performance Over Safety

**Rationale:**
- LLM validation adds significant latency to every tool call
- Development workflows benefit from immediate feedback
- Researchers need fast iteration cycles

**Tradeoff:** Unvalidated tool calls can execute dangerous operations.

## Alternative Design: Security-by-Default

An alternative approach would bundle Sondera with SuperClaude:

### Arguments For:

1. **Consistent Security Posture**
   - All installations protected by default
   - Reduces risk of misconfiguration
   - Aligns with modern "secure by default" practices

2. **Enterprise Readiness**
   - Production deployments need security
   - Compliance requirements often mandate validation
   - Audit logging built-in

3. **Lower Cognitive Load**
   - Users don't need to remember to add security
   - One installation path (simpler documentation)
   - Security updates bundled with framework updates

### Arguments Against:

1. **Complex Dependencies**
   - Requires Rust toolchain
   - Requires Ollama + 2 models (~30GB)
   - Platform constraints (Unix sockets)

2. **Performance Overhead**
   - Every tool call validated by 2 LLMs
   - Significant latency impact
   - Resource consumption on every operation

3. **Use Case Diversity**
   - Research users don't need enterprise security
   - Development environments prioritize speed
   - Teaching/learning contexts need simplicity

## Current Implementation

### Installation Paths

SuperClaude provides two documented installation paths:

#### 1. Quick Start (Default)
```bash
git clone https://github.com/Tony363/SuperClaude.git
cd SuperClaude
```
- **Use Case:** Development, research, learning
- **Security:** Trust-based (no validation)
- **Performance:** Fast (no overhead)
- **Setup Time:** < 5 minutes

#### 2. Production Setup (With Sondera)
```bash
./install-with-sondera.sh
```
- **Use Case:** Production, compliance, high-security environments
- **Security:** Policy-enforced validation across all 14 lifecycle events (PreToolUse, PostToolUse, UserPromptSubmit, SessionStart, etc.)
- **Performance:** Slower (LLM overhead)
- **Setup Time:** 20-30 minutes (includes model downloads)

### Testing
```bash
./test-sondera-integration.sh
```

Verifies:
- Hook configuration (`.claude/settings.local.json`)
- Harness service running (Unix socket)
- Model availability
- End-to-end connectivity

## When to Use Sondera

### ✅ Use Sondera When:

- **Production deployments** - Operating on live systems
- **Compliance requirements** - SOC2, HIPAA, PCI-DSS
- **Shared infrastructure** - Multiple users, teams, or tenants
- **High-value targets** - Financial systems, healthcare, critical infrastructure
- **Untrusted operators** - Automated systems, third-party access

### ❌ Skip Sondera When:

- **Local development** - Trusted developer workstation
- **Research and experimentation** - Academic, exploratory work
- **Learning environments** - Educational contexts, tutorials
- **Performance-critical** - Scenarios where latency matters
- **Resource-constrained** - Limited disk space, RAM, or compute

## Future Considerations

### Potential Improvements

1. **Lightweight Mode**
   - Single-model validation (faster)
   - Cached policy decisions (reduce LLM calls)
   - Configurable validation depth

2. **Platform Support**
   - Windows compatibility (TCP sockets instead of Unix)
   - Docker image (bundled dependencies)
   - Cloud-native deployment (separate service)

3. **Hybrid Approach**
   - Risk-based validation (validate only dangerous operations)
   - Learning mode (warn but don't block)
   - Policy profiles (development vs. production)

## Related Files

| File | Purpose |
|------|---------|
| `install-with-sondera.sh` | Automated installation script |
| `test-sondera-integration.sh` | Integration verification |
| `.claude/settings.local.json` | Hook configuration (created by installer) |
| `README.md` | Main documentation with installation paths |

## External Resources

- **Sondera Repository:** (Update with actual URL)
- **Cedar Policy Language:** https://www.cedarpolicy.com/
- **Ollama Models:** https://ollama.ai/library

## Contributing

If you believe Sondera should be bundled by default, or have ideas for improving the integration, please open an issue or PR with:

1. **Use Case:** Describe your deployment scenario
2. **Rationale:** Why the current approach doesn't work
3. **Proposal:** Specific changes to the installation/architecture
4. **Tradeoffs:** What compromises are acceptable

---

**Philosophy:** SuperClaude prioritizes flexibility and simplicity, treating security as a deployment-time decision rather than a framework mandate. This may evolve as the project matures and user needs crystallize.
