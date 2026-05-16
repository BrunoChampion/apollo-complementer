from app.core.markets import country_market_status
from app.domain.candidates import CandidateStatus, SourceCandidate
from app.domain.leads import LeadAction, LeadRow, LeadStatus
from app.integrations.sheets.base import SheetClient
from app.integrations.sheets.constants import LEADS_HEADERS, LEADS_TAB
from app.services.flexible_match import title_fit_score
from app.services.readiness import validate_readiness


class PromotionService:
    """Evaluate candidates and promote qualifying ones to the Leads tab."""

    def __init__(self, sheet_client: SheetClient) -> None:
        self.sheet_client = sheet_client

    def should_promote(self, candidate: SourceCandidate) -> tuple[bool, str | None]:
        if candidate.candidate_status == CandidateStatus.DUPLICATE:
            return False, "candidate is duplicate"
        if not candidate.company_name:
            return False, "missing company_name"
        if not candidate.prospect_name and not candidate.prospect_title:
            return False, "missing prospect_name and prospect_title"
        if country_market_status(candidate.country) == "unsupported":
            return False, "unsupported country"
        readiness = validate_readiness(candidate)
        for key, value in readiness.as_update().items():
            setattr(candidate, key, value)
        if not readiness.ready_for_enrichment:
            return False, (
                f"{readiness.identity_validation_status}: "
                f"{readiness.identity_validation_reason}; "
                f"{readiness.icp_status}: {readiness.icp_score_reason}"
            )
        score = self._preliminary_score(candidate)
        if score < 40:
            return False, f"preliminary score too low: {score}"
        return True, None

    def _preliminary_score(self, candidate: SourceCandidate) -> int:
        score = 0
        if candidate.company_name:
            score += 20
        if candidate.prospect_name:
            score += 15
        if candidate.prospect_title:
            score += 15
            title_score, _reason = title_fit_score(candidate.prospect_title)
            score += min(title_score, 25)
        if candidate.prospect_email:
            score += 5
        if candidate.company_website or candidate.company_domain:
            score += 15
        if candidate.company_size:
            try:
                size = int(candidate.company_size)
                if 20 <= size <= 200:
                    score += 15
                elif 201 <= size <= 1000:
                    score += 10
            except ValueError:
                pass
        if country_market_status(candidate.country) == "supported":
            score += 15
        return min(score, 100)

    def promote(self, candidate: SourceCandidate) -> None:
        lead = LeadRow(
            lead_id=candidate.candidate_id,
            company_name=candidate.company_name,
            company_website=candidate.company_website,
            company_domain=candidate.company_domain,
            company_linkedin_url=candidate.company_linkedin_url,
            prospect_name=candidate.prospect_name,
            prospect_title=candidate.prospect_title,
            prospect_linkedin_url=candidate.prospect_linkedin_url,
            prospect_email=candidate.prospect_email,
            country=candidate.country,
            region=candidate.region,
            industry=candidate.industry,
            company_size=candidate.company_size,
            technologies=_raw_value(candidate, "Technologies"),
            annual_revenue=_raw_value(candidate, "Annual Revenue"),
            total_funding=_raw_value(candidate, "Total Funding"),
            latest_funding=_raw_value(candidate, "Latest Funding"),
            latest_funding_amount=_raw_value(candidate, "Latest Funding Amount"),
            apollo_contact_id=candidate.source_record_id,
            apollo_account_id=_raw_value(candidate, "Apollo Account Id"),
            source=candidate.source_provider,
            manual_company_linkedin_text=candidate.manual_company_linkedin_text,
            manual_person_linkedin_text=candidate.manual_person_linkedin_text,
            manual_company_linkedin_copied_at=candidate.manual_company_linkedin_copied_at,
            manual_person_linkedin_copied_at=candidate.manual_person_linkedin_copied_at,
            identity_validation_status=candidate.identity_validation_status,
            identity_validation_reason=candidate.identity_validation_reason,
            icp_status=candidate.icp_status,
            icp_score=candidate.icp_score,
            icp_score_reason=candidate.icp_score_reason,
            ready_for_enrichment=candidate.ready_for_enrichment,
            ready_for_draft=False,
            source_url=candidate.source_url or candidate.prospect_linkedin_url,
            action=LeadAction.RESEARCH_AND_DRAFT,
            status=LeadStatus.READY_FOR_ENRICHMENT,
            agent_note=(
                "Promoted without email. Export verified email from Apollo after fit "
                "validation."
                if not candidate.prospect_email
                else None
            ),
        )
        self.sheet_client.append_row(
            tab_name=LEADS_TAB,
            values=lead.model_dump(mode="json"),
            headers=LEADS_HEADERS,
        )

    def evaluate_and_promote(
        self,
        candidates: list[SourceCandidate],
    ) -> tuple[int, int]:
        """Evaluate candidates and promote those that qualify.

        Returns (promoted_count, rejected_count).
        """
        promoted = 0
        rejected = 0
        for candidate in candidates:
            if candidate.candidate_status == CandidateStatus.DUPLICATE:
                continue
            should_promote, _reason = self.should_promote(candidate)
            if should_promote:
                self.promote(candidate)
                candidate.candidate_status = CandidateStatus.PROMOTED_TO_LEAD
                promoted += 1
            else:
                candidate.candidate_status = (
                    CandidateStatus.DISQUALIFIED
                    if candidate.icp_status == "disqualified"
                    else CandidateStatus.NEEDS_REVIEW
                )
                rejected += 1
        return promoted, rejected


def _raw_value(candidate: SourceCandidate, key: str) -> str | None:
    if not candidate.raw_data_json:
        return None
    value = candidate.raw_data_json.get(key)
    if value is None:
        return None
    return str(value)
