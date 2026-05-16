from __future__ import annotations

import unicodedata
from functools import lru_cache

from app.core.config import Settings, get_settings


def normalize_country(country: str | None) -> str:
    """Normalize country names for ICP checks."""
    if not country:
        return ""
    normalized = unicodedata.normalize("NFKD", country)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.lower().replace("-", " ").split())


def parse_country_list(value: str | list[str] | tuple[str, ...] | None) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        raw_values = value.split(",")
    else:
        raw_values = list(value)
    return {normalized for item in raw_values if (normalized := normalize_country(item))}


@lru_cache
def _country_sets(
    supported_countries: str,
    unsupported_countries: str,
) -> tuple[set[str], set[str]]:
    supported = parse_country_list(supported_countries)
    unsupported = parse_country_list(unsupported_countries)
    return supported, unsupported


def get_supported_country_set(settings: Settings | None = None) -> set[str]:
    settings = settings or get_settings()
    supported, _ = _country_sets(settings.supported_countries, settings.unsupported_countries)
    return supported


def get_unsupported_country_set(settings: Settings | None = None) -> set[str]:
    settings = settings or get_settings()
    _, unsupported = _country_sets(settings.supported_countries, settings.unsupported_countries)
    return unsupported


def is_supported_country(country: str | None, settings: Settings | None = None) -> bool:
    return normalize_country(country) in get_supported_country_set(settings)


def is_unsupported_country(country: str | None, settings: Settings | None = None) -> bool:
    return normalize_country(country) in get_unsupported_country_set(settings)


def country_market_status(country: str | None, settings: Settings | None = None) -> str:
    """Return supported, unsupported, unknown, or out_of_scope."""
    normalized = normalize_country(country)
    if not normalized:
        return "unknown"
    if is_unsupported_country(normalized, settings):
        return "unsupported"
    if is_supported_country(normalized, settings):
        return "supported"
    return "out_of_scope"
