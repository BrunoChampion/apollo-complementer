from app.core.config import Settings
from app.domain.candidates import CandidateStatus, SourceCandidate
from app.services.apollo_enrichment_policy import ApolloEmailEnrichmentPolicy
from app.services.flexible_match import buyer_title_category, normalize_domain


def _candidate(**overrides) -> SourceCandidate:
    data = {
        "candidate_id": "apollo_p1",
        "source_provider": "apollo",
        "source_record_id": "p1",
        "company_name": "Acme",
        "company_website": "https://www.acme.com",
        "prospect_name": "Ana Perez",
        "prospect_title": "Gerente General",
        "prospect_linkedin_url": "https://linkedin.com/in/ana",
        "country": "Mexico",
    }
    data.update(overrides)
    return SourceCandidate.model_validate(data)


def test_policy_approves_high_fit_without_strict_title_equality() -> None:
    policy = ApolloEmailEnrichmentPolicy(
        Settings(apollo_email_enrichment_min_score=75)
    )

    decision = policy.evaluate(_candidate())

    assert decision.should_enrich is True
    assert decision.estimated_credits == 1
    assert decision.score >= 75


def test_policy_blocks_unsupported_country_even_with_good_title() -> None:
    decision = ApolloEmailEnrichmentPolicy().evaluate(_candidate(country="Brasil"))

    assert decision.should_enrich is False
    assert "unsupported country" in decision.guardrail_blocks


def test_policy_skips_existing_email_to_save_credits() -> None:
    decision = ApolloEmailEnrichmentPolicy().evaluate(
        _candidate(prospect_email="ana@acme.com")
    )

    assert decision.should_enrich is False
    assert decision.estimated_credits == 0
    assert "prospect already has an email" in decision.guardrail_blocks


def test_policy_blocks_duplicates() -> None:
    decision = ApolloEmailEnrichmentPolicy().evaluate(
        _candidate(candidate_status=CandidateStatus.DUPLICATE)
    )

    assert decision.should_enrich is False
    assert "candidate is a duplicate" in decision.guardrail_blocks


def test_flexible_title_and_domain_matching() -> None:
    assert buyer_title_category("Director de Operaciones") == "ops_revenue_buyer"
    assert buyer_title_category("Co-Founder & CEO") == "decision_maker"
    assert normalize_domain("https://www.acme.com/path?a=1") == "acme.com"
