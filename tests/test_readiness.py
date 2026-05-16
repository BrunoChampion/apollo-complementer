from app.domain.leads import LeadRow
from app.services.readiness import validate_readiness


def _lead(**overrides):
    data = {
        "lead_id": "lead-1",
        "company_name": "Acme Inc",
        "company_linkedin_url": "https://linkedin.com/company/acme",
        "prospect_name": "Juan Perez",
        "prospect_title": "COO",
        "prospect_linkedin_url": "https://linkedin.com/in/juanperez",
        "country": "Argentina",
        "industry": "SaaS",
        "company_size": "50",
        "manual_company_linkedin_text": (
            "Acme Inc is a B2B SaaS company with 50 employees, support operations, "
            "onboarding and documentation workflows."
        ),
        "manual_person_linkedin_text": (
            "Juan Perez is COO at Acme Inc and works with B2B software customers."
        ),
    }
    data.update(overrides)
    return LeadRow.model_validate(data)


def test_ready_when_linkedin_identity_and_icp_are_clear() -> None:
    result = validate_readiness(_lead())

    assert result.identity_validation_status == "valid"
    assert result.icp_status == "qualified"
    assert result.ready_for_enrichment is True


def test_blocks_when_manual_linkedin_text_is_missing() -> None:
    result = validate_readiness(_lead(manual_person_linkedin_text=None))

    assert result.identity_validation_status == "missing_required_context"
    assert result.ready_for_enrichment is False


def test_blocks_identity_conflict_without_guessing_similar_people() -> None:
    result = validate_readiness(
        _lead(manual_person_linkedin_text="Juan Pablo is COO at Acme Inc.")
    )

    assert result.identity_validation_status == "identity_conflict"
    assert result.ready_for_enrichment is False


def test_unknown_headcount_requires_manual_review() -> None:
    result = validate_readiness(
        _lead(
            company_size=None,
            manual_company_linkedin_text=(
                "Acme Inc is a B2B SaaS company with support operations and documentation."
            ),
        )
    )

    assert result.icp_status == "needs_manual_review"
    assert result.ready_for_enrichment is False


def test_brazil_is_disqualified_even_when_manual_linkedin_text_is_missing() -> None:
    result = validate_readiness(
        _lead(
            country="Brazil",
            manual_company_linkedin_text=None,
            manual_person_linkedin_text=None,
        )
    )

    assert result.identity_validation_status == "blocked_unsupported_country"
    assert result.icp_status == "disqualified"
    assert result.icp_score_reason == "unsupported country"
    assert result.ready_for_enrichment is False
