# Project Conventions

> **Template**: Customize this file for your team's conventions.
> Delete this notice and the example content, then fill in your own.

## Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Files | snake_case | `user_service.py` |
| Classes | PascalCase | `UserService` |
| Functions | snake_case | `get_user_by_id()` |
| Constants | UPPER_SNAKE | `MAX_RETRY_COUNT` |
| API routes | kebab-case | `/api/user-profiles` |
| DB tables | snake_case plural | `user_profiles` |

## Directory Structure

```
src/
  api/           # HTTP layer (routes, middleware)
  models/        # Data models
  services/      # Business logic
  utils/         # Shared utilities
tests/
  unit/          # Unit tests (mirror src/ structure)
  integration/   # Integration tests
  e2e/           # End-to-end tests
```

## Git Conventions

- **Branch names**: `feat/`, `fix/`, `chore/`, `docs/` prefixes
- **Commit messages**: Conventional Commits format
- **PR size**: Prefer < 400 lines changed

## Testing Conventions

- Test files mirror source structure: `src/services/auth.py` -> `tests/unit/services/test_auth.py`
- Use `pytest` markers: `@pytest.mark.integration`, `@pytest.mark.slow`
- Mock external services, use real fixtures for DB tests

## Environment

- `.env` is the single source for credentials
- Never hardcode secrets in source files
- Use `.env.example` as the template (committed to repo)
