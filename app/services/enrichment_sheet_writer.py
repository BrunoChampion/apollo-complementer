from __future__ import annotations

import logging
from typing import Any

from app.domain.enrichment import EnrichmentResult
from app.integrations.sheets.base import SheetClient
from app.integrations.sheets.constants import ENRICHMENT_HEADERS, ENRICHMENT_TAB

logger = logging.getLogger(__name__)


def enrichment_sheet_values(result: EnrichmentResult | dict[str, Any]) -> dict[str, Any]:
    """Build the flattened row expected by the Enrichment tab."""

    enrichment = (
        result
        if isinstance(result, EnrichmentResult)
        else EnrichmentResult.model_validate(result)
    )
    values = enrichment.model_dump(mode="json")
    values["enrichment_result_json"] = enrichment.model_dump(mode="json")
    review_required = bool(values.get("review_required"))
    if review_required and values.get("user_decision") != "approve_exception":
        values["recommended_action"] = "needs_manual_research"
    evidence_items = values.pop("evidence_items", None) or []
    values["evidence_summary"] = " | ".join(
        item.get("quote_or_summary") or item.get("claim") or ""
        for item in evidence_items[:3]
        if item.get("quote_or_summary") or item.get("claim")
    )
    values["evidence_urls"] = " | ".join(
        item.get("source_url") or ""
        for item in evidence_items
        if item.get("source_url")
    )
    return values


class EnrichmentSheetWriter:
    """Append enrichment runs to the user-visible Enrichment tab."""

    def __init__(self, sheet_client: SheetClient) -> None:
        self.sheet_client = sheet_client

    def append(self, result: EnrichmentResult | dict[str, Any]) -> None:
        values = enrichment_sheet_values(result)
        logger.info(
            "enrichment.sheet_append.start tab=%s lead_id=%s enrichment_id=%s action=%s",
            ENRICHMENT_TAB,
            values.get("lead_id"),
            values.get("enrichment_id"),
            values.get("recommended_action"),
        )
        self.sheet_client.append_row(
            tab_name=ENRICHMENT_TAB,
            values=values,
            headers=ENRICHMENT_HEADERS,
        )
        logger.info(
            "enrichment.sheet_append.done tab=%s lead_id=%s enrichment_id=%s",
            ENRICHMENT_TAB,
            values.get("lead_id"),
            values.get("enrichment_id"),
        )
