---
name: sc-e2e
description: E2E testing workflow supporting Playwright, Cypress, and Selenium. Run, debug, record, trace, generate test scaffolds, and view reports. Use when running browser tests, debugging E2E failures, or generating test scaffolds.
---

# E2E Testing Skill

Comprehensive end-to-end testing workflow with support for multiple frameworks and interactive debugging.

## Quick Start

```bash
# Run all E2E tests
/sc:e2e run

# Run specific test file
/sc:e2e run --file auth.spec.ts

# Debug failing test
/sc:e2e debug --file auth.spec.ts --ui

# Record user interactions
/sc:e2e record --url /login

# Run with tracing enabled
/sc:e2e trace --file checkout.spec.ts

# Generate test scaffold
/sc:e2e generate spec user-profile

# View test report
/sc:e2e report
```

## Behavioral Flow

1. **Detect** - Identify E2E framework (Playwright, Cypress, Selenium)
2. **Configure** - Parse mode and options from arguments
3. **Execute** - Run the selected mode
4. **Analyze** - Parse results, identify failures
5. **Interact** - Offer debugging, re-run, or fix options
6. **Report** - Present results with actionable next steps

## Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--file` | string | - | Specific test file to target |
| `--grep` | string | - | Filter tests by name pattern |
| `--headed` | bool | false | Run in headed browser mode |
| `--workers` | int | auto | Number of parallel workers |
| `--ui` | bool | false | Open framework UI mode |
| `--url` | string | / | Starting URL for record mode |
| `--output` | string | - | Output file for generated code |
| `--framework` | string | auto | Force framework: `playwright`, `cypress`, `selenium` |

## Framework Detection

Auto-detect the E2E framework from project config:

| Framework | Detection | Config File |
|-----------|-----------|-------------|
| Playwright | `@playwright/test` in package.json | `playwright.config.ts` |
| Cypress | `cypress` in package.json | `cypress.config.ts` |
| Selenium | `selenium-webdriver` in package.json | `wdio.conf.js` |

```bash
# Detection logic
if [ -f "playwright.config.ts" ] || [ -f "playwright.config.js" ]; then
  FRAMEWORK="playwright"
elif [ -f "cypress.config.ts" ] || [ -f "cypress.config.js" ]; then
  FRAMEWORK="cypress"
elif [ -f "wdio.conf.js" ] || [ -f "wdio.conf.ts" ]; then
  FRAMEWORK="selenium"
fi
```

## Mode 1: `run` - Execute Tests

Run E2E tests with optional filters and configuration.

### Playwright
```bash
npx playwright test [--grep "pattern"] [--headed] [--workers N] [file]
```

### Cypress
```bash
npx cypress run [--spec "file"] [--headed] [--browser chrome]
```

### Post-Run Analysis

After test execution, parse output and offer interactive options:

```
Test run complete: X passed, Y failed

  [r] Re-run failed tests
  [d] Debug failing test
  [t] View trace/screenshot
  [f] Fix with /sc:tdd
  [a] Run all tests
  [q] Quit
```

## Mode 2: `debug` - Interactive Debugging

Launch the framework's debug mode for step-through testing.

### Playwright Debug Options
| Option | Command | Use Case |
|--------|---------|----------|
| UI mode | `npx playwright test --ui` | Visual step-through with time-travel |
| Inspector | `PWDEBUG=1 npx playwright test` | Selector builder + breakpoints |
| Slow-mo | `npx playwright test --headed --slowmo=500` | Watch test execution |

### Cypress Debug Options
| Option | Command | Use Case |
|--------|---------|----------|
| Open mode | `npx cypress open` | Interactive test runner |
| Debug | `npx cypress run --headed --no-exit` | Keep browser open on failure |

### Debugging Tips
- Use `await page.pause()` (Playwright) or `cy.pause()` (Cypress) for breakpoints
- Check screenshots in `test-results/` or `cypress/screenshots/`
- Use trace viewer for time-travel debugging

## Mode 3: `record` - Record User Interactions

Use codegen tools to record browser interactions and generate test code.

### Playwright
```bash
npx playwright codegen http://localhost:3000[url-path]
```

### Cypress
```bash
npx cypress open  # Use Cypress Studio for recording
```

### Post-Recording

