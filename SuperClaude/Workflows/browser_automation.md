# Browser MCP Automation Workflows

This document outlines practical Browser MCP workflows that can be invoked from
SuperClaude slash commands (for example `/sc:test --browser --url https://app.example.com`).

## Prerequisites

1. **Installation**:
   ```bash
   # Install Browser MCP via Claude Desktop
   claude mcp add -s user -- browser npx -y @browsermcp/mcp@latest

   # Verify installation
   claude mcp list | grep browser
   ```

2. **Enable in Configuration**:
   ```yaml
   # SuperClaude/Config/mcp.yaml
   browser:
     enabled: true  # Change from false to true
   ```

## Workflow Examples

### 1. UI Regression Testing Workflow

**Purpose**: Automated visual regression testing for web applications

```python
# Example: Visual regression test workflow
async def run_visual_regression_test():
    """Execute visual regression tests using Browser MCP."""

    # Initialize Browser MCP
    browser = get_mcp_integration("browser", config={"enabled": True})
    await browser.initialize()

    # Test scenarios
    test_pages = [
        "https://app.example.com/dashboard",
        "https://app.example.com/profile",
        "https://app.example.com/settings"
    ]

    results = []

    for page_url in test_pages:
        # Navigate to page
        await browser.navigate(page_url)
        await browser.wait(2)  # Wait for page load

        # Capture screenshot
        screenshot = await browser.screenshot(
            path=f"tests/visual/{page_url.split('/')[-1]}.png",
            full_page=True
        )

        # Get accessibility snapshot
        snapshot = await browser.snapshot()

        results.append({
            "url": page_url,
            "screenshot": screenshot.path,
            "accessibility_issues": validate_accessibility(snapshot)
        })

    # Cleanup
    await browser.cleanup()

    return results
```

**Command Integration**:
```bash
/sc:test --type visual --browser
```

### 2. Form Validation Testing Workflow

**Purpose**: Test form validation and submission flows

```python
# Example: Form validation testing
async def test_form_validation():
    """Test form validation using Browser MCP."""

    browser = get_mcp_integration("browser", config={"enabled": True})
    await browser.initialize()

    # Navigate to form
    await browser.navigate("https://app.example.com/signup")

    # Test invalid email
    await browser.type_text("#email", "invalid-email", description="Email field")
    await browser.click("#submit", "Submit button")

    # Check for validation error
    snapshot = await browser.snapshot()
    assert "Invalid email" in str(snapshot.accessibility_tree)

    # Test valid submission
    await browser.type_text("#email", "user@example.com", description="Email field")
    await browser.type_text("#password", "SecurePass123!", description="Password field")
    await browser.select_option("#country", ["US"], "Country selector")

    # Submit form
    await browser.click("#submit", "Submit button")
    await browser.wait(3)

    # Verify success
    current_url = browser.current_url
    assert "welcome" in current_url

    await browser.cleanup()
```

### 3. Screenshot Documentation Workflow

**Purpose**: Automatically generate screenshots for documentation

```python
# Example: Documentation screenshot generator
async def generate_documentation_screenshots():
    """Generate screenshots for documentation."""

    browser = get_mcp_integration(
        "browser",
        config={"enabled": True},
        browser_config=BrowserConfig(
            mode=BrowserMode.headed,  # Show browser for demo
            viewport_width=1920,
            viewport_height=1080
        )
    )

    await browser.initialize()

    docs_scenarios = [
        {
            "url": "https://app.example.com/dashboard",
            "actions": [
                ("click", "#menu-toggle", "Open menu"),
                ("wait", 1),
                ("screenshot", "docs/images/dashboard-menu.png")
            ]
        },
        {
            "url": "https://app.example.com/settings",
            "actions": [
                ("click", "#theme-selector", "Theme dropdown"),
                ("select", "#theme-selector", ["dark"], "Select dark theme"),
                ("screenshot", "docs/images/dark-theme.png")
            ]
        }
    ]

    for scenario in docs_scenarios:
        await browser.navigate(scenario["url"])

        for action in scenario["actions"]:
            if action[0] == "click":
                await browser.click(action[1], action[2])
            elif action[0] == "select":
                await browser.select_option(action[1], action[2], action[3])
            elif action[0] == "wait":
                await browser.wait(action[1])
            elif action[0] == "screenshot":
                await browser.screenshot(path=action[1])

    await browser.cleanup()
```

### 4. Accessibility Testing Workflow

**Purpose**: Validate accessibility compliance

