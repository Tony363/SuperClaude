# Operations Overview (Minimal Profile)

Use this condensed reference to keep core operational guardrails without the
full `OPERATIONS.md` payload. The complete procedures (release management,
incident playbooks, advanced automation) remain available in
`SuperClaude/Core/OPERATIONS.md` or when using the full memory profile.

## Key Practices

- **Version control**: work on feature branches, commit small logical chunks,
  and include spec/task references in commit messages.
- **Testing**: run relevant test suites locally before raising PRs; record
  failing cases and remediation steps in command output.
- **CI hygiene**: keep pipelines green, avoid breaking main, and prefer
  feature flags for risky rollouts.
- **Documentation**: update specs/ADRs when architecture changes and append
  brief notes to change logs when user-facing behaviour shifts.
- **Security**: never commit secrets, validate dependencies, and flag external
  service requirements in summaries.

See the full operations manual for detailed runbook steps, escalation paths,
and checklists.
