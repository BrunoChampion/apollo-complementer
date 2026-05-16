# Self-Hosted Langfuse

This folder contains the local/VM Docker Compose setup for Langfuse v3.

## Setup

1. Copy the env template:

```bash
cp infra/langfuse/.env.example infra/langfuse/.env
```

2. Replace every placeholder value in `infra/langfuse/.env`.

Generate secrets with:

```bash
openssl rand -base64 32
openssl rand -hex 32
```

3. Start Langfuse:

```bash
cd infra/langfuse
docker compose up -d
```

4. Open Langfuse:

```text
http://localhost:3000
```

5. Put the initialized project keys in the app root `.env`:

```bash
LANGFUSE_HOST=http://localhost:3000
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
```

If you keep `LANGFUSE_INIT_PROJECT_PUBLIC_KEY` and `LANGFUSE_INIT_PROJECT_SECRET_KEY` in `infra/langfuse/.env`, use those same values in the app root `.env`.

## Ports

- `3000`: Langfuse web UI/API.
- `3030`: Langfuse worker, bound to localhost.
- `5433`: Langfuse Postgres, bound to localhost to avoid colliding with app Postgres defaults.
- `8123` and `9000`: ClickHouse, bound to localhost.
- `6379`: Redis, bound to localhost.
- `9090`: MinIO S3 API.
- `9091`: MinIO console, bound to localhost.

For a public VM, expose only the Langfuse web port and MinIO API when needed, and keep the rest private.