```python
# Example: Accessibility testing workflow
async def test_accessibility():
    """Test accessibility using Browser MCP."""

    browser = get_mcp_integration("browser", config={"enabled": True})
    await browser.initialize()

    # Navigate to page
    await browser.navigate("https://app.example.com")

    # Get accessibility tree
    snapshot = await browser.snapshot()

    # Check for common issues
    issues = []

    # Check for missing alt text
    if not check_alt_text(snapshot.accessibility_tree):
        issues.append("Missing alt text on images")

    # Test keyboard navigation
    await browser.press_key("Tab")
    await browser.press_key("Tab")
    await browser.press_key("Enter")

    # Check focus indicators
    focus_snapshot = await browser.snapshot()
    if not check_focus_indicators(focus_snapshot):
        issues.append("Missing focus indicators")

    # Test screen reader labels
    if not check_aria_labels(snapshot.accessibility_tree):
        issues.append("Missing ARIA labels")

    await browser.cleanup()

    return issues
```

### 5. E2E User Journey Testing

**Purpose**: Test complete user workflows

```python
# Example: E2E user journey test
async def test_user_journey():
    """Test complete user journey with Browser MCP."""

    browser = get_mcp_integration("browser", config={"enabled": True})
    await browser.initialize()

    journey_steps = [
        # Landing page
        ("navigate", "https://app.example.com"),
        ("screenshot", "journey/01-landing.png"),

        # Login
        ("click", "#login-btn", "Login button"),
        ("type", "#username", "testuser@example.com", "Username field"),
        ("type", "#password", "TestPass123!", "Password field"),
        ("click", "#submit", "Submit login"),
        ("wait", 2),
        ("screenshot", "journey/02-dashboard.png"),

        # Create item
        ("click", "#create-new", "Create new button"),
        ("type", "#item-name", "Test Item", "Item name field"),
        ("select", "#category", ["Work"], "Category selector"),
        ("click", "#save", "Save button"),
        ("screenshot", "journey/03-item-created.png"),

        # Verify and logout
        ("navigate", "https://app.example.com/items"),
        ("screenshot", "journey/04-items-list.png"),
        ("click", "#user-menu", "User menu"),
        ("click", "#logout", "Logout option")
    ]

    for step in journey_steps:
        action = step[0]

        if action == "navigate":
            await browser.navigate(step[1])
        elif action == "click":
            await browser.click(step[1], step[2])
        elif action == "type":
            await browser.type_text(step[1], step[2], description=step[3])
        elif action == "select":
            await browser.select_option(step[1], step[2], step[3])
        elif action == "wait":
            await browser.wait(step[1])
        elif action == "screenshot":
            await browser.screenshot(path=step[1])

    await browser.cleanup()
```

## Integration with SuperClaude Commands

### Test Command with Browser Support

```bash
# Run UI tests with Browser MCP
/sc:test --type e2e --browser

# Visual regression testing
/sc:test --type visual --browser --coverage

# Accessibility testing
/sc:test --type accessibility --browser
```

### Combined Workflow Example

```python
# Example: Complete test suite with Browser MCP
async def run_complete_test_suite():
    """Run complete test suite including browser tests."""

    results = {
        "unit_tests": await run_unit_tests(),
        "integration_tests": await run_integration_tests(),
        "browser_tests": {
            "visual_regression": await run_visual_regression_test(),
            "accessibility": await test_accessibility(),
            "user_journey": await test_user_journey()
        }
    }

    # Generate report
    generate_test_report(results)

    return results
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/browser-tests.yml
name: Browser Tests

on: [push, pull_request]

jobs:
  browser-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v2

      - name: Setup Node.js
        uses: actions/setup-node@v2
        with:
          node-version: '18'

      - name: Install Browser MCP
        run: |
          npm install -g @browsermcp/mcp@latest

      - name: Run Browser Tests
        env:
          CI: true
          BROWSER_MCP_HEADLESS: true
        run: |
          python -m pytest tests/test_browser_mcp.py

      - name: Upload Screenshots
        if: failure()
        uses: actions/upload-artifact@v2
        with:
          name: test-screenshots
          path: .superclaude_metrics/screenshots/
```

## Troubleshooting

### Common Issues and Solutions

1. **Browser MCP not found**:
   ```bash
   # Reinstall Browser MCP
   claude mcp remove browser
   claude mcp add -s user -- browser npx -y @browsermcp/mcp@latest
   ```

2. **Headless mode issues**:
   ```python
   # Force headless mode
   browser_config = BrowserConfig(mode=BrowserMode.headless)
   ```

3. **Timeout errors**:
   ```python
   # Increase timeout
   browser_config = BrowserConfig(timeout=60000)  # 60 seconds
   ```

4. **Screenshot directory errors**:
   ```python
   # Ensure directory exists
   os.makedirs(".superclaude_metrics/screenshots", exist_ok=True)
   ```

## Best Practices

1. **Always use headless mode in CI/CD**
2. **Clean up browser sessions after tests**
3. **Use descriptive selectors and descriptions**
4. **Implement proper wait strategies**
5. **Capture screenshots on failures**
6. **Test accessibility alongside functionality**
7. **Use Page Object Model for complex UIs**
8. **Run visual regression tests on consistent environments**

## Security Considerations

- Browser MCP operates locally only
- No external network access required
- Credentials should never be hardcoded
- Use environment variables for sensitive data
- Review console logs for sensitive information
- Clear browser data between test runs
