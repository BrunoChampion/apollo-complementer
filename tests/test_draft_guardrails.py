from app.graph.draft_guardrails import (
    language_validator,
    route_after_guardrail_or_repair,
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


def test_tone_checker_rejects_role_first_opener() -> None:
    result = tone_checker(
        _state(
            "Hola Sebastian, vi que en tu rol de COO lideras Delivery y Support. "
            "Tiene sentido que te las comparta brevemente?"
        )
    )

    assert result["status"] == "needs_revision"
    assert "company signal" in result["agent_note"]


def test_tone_checker_rejects_trigger_first_opener() -> None:
    result = tone_checker(
        _state(
            "Hola Manuel, vi que Vambe lanzó la Operación 70: 70 nuevos talentos "
            "en 70 días. En empresas B2B con ese tipo de operación suele aparecer "
            "una fricción. Tiene sentido que te las comparta brevemente?"
        )
    )

    assert result["status"] == "needs_revision"
    assert "operational surface" in result["agent_note"]


def test_tone_checker_rejects_precise_milestone_opener() -> None:
    result = tone_checker(
        _state(
            "Hola Sebastian, vi que Bankingly acaba de obtener su informe SOC 2 "
            "Type II con 100% de cumplimiento. Tiene sentido que te las comparta?"
        )
    )

    assert result["status"] == "needs_revision"
    assert "operational company characteristic" in result["agent_note"]


def test_tone_checker_rejects_enumerative_product_catalog_opener() -> None:
    result = tone_checker(
        _state(
            "Hola Sebastian, vi que Bankingly incluye canales digitales bancarios, "
            "alta digital, originacion de prestamos, chatbots/agentes de IA, billetera, "
            "pagos, monitoreo de fraude y transferencias. Tiene sentido que te las comparta?"
        )
    )

    assert result["status"] == "needs_revision"
    assert "listing many capabilities" in result["agent_note"]


def test_route_repairs_repairable_guardrail_once() -> None:
    state = _state("Hola Ana, vi que Acme incluye soporte, CRM, tickets y onboarding.")
    state.update(
        {
            "status": "needs_revision",
            "quality_issues": ["opener should be natural and concise, not a product catalog"],
            "draft_repair_count": 0,
        }
    )

    assert route_after_guardrail_or_repair(state) == "repair_draft"


def test_route_does_not_repair_unsupported_claim() -> None:
    state = _state("Hola Ana, vi que Acme contrató 5 developers.")
    state.update(
        {
            "status": "needs_revision",
            "quality_issues": ["unsupported claim: Acme contrató 5 developers"],
            "draft_repair_count": 0,
        }
    )

    assert route_after_guardrail_or_repair(state) == "write_result"


def test_tone_checker_rejects_trivial_ai_pitch() -> None:
    result = tone_checker(
        _state(
            "Hola Ana, vi que Acme trabaja con onboarding B2B. "
            "Podría ayudarles a generar checklist y resumir notas. "
            "Tiene sentido que te las comparta brevemente?"
        )
    )

    assert result["status"] == "needs_revision"
    assert "real architecture" in result["quality_issues"][0]


def test_tone_checker_passes_concise_operational_surface_opener() -> None:
    result = tone_checker(
        _state(
            "Hola Sebastian, vi que Bankingly trabaja con bancos y cooperativas en "
            "canales digitales, onboarding y productos de IA. "
            "Tiene sentido que te las comparta?"
        )
    )

    assert result["status"] == "tone_verified"


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
