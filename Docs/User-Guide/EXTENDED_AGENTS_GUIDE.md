# Extended Agents Guide - SuperClaude Framework

## Overview

The Extended Agent Library is a comprehensive collection of 100+ specialized domain experts that provide production-ready expertise for specific technologies, frameworks, and development domains. Unlike the 15 core agents designed for general development tasks, Extended agents offer deep, specialized knowledge for complex, technology-specific challenges.

### Key Benefits

- **Deep Specialization**: Each agent is an expert in their specific domain
- **Production-Ready**: Agents follow industry best practices and modern patterns
- **Token Efficient**: Smart conditional loading - agents load only when requested
- **Comprehensive Coverage**: 10 categories covering all development domains
- **Consistent Interface**: Same Task() interface as core agents

## Smart Conditional Loading System

### Token Efficiency

The Extended Agent Library uses an intelligent loading system designed for maximum token efficiency:

| Loading State | Token Usage | What's Available |
|---------------|-------------|------------------|
| **Baseline** | ~10KB | Core framework + 15 core agents |
| **With Extended** | +11KB | All 100+ Extended agents active |
| **Full Framework** | ~40KB | Everything loaded |

### Loading Triggers

Extended agents are **NOT loaded by default**. They load automatically when:

- **Explicit Request**: `Task(Extended/category/agent-name)`
- **Auto-Delegation**: `--delegate` flag with specialized needs
- **Category Browse**: Accessing Extended agent documentation

### Loading Examples

```bash
# Baseline: Only core agents loaded (~10KB)
Task(refactoring-expert)  # Uses core agent

# Extended Loading: Adds ~11KB when first Extended agent used
Task(Extended/02-language-specialists/typescript-pro)

# After first Extended agent: All Extended agents available
Task(Extended/03-infrastructure/kubernetes-specialist)
```

## Agent Categories

### 01-core-development (12 agents)
**Foundation development patterns**

Essential building blocks for modern applications:
- **api-designer.md** - REST and GraphQL API architect
- **backend-developer.md** - Server-side expert for scalable APIs
- **electron-pro.md** - Desktop application expert
- **frontend-developer.md** - UI/UX specialist for React, Vue, Angular
- **fullstack-developer.md** - End-to-end feature development
- **graphql-architect.md** - GraphQL schema and federation expert
- **microservices-architect.md** - Distributed systems designer
- **mobile-developer.md** - Cross-platform mobile specialist
- **ui-designer.md** - Visual design and interaction specialist
- **websocket-engineer.md** - Real-time communication specialist
- **wordpress-master.md** - WordPress development and optimization

**Best For**: Building new applications, implementing complex features, system architecture

### 02-language-specialists (24 agents)
**Deep expertise in specific programming languages and frameworks**

Language-specific experts with ecosystem mastery:
- **typescript-pro.md** - Advanced TypeScript patterns, type gymnastics
- **python-pro.md** - Python ecosystem mastery, async patterns
- **rust-engineer.md** - Memory safety, systems programming
- **golang-pro.md** - Go concurrency, microservices
- **react-specialist.md** - React 18+, hooks, performance
- **vue-expert.md** - Vue 3, Composition API
- **angular-architect.md** - Enterprise Angular patterns
- **nextjs-developer.md** - Full-stack Next.js, SSR/SSG
- **java-architect.md** - Enterprise Java, Spring ecosystem
- **spring-boot-engineer.md** - Microservices with Spring Boot
- **rails-expert.md** - Rails 7+, rapid development
- **django-developer.md** - Python web framework
- **laravel-specialist.md** - PHP modern development
- **csharp-developer.md** - .NET development
- **dotnet-core-expert.md** - Modern .NET applications
- **flutter-expert.md** - Cross-platform mobile development
- **swift-expert.md** - iOS/macOS development
- **kotlin-specialist.md** - Android/JVM development
- **cpp-pro.md** - C++ systems programming
- **php-pro.md** - Modern PHP development
- **javascript-pro.md** - Vanilla JS mastery
- **sql-pro.md** - Database query optimization

