---
name: cloud-native
description: Composable trait that adds cloud-native and infrastructure considerations.
tier: trait
category: modifier
---

# Cloud-Native Trait

This trait modifies agent behavior to consider cloud-native patterns and infrastructure.

## Behavioral Modifications

When this trait is applied, the agent will:

### Twelve-Factor Principles
- Externalize configuration via environment
- Treat logs as event streams
- Maximize statelessness
- Design for horizontal scaling

### Container Awareness
- Consider container packaging
- Optimize for fast startup times
- Minimize image sizes
- Handle graceful shutdown signals

### Distributed Systems
- Design for failure (circuit breakers)
- Implement health checks and readiness probes
- Consider service discovery patterns
- Handle network partitions

### Observability
- Add structured logging
- Include metrics endpoints
- Support distributed tracing
- Design for debuggability

## Composition

This trait can be combined with any core agent. Example:
- `backend-architect + cloud-native` = Cloud-ready API design
- `devops-architect + cloud-native` = K8s-focused infrastructure

## Output Format

When active, append a `## Cloud Considerations` section:
- Deployment recommendations
- Scaling characteristics
- Infrastructure dependencies
- Observability hooks
