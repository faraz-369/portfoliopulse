# Deployment

## Local development

The checked-in Compose configuration is for local development. Copy `.env.example` to `.env`, install Docker Desktop, and run `docker compose up --build`. Compose starts PostgreSQL, waits for database health, applies Alembic migrations, and launches FastAPI and Streamlit. It does not seed demo data. The local Compose database defaults are development-only; never reuse them for a shared deployment. Local URLs and the demo walkthrough are in the README.

To explicitly load synthetic demo data after the services are running:

```powershell
docker compose exec -e ENABLE_DEMO_SEEDING=true backend python -m scripts.seed_demo_data
```

The seed command is idempotent and preserves existing passwords. To use a non-default local demo password, set `DEMO_PASSWORD` in the development `.env` before running the seed. The seed command refuses to run unless the environment is development and seeding is explicitly enabled.

## Production configuration requirements

No production Compose file, cloud deployment, or deployment automation is included or claimed. A production deployment must provide these settings through its runtime environment or a secret manager:

| Setting | Requirement |
|---|---|
| `ENVIRONMENT` | Must explicitly be `production`. |
| `SECRET_KEY` | Required; at least 32 characters, non-default, and generated/stored as a secret. |
| `DATABASE_URL` | Explicit PostgreSQL URL; SQLite and the local development database password are rejected. |
| `CORS_ORIGINS` | Explicit comma-separated trusted HTTPS origins; empty, wildcard, or HTTP production origins are rejected. |
| `ENABLE_DEMO_SEEDING` | Must remain false; production startup rejects true. |
| `DEMO_PASSWORD` | Must not be configured in production. |

Settings are validated while the application modules load, before the FastAPI app and database engine are initialized. Validation messages do not print secret values. Migrations remain an explicit startup operation in the local Compose command and are not coupled to synthetic-data seeding.

These configuration checks are a fail-closed baseline, not a complete production deployment plan. TLS termination, private networking, managed secrets, backups and recovery, monitoring, non-root containers, resource limits, and production CI/CD still need to be designed and verified.
