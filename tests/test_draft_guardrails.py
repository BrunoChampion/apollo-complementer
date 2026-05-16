from app.graph.draft_guardrails import (
    language_validator,
    tone_checker,
    verify_claims_against_evidence,
)


def _state(email_draft: str, country: str = "Mexico") -> dict:
    return {
        "run_id": "run-1",
        "lead_id": "lead-1",
        "action": "enrich_and_draft",
        "lead": {"lead_id": "lead-1", "company_name": "Acme", "country": country},
        "email_draft": email_draft,
        "evidence_items": [
            {
                "claim": "Acme uses HubSpot on its website",
                "quote_or_summary": "hubspot.net script detected",
                "source_type": "website",
            }
        ],
        "playbook": {"message_rules": {"avoid_phrases": ["plantilla generica"]}},
    }


def test_verify_claims_detects_unsupported_number() -> None:
    result = verify_claims_against_evidence(
        _state("Hola Ana, vi que Acme contrató 5 developers este mes. Tiene sentido conversar?")
    )

    assert result["status"] == "needs_revision"
    assert "unsupported claim" in result["quality_issues"][0]


def test_verify_claims_passes_with_claim_or_quote_match() -> None:
    result = verify_claims_against_evidence(
        _state("Hola Ana, vi que Acme uses HubSpot on its website. Tiene sentido conversar?")
    )

    assert result["status"] == "claims_verified"


def test_language_validator_rejects_non_spanish() -> None:
    result = language_validator(_state("Hello Ana, I saw Acme uses HubSpot.", country="Chile"))

    assert result["status"] == "needs_revision"
    assert "Spanish" in result["agent_note"]


def test_language_validator_discards_brazil() -> None:
    result = language_validator(_state("Hola Ana, vi que Acme tiene HubSpot.", country="Brazil"))

    assert result["status"] == "needs_revision"
    assert "unsupported" in result["agent_note"]


def test_tone_checker_detects_generic() -> None:
    result = tone_checker(
        _state("Hola Ana, espero que este correo te encuentre bien. Tiene sentido conversar?")
    )

    assert result["status"] == "needs_revision"
    assert "generic outbound tone" in result["agent_note"]


def test_tone_checker_passes_specific_spanish_copy() -> None:
    result = tone_checker(
        _state(
            "Hola Ana, vi que Acme usa HubSpot. "
            "Creo que podría haber 2-3 ideas aplicables a Acme. "
            "Tiene sentido que te las comparta brevemente?"
        )
    )

    assert result["status"] == "tone_verified"


def test_verify_claims_allows_hypothesis_cta_number() -> None:
    result = verify_claims_against_evidence(
        _state(
            "Hola Ana, vi que Acme uses HubSpot on its website. "
            "Creo que podría haber 2-3 ideas aplicables a Acme. "
            "Tiene sentido que te las comparta brevemente?"
        )
    )

    assert result["status"] == "claims_verified"


def test_verify_claims_allows_nyvex_credibility_line() -> None:
    result = verify_claims_against_evidence(
        _state(
            "Hola Ana, vi que Acme uses HubSpot on its website. "
            "Desde NYVEX trabajé recientemente en un sistema de IA/RAG para una "
            "empresa B2B de HR software. "
            "Creo que podría haber 2-3 ideas aplicables a Acme. "
            "Tiene sentido que te las comparta brevemente?"
        )
    )

    assert result["status"] == "claims_verified"
