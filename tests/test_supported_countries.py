from app.core.config import Settings
from app.core.markets import (
    country_market_status,
    is_supported_country,
    is_unsupported_country,
    normalize_country,
    parse_country_list,
)


def test_normalize_country_strips_accents_and_case() -> None:
    assert normalize_country("  MÉXICO ") == "mexico"
    assert normalize_country("Panamá") == "panama"
    assert normalize_country("Costa-Rica") == "costa rica"


def test_parse_country_list() -> None:
    countries = parse_country_list("Mexico, Colombia, Perú, España")
    assert countries == {"mexico", "colombia", "peru", "espana"}


def test_supported_spanish_high_ticket_countries() -> None:
    settings = Settings()

    assert is_supported_country("Mexico", settings)
    assert is_supported_country("México", settings)
    assert is_supported_country("Colombia", settings)
    assert is_supported_country("Chile", settings)
    assert is_supported_country("Peru", settings)
    assert is_supported_country("Argentina", settings)
    assert is_supported_country("Uruguay", settings)
    assert is_supported_country("Costa Rica", settings)
    assert is_supported_country("Panamá", settings)
    assert is_supported_country("Spain", settings)


def test_brazil_is_unsupported() -> None:
    settings = Settings()

    assert is_unsupported_country("Brazil", settings)
    assert is_unsupported_country("Brasil", settings)
    assert country_market_status("Brazil", settings) == "unsupported"


def test_country_market_status_distinguishes_unknown_and_out_of_scope() -> None:
    settings = Settings()

    assert country_market_status(None, settings) == "unknown"
    assert country_market_status("", settings) == "unknown"
    assert country_market_status("Germany", settings) == "out_of_scope"
    assert country_market_status("Colombia", settings) == "supported"
