from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any

from app.core.markets import country_market_status
from app.graph.state import LeadState

FACTUAL_SIGNALS = (
    r"\d",
    "contrat",
    "hiring",
    "busca",
    "hubspot",
    "salesforce",
    "intercom",
    "zendesk",
    "shopify",
    "woocommerce",
    "funding",
    "inversion",
    "inversión",
    "expansion",
    "expansión",
    "clientes",
)

SPANISH_MARKERS = (
    "hola",
    "vi que",
    "equipo",
    "empresa",
    "tiene",
    "sentido",
    "conversar",
    "operaciones",
    "ventas",
)

NON_SPANISH_MARKERS = (
    "hello",
    "hi ",
    "olá",
    "voce",
    "você",
    "equipe",
)

BASE_AVOID_PHRASES = (
    "i hope this email finds you well",
    "i am reaching out because",
    "just checking in",
    "wanted to touch base",
    "circle back",
    "quick question",
    "espero que este correo te encuentre bien",
    "me pongo en contacto porque",
)


def verify_claims_against_evidence(state: LeadState) -> dict[str, Any]:
    draft = _draft_text(state)
    evidence_texts = _evidence_texts(state.get("evidence_items", []))
    unsupported = []

    for sentence in _sentences(draft):
        if not _is_strong_claim(sentence):
            continue
        if not _supported_by_evidence(sentence, evidence_texts):
            unsupported.append(sentence)

    if unsupported:
        return {
            "status": "needs_revision",
            "quality_issues": state.get("quality_issues", []) + [
                f"unsupported claim: {claim}" for claim in unsupported
            ],
            "agent_note": "Draft needs revision: unsupported factual claim.",
        }
    return {"status": "claims_verified"}


def language_validator(state: LeadState) -> dict[str, Any]:
    lead = state.get("lead", {})
    country = lead.get("country")
    if country_market_status(country) == "unsupported":
        return {
            "status": "needs_revision",
            "agent_note": "Draft not generated: country is unsupported for Spanish ICP.",
        }

    text = _draft_text(state).lower()
    has_spanish = any(marker in text for marker in SPANISH_MARKERS)
    has_non_spanish = any(marker in text for marker in NON_SPANISH_MARKERS)
    if not has_spanish or has_non_spanish:
        return {
            "status": "needs_revision",
            "quality_issues": state.get("quality_issues", []) + [
                "draft should be in professional Spanish"
            ],
            "agent_note": "Draft needs revision: language should be Spanish.",
        }
    return {"status": "language_verified"}


def tone_checker(state: LeadState) -> dict[str, Any]:
    text = _draft_text(state).lower()
    playbook = state.get("playbook", {})
    message_rules = playbook.get("message_rules", {}) if isinstance(playbook, dict) else {}
    avoid_phrases = list(BASE_AVOID_PHRASES)
    avoid_phrases.extend(message_rules.get("avoid_phrases") or [])
    detected = sorted({phrase for phrase in avoid_phrases if phrase.lower() in text})
    if detected:
        return {
            "status": "needs_revision",
            "quality_issues": state.get("quality_issues", []) + [
                f"contains avoided phrase: {phrase}" for phrase in detected
            ],
            "agent_note": "Draft needs revision: generic outbound tone detected.",
        }
    return {"status": "tone_verified"}


def route_after_guardrail(state: LeadState) -> str:
    return "write_result" if state.get("status") == "needs_revision" else "next"


def _draft_text(state: LeadState) -> str:
    return str(state.get("revised_draft") or state.get("email_draft") or "")


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _is_strong_claim(sentence: str) -> bool:
    lower = sentence.lower()
    if lower.startswith("desde nyvex trabajé recientemente"):
        return False
    if lower.startswith("en empresas b2b con ese tipo de operación suele aparecer"):
        return False
    if "tiene sentido" in lower and "hipótesis" in lower:
        return False
    number_safe = re.sub(r"\bb2b\b|2-3", "", lower)
    return any(re.search(signal, number_safe) for signal in FACTUAL_SIGNALS)


def _evidence_texts(evidence_items: list[dict[str, Any]]) -> list[str]:
    texts = []
    for item in evidence_items:
        texts.append(str(item.get("claim") or "").lower())
        texts.append(str(item.get("quote_or_summary") or "").lower())
    return [text for text in texts if text]


def _supported_by_evidence(sentence: str, evidence_texts: list[str]) -> bool:
    normalized_sentence = sentence.lower()
    for evidence in evidence_texts:
        if evidence and (evidence in normalized_sentence or normalized_sentence in evidence):
            return True
        if SequenceMatcher(None, normalized_sentence, evidence).ratio() >= 0.72:
            return True
        if _token_overlap(normalized_sentence, evidence) >= 0.55:
            return True
    return False


def _token_overlap(sentence: str, evidence: str) -> float:
    sentence_tokens = _meaningful_tokens(sentence)
    evidence_tokens = _meaningful_tokens(evidence)
    if not evidence_tokens:
        return 0.0
    return len(sentence_tokens & evidence_tokens) / len(evidence_tokens)


def _meaningful_tokens(text: str) -> set[str]:
    stopwords = {
        "con",
        "de",
        "el",
        "en",
        "la",
        "las",
        "los",
        "que",
        "the",
        "to",
        "on",
        "su",
        "sus",
        "un",
        "una",
        "vi",
    }
    return {
        token
        for token in re.findall(r"[a-záéíóúñ0-9]+", text.lower())
        if len(token) > 2 and token not in stopwords
    }
