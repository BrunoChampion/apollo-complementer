import csv
from pathlib import Path

from app.domain.candidates import SourceCandidate, SourceProvider
from app.integrations.imports.base import (
    ApolloCsvMapper,
    FindymailCsvMapper,
    GenericCsvMapper,
    HunterCsvMapper,
    SnovCsvMapper,
)


def _load_first_row(fixture_name: str) -> dict[str, str]:
    path = Path(f"tests/fixtures/{fixture_name}")
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        return dict(next(reader))


class TestApolloCsvMapper:
    def test_maps_first_name_and_last_name(self) -> None:
        row = _load_first_row("apollo_sample.csv")
        mapper = ApolloCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["prospect_name"] == "Juan Perez"

    def test_maps_company_and_email(self) -> None:
        row = _load_first_row("apollo_sample.csv")
        mapper = ApolloCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["company_name"] == "Acme Inc"
        assert mapped["prospect_email"] == "juan@acme.com"
        assert mapped["prospect_title"] == "CEO"

    def test_maps_linkedin_and_country(self) -> None:
        row = _load_first_row("apollo_sample.csv")
        mapper = ApolloCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["company_linkedin_url"] == "https://linkedin.com/company/acme"
        assert mapped["prospect_linkedin_url"] == "https://linkedin.com/in/juanperez"
        assert mapped["country"] == "Argentina"

    def test_sets_source_provider(self) -> None:
        row = _load_first_row("apollo_sample.csv")
        mapper = ApolloCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["source_provider"] == SourceProvider.APOLLO.value

    def test_generates_candidate_id(self) -> None:
        row = _load_first_row("apollo_sample.csv")
        mapper = ApolloCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["candidate_id"].startswith("cand_")

    def test_validates_as_source_candidate(self) -> None:
        row = _load_first_row("apollo_sample.csv")
        mapper = ApolloCsvMapper()
        mapped = mapper.map_row(row)
        candidate = SourceCandidate.from_mapping(mapped)
        assert candidate.company_name == "Acme Inc"
        assert candidate.prospect_name == "Juan Perez"

    def test_maps_current_apollo_contacts_export_format(self) -> None:
        row = {
            "First Name": "Alejandra",
            "Last Name": "Mardones",
            "Title": "COO",
            "Company Name": "Teamcore",
            "Email Status": "Verified",
            "# Employees": "350",
            "Industry": "information technology & services",
            "Person Linkedin Url": "http://www.linkedin.com/in/alejandra-mardones",
            "Website": "https://teamcore.com",
            "Company Linkedin Url": "http://www.linkedin.com/company/teamcore-solutions",
            "City": "Santiago",
            "Country": "Chile",
            "Company Country": "Chile",
            "Technologies": "Hubspot, Salesforce, Zoho",
            "Annual Revenue": "3000000",
            "Apollo Contact Id": "69fd241b1466590001234ff4",
            "Apollo Account Id": "69fd241c146659000123501d",
            "Secondary Email": "alejandra.personal@example.com",
            "Secondary Email Status": "Verified",
        }

        mapped = ApolloCsvMapper().map_row(row)
        candidate = SourceCandidate.from_mapping(mapped)

        assert candidate.source_record_id == "69fd241b1466590001234ff4"
        assert candidate.company_name == "Teamcore"
        assert candidate.company_website == "https://teamcore.com"
        assert candidate.company_domain == "teamcore.com"
        assert candidate.prospect_name == "Alejandra Mardones"
        assert candidate.prospect_email is None
        assert candidate.company_size == "350"
        assert candidate.country == "Chile"
        assert candidate.raw_data_json["Technologies"] == "Hubspot, Salesforce, Zoho"
        assert candidate.raw_data_json["Secondary Email"] == "alejandra.personal@example.com"


