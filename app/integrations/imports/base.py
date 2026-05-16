import uuid
from typing import Any, Protocol

from app.domain.candidates import SourceProvider


class CsvMapper(Protocol):
    def map_row(self, row: dict[str, str]) -> dict[str, Any]:
        """Convert external CSV row dict to internal SourceCandidate fields."""


class BaseCsvMapper:
    """Base mapper with column mapping and raw-data preservation.

    Subclasses must define `COLUMN_MAP` and `PROVIDER`.
    """

    COLUMN_MAP: dict[str, str] = {}
    PROVIDER: SourceProvider = SourceProvider.GENERIC

    def normalize_key(self, key: str) -> str:
        return key.lower().strip()

    def map_row(self, row: dict[str, str]) -> dict[str, Any]:
        mapped: dict[str, Any] = {}
        raw_data: dict[str, Any] = {}

        for key, value in row.items():
            normalized = self.normalize_key(key)
            clean_value = value.strip() if value else None
            if clean_value == "":
                clean_value = None

            if clean_value is None:
                continue

            if normalized in self.COLUMN_MAP:
                internal_key = self.COLUMN_MAP[normalized]
                mapped[internal_key] = clean_value
            else:
                raw_data[key] = clean_value

        mapped.setdefault("source_provider", self.PROVIDER.value)
        if not mapped.get("candidate_id"):
            mapped["candidate_id"] = f"cand_{uuid.uuid4().hex[:12]}"

        if raw_data:
            existing_raw = mapped.get("raw_data_json")
            if isinstance(existing_raw, dict):
                existing_raw.update(raw_data)
            else:
                mapped["raw_data_json"] = raw_data

        return mapped

    @staticmethod
    def combine_fields(row: dict[str, str], *fields: str, separator: str = " ") -> str | None:
        parts = [row.get(field, "").strip() for field in fields]
        combined = separator.join(part for part in parts if part)
        return combined if combined else None


class GenericCsvMapper(BaseCsvMapper):
    """Generic mapper that normalizes keys and preserves raw data.

    Expects CSV columns to roughly match internal field names.
    """

    COLUMN_MAP = {
        "candidate_id": "candidate_id",
        "source_record_id": "source_record_id",
        "source_url": "source_url",
        "company_name": "company_name",
        "company_website": "company_website",
        "company_domain": "company_domain",
        "company_linkedin_url": "company_linkedin_url",
        "prospect_name": "prospect_name",
        "prospect_title": "prospect_title",
        "prospect_linkedin_url": "prospect_linkedin_url",
        "prospect_email": "prospect_email",
        "country": "country",
        "region": "region",
        "industry": "industry",
        "company_size": "company_size",
        "raw_headline": "raw_headline",
        "raw_company_description": "raw_company_description",
        "candidate_status": "candidate_status",
        "candidate_score": "candidate_score",
        "candidate_score_reason": "candidate_score_reason",
        "manual_company_linkedin_text": "manual_company_linkedin_text",
        "manual_person_linkedin_text": "manual_person_linkedin_text",
        "manual_company_linkedin_copied_at": "manual_company_linkedin_copied_at",
        "manual_person_linkedin_copied_at": "manual_person_linkedin_copied_at",
        "identity_validation_status": "identity_validation_status",
        "identity_validation_reason": "identity_validation_reason",
        "icp_status": "icp_status",
        "icp_score": "icp_score",
        "icp_score_reason": "icp_score_reason",
        "ready_for_enrichment": "ready_for_enrichment",
        "ready_for_draft": "ready_for_draft",
        "dedupe_key": "dedupe_key",
        "duplicate_of": "duplicate_of",
        "import_batch_id": "import_batch_id",
        "created_at": "created_at",
        "reviewed_by": "reviewed_by",
        "reviewed_at": "reviewed_at",
        "notes": "notes",
    }
    PROVIDER = SourceProvider.GENERIC


