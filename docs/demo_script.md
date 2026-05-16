# Demo Script

Goal: show the full sourcing-to-draft flow in under 15 minutes without a custom frontend.

## Prerequisites

- Backend running: `uvicorn app.main:app --reload`
- Google Sheet with tabs: `Leads`, `Runs`, `Email Drafts`, `Imports`, `Source Candidates`, `Enrichment`
- Apps Script installed (`apps_script/Code.gs`)

---

## 1. CSV Import Demo

1. Paste a small CSV into the `Imports` tab or a temp tab.
2. Run:
   ```text
   Revenue Copilot -> Importar candidatos CSV
   ```
3. Check `Source Candidates` tab for imported rows.
4. Check `Imports` tab for batch record.

## 2. Apollo Sourcing Job Demo

1. Create a sourcing job via API:
   ```bash
   curl -X POST http://127.0.0.1:8000/sourcing/jobs \
     -H "Content-Type: application/json" \
     -H "x-revenue-copilot-secret: $SECRET" \
     -d '{
       "name": "LATAM COOs",
       "provider": "apollo",
       "query_params": {
         "countries": ["Argentina", "Colombia"],
         "titles": ["COO", "Head of Operations"]
       },
       "max_candidates": 10,
       "enrich_emails": false
     }'
   ```
2. Run the job:
   ```bash
   curl -X POST http://127.0.0.1:8000/sourcing/jobs/{job_id}/run \
     -H "x-revenue-copilot-secret: $SECRET"
   ```
3. Verify `Source Candidates` tab has new rows.
4. Verify `sourcing_job_runs` table has the run record.

## 3. Promotion Demo

1. In `Source Candidates`, mark 2-3 rows as selected (or use API).
2. Run:
   ```text
   Revenue Copilot -> Promover candidatos seleccionados
   ```
3. Check `Leads` tab for promoted rows.
4. Rejected rows stay in `Source Candidates` with status `needs_review`.

## 4. Enrichment Demo

1. Run:
   ```text
   Revenue Copilot -> Enriquecer pendientes
   ```
2. Check `Enrichment` tab for enrichment results.
3. Review `recommended_action` column:
   - `draft` → ready for next step.
   - `needs_manual_research` → investigate or skip.
   - `discard` → remove from pipeline.

## 5. Draft Demo

1. Run:
   ```text
   Revenue Copilot -> Enriquecer y redactar
   ```
2. Check `Email Drafts` tab or `email_draft` column in `Leads`.
3. Verify drafts use real evidence, not generic templates.

## 6. End-to-End Orchestration Demo

1. Run the full pipeline in one API call:
   ```bash
   curl -X POST http://127.0.0.1:8000/orchestrate \
     -H "Content-Type: application/json" \
     -H "x-revenue-copilot-secret: $SECRET" \
     -d '{
       "job_run_id": "your_job_run_id",
       "run_id": "demo_e2e"
     }'
   ```
2. Response shows:
   - `candidates_processed`
   - `promoted`
   - `rejected`
   - `enrichment_results`
   - `drafts_created`

## 7. Gmail Draft Demo

1. Approve rows with good drafts (set `action = approve`).
2. Run:
   ```text
   Revenue Copilot -> Crear borradores Gmail aprobados
   ```
3. Check Gmail for drafts.
4. Review manually before sending.

## 8. Export Demo

```bash
python scripts/export_smartlead_csv.py \
  --fake --sheet-path tests/fixtures/leads_export.csv \
  --output smartlead_export.csv
```

## Talking Points

- Sheets stays the seller UI.
- Apollo API is optional and credit-budgeted.
- Enrichment decides quality before drafting.
- Evidence-backed drafts reduce unsupported personalization.
- Human approval at every critical step (promote, draft, send).
- No auto-send, no LinkedIn automation, no scraping.
- Langfuse/DB make debugging auditable.
- HubSpot is optional.

## Full Flow Summary

```text
CSV / Apollo Job
    |
    v
Source Candidates
    |
    v
Promote -> Leads
    |
    v
Enrich -> Evidence + Score
    |
    v
Gate -> Draft (if score >= 80, evidence >= 2, confidence >= 65)
    |
    v
Review -> Approve
    |
    v
Gmail Draft -> Manual Send
    |
    v
Track Reply -> Update Sheet
```
# Third Implementation Demo Notes

The current implementation adds an iterative enrichment researcher with tools:

- `web_search` reads search snippets only.
- `analyze_website_stack` inspects the company homepage for CRM/chat/ecommerce signals.
- `github_search_org` checks public GitHub org signals best-effort.

Demo flow:

1. Promote or select a Spanish-speaking high-ticket B2B lead.
2. Run enrichment and draft.
3. Review the `enrichment_result`, evidence, and draft in Google Sheets.
4. Add `revision_instruction` in the Sheet.
5. Run `POST /enrichment/revise` to revise without re-running enrichment.

Brazil and non-Spanish-speaking markets should be discarded or held for manual review; they should not generate drafts.
