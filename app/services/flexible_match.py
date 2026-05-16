from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def normalize_domain(value: str | None) -> str:
    text = normalize_text(value)
    text = text.removeprefix("https://").removeprefix("http://")
    text = text.removeprefix("www.")
    return text.split("/")[0].split("?")[0]


def fuzzy_contains(value: str | None, options: list[str], *, threshold: float = 0.82) -> bool:
    text = normalize_text(value)
    if not text:
        return False
    for option in options:
        candidate = normalize_text(option)
        if candidate and candidate in text:
            return True
        for token in _ngrams(text, max(1, len(candidate.split()))):
            if SequenceMatcher(None, token, candidate).ratio() >= threshold:
                return True
    return False


def buyer_title_category(title: str | None) -> str | None:
    text = normalize_text(title)
    if not text:
        return None

    decision_maker = [
        "ceo",
        "chief executive officer",
        "founder",
        "co founder",
        "cofounder",
        "owner",
        "socio",
        "partner",
        "gerente general",
        "director general",
        "managing director",
        "presidente",
        "vp",
        "vice president",
    ]
    operations_revenue = [
        "coo",
        "chief operating officer",
        "operaciones",
        "operations",
        "revenue",
        "revops",
        "sales ops",
        "go to market",
        "gtm",
        "comercial",
        "ventas",
        "growth",
        "customer success",
    ]
    technical_influencer = [
        "cto",
        "chief technology officer",
        "cio",
        "chief information officer",
        "technology",
        "tecnologia",
        "data",
        "automation",
        "automatizacion",
        "ai",
        "ia",
        "digital",
        "sistemas",
    ]
    seniority = ["head", "director", "gerente", "manager", "lead", "lider", "jefe"]

    if fuzzy_contains(text, decision_maker):
        return "decision_maker"
    if fuzzy_contains(text, operations_revenue):
        return "ops_revenue_buyer"
    if fuzzy_contains(text, technical_influencer):
        return "technical_influencer"
    if fuzzy_contains(text, seniority):
        return "senior_influencer"
    return None


def title_fit_score(title: str | None) -> tuple[int, str]:
    category = buyer_title_category(title)
    if category == "decision_maker":
        return 35, "decision maker title"
    if category == "ops_revenue_buyer":
        return 30, "operations/revenue buyer title"
    if category == "technical_influencer":
        return 22, "technical influencer title"
    if category == "senior_influencer":
        return 15, "senior influencer title"
    return 0, "title not clearly mapped to buyer persona"


def _ngrams(text: str, size: int) -> list[str]:
    words = text.split()
    if size <= 1:
        return words
    if len(words) < size:
        return [text]
    return [" ".join(words[index : index + size]) for index in range(len(words) - size + 1)]
