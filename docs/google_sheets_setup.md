# Google Sheets Setup

Phase 7 connects the backend to a real Google Sheet while keeping Google Sheets as the seller UI.

## Backend Environment

Set these variables:

```bash
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/service-account.json
GOOGLE_SHEETS_DEFAULT_TAB=Leads
GOOGLE_SHEETS_RUNS_TAB=Runs
GOOGLE_SHEETS_EMAIL_DRAFTS_TAB=Email Drafts
GOOGLE_SHEETS_IMPORTS_TAB=Imports
GOOGLE_SHEETS_SOURCE_CANDIDATES_TAB=Source Candidates
GOOGLE_SHEETS_ENRICHMENT_TAB=Enrichment
APPS_SCRIPT_SHARED_SECRET=choose-a-shared-secret
```

The service account needs edit access to the target spreadsheet. Share the spreadsheet with the service account email.

## Expected Sheet Tabs

The workbook contains six tabs:

```text
Leads
Runs
Email Drafts
Imports
Source Candidates
Enrichment
```

### Leads
Main tab for leads being processed. The backend reads and updates rows here.

### Runs
Execution summary for each run. The backend appends run summaries here.

### Email Drafts
Gmail drafts created for human review. Includes manual columns such as `sent_manually`, `sent_at`, and `reply_status` for the user to update.

### Imports
Records each CSV or API import batch. The backend appends import metadata here.

### Source Candidates
Candidates imported from Apollo, Snov, Hunter, Findymail or generic CSVs before deduplication and promotion to Leads.

### Enrichment
Stores enrichment results per lead, including company summary, pain hypothesis, evidence count and confidence score.

## Apps Script

1. Open the Google Sheet.
2. Go to Extensions -> Apps Script.
3. Paste `apps_script/Code.gs`.
4. Set Script Properties:

```text
REVENUE_COPILOT_API_BASE_URL=https://your-backend.example.com
REVENUE_COPILOT_SHARED_SECRET=same-value-as-APPS_SCRIPT_SHARED_SECRET
```

5. Reload the Sheet.
6. Use `Revenue Copilot -> Configurar plantilla` to create/update all six tabs with headers.
7. Use the other `Revenue Copilot` menu items to process rows.

The script calls `POST /runs`, receives a `run_id`, and returns immediately. The backend processes in the background.

## Manual Validation

1. Create a new Google Sheet.
2. Paste `apps_script/Code.gs` and run `Revenue Copilot -> Configurar plantilla`.
3. Confirm all six tabs are created with correct headers.
4. Add 3 leads to `Leads`.
5. Set `action = research_and_draft`.
6. Click `Revenue Copilot -> Procesar pendientes`.
7. Confirm the toast shows a `run_id`.
8. Confirm backend updates `status`, `run_id`, `locked_at`, and `agent_note`.
