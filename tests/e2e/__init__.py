"""E2E Application Generation Tests.

This package provides end-to-end testing for SuperClaude's ability to generate
complete, working applications from prompts. Unlike keyword-based tests, these
validate that generated code actually compiles, runs, and passes tests.

Modules:
    runner: Test execution engine for E2E app generation
    validators: Language-specific validation implementations
    conftest: Pytest fixtures for E2E tests
    test_e2e_apps: Pytest integration for running E2E tests
"""

__all__ = ["runner", "validators"]
