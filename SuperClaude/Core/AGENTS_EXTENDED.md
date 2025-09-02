# Extended Agent Library - Quick Discovery Guide

## Overview
The Extended Agent Library provides 100+ specialized agents from the awesome-claude-code-subagents collection, offering production-ready expertise for specific domains and technologies.

## Quick Selection by Task

### 🚀 "I need help with a specific language/framework"
**→ Check `02-language-specialists/`**
- **TypeScript**: `typescript-pro.md` - Advanced TypeScript patterns, type gymnastics
- **Python**: `python-pro.md` - Ecosystem mastery, async patterns
- **Rust**: `rust-engineer.md` - Memory safety, systems programming
- **Go**: `golang-pro.md` - Concurrency, microservices
- **React**: `react-specialist.md` - React 18+, hooks, performance
- **Vue**: `vue-expert.md` - Vue 3, Composition API
- **Angular**: `angular-architect.md` - Enterprise patterns
- **Next.js**: `nextjs-developer.md` - Full-stack, SSR/SSG
- **Spring Boot**: `spring-boot-engineer.md` - Java microservices
- **Rails**: `rails-expert.md` - Rails 7+, rapid development

### 🏗️ "I need infrastructure/DevOps help"
**→ Check `03-infrastructure/`**
- **Kubernetes**: `kubernetes-specialist.md` - Container orchestration
- **Terraform**: `terraform-engineer.md` - Infrastructure as Code
- **AWS/GCP/Azure**: `cloud-architect.md` - Multi-cloud expertise
- **CI/CD**: `devops-engineer.md` - Pipeline automation
- **Site Reliability**: `sre-engineer.md` - Monitoring, resilience
- **Incident Response**: `incident-responder.md` - Crisis management

### 🔒 "I need security/quality expertise"
**→ Check `04-quality-security/`**
- **Security Audit**: `security-auditor.md` - Vulnerability assessment
- **Penetration Testing**: `penetration-tester.md` - Ethical hacking
- **QA Automation**: `qa-expert.md` - Test frameworks
- **Accessibility**: `accessibility-tester.md` - WCAG compliance
- **Performance**: `performance-engineer.md` - Optimization
- **Code Review**: `code-reviewer.md` - Quality guardian

### 🤖 "I need AI/ML/Data expertise"
**→ Check `05-data-ai/`**
- **Machine Learning**: `ml-engineer.md` - Model development
- **LLM Architecture**: `llm-architect.md` - Large language models
- **Data Engineering**: `data-engineer.md` - Pipeline architecture
- **MLOps**: `mlops-engineer.md` - Model deployment
- **NLP**: `nlp-engineer.md` - Natural language processing
- **Database Optimization**: `database-optimizer.md` - Query performance

### 💎 "I need domain-specific expertise"
**→ Check `07-specialized-domains/`**
- **Blockchain/Web3**: `blockchain-developer.md` - Smart contracts, DeFi
- **Gaming**: `game-developer.md` - Game engines, physics
- **IoT**: `iot-engineer.md` - Embedded systems, sensors
- **FinTech**: `fintech-engineer.md` - Financial systems
- **Payments**: `payment-integration.md` - Payment gateways
- **SEO**: `seo-specialist.md` - Search optimization

### 🛠️ "I need developer tooling/experience help"
**→ Check `06-developer-experience/`**
- **Build Systems**: `build-engineer.md` - Webpack, Vite, etc.
- **CLI Tools**: `cli-developer.md` - Command-line interfaces
- **Legacy Code**: `legacy-modernizer.md` - Modernization
- **Refactoring**: `refactoring-specialist.md` - Code improvement
- **Documentation**: `documentation-engineer.md` - Technical docs

### 📊 "I need business/product expertise"
**→ Check `08-business-product/`**
- **Product Management**: `product-manager.md` - Strategy, roadmaps
- **Technical Writing**: `technical-writer.md` - Documentation
- **UX Research**: `ux-researcher.md` - User studies
- **Project Management**: `project-manager.md` - Agile, Scrum
- **Business Analysis**: `business-analyst.md` - Requirements

### 🔄 "I need multi-agent coordination"
**→ Check `09-meta-orchestration/`**
- **Agent Coordination**: `multi-agent-coordinator.md` - Complex workflows
- **Workflow Automation**: `workflow-orchestrator.md` - Process automation
- **Context Management**: `context-manager.md` - State optimization
- **Task Distribution**: `task-distributor.md` - Work allocation

## Usage Examples

### Direct Invocation
```bash
# Use specific extended agent
Task(Extended/02-language-specialists/rust-engineer)

# With context
Task(Extended/03-infrastructure/kubernetes-specialist, {
  goal: "Deploy microservices to K8s",
  constraints: ["Use Helm charts", "Enable auto-scaling"]
})
```

### Discovery Pattern
1. Check this guide for the right category
2. Browse category directory for specific agent
3. Read agent file for detailed capabilities
4. Invoke with appropriate context

## Top 20 Most Useful Extended Agents

1. **typescript-pro** - TypeScript mastery
2. **python-pro** - Python ecosystem expert
3. **react-specialist** - Modern React patterns
4. **kubernetes-specialist** - K8s orchestration
5. **rust-engineer** - Systems programming
6. **golang-pro** - Go concurrency
7. **ml-engineer** - Machine learning
8. **cloud-architect** - Multi-cloud design
9. **security-auditor** - Security assessment
10. **nextjs-developer** - Full-stack Next.js
11. **vue-expert** - Vue 3 expertise
12. **terraform-engineer** - IaC expert
13. **blockchain-developer** - Web3 development
14. **qa-expert** - Test automation
15. **devops-engineer** - CI/CD pipelines
16. **database-optimizer** - Query optimization
17. **api-designer** - REST/GraphQL APIs
18. **mobile-developer** - Cross-platform mobile
19. **microservices-architect** - Distributed systems
20. **technical-writer** - Documentation expert

## Category Deep Dive

### 01-core-development (14 agents)
Foundation development patterns: APIs, backends, frontends, full-stack, microservices

### 02-language-specialists (26 agents)
Deep expertise in specific languages and their ecosystems

### 03-infrastructure (12 agents)
Cloud, containers, networking, platform engineering

### 04-quality-security (12 agents)
Testing, security, performance, quality assurance

### 05-data-ai (12 agents)
Data pipelines, ML/AI, analytics, databases

### 06-developer-experience (10 agents)
Tools, automation, productivity, refactoring

### 07-specialized-domains (11 agents)
Industry-specific: finance, gaming, IoT, blockchain

### 08-business-product (10 agents)
Product management, documentation, user research

### 09-meta-orchestration (8 agents)
Multi-agent coordination, workflow automation

### 10-research-analysis (6 agents)
Market research, competitive analysis, trends

## Integration with Core Agents

The Extended Library complements SuperClaude's 15 core agents:
- **Core agents**: Quick access, general purpose
- **Extended agents**: Specialized expertise, production patterns

Use core agents for common tasks, extended agents for specialized needs.

## Best Practices

1. **Start with core agents** - Often sufficient for general tasks
2. **Use extended for specifics** - When you need deep expertise
3. **Check agent descriptions** - Each file has detailed capabilities
4. **Provide context** - Extended agents work best with clear goals
5. **Combine agents** - Use multiple agents for complex workflows

## Finding the Right Agent

Ask yourself:
1. What technology/domain am I working with?
2. What type of task (development/testing/design)?
3. What level of expertise needed?

Then navigate to the appropriate category and select the most specific agent for your needs.

---

*Extended Agent Library - 100+ specialized agents for every development need*