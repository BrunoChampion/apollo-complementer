from app.services.quality import evaluate_message_quality


def test_quality_checks_flag_generic_or_unsafe_message() -> None:
    result = evaluate_message_quality(
        message="Espero que estes bien. Podemos revolucionar tu negocio con linkedin automation.",
        max_words=120,
        avoid_phrases=["Espero que estes bien", "revolucionar tu negocio"],
        evidence_items=[],
    )

    assert result.score == 0
    assert "contains avoided phrase: Espero que estes bien" in result.issues
    assert "contains avoided phrase: revolucionar tu negocio" in result.issues
    assert "missing soft CTA" in result.issues
    assert "missing evidence items" in result.issues
    assert "mentions unsafe automation" in result.issues


def test_quality_checks_accept_specific_evidence_backed_message() -> None:
    result = evaluate_message_quality(
        message="Hola Ana, vi que Pacific Data Co vende servicios B2B. Tiene sentido conversar?",
        max_words=120,
        avoid_phrases=["Espero que estes bien"],
        evidence_items=[{"claim": "vende servicios B2B"}],
    )

    assert result.score == 100
    assert result.issues == []
