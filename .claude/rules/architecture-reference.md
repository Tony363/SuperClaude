# Architecture Reference

> **Template**: Customize this file for your project's architecture.
> Delete this notice and the example content, then fill in your own.

## Key Components

| File | Purpose |
|------|---------|
| `src/main.py` | Application entry point, server setup |
| `src/api/routes/` | API route handlers |
| `src/models/` | Data models (ORM, Pydantic, etc.) |
| `src/services/` | Business logic layer |
| `src/config.py` | Configuration and environment loading |

## API Routes

| Router | Mount | Key Endpoints |
|--------|-------|---------------|
| `auth.py` | `/auth` | POST `/login`, GET `/me` |
| `users.py` | `/users` | CRUD endpoints |
| `health.py` | `/health` | GET `/` (health check) |

## Database Layer

- **ORM**: (e.g., SQLAlchemy, Tortoise, Prisma)
- **Database**: (e.g., PostgreSQL, SQLite)
- **Migrations**: (e.g., Alembic, Aerich)

### Key Models

| Model | Table | Purpose |
|-------|-------|---------|
| `User` | `users` | User accounts |
| `Session` | `sessions` | Auth sessions |

## External Dependencies

| Service | Purpose | Config |
|---------|---------|--------|
| Redis | Caching, sessions | `REDIS_URL` |
| S3 | File storage | `AWS_*` env vars |
