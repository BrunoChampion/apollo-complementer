# Sheet Template

Create a workbook with these tabs:

```text
Leads
Runs
Email Drafts
Imports
Source Candidates
Enrichment
```

## Leads Tab

Recommended visible columns:

```text
lead_id
company_name
company_website
company_domain
company_linkedin_url
prospect_name
prospect_title
prospect_linkedin_url
prospect_email
country
region
industry
company_size
technologies
annual_revenue
total_funding
latest_funding
latest_funding_amount
apollo_contact_id
apollo_account_id
source
manual_context
manual_company_context
manual_person_context
manual_linkedin_notes
source_url
action
status
fit_score
fit_score_reason
quality_score
quality_issues
evidence_quality
manual_context_summary
message_angle
email_subject
email_draft
revision_instruction
revision_instruction_hash
last_processed_revision_hash
revision_count
revised_draft
approved
final_subject
final_message
gmail_draft_id
gmail_draft_url
export_ready
agent_note
error_message
run_id
locked_at
processed_at
last_updated_by_agent_at
```

## Runs Tab

```text
run_id
started_at
finished_at
source
sheet_id
created_by
status
total_rows
success_count
error_count
skipped_count
drafts_created
batch_limit
notes
```

## Email Drafts Tab

```text
run_id
lead_id
created_at
company_name
prospect_name
prospect_title
prospect_email
email_subject
gmail_draft_id
gmail_draft_url
approved
sent_manually
sent_at
reply_status
notes
```

## Imports Tab

```text
import_batch_id
source_provider
source_type
file_name
created_by
created_at
total_rows
imported_count
duplicate_count
rejected_count
error_count
status
notes
```

## Source Candidates Tab

```text
candidate_id
source_provider
source_record_id
source_url
company_name
company_website
company_domain
company_linkedin_url
prospect_name
prospect_title
prospect_linkedin_url
prospect_email
country
region
industry
company_size
raw_headline
raw_company_description
raw_data_json
candidate_status
candidate_score
candidate_score_reason
dedupe_key
duplicate_of
import_batch_id
created_at
reviewed_by
reviewed_at
notes
```

## Enrichment Tab

```text
enrichment_id
run_id
lead_id
company_name
company_website
company_domain
company_linkedin_url
prospect_name
prospect_title
prospect_linkedin_url
country
industry
company_size
enrichment_status
company_summary
b2b_fit
operational_pain_hypothesis
possible_ai_use_case
personalization_angle
trigger_summary
risk_flags
evidence_count
evidence_sources
evidence_summary
evidence_urls
confidence_score
recommended_action
created_at
finished_at
error_message
```

You can also start from:

```text
examples/leads_template.csv
```

If using Google Sheets, paste `apps_script/Code.gs` and run:

```text
Revenue Copilot -> Configurar plantilla
```

Recommended actions:

```text
research_and_draft
revise
create_gmail_draft
skip
import_candidates
enrich
enrich_and_draft
source_apollo
verify_email
```

Recommended statuses:

```text
new
processing
drafted
needs_revision
revised
approved
gmail_draft_created
exported
error
skipped
imported
duplicate
enrichment_pending
enriching
enriched
insufficient_data
needs_manual_research
needs_email_verification
discarded
candidate_promoted
```

Conditional formatting:

- `processing`: blue
- `drafted`: light green
- `needs_revision`: yellow
- `revised`: green
- `gmail_draft_created`: dark green
- `error`: red
- `enrichment_pending`: light blue
- `enriched`: green
- `insufficient_data`: orange
- low evidence/quality: orange
