from typing import Any

from pydantic import BaseModel, ConfigDict

from app.domain.leads import LeadRow


class EvidenceItem(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    claim: str
    source_type: str
    source_url: str | None = None
    confidence: str
    used_in_message: bool = False


def extract_evidence_items(lead: LeadRow, summary: str) -> list[EvidenceItem]:
    if not summary or summary == "No manual context provided.":
        return []
    return [
        EvidenceItem(
            claim=summary[:160],
            source_type="manual_context",
            source_url=lead.source_url,
            confidence="medium",
            used_in_message=True,
        )
    ]


def evidence_to_json(items: list[EvidenceItem]) -> list[dict[str, Any]]:
    return [item.model_dump(mode="json") for item in items]