class TestSnovCsvMapper:
    def test_maps_name_field(self) -> None:
        row = _load_first_row("snov_sample.csv")
        mapper = SnovCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["prospect_name"] == "Juan Perez"

    def test_maps_company_and_position(self) -> None:
        row = _load_first_row("snov_sample.csv")
        mapper = SnovCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["company_name"] == "Acme Inc"
        assert mapped["prospect_title"] == "CEO"
        assert mapped["prospect_email"] == "juan@acme.com"

    def test_sets_source_provider(self) -> None:
        row = _load_first_row("snov_sample.csv")
        mapper = SnovCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["source_provider"] == SourceProvider.SNOV.value

    def test_validates_as_source_candidate(self) -> None:
        row = _load_first_row("snov_sample.csv")
        mapper = SnovCsvMapper()
        mapped = mapper.map_row(row)
        candidate = SourceCandidate.from_mapping(mapped)
        assert candidate.company_name == "Acme Inc"
        assert candidate.prospect_name == "Juan Perez"


class TestHunterCsvMapper:
    def test_combines_first_and_last_name(self) -> None:
        row = _load_first_row("hunter_sample.csv")
        mapper = HunterCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["prospect_name"] == "Juan Perez"

    def test_maps_company_and_position(self) -> None:
        row = _load_first_row("hunter_sample.csv")
        mapper = HunterCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["company_name"] == "Acme Inc"
        assert mapped["prospect_title"] == "CEO"
        assert mapped["prospect_email"] == "juan@acme.com"

    def test_sets_source_provider(self) -> None:
        row = _load_first_row("hunter_sample.csv")
        mapper = HunterCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["source_provider"] == SourceProvider.HUNTER.value

    def test_validates_as_source_candidate(self) -> None:
        row = _load_first_row("hunter_sample.csv")
        mapper = HunterCsvMapper()
        mapped = mapper.map_row(row)
        candidate = SourceCandidate.from_mapping(mapped)
        assert candidate.company_name == "Acme Inc"
        assert candidate.prospect_name == "Juan Perez"


class TestFindymailCsvMapper:
    def test_combines_first_and_last_name(self) -> None:
        row = _load_first_row("findymail_sample.csv")
        mapper = FindymailCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["prospect_name"] == "Juan Perez"

    def test_maps_company_and_website(self) -> None:
        row = _load_first_row("findymail_sample.csv")
        mapper = FindymailCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["company_name"] == "Acme Inc"
        assert mapped["company_website"] == "https://acme.com"
        assert mapped["prospect_title"] == "CEO"

    def test_sets_source_provider(self) -> None:
        row = _load_first_row("findymail_sample.csv")
        mapper = FindymailCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["source_provider"] == SourceProvider.FINDYMAIL.value

    def test_validates_as_source_candidate(self) -> None:
        row = _load_first_row("findymail_sample.csv")
        mapper = FindymailCsvMapper()
        mapped = mapper.map_row(row)
        candidate = SourceCandidate.from_mapping(mapped)
        assert candidate.company_name == "Acme Inc"
        assert candidate.prospect_name == "Juan Perez"


class TestGenericCsvMapper:
    def test_maps_known_fields_directly(self) -> None:
        row = {
            "candidate_id": "cand_999",
            "company_name": "GenericCorp",
            "prospect_email": "ana@generic.com",
            "prospect_title": "VP Sales",
        }
        mapper = GenericCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["candidate_id"] == "cand_999"
        assert mapped["company_name"] == "GenericCorp"
        assert mapped["prospect_email"] == "ana@generic.com"

    def test_preserves_unknown_fields_in_raw_data(self) -> None:
        row = {
            "company_name": "GenericCorp",
            "custom_field": "custom_value",
        }
        mapper = GenericCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["raw_data_json"]["custom_field"] == "custom_value"

    def test_generates_candidate_id_when_missing(self) -> None:
        row = {"company_name": "NoIdCorp"}
        mapper = GenericCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["candidate_id"].startswith("cand_")

    def test_generates_candidate_id_when_empty(self) -> None:
        row = {"candidate_id": "", "company_name": "EmptyIdCorp"}
        mapper = GenericCsvMapper()
        mapped = mapper.map_row(row)
        assert mapped["candidate_id"].startswith("cand_")

    def test_validates_as_source_candidate(self) -> None:
        row = {
            "company_name": "GenericCorp",
            "prospect_name": "Ana Lopez",
            "prospect_email": "ana@generic.com",
        }
        mapper = GenericCsvMapper()
        mapped = mapper.map_row(row)
        candidate = SourceCandidate.from_mapping(mapped)
        assert candidate.company_name == "GenericCorp"