**Best For**: Language-specific development, framework expertise, ecosystem guidance

### 03-infrastructure (13 agents)
**Cloud, containers, and platform engineering**

Infrastructure and DevOps specialists:
- **kubernetes-specialist.md** - Container orchestration expert
- **terraform-engineer.md** - Infrastructure as Code specialist
- **cloud-architect.md** - Multi-cloud expertise (AWS/GCP/Azure)
- **devops-engineer.md** - CI/CD pipeline automation
- **devops-incident-responder.md** - Crisis management
- **sre-engineer.md** - Site reliability engineering
- **platform-engineer.md** - Developer platform building
- **network-engineer.md** - Network architecture and security
- **database-administrator.md** - Database management and optimization
- **deployment-engineer.md** - Deployment strategies and automation
- **security-engineer.md** - Infrastructure security
- **incident-responder.md** - Incident management

**Best For**: Infrastructure design, cloud migration, DevOps automation, platform building

### 04-quality-security (13 agents)
**Testing, security, and quality assurance**

Quality and security specialists:
- **security-auditor.md** - Comprehensive security assessment
- **penetration-tester.md** - Ethical hacking and vulnerability testing
- **qa-expert.md** - Test automation and quality frameworks
- **accessibility-tester.md** - WCAG compliance and accessibility
- **performance-engineer.md** - Performance optimization and monitoring
- **code-reviewer.md** - Code quality and review processes
- **test-automator.md** - Test automation frameworks
- **architect-reviewer.md** - Architecture quality assessment
- **chaos-engineer.md** - Resilience and fault tolerance testing
- **compliance-auditor.md** - Regulatory compliance
- **debugger.md** - Advanced debugging techniques
- **error-detective.md** - Error investigation and resolution

**Best For**: Security audits, test automation, performance optimization, quality gates

### 05-data-ai (13 agents)
**Machine learning, data engineering, and AI systems**

Data and AI specialists:
- **ml-engineer.md** - Machine learning model development
- **llm-architect.md** - Large language model systems
- **ai-engineer.md** - AI system architecture
- **data-engineer.md** - Data pipeline architecture
- **data-scientist.md** - Data analysis and modeling
- **mlops-engineer.md** - ML model deployment and operations
- **nlp-engineer.md** - Natural language processing
- **database-optimizer.md** - Database performance tuning
- **postgres-pro.md** - PostgreSQL expertise
- **data-analyst.md** - Data analysis and visualization
- **prompt-engineer.md** - LLM prompt optimization
- **data-researcher.md** - Research methodology

**Best For**: AI/ML projects, data pipelines, model deployment, database optimization

### 06-developer-experience (11 agents)
**Tools, automation, and developer productivity**

Developer experience and productivity specialists:
- **build-engineer.md** - Build systems (Webpack, Vite, etc.)
- **cli-developer.md** - Command-line interface development
- **legacy-modernizer.md** - Legacy code modernization
- **refactoring-specialist.md** - Code improvement and refactoring
- **documentation-engineer.md** - Technical documentation
- **tooling-engineer.md** - Developer tooling
- **dependency-manager.md** - Dependency management
- **git-workflow-manager.md** - Git workflow optimization
- **dx-optimizer.md** - Developer experience optimization
- **mcp-developer.md** - MCP server development

**Best For**: Tool building, legacy modernization, developer productivity, documentation

### 07-specialized-domains (12 agents)
**Industry-specific expertise**

Domain-specific specialists:
- **blockchain-developer.md** - Smart contracts, DeFi, Web3
- **game-developer.md** - Game engines, physics, graphics
- **iot-engineer.md** - Embedded systems, sensors, IoT
- **fintech-engineer.md** - Financial systems and regulations
- **payment-integration.md** - Payment gateways and processing
- **embedded-systems.md** - Hardware-software integration
- **mobile-app-developer.md** - Native mobile development
- **seo-specialist.md** - Search engine optimization
- **quant-analyst.md** - Quantitative analysis
- **risk-manager.md** - Risk assessment and management
- **api-documenter.md** - API documentation

**Best For**: Industry-specific requirements, specialized technology domains

