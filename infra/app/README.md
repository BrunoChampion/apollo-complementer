# Revenue Ops Copilot Infrastructure

This folder contains infrastructure services for the app itself.

## Postgres

The app uses Postgres through the root `.env`:

```bash
DATABASE_URL=postgresql+psycopg://revenue_ops:...@localhost:5432/revenue_ops_copilot
```

Start the database from the repository root:

```bash
docker compose --env-file .env -f infra/app/docker-compose.yml up -d
```

Then run migrations:

```bash
alembic upgrade head
```

Langfuse has its own Postgres in `infra/langfuse`; keep it separate from this app database.