1. Review generated code
2. Offer conversion to page object pattern:
   - Extract selectors to page object class
   - Convert actions to reusable methods
   - Add assertions from existing patterns

## Mode 4: `trace` - Tracing

Run tests with tracing enabled or view existing traces.

### Playwright
```bash
# Run with tracing
npx playwright test --trace on [file]

# View trace
npx playwright show-trace test-results/[trace].zip
```

### Cypress
```bash
# Traces are auto-captured in cypress/videos/
# Screenshots in cypress/screenshots/
```

## Mode 5: `generate` - Test Scaffolding

Generate test files following project patterns.

### `generate spec <name>`

Create a new test spec file with:
- Import statements for the framework
- Describe blocks with page name
- beforeEach with login/navigation
- Empty test stubs for common scenarios

### `generate page <name>`

Create a new page object with:
- Selector constants extracted from the target page component
- Action methods (click, fill, navigate)
- Assertion helpers (expectLoaded, expectError)

### Page Object Pattern

```typescript
// Playwright page object template
import { Page, Locator, expect } from '@playwright/test';

export class UserProfilePage {
  readonly page: Page;
  readonly nameInput: Locator;
  readonly saveButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.nameInput = page.getByTestId('profile-name');
    this.saveButton = page.getByTestId('profile-save');
  }

  async goto(): Promise<void> {
    await this.page.goto('/profile');
  }

  async updateName(name: string): Promise<void> {
    await this.nameInput.fill(name);
    await this.saveButton.click();
  }

  async expectLoaded(): Promise<void> {
    await expect(this.nameInput).toBeVisible();
  }
}
```

## Mode 6: `report` - View Reports

View and analyze test reports.

### Playwright
```bash
npx playwright show-report
```

### Cypress
```bash
# Open Mochawesome report if configured
open cypress/reports/index.html
```

### Summary Output
```
## E2E Test Report

| Suite | Tests | Passed | Failed | Skipped | Duration |
|-------|-------|--------|--------|---------|----------|
| Auth | 5 | 5 | 0 | 0 | 12.3s |
| Dashboard | 8 | 7 | 1 | 0 | 24.1s |
| Checkout | 3 | 3 | 0 | 0 | 18.7s |

**Total**: 16 tests, 15 passed, 1 failed (93.8%)
```

## Environment Variables

| Variable | Purpose |
|----------|---------|
| `BASE_URL` | Application URL for tests (default: http://localhost:3000) |
| `E2E_USERNAME` | Test user credentials |
| `E2E_PASSWORD` | Test user password |
| `CI` | Adjusts workers and retries for CI |
| `PWDEBUG` | Enable Playwright Inspector |

## MCP Integration

### PAL MCP

| Tool | When to Use | Purpose |
|------|-------------|---------|
| `mcp__pal__debug` | Test failures | Root cause analysis for E2E failures |
| `mcp__pal__codereview` | Generated tests | Review test quality and coverage |
| `mcp__pal__apilookup` | Framework docs | Get current Playwright/Cypress API docs |

### PAL Usage Patterns

```bash
# Debug failing E2E test
mcp__pal__debug(
    step="E2E test 'checkout flow' fails on payment step",
    hypothesis="Selector changed after UI update",
    confidence="medium",
    relevant_files=["tests/e2e/checkout.spec.ts", "src/components/PaymentForm.tsx"]
)

# Review generated page object
mcp__pal__codereview(
    review_type="quick",
    step="Review generated page object for completeness",
    relevant_files=["tests/e2e/pages/checkout.page.ts"]
)
```

### Rube MCP

| Tool | When to Use | Purpose |
|------|-------------|---------|
| `mcp__rube__RUBE_MULTI_EXECUTE_TOOL` | CI integration | Post E2E results to Slack, update tickets |

## Tool Coordination

- **Bash** - Framework CLI commands (playwright, cypress)
- **Glob** - Test file discovery, page component scanning
- **Grep** - Selector extraction from components, test output parsing
- **Read** - Component inspection for page object generation
- **Write** - Generated test files, page objects

## Related Skills

- `/sc:test` - Unit and integration testing
- `/sc:tdd` - Test-driven development workflow
- `/sc:pr-check` - Pre-PR validation including E2E
- `/sc:implement` - Feature implementation with test generation