### 08-business-product (12 agents)
**Product management and business analysis**

Business and product specialists:
- **product-manager.md** - Product strategy and roadmaps
- **project-manager.md** - Project management and Agile
- **business-analyst.md** - Requirements analysis
- **technical-writer.md** - Technical documentation
- **ux-researcher.md** - User experience research
- **customer-success-manager.md** - Customer success strategies
- **scrum-master.md** - Agile methodology
- **sales-engineer.md** - Technical sales support
- **content-marketer.md** - Technical content marketing
- **legal-advisor.md** - Technology legal compliance

**Best For**: Product strategy, requirements gathering, user research, agile processes

### 09-meta-orchestration (9 agents)
**Multi-agent coordination and workflow automation**

Orchestration and coordination specialists:
- **multi-agent-coordinator.md** - Complex workflow coordination
- **workflow-orchestrator.md** - Process automation
- **context-manager.md** - Context and state optimization
- **task-distributor.md** - Work allocation and distribution
- **agent-organizer.md** - Agent selection and management
- **knowledge-synthesizer.md** - Information synthesis
- **error-coordinator.md** - Error handling coordination
- **performance-monitor.md** - Performance monitoring

**Best For**: Complex multi-step workflows, agent coordination, automation

### 10-research-analysis (7 agents)
**Market research and analysis**

Research and analysis specialists:
- **research-analyst.md** - Research methodology and analysis
- **market-researcher.md** - Market analysis and trends
- **competitive-analyst.md** - Competitive landscape analysis
- **trend-analyst.md** - Technology trend analysis
- **search-specialist.md** - Information discovery
- **data-researcher.md** - Research data analysis

**Best For**: Market research, competitive analysis, trend identification

## Usage Methods

### 1. Direct Invocation

Use the full path to specify exactly which agent you want:

```bash
# TypeScript expertise
Task(Extended/02-language-specialists/typescript-pro)

# Kubernetes help
Task(Extended/03-infrastructure/kubernetes-specialist)

# Security audit
Task(Extended/04-quality-security/security-auditor)

# ML development
Task(Extended/05-data-ai/ml-engineer)
```

### 2. Auto-Selection with --delegate

Let the framework choose the best agent based on context:

```bash
# Auto-selects appropriate Extended agent based on context
--delegate "Optimize this TypeScript application"
--delegate "Deploy microservices to Kubernetes"
--delegate "Implement machine learning pipeline"
```

### 3. Context Package

Provide comprehensive context for optimal results:

```bash
Task(Extended/03-infrastructure/kubernetes-specialist, {
  goal: "Deploy microservices architecture to production",
  constraints: ["Use Helm charts", "Enable auto-scaling", "Multi-region"],
  existing_setup: "Docker Compose currently",
  requirements: ["Zero downtime deployment", "Resource optimization"]
})
```

### 4. Quality-Driven Execution

All Extended agents use the same quality scoring system:

- **90-100**: Production-ready → Accept immediately
- **70-89**: Acceptable → Review implementation notes
- **<70**: Needs improvement → Auto-retry with refinements

## Integration Points

### Task Tool as Delegation Engine

Extended agents integrate seamlessly with the Task tool:

```bash
# Task tool routes to appropriate Extended agent
Task(Extended/category/agent-name)

# With context and constraints
Task(Extended/02-language-specialists/rust-engineer, {
  goal: "Optimize memory usage",
  constraints: ["No unsafe code", "Maintain API compatibility"]
})
```

### AGENTS_EXTENDED.md Discovery Guide

Use the discovery guide to find the right agent:

1. **Browse by task type**: Check category descriptions
2. **Quick reference**: Top 20 most useful agents
3. **Selection matrix**: Choose based on technology/domain
4. **Usage examples**: See practical implementation patterns

### Conditional Loading via CLAUDE_MINIMAL.md

The loading system is controlled by CLAUDE_MINIMAL.md:

- **Baseline**: Core agents only (~10KB)
- **Extended Trigger**: First Extended agent request (+11KB)
- **Full Access**: All Extended agents available after first load

### MCP Server Integration

