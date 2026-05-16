# Weekly Operations Guide

## Goal

Run 25-40 highly personalized outbound emails per week without manual investigation of every lead.

## Weekly Workflow

### Monday: Sourcing

1. **Review Source Candidates tab**
   - Check weekend CSV imports or Apollo job runs.
   - Mark obvious duplicates or junk as `rejected`.

2. **Run Apollo job (if enabled)**
   ```
   Revenue Copilot -> Crear busqueda Apollo
   ```
   Or use the API:
   ```bash
   curl -X POST /sourcing/jobs/{job_id}/run
   ```
   - Verify budget before running.
   - Do not exceed 50 candidates per run.

3. **Promote candidates to Leads**
   ```
   Revenue Copilot -> Promover candidatos seleccionados
   ```
   - Only promote candidates with company, name, title, and email.
   - Reject incomplete records.

### Tuesday: Enrichment

1. **Enrich pending leads**
   ```
   Revenue Copilot -> Enriquecer pendientes
   ```
   - This runs the web enrichment agent.
   - Results are written to the `Enrichment` tab and lead rows.

2. **Review enrichment results**
   - Open the `Enrichment` tab.
   - Verify `recommended_action` for each lead:
     - `draft` → ready for email.
     - `needs_manual_research` → investigate further or skip.
     - `discard` → remove from pipeline.

3. **Quality check**
   - Do not trust scores blindly. Spot-check 3-5 leads.
   - Verify evidence items have real URLs, not hallucinated claims.

### Wednesday: Drafting

1. **Enrich and draft**
   ```
   Revenue Copilot -> Enriquecer y redactar
   ```
   - This runs enrichment + draft for leads that pass the gate.
   - Drafts are written to the `Email Drafts` tab and lead rows.

2. **Review drafts**
   - Open Gmail drafts (if `create_gmail_draft` was used).
   - Or review `email_draft` column in `Leads` tab.
   - Check for:
     - Specific evidence (not generic fluff).
     - No hallucinated claims.
     - Proper tone for LATAM (Spanish if needed).

3. **Revise if needed**
   - Set `action = revise` and add `revision_instruction`.
   - Re-run: `Revenue Copilot -> Enriquecer y redactar`.

### Thursday: Approval

1. **Approve ready drafts**
   - Set `action = approve` on rows you want to send.
   - Set `action = reject` on rows with poor drafts.

2. **Create Gmail drafts**
   ```
   Revenue Copilot -> Crear borradores Gmail aprobados
   ```
   - Only approved rows become Gmail drafts.
   - Never auto-send.

3. **Manual send from Gmail**
   - Open Gmail.
   - Review each draft one last time.
   - Send individually.

### Friday: Tracking

1. **Update replies**
   - When a lead replies, update the `reply_result` column.
   - Use `meeting_booked`, `interested`, `not_interested`, `no_reply`.

2. **Export for Smartlead/Instantly (optional)**
   ```bash
   python scripts/export_smartlead_csv.py --sheet-id YOUR_SHEET_ID
   ```

3. **Review weekly metrics**
   - Leads sourced: count in `Source Candidates`.
   - Leads promoted: count status `promoted_to_lead`.
   - Drafts created: count in `Email Drafts`.
   - Emails sent: count `reply_result` not empty.
   - Replies: count positive replies.

## Daily Limits

| Activity | Max Recommended |
|----------|----------------|
| Apollo candidates per run | 50 |
| Enrichments per batch | 25 |
| Drafts created per batch | 25 |
| Gmail drafts created | 40/day |
| Manual sends | 40/day |

## Quality Gates (Do Not Skip)

- [ ] Enrichment confidence ≥ 65 before drafting.
- [ ] At least 2 evidence items with real URLs.
- [ ] No generic templates ("I hope this email finds you well").
- [ ] No claims without evidence.
- [ ] B2B only — B2C leads are auto-discarded by scoring.

## Related Docs

- [Quality Checklist](quality_checklist.md)
- [Credit Cost Guide](credit_cost_guide.md)
- [LATAM Benchmark Guide](latam_benchmark_guide.md)
# Third Implementation Operating Notes

- Work only Spanish-speaking high-ticket markets: Mexico, Colombia, Chile, Peru, Argentina, Uruguay, Costa Rica, Panama, and Spain.
- Do not process Brazil in this workflow.
- Review `enrichment_result` before approving a draft.
- For revisions, write the desired change in `revision_instruction` on the `Leads` tab and run the enriched revise endpoint.
- The revise flow reuses existing evidence and does not spend enrichment credits again.
- If a draft is marked `needs_revision`, inspect `quality_issues` and `agent_note` before approving.
