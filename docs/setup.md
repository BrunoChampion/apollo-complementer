# Setup

## Requirements

- Python 3.11+
- Postgres for a real deployment
- Google service account for Sheets
- Gmail OAuth refresh token for drafts
- Optional Langfuse project
- Optional SMTP account for run summaries
- Optional HubSpot private app token

## Install

```bash
pip install -e ".[dev]"
```

## Environment

Start from:

```bash
cp .env.example .env
```

For local fake-sheet development, the defaults are enough.

For Postgres:

```text
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/revenue_ops_copilot
```

For Google Sheets:

```text
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/service-account.json
GOOGLE_SHEETS_DEFAULT_TAB=Leads
APPS_SCRIPT_SHARED_SECRET=...
```

For Gmail drafts:

```text
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REFRESH_TOKEN=...
```

For summaries:

```text
SUMMARY_EMAIL_TO=seller@example.com
SUMMARY_EMAIL_FROM=ops@example.com
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USERNAME=...
SMTP_PASSWORD=...
```

## Validate

```bash
pytest
ruff check .
ruff format --check .
```

## Run API

```bash
uvicorn app.main:app --reload
```

## Local Fake-Sheet Smoke Test

```bash
curl -X POST http://127.0.0.1:8000/runs \
  -H "Content-Type: application/json" \
  -d "{\"source\":\"fake_sheet\",\"sheet_path\":\"examples/leads_demo.csv\",\"process_async\":false}"
```
