# Quality Checklist

Use this checklist before promoting candidates, approving drafts, or sending emails.

## Candidate Quality (Before Promotion)

- [ ] **Company name** is present and real (not "N/A" or "Unknown").
- [ ] **Prospect name** is present (first + last ideal).
- [ ] **Title** is relevant to buyer persona (COO, CTO, Head of Ops, etc.).
- [ ] **Email** is present and not generic (`info@`, `contact@`, `support@`, `noreply@`).
- [ ] **Country** is in LATAM (if targeting LATAM).
- [ ] **Not a duplicate** (check `dedupe_key` or `duplicate_of`).
- [ ] **Preliminary score ≥ 40** (PromotionService rejects below this).

## Enrichment Quality (Before Drafting)

- [ ] **Enrichment status** = `enriched` (not `failed` or `insufficient_data`).
- [ ] **Confidence score ≥ 65** (Draft gating blocks below this).
- [ ] **At least 2 evidence items** with real source URLs.
- [ ] **B2B fit** = `true` (B2C leads should be discarded).
- [ ] **Company size** is 20-200 employees (micro-enterprises score low).
- [ ] **No major risk flags** (e.g., "B2C", "microenterprise", "junior title").
- [ ] **Operational pain hypothesis** is specific, not generic.

## Draft Quality (Before Approval)

- [ ] **Subject line** is specific (mentions company, trigger, or use case).
- [ ] **Opening line** references real evidence (e.g., job posting, pricing page, blog).
- [ ] **No hallucinated claims** — every claim has an evidence item.
- [ ] **No generic fluff** — avoid "I hope this email finds you well" and "I am reaching out because".
- [ ] **Value proposition** is tied to a real pain or use case.
- [ ] **Call to action** is clear and low friction (e.g., "Would a 15-min call work?").
- [ ] **Tone** matches LATAM business culture (warm, direct, not overly formal).
- [ ] **Language** matches prospect country (Spanish for most LATAM, Portuguese for Brazil).

## Pre-Send Quality (Manual Gmail Review)

- [ ] **Recipient email** looks correct.
- [ ] **Company name** spelled correctly.
- [ ] **Prospect name** spelled correctly.
- [ ] **No broken links** in the email body.
- [ ] **Signature** is present and professional.
- [ ] **Unsubscribe line** is included (if required by local law).

## Red Flags (Reject Immediately)

- [ ] Email contains claims not backed by evidence.
- [ ] Enrichment returned "insufficient_data" but draft was created anyway.
- [ ] Candidate is clearly B2C (e.g., personal trainer, individual freelancer).
- [ ] Duplicate was not caught by deduplication.
- [ ] Draft is templated/generic with only company name swapped.

## Scoring Quick Reference

| Action | Minimum Score | Minimum Evidence | Minimum Confidence |
|--------|---------------|------------------|--------------------|
| Promote candidate | 40 | 0 | N/A |
| Draft email | 80 | 2 items | 65 |
| Manual research | 60 | 0+ | Any |
| Discard | < 35 | Any | Any |

## Related Docs

- [Weekly Operations Guide](weekly_operations_guide.md)
- [Credit Cost Guide](credit_cost_guide.md)
- [LATAM Benchmark Guide](latam_benchmark_guide.md)
