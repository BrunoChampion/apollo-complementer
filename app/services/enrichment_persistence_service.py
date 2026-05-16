from app.db.models import EnrichmentRun
from app.db.repositories import EnrichmentRepository
from app.domain.enrichment import EnrichmentResult
from app.integrations.sheets.base import SheetClient
from app.services.enrichment_sheet_writer import EnrichmentSheetWriter


class EnrichmentPersistenceService:
    """Persist enrichment results to Postgres and Google Sheets."""

    def __init__(
        self,
        repository: EnrichmentRepository,
        sheet_client: SheetClient,
    ) -> None:
        self.repository = repository
        self.sheet_client = sheet_client
        self.sheet_writer = EnrichmentSheetWriter(sheet_client)

    def persist(self, result: EnrichmentResult) -> EnrichmentRun:
        enrichment = self.repository.create_enrichment_run(
            run_id=result.run_id,
            lead_id=result.lead_id,
            status=result.enrichment_status.value,
            company_summary=result.company_summary,
            b2b_fit=result.b2b_fit,
            operational_pain_hypothesis=result.operational_pain_hypothesis,
            possible_ai_use_case=result.possible_ai_use_case,
            personalization_angle=result.personalization_angle,
            trigger_summary=result.trigger_summary,
            risk_flags=result.risk_flags,
            confidence_score=result.confidence_score,
            recommended_action=(
                result.recommended_action.value if result.recommended_action else None
            ),
            error_message=result.error_message,
        )

        if result.evidence_items:
            for item in result.evidence_items:
                self.repository.create_evidence_item(
                    enrichment_run_id=enrichment.id,
                    claim=item.claim,
                    source_type=item.source_type.value,
                    source_url=item.source_url,
                    quote_or_summary=item.quote_or_summary,
                    confidence=item.confidence,
                    used_in_message=item.used_in_message,
                )

        self._write_to_sheet(result)
        return enrichment

    def _write_to_sheet(self, result: EnrichmentResult) -> None:
        self.sheet_writer.append(result)