class ApolloCsvMapper(BaseCsvMapper):
    """Mapper for Apollo.io CSV exports."""

    COLUMN_MAP = {
        "apollo contact id": "source_record_id",
        "title": "prospect_title",
        "email": "prospect_email",
        "company": "company_name",
        "company name": "company_name",
        "company website": "company_website",
        "website": "company_website",
        "company linkedin url": "company_linkedin_url",
        "person linkedin url": "prospect_linkedin_url",
            "company country": "country",
            "country": "country",
        "industry": "industry",
        "employees": "company_size",
        "# employees": "company_size",
        "city": "region",
        "company city": "region",
        "headline": "raw_headline",
        "company description": "raw_company_description",
    }
    PROVIDER = SourceProvider.APOLLO

    def map_row(self, row: dict[str, str]) -> dict[str, Any]:
        mapped = super().map_row(row)
        prospect_name = self.combine_fields(row, "First Name", "Last Name")
        if prospect_name:
            mapped["prospect_name"] = prospect_name
        if not mapped.get("country"):
            country = self.combine_fields(row, "Company Country")
            if country:
                mapped["country"] = country
        else:
            company_country = self.combine_fields(row, "Company Country")
            if company_country:
                mapped["country"] = company_country
        return mapped


class SnovCsvMapper(BaseCsvMapper):
    """Mapper for Snov.io CSV exports."""

    COLUMN_MAP = {
        "position": "prospect_title",
        "email": "prospect_email",
        "company name": "company_name",
        "company domain": "company_domain",
        "company url": "company_website",
        "company linkedin": "company_linkedin_url",
        "person linkedin": "prospect_linkedin_url",
        "country": "country",
        "industry": "industry",
        "size": "company_size",
        "city": "region",
    }
    PROVIDER = SourceProvider.SNOV

    def map_row(self, row: dict[str, str]) -> dict[str, Any]:
        mapped = super().map_row(row)
        name = self.combine_fields(row, "Name")
        if name:
            mapped["prospect_name"] = name
        return mapped


class HunterCsvMapper(BaseCsvMapper):
    """Mapper for Hunter.io CSV exports."""

    COLUMN_MAP = {
        "email": "prospect_email",
        "position": "prospect_title",
        "company": "company_name",
        "domain": "company_domain",
        "linkedin": "prospect_linkedin_url",
        "phone number": "source_record_id",  # stored as raw since no phone field
    }
    PROVIDER = SourceProvider.HUNTER

    def map_row(self, row: dict[str, str]) -> dict[str, Any]:
        mapped = super().map_row(row)
        prospect_name = self.combine_fields(row, "First Name", "Last Name")
        if prospect_name:
            mapped["prospect_name"] = prospect_name
        return mapped


class FindymailCsvMapper(BaseCsvMapper):
    """Mapper for Findymail CSV exports."""

    COLUMN_MAP = {
        "email": "prospect_email",
        "title": "prospect_title",
        "company": "company_name",
        "website": "company_website",
        "linkedin": "prospect_linkedin_url",
        "industry": "industry",
        "employees": "company_size",
        "country": "country",
    }
    PROVIDER = SourceProvider.FINDYMAIL

    def map_row(self, row: dict[str, str]) -> dict[str, Any]:
        mapped = super().map_row(row)
        prospect_name = self.combine_fields(row, "First Name", "Last Name")
        if prospect_name:
            mapped["prospect_name"] = prospect_name
        return mapped


def mapper_for_provider(provider: SourceProvider) -> CsvMapper:
    if provider == SourceProvider.APOLLO:
        return ApolloCsvMapper()
    if provider == SourceProvider.SNOV:
        return SnovCsvMapper()
    if provider == SourceProvider.HUNTER:
        return HunterCsvMapper()
    if provider == SourceProvider.FINDYMAIL:
        return FindymailCsvMapper()
    return GenericCsvMapper()