Extended agents work seamlessly with MCP servers:

```bash
# Extended agent + MCP server combination
Task(Extended/02-language-specialists/typescript-pro) + --tools sequential

# Infrastructure agent + cloud tools
Task(Extended/03-infrastructure/kubernetes-specialist) + --tools playwright
```

## Practical Examples

### Frontend Development

```bash
# React application with TypeScript
Task(Extended/02-language-specialists/typescript-pro, {
  goal: "Build type-safe React components",
  constraints: ["100% type coverage", "No any types"]
})

# Then use React specialist for advanced patterns
Task(Extended/02-language-specialists/react-specialist, {
  goal: "Implement performance optimizations",
  context: "Large component tree with frequent updates"
})
```

### Infrastructure Setup

```bash
# Kubernetes deployment
Task(Extended/03-infrastructure/kubernetes-specialist, {
  goal: "Design production-ready K8s architecture",
  constraints: ["Multi-environment", "Auto-scaling", "Security hardening"]
})

# Infrastructure as Code
Task(Extended/03-infrastructure/terraform-engineer, {
  goal: "Create Terraform modules for AWS deployment",
  context: "Microservices with RDS and Redis"
})
```

### Security Assessment

```bash
# Comprehensive security audit
Task(Extended/04-quality-security/security-auditor, {
  goal: "Audit web application security",
  scope: ["Authentication", "API endpoints", "Data handling"]
})

# Penetration testing
Task(Extended/04-quality-security/penetration-tester, {
  goal: "Test application vulnerabilities",
  constraints: ["Non-destructive testing", "Production-like environment"]
})
```

### Data and AI Projects

```bash
# Machine learning pipeline
Task(Extended/05-data-ai/ml-engineer, {
  goal: "Build ML model training pipeline",
  constraints: ["Scalable", "Reproducible", "Model versioning"]
})

# Data engineering
Task(Extended/05-data-ai/data-engineer, {
  goal: "Design real-time data pipeline",
  context: "High-volume streaming data, Apache Kafka"
})
```

## Best Practices

### Agent Selection Strategy

1. **Start with core agents** for general tasks
2. **Use Extended for specialization** when you need deep expertise
3. **Check agent descriptions** before selection
4. **Provide context** for better results
5. **Combine agents** for complex workflows

### Optimal Workflows

#### For New Projects
```bash
# 1. Architecture design
Task(Extended/01-core-development/microservices-architect)

# 2. Technology-specific implementation
Task(Extended/02-language-specialists/typescript-pro)

# 3. Infrastructure setup
Task(Extended/03-infrastructure/kubernetes-specialist)

# 4. Quality gates
Task(Extended/04-quality-security/qa-expert)
```

#### For Existing Projects
```bash
# 1. Analysis phase
--delegate "Analyze current architecture"

# 2. Specific improvements
Task(Extended/06-developer-experience/legacy-modernizer)

# 3. Quality improvement
Task(Extended/04-quality-security/performance-engineer)
```

### Context Optimization

Provide comprehensive context for best results:

```bash
Task(Extended/category/agent, {
  goal: "Clear, specific objective",
  constraints: ["Technical limitations", "Requirements"],
  context: "Current state and background",
  preferences: ["Technology choices", "Patterns to follow"]
})
```

## Common Use Cases and Workflows

### Full-Stack Application Development

```bash
# 1. API Design
Task(Extended/01-core-development/api-designer)

# 2. Backend Implementation
Task(Extended/02-language-specialists/nodejs-developer)

# 3. Frontend Development
Task(Extended/02-language-specialists/react-specialist)

# 4. Testing Strategy
Task(Extended/04-quality-security/qa-expert)

# 5. Deployment
Task(Extended/03-infrastructure/devops-engineer)
```

### Legacy System Modernization

```bash
# 1. Assessment
Task(Extended/06-developer-experience/legacy-modernizer)

# 2. Migration Strategy
Task(Extended/01-core-development/system-architect)

# 3. Implementation
Task(Extended/02-language-specialists/[target-language])

# 4. Quality Assurance
Task(Extended/04-quality-security/code-reviewer)
```

