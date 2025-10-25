# SuperClaude Tools Reference

## Task Agents
Quick selection guide for specialized agents.

### Analysis & Discovery
- **general-purpose**: Unknown scope, exploration, multi-step research
- **root-cause-analyst**: Debugging, error investigation, bottlenecks
- **requirements-analyst**: Feature analysis, PRD breakdown, scoping

### Code & Quality
- **refactoring-expert**: Technical debt, code cleanup, patterns
- **quality-engineer**: Test coverage, edge cases, quality metrics
- **performance-engineer**: Optimization, bottlenecks, efficiency

### Architecture & Design
- **system-architect**: System design, scalability, architecture
- **backend-architect**: API design, database, server patterns
- **frontend-architect**: UI/UX, components, accessibility
- **security-engineer**: Audits, vulnerabilities, compliance

### Documentation & Learning
- **technical-writer**: API docs, user guides, documentation
- **learning-guide**: Tutorials, educational content, explanations
- **socratic-mentor**: Teaching through questions, concept exploration

### Operations
- **devops-architect**: Infrastructure, CI/CD, deployment
- **python-expert**: Python-specific expertise and patterns

## Extended Agent Library (100+ Specialized Agents)

Located in `Agents/Extended/` - organized by category for specialized needs:

### Categories Overview
- **01-core-development** (14 agents): API designer, backend/frontend developers, fullstack, microservices, GraphQL, WebSocket, mobile, Electron
- **02-language-specialists** (26 agents): TypeScript, Python, Rust, Go, Java, C++, C#, Swift, Kotlin, PHP, Ruby, and framework experts
- **03-infrastructure** (12 agents): Cloud architect, DevOps, Kubernetes, Terraform, SRE, network engineering, platform engineering
- **04-quality-security** (12 agents): QA, penetration testing, security auditing, chaos engineering, accessibility testing
- **05-data-ai** (12 agents): ML engineer, data scientist, LLM architect, MLOps, NLP, database optimization
- **06-developer-experience** (10 agents): Build engineering, CLI development, tooling, refactoring, legacy modernization
- **07-specialized-domains** (11 agents): Blockchain, IoT, gaming, fintech, embedded systems, payments, SEO
- **08-business-product** (10 agents): Product management, technical writing, UX research, project management
- **09-meta-orchestration** (8 agents): Multi-agent coordination, workflow orchestration, context management
- **10-research-analysis** (6 agents): Market research, competitive analysis, trend analysis

### When to Use Extended Agents
| Need | Use Extended Category |
|------|----------------------|
| Specific language/framework expertise | 02-language-specialists |
| Infrastructure/DevOps beyond basics | 03-infrastructure |
| Advanced quality/security requirements | 04-quality-security |
| AI/ML/Data pipeline work | 05-data-ai |
| Domain-specific development | 07-specialized-domains |
| Complex multi-agent workflows | 09-meta-orchestration |

### Most Popular Extended Agents
- `Extended/02-language-specialists/typescript-pro.md` - Advanced TypeScript patterns
- `Extended/02-language-specialists/rust-engineer.md` - Memory-safe systems programming  
- `Extended/03-infrastructure/kubernetes-specialist.md` - K8s orchestration expert
- `Extended/07-specialized-domains/blockchain-developer.md` - Web3/crypto development
- `Extended/05-data-ai/ml-engineer.md` - Machine learning pipelines

## MCP Servers
Specialized tools for enhanced capabilities.

### Core Development
- **Sequential**: Multi-step reasoning, complex analysis  
  - Use for: Debugging, architecture review, systematic problem solving
- **Zen**: Multi-model consensus and validation  
  - Use for: Design reviews, risk assessments, cross-model agreement
- **Fetch**: Web content retrieval and extraction
- **Filesystem**: Secure file system operations  
  - Use for: Style enforcement, multi-file replacements, framework updates

### UI & Documentation  
- **MCP-Deepwiki**: Technical documentation and code examples  
  - Use for: React/Vue/Angular components, accessible UI, design systems
- **Deepwiki**: Technical documentation, framework patterns  
  - Use for: Library docs, API references, best practices
- **Browser Automation**: External Playwright/Cypress pipelines (manual)  
  - Use for: Visual testing, user flows, accessibility validation

### Persistence
- **UnifiedStore**: Built-in session memory and symbol catalog  
  - Use for: Session checkpoints, state restoration, refactor planning

## Quality Evaluation
Simple scoring system for all outputs:

| Score | Action | Description |
|-------|--------|-------------|
| 90-100 | ✅ Accept | Production-ready |
| 70-89 | ⚠️ Review | Acceptable with notes |
| < 70 | 🔄 Iterate | Auto-improve required |

Quality dimensions: Correctness (40%), Completeness (30%), Code Quality (20%), Performance (10%)

## Tool Selection Matrix

| Task | First Choice | Alternative |
|------|-------------|-------------|
| Find unknown code | Task(general-purpose) | Grep/Glob |
| Debug error | Task(root-cause-analyst) | Sequential |
| Refactor code | Task(refactoring-expert) | MultiEdit |
| Fetch web content | Fetch | WebSearch |
| Get docs | Deepwiki | WebSearch |
| Rename symbol | UnifiedStore | Manual search |
| Bulk edits | MultiEdit | Sequential edits |
| Complex analysis | Sequential | Native reasoning |
| Browser test | External Playwright/Cypress | Unit tests |

## Decision Flow
```
Unknown scope? → Task(general-purpose)
Debugging? → Task(root-cause-analyst)
Web content? → Fetch
File operations? → Filesystem
Bulk edits? → MultiEdit
Complex reasoning? → Sequential
Browser testing? → External Playwright/Cypress pipeline
Quality < 70? → Auto-iterate with feedback
```
