# Benchmark Guide: LATAM Sourcing Providers

## Objective

Compare Apollo, Snov.io, Hunter, and Findymail for LATAM coverage before committing to a paid API subscription.

## Recommended Benchmark Protocol

Run a controlled test with **50-100 leads per provider** using CSV exports (not API), then enrich and score them with the built-in enrichment agent.

### 1. Prepare Test Queries

For each provider, download a CSV using the same ICP criteria:

```text
Countries: Argentina, Colombia, Mexico, Chile, Peru
Titles: COO, Head of Operations, CTO, Founder
Company size: 20-200 employees
```

### 2. Import CSVs

Use the backend or Apps Script menu:

```text
Revenue Copilot -> Importar candidatos CSV
```

### 3. Track Results

Use a dedicated Google Sheet or tab with the following columns:

| Column | Description |
|--------|-------------|
| provider | Apollo / Snov / Hunter / Findymail |
| company_found | Company name present |
| person_found | Prospect name present |
| email_found | Email present |
| email_verified | Email looks valid (not generic) |
| title_current | Title matches current role |
| country | Country matches LATAM target |
| cost_per_valid_contact | Export cost / valid contacts |
| fit_after_enrichment | Recommended action after enrichment |
| reply_result | Actual reply (tracked after outreach) |
| notes | Free text observations |

### 4. Scoring Criteria

A contact is considered **valid** only if:

- Company name is present.
- Prospect name is present.
- Email is present and not generic (no `info@`, `contact@`, `support@`).
- Title is relevant to buyer persona.
- Country is in LATAM.

### 5. Minimum Viable Quality Threshold

Before integrating any provider API, require:

- **≥ 60% valid contact rate** (email + name + company + title).
- **≥ 40% enrichment recommendation = draft** (not `discard` or `needs_manual_research`).
- **Cost per valid contact ≤ $1.50 USD** (for paid exports).

### 6. Decision Matrix

| Provider | Valid Rate | Draft Rate | Cost/Contact | Integrate API? |
|----------|------------|------------|--------------|----------------|
| Apollo   | ?          | ?          | ?            | Decide after benchmark |
| Snov     | ?          | ?          | ?            | Decide after benchmark |
| Hunter   | ?          | ?          | ?            | Decide after benchmark |
| Findymail| ?          | ?          | ?            | Decide after benchmark |

### 7. Important Notes

- **Apollo LATAM coverage is known to be weaker than US/EU.** Do not assume it works well without testing.
- Always run enrichment **before** deciding to promote to leads. The enrichment agent will flag B2C, micro-enterprises, and fake titles.
- Do not purchase annual plans until the 50-100 lead benchmark is complete.
- Prefer CSV exports for the benchmark to avoid burning API credits.

## Example Benchmark Template

Create a Google Sheet named `Sourcing Benchmark` with tabs:

1. **Raw Results** — paste provider exports here.
2. **Scoring** — one row per provider with calculated rates.
3. **Enrichment** — enrichment agent output per lead.
4. **Decision Log** — why you chose or rejected each provider.

## Related Docs

- [Credit Cost Guide](credit_cost_guide.md)
- [Weekly Operations Guide](weekly_operations_guide.md)
- [Quality Checklist](quality_checklist.md)
