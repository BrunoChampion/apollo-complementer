import csv
from io import StringIO
from typing import Literal

from pydantic import ValidationError

from app.domain.leads import LeadRow
from app.integrations.sheets.base import SheetClient

ExportPlatform = Literal["smartlead", "instantly"]

EXPORT_COLUMNS = [
    "email",
    "first_name",
    "last_name",
    "company_name",
    "company_website",
    "job_title",
    "country",
    "custom_intro",
    "pain_hypothesis",
    "message_angle",
    "email_subject",
    "email_body",
]


def export_approved_leads_csv(sheet_client: SheetClient, *, platform: ExportPlatform) -> str:
    rows = []
    for sheet_row in sheet_client.read_rows():
        try:
            lead = LeadRow.from_mapping(sheet_row.values)
        except ValidationError:
            continue
        if should_export_lead(lead):
            rows.append(map_lead_to_export_row(lead))

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=EXPORT_COLUMNS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def should_export_lead(lead: LeadRow) -> bool:
    if not lead.prospect_email:
        return False
    if not (lead.approved or lead.export_ready):
        return False
    return bool(lead.final_message or lead.revised_draft or lead.email_draft)


def map_lead_to_export_row(lead: LeadRow) -> dict[str, str]:
    first_name, last_name = split_name(lead.prospect_name)
    return {
        "email": lead.prospect_email or "",
        "first_name": first_name,
        "last_name": last_name,
        "company_name": lead.company_name,
        "company_website": lead.company_website or "",
        "job_title": lead.prospect_title or "",
        "country": lead.country or "",
        "custom_intro": lead.manual_context or "",
        "pain_hypothesis": lead.evidence_quality or "",
        "message_angle": lead.message_angle or "",
        "email_subject": lead.final_subject or lead.email_subject or "",
        "email_body": lead.final_message or lead.revised_draft or lead.email_draft or "",
    }


def split_name(name: str | None) -> tuple[str, str]:
    if not name:
        return "", ""
    parts = name.split()
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])
