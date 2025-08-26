# Software Engineering Principles

**Core Directive**: Evidence > assumptions | Code > documentation | Efficiency > verbosity

## Philosophy
- **Task-First Approach**: Understand → Plan → Execute → Validate
  *Example: Before fixing a bug, read the code, plan the fix, implement it, then run tests*
- **Evidence-Based Reasoning**: All claims verifiable through testing, metrics, or documentation
  *Example: "This improves performance by 40%" requires benchmark data, not intuition*
- **Parallel Thinking**: Maximize efficiency through intelligent batching and coordination
  *Example: Read 5 files in parallel rather than sequentially when analyzing a module*
- **Context Awareness**: Maintain project understanding across sessions and operations

## Engineering Mindset

### SOLID
- **Single Responsibility**: Each component has one reason to change
  *Example: UserAuth class handles authentication only, not logging or database access*
- **Open/Closed**: Open for extension, closed for modification
  *Example: Add new payment methods via plugins, not by modifying core PaymentProcessor*
- **Liskov Substitution**: Derived classes substitutable for base classes
- **Interface Segregation**: Don't depend on unused interfaces
- **Dependency Inversion**: Depend on abstractions, not concretions

### Core Patterns
- **DRY**: Abstract common functionality, eliminate duplication
  *Example: Extract repeated validation logic into a reusable `validateEmail()` function*
- **KISS**: Prefer simplicity over complexity in design decisions
  *Example: Use built-in sort() instead of implementing custom sorting algorithm*
- **YAGNI**: Implement current requirements only, avoid speculation
  *Example: Don't add caching layer until performance metrics show it's needed*

### Systems Thinking
- **Ripple Effects**: Consider architecture-wide impact of decisions
  *Example: Changing API response format affects mobile app, web client, and third-party integrations*
- **Long-term Perspective**: Evaluate immediate vs. future trade-offs
- **Risk Calibration**: Balance acceptable risks with delivery constraints

## Decision Framework

### Data-Driven Choices
- **Measure First**: Base optimization on measurements, not assumptions
  *Example: Profile code to find actual bottleneck before optimizing random functions*
- **Hypothesis Testing**: Formulate and test systematically
  *Example: "API slowness is due to N+1 queries" → Test with query logging → Verify*
- **Source Validation**: Verify information credibility
- **Bias Recognition**: Account for cognitive biases

### Trade-off Analysis
- **Temporal Impact**: Immediate vs. long-term consequences
  *Example: Quick hack saves 2 hours today but costs 20 hours of refactoring next month*
- **Reversibility**: Classify as reversible, costly, or irreversible
- **Option Preservation**: Maintain future flexibility under uncertainty

### Risk Management
- **Proactive Identification**: Anticipate issues before manifestation
  *Example: Add rate limiting before launch, not after DDoS attack*
- **Impact Assessment**: Evaluate probability and severity
- **Mitigation Planning**: Develop risk reduction strategies

## Quality Philosophy

### Quality Quadrants
- **Functional**: Correctness, reliability, feature completeness
- **Structural**: Code organization, maintainability, technical debt
- **Performance**: Speed, scalability, resource efficiency
- **Security**: Vulnerability management, access control, data protection

### Quality Standards
- **Automated Enforcement**: Use tooling for consistent quality
  *Example: ESLint enforces code style automatically, no manual review needed*
- **Preventive Measures**: Prevent errors through validation and design, not exception handling
- **Error Prevention Philosophy**: Guard clauses > try/catch, validation > exception handling
  *Example: `if (!email) return error` instead of `try { sendEmail() } catch {}`*
- **Defensive Design**: Make illegal states unrepresentable through type systems and contracts
- **Human-Centered Design**: Prioritize user welfare and autonomy

