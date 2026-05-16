# Credit Cost Guide

## Apollo Credits

### Search
- **People API Search**: currently documented by Apollo as not consuming credits. It does not return email addresses or phone numbers.
- **Company / Organization search**: consumes credits according to Apollo's API pricing.

### Enrichment
- **People / email enrichment**: consumes credits according to your Apollo plan. The system only calls it after a deterministic spend policy approves the candidate.
- **Organization enrichment**: consumes credits according to Apollo's API pricing.

### Budget Defaults

| Setting | Default | Purpose |
|---------|---------|---------|
| `APOLLO_MONTHLY_CREDIT_BUDGET` | 2500 | Hard stop to prevent accidental overuse |
| `APOLLO_MAX_CANDIDATES_PER_RUN` | 50 | Limit results per sourcing job |
| `APOLLO_ENRICH_EMAILS` | `false` | Do not evaluate candidates for paid email enrichment by default |
| `APOLLO_EMAIL_ENRICHMENT_MIN_SCORE` | 75 | Minimum flexible-fit score required before calling People Enrichment |
| `APOLLO_MIN_CANDIDATE_SCORE` | 60 | Minimum pre-enrichment score to keep |

### Cost Estimation per Run

Example: sourcing job with `max_candidates = 50`, no email enrichment.

```text
People API Search: 0 credits
Total: 0 Apollo credits
```

Example: same job **with** email enrichment enabled and 8 candidates approved by policy.

```text
People API Search: 0 credits
Email enrichment: 8 approved candidates
Total: depends on Apollo's current per-enrichment credit rules for your plan
```

### Monthly Budget Safety

The system enforces a **hard stop** in `CreditBudgetService`:

1. Before each sourcing job, a minimum budget check is performed.
2. Before each paid enrichment call, the remaining Apollo budget is checked again.
3. If `used + estimated > budget`, a `BudgetExceededError` is raised and the paid call does not run.
4. After the job completes, actual enrichment credits used are recorded in `provider_usage`.

### OpenAI Costs

- **Enrichment agent**: ~1-2k tokens per lead = ~$0.005-0.02 per lead (GPT-4o-mini or GPT-5.5).
- **Draft agent**: ~2-4k tokens per lead = ~$0.01-0.04 per lead.
- **Estimated monthly cost for 100 leads**: $2-6 USD.

### Google Sheets / Gmail

- Google Sheets API: free within quotas.
- Gmail API: free within quotas.
- If using Google Workspace, ensure API access is enabled.

### HubSpot

- HubSpot Private App token required.
- Operations are free within HubSpot CRM limits.

## Credit-Saving Rules

1. **CSV before API**: Always test with CSV imports before enabling Apollo API.
2. **Enrichment before draft**: Do not run draft agent on leads with low enrichment confidence.
3. **No email enrichment by default**: Only enable `enrich_emails` when you are ready to let the policy spend credits on strong-fit candidates.
4. **Batch sizing**: Keep `max_candidates` small (25-50) per run. Multiple small runs are safer than one giant run.
5. **Review before promote**: Use the `Source Candidates` tab to review before promoting to `Leads`.
6. **No strict equality for human data**: The spend policy normalizes domains, countries, and titles, then maps flexible title variants such as `CEO`, `Founder`, `Gerente General`, and `Director de Operaciones` to buyer categories.

## Related Docs

- [LATAM Benchmark Guide](latam_benchmark_guide.md)
- [Weekly Operations Guide](weekly_operations_guide.md)
