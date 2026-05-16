import pytest
from pydantic import ValidationError

from app.playbook.loader import dump_playbook_data, load_playbook


def test_loads_default_sales_playbook() -> None:
    playbook = load_playbook()

    assert playbook.company.name == "NYVEX"
    assert "10-200 employees" in playbook.icp.company_size
    assert playbook.buyer_personas
    assert playbook.value_props
    assert playbook.message_rules.max_words_email == 120


def test_dump_playbook_returns_plain_data() -> None:
    playbook = load_playbook()

    data = dump_playbook_data(playbook)

    assert data["company"]["name"] == "NYVEX"
    assert isinstance(data["value_props"], list)
    assert "prospecting_rules" not in data


def test_invalid_playbook_fails_clearly() -> None:
    with pytest.raises(ValidationError):
        load_playbook("tests/fixtures/invalid_playbook.yaml")
