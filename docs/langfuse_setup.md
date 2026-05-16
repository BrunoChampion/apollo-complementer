# Langfuse Setup

Phase 9 adds optional tracing. The app keeps working when Langfuse is not configured.

## Recommended NYVEX Setup

NYVEX will use self-hosted Langfuse. The Docker Compose setup lives in:

```text
infra/langfuse
```

Start from `infra/langfuse/.env.example`, create `infra/langfuse/.env`, replace every `CHANGE_ME` value, then run:

```bash
cd infra/langfuse
docker compose up -d
```

Langfuse will be available at:

```text
http://localhost:3000
```

## Environment

```bash
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_HOST=http://localhost:3000
```

For self-hosted Langfuse, these keys come from your local Langfuse project, not from Langfuse Cloud. If you use the headless initialization variables in `infra/langfuse/.env`, copy those same project keys into the app root `.env`.

## What Gets Traced

Current tracing captures:

- run processing spans,
- row processing spans,
- row-level errors,
- metadata for `run_id`, `lead_id`, `action`, `row_number`, source and batch limits,
- quality and fit scores when present in row outputs.

Expected metadata shape:

```json
{
  "run_id": "...",
  "lead_id": "...",
  "action": "research_and_draft",
  "company_name": "...",
  "quality_score": 82,
  "fit_score": 90
}
```

Later LLM provider integrations should attach token usage and latency at node/tool level.