### AI/ML Project Pipeline

```bash
# 1. Data Engineering
Task(Extended/05-data-ai/data-engineer)

# 2. Model Development
Task(Extended/05-data-ai/ml-engineer)

# 3. MLOps Setup
Task(Extended/05-data-ai/mlops-engineer)

# 4. Performance Optimization
Task(Extended/04-quality-security/performance-engineer)
```

## Integration with Core Agents

Extended agents complement the 15 core agents:

### Core vs Extended Decision Matrix

| Task Type | Use Core Agent | Use Extended Agent |
|-----------|---------------|-------------------|
| General debugging | ✅ root-cause-analyst | Extended for specific language |
| Code refactoring | ✅ refactoring-expert | Extended for specific patterns |
| Documentation | ✅ technical-writer | Extended for API docs |
| Performance issues | ✅ performance-engineer | Extended for specific optimization |
| Security review | ✅ security-engineer | Extended for comprehensive audit |

### Workflow Integration

```bash
# Start with core for general assessment
Task(root-cause-analyst)

# Move to Extended for specialized work
Task(Extended/02-language-specialists/rust-engineer)

# Return to core for final coordination
Task(quality-engineer)
```

## Performance Considerations

### Token Usage Optimization

- **Lazy Loading**: Extended agents load only when needed
- **Smart Caching**: Once loaded, all Extended agents remain available
- **Context Sharing**: Agents share context efficiently
- **Quality Gates**: Automatic retry prevents token waste on poor outputs

### Memory Management

- **Session Persistence**: Extended agents remember context within session
- **Cross-Session**: Use memory tools for persistence across sessions
- **Resource Cleanup**: Automatic cleanup when session ends

## Troubleshooting

### Common Issues

**Extended Agent Not Found**
```bash
# ❌ Wrong path
Task(typescript-pro)

# ✅ Correct path
Task(Extended/02-language-specialists/typescript-pro)
```

**Agent Selection Confusion**
```bash
# Use discovery guide to find right agent
# Check AGENTS_EXTENDED.md for category mapping
```

**Context Not Provided**
```bash
# ❌ Vague request
Task(Extended/05-data-ai/ml-engineer)

# ✅ Clear context
Task(Extended/05-data-ai/ml-engineer, {
  goal: "Build image classification model",
  constraints: ["TensorFlow", "Mobile deployment"]
})
```

### Debug Commands

```bash
# Check which agents are loaded
Task(list-loaded-agents)

# Verify Extended agent availability
Task(check-extended-library)

# Get agent capabilities
Task(describe-agent, Extended/category/agent-name)
```

## Advanced Features

### Multi-Agent Orchestration

Use meta-orchestration agents for complex workflows:

```bash
Task(Extended/09-meta-orchestration/multi-agent-coordinator, {
  goal: "Coordinate full-stack development",
  agents: [
    "Extended/01-core-development/api-designer",
    "Extended/02-language-specialists/typescript-pro",
    "Extended/03-infrastructure/kubernetes-specialist"
  ]
})
```

### Dynamic Agent Selection

```bash
# Let the framework choose optimal agent combination
--delegate --extended "Build scalable Node.js API with TypeScript"
```

### Context Inheritance

```bash
# Agents inherit context from previous agents in workflow
Task(Extended/01-core-development/api-designer)
# Context flows to next agent
Task(Extended/02-language-specialists/nodejs-developer)
```

## Conclusion

The Extended Agent Library provides comprehensive expertise for any development challenge. With 100+ specialized agents organized into 10 clear categories, you can access production-ready knowledge for specific technologies and domains while maintaining token efficiency through smart conditional loading.

**Quick Start Checklist:**
1. ✅ Identify your technology/domain need
2. ✅ Find the appropriate category (01-10)
3. ✅ Select the specific agent
4. ✅ Provide clear context and constraints
5. ✅ Let quality scoring guide iterations

**Remember**: Start with core agents for general tasks, move to Extended agents when you need specialized expertise, and combine agents for complex workflows.

---

*Extended Agent Library - Production-ready expertise for every development challenge*