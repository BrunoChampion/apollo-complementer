import shutil
from pathlib import Path

from app.domain.candidates import CandidateStatus, SourceCandidate
from app.integrations.sheets.constants import LEADS_TAB, SOURCE_CANDIDATES_TAB
from app.integrations.sheets.fake_multi_tab import MultiTabFakeSheetClient
from app.services.dedupe_service import DedupeService
from app.services.import_service import CsvImportService
from app.services.promotion_service import PromotionService

TEMP_DIR = Path("C:/Users/bruno/AppData/Local/Temp/opencode/dedupe_promotion_test")


def setup_module() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def teardown_module() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)


def _make_candidate(
    candidate_id: str = "cand_001",
    email: str | None = "juan@acme.com",
    linkedin: str | None = "https://linkedin.com/in/juanperez",
    company: str = "Acme Inc",
    domain: str | None = "acme.com",
    name: str | None = "Juan Perez",
    title: str | None = "CEO",
    country: str | None = "Argentina",
    size: str | None = "50",
) -> SourceCandidate:
    return SourceCandidate.model_validate(
        {
            "candidate_id": candidate_id,
            "company_name": company,
            "company_domain": domain,
            "company_linkedin_url": "https://linkedin.com/company/acme",
            "prospect_name": name,
            "prospect_title": title,
            "prospect_email": email,
            "prospect_linkedin_url": linkedin,
            "country": country,
            "company_size": size,
            "manual_company_linkedin_text": (
                f"{company} is a B2B SaaS company with {size or 50} employees, "
                "customer support operations, onboarding and documentation workflows."
            ),
            "manual_person_linkedin_text": (
                f"{name or 'Unknown'} is {title or 'leader'} at {company} "
                "working with B2B software customers."
            ),
            "source_provider": "apollo",
        }
    )


class TestDedupeService:
    def test_duplicate_by_email(self) -> None:
        existing = [_make_candidate(candidate_id="existing_001", email="juan@acme.com")]
        service = DedupeService(existing)
        new = _make_candidate(candidate_id="new_001", email="juan@acme.com")
        dup = service.find_duplicate(new)
        assert dup is not None
        assert dup.candidate_id == "existing_001"

    def test_duplicate_by_linkedin(self) -> None:
        existing = [
            _make_candidate(
                candidate_id="existing_002",
                email=None,
                linkedin="https://linkedin.com/in/juan",
            )
        ]
        service = DedupeService(existing)
        new = _make_candidate(
            candidate_id="new_002",
            email="other@email.com",
            linkedin="https://linkedin.com/in/juan",
        )
        dup = service.find_duplicate(new)
        assert dup is not None
        assert dup.candidate_id == "existing_002"

    def test_duplicate_by_domain_and_name(self) -> None:
        existing = [
            _make_candidate(
                candidate_id="existing_003",
                email=None,
                linkedin=None,
                domain="acme.com",
                name="Juan Perez",
            )
        ]
        service = DedupeService(existing)
        new = _make_candidate(
            candidate_id="new_003",
            email=None,
            linkedin=None,
            domain="acme.com",
            name="Juan Perez",
            title="Founder",
        )
        dup = service.find_duplicate(new)
        assert dup is not None
        assert dup.candidate_id == "existing_003"

    def test_no_duplicate_when_different(self) -> None:
        existing = [_make_candidate(candidate_id="existing_004", email="juan@acme.com")]
        service = DedupeService(existing)
        new = _make_candidate(
            candidate_id="new_004",
            email="maria@cloudops.io",
            domain="cloudops.io",
            name="Maria Gomez",
            linkedin="https://linkedin.com/in/mariagomez",
        )
        assert service.find_duplicate(new) is None

    def test_mark_duplicate_sets_status_and_duplicate_of(self) -> None:
        existing = _make_candidate(candidate_id="existing_005")
        new = _make_candidate(candidate_id="new_005", email="juan@acme.com")
        service = DedupeService([existing])
        service.mark_duplicate(new, existing)
        assert new.candidate_status == CandidateStatus.DUPLICATE
        assert new.duplicate_of == "existing_005"

    def test_generate_dedupe_key_email(self) -> None:
        candidate = _make_candidate(email="juan@acme.com")
        service = DedupeService()
        assert service.generate_dedupe_key(candidate) == "email:juan@acme.com"

    def test_generate_dedupe_key_domain_name(self) -> None:
        candidate = _make_candidate(email=None, linkedin=None)
        service = DedupeService()
        assert service.generate_dedupe_key(candidate) == "domain_name:acme.com:Juan Perez"


class TestPromotionService:
    def test_should_promote_valid_candidate(self) -> None:
        client = MultiTabFakeSheetClient(directory=TEMP_DIR / "promo_1")
        service = PromotionService(client)
        candidate = _make_candidate()
        should, reason = service.should_promote(candidate)
        assert should is True
        assert reason is None

    def test_should_reject_missing_company_name(self) -> None:
        client = MultiTabFakeSheetClient(directory=TEMP_DIR / "promo_2")
        service = PromotionService(client)
        candidate = SourceCandidate.model_construct(
            candidate_id="cand_001",
            source_provider="apollo",
            company_name="",
            prospect_name="Juan Perez",
            prospect_title="CEO",
            prospect_email="juan@acme.com",
        )
        should, reason = service.should_promote(candidate)
        assert should is False
        assert reason == "missing company_name"

    def test_should_reject_missing_name_and_title(self) -> None:
        client = MultiTabFakeSheetClient(directory=TEMP_DIR / "promo_3")
        service = PromotionService(client)
        candidate = _make_candidate(name=None, title=None)
        should, reason = service.should_promote(candidate)
        assert should is False
        assert reason == "missing prospect_name and prospect_title"

    def test_should_promote_without_email_for_prefit_validation(self) -> None:
        client = MultiTabFakeSheetClient(directory=TEMP_DIR / "promo_4")
        service = PromotionService(client)
        candidate = _make_candidate(email=None)
        should, reason = service.should_promote(candidate)
        assert should is True
        assert reason is None

    def test_should_not_promote_duplicate(self) -> None:
        client = MultiTabFakeSheetClient(directory=TEMP_DIR / "promo_5")
        service = PromotionService(client)
        candidate = SourceCandidate.model_construct(
            candidate_id="cand_dup",
            source_provider="apollo",
            company_name="BigCorp",
            prospect_name="Juan",
            prospect_title="CEO",
            prospect_email="juan@bigcorp.com",
            candidate_status=CandidateStatus.DUPLICATE,
        )
        should, reason = service.should_promote(candidate)
        assert should is False

    def test_should_reject_brazil(self) -> None:
        client = MultiTabFakeSheetClient(directory=TEMP_DIR / "promo_brazil")
        service = PromotionService(client)
        should, reason = service.should_promote(_make_candidate(country="Brazil", email=None))
        assert should is False
        assert reason == "unsupported country"

    def test_promote_writes_to_leads_tab(self) -> None:
        client = MultiTabFakeSheetClient(directory=TEMP_DIR / "promo_6")
        service = PromotionService(client)
        candidate = _make_candidate(candidate_id="cand_promo_001")
        service.promote(candidate)
        leads = client.read_rows(tab_name=LEADS_TAB)
        assert len(leads) == 1
        assert leads[0].values["lead_id"] == "cand_promo_001"
        assert leads[0].values["company_name"] == "Acme Inc"

    def test_promote_carries_research_context_to_leads(self) -> None:
        client = MultiTabFakeSheetClient(directory=TEMP_DIR / "promo_context")
        service = PromotionService(client)
        candidate = _make_candidate(
            candidate_id="cand_context",
            linkedin="https://linkedin.com/in/ana",
        )
        candidate.company_website = "https://acme.com"
        candidate.company_linkedin_url = "https://linkedin.com/company/acme"
        candidate.region = "Santiago"
        candidate.raw_data_json = {
            "Technologies": "Hubspot, Salesforce",
            "Annual Revenue": "3000000",
            "Apollo Account Id": "account-1",
        }

        service.promote(candidate)

        lead = client.read_rows(tab_name=LEADS_TAB)[0].values
        assert lead["company_domain"] == "acme.com"
        assert lead["company_linkedin_url"] == "https://linkedin.com/company/acme"
        assert lead["prospect_linkedin_url"] == "https://linkedin.com/in/ana"
        assert lead["technologies"] == "Hubspot, Salesforce"
        assert lead["annual_revenue"] == "3000000"
        assert lead["apollo_account_id"] == "account-1"

    def test_evaluate_and_promote(self) -> None:
        client = MultiTabFakeSheetClient(directory=TEMP_DIR / "promo_7")
        service = PromotionService(client)
        candidates = [
            _make_candidate(candidate_id="good_001"),
            _make_candidate(
                candidate_id="bad_001",
                name=None,
                title=None,
                email=None,
            ),
        ]
        promoted, rejected = service.evaluate_and_promote(candidates)
        assert promoted == 1
        assert rejected == 1
        assert candidates[0].candidate_status == CandidateStatus.PROMOTED_TO_LEAD
        assert candidates[1].candidate_status == CandidateStatus.NEEDS_REVIEW


class TestImportServiceWithDedupeAndPromotion:
    def test_import_detects_duplicates(self) -> None:
        client = MultiTabFakeSheetClient(directory=TEMP_DIR / "import_1")
        service = CsvImportService(sheet_client=client)

        # First import
        service.import_csv(
            file_path="tests/fixtures/candidates_sample.csv",
            source_provider="apollo",
        )

        # Second import of same file should mark duplicates
        batch = service.import_csv(
            file_path="tests/fixtures/candidates_sample.csv",
            source_provider="apollo",
        )

        assert batch.duplicate_count == 3
        assert batch.imported_count == 0

        candidates = client.read_rows(tab_name=SOURCE_CANDIDATES_TAB)
        # 3 from first + 3 from second = 6 total
        assert len(candidates) == 6
        # Last 3 should be duplicates
        assert candidates[-1].values["candidate_status"] == "duplicate"
        assert candidates[-1].values["duplicate_of"] == "cand_003"

    def test_import_promotes_to_leads(self) -> None:
        client = MultiTabFakeSheetClient(directory=TEMP_DIR / "import_2")
        service = CsvImportService(sheet_client=client)

        batch = service.import_csv(
            file_path="tests/fixtures/candidates_sample.csv",
            source_provider="apollo",
            promote_to_leads=True,
        )

        assert batch.imported_count == 3
        assert batch.rejected_count == 0

        leads = client.read_rows(tab_name=LEADS_TAB)
        assert len(leads) == 3
        assert leads[0].values["status"] == "ready_for_enrichment"

    def test_import_rejects_incomplete_when_promoting(self) -> None:
        client = MultiTabFakeSheetClient(directory=TEMP_DIR / "import_3")
        service = CsvImportService(sheet_client=client)

        # Create a CSV with one incomplete row
        import csv

        csv_path = TEMP_DIR / "incomplete.csv"
        with csv_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "candidate_id",
                    "company_name",
                    "company_linkedin_url",
                    "prospect_name",
                    "prospect_title",
                    "prospect_linkedin_url",
                    "prospect_email",
                    "country",
                    "company_size",
                    "manual_company_linkedin_text",
                    "manual_person_linkedin_text",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "candidate_id": "good",
                    "company_name": "GoodCorp",
                    "company_linkedin_url": "https://linkedin.com/company/goodcorp",
                    "prospect_name": "Juan",
                    "prospect_title": "CEO",
                    "prospect_linkedin_url": "https://linkedin.com/in/juan",
                    "prospect_email": "juan@good.com",
                    "country": "Argentina",
                    "company_size": "50",
                    "manual_company_linkedin_text": (
                        "GoodCorp is a B2B SaaS company with 50 employees, "
                        "support operations and documentation workflows."
                    ),
                    "manual_person_linkedin_text": (
                        "Juan is CEO at GoodCorp and works with B2B software customers."
                    ),
                }
            )
            writer.writerow(
                {
                    "candidate_id": "bad",
                    "company_name": "BadCorp",
                    "company_linkedin_url": "https://linkedin.com/company/badcorp",
                    "prospect_name": "Nobody",
                    "prospect_title": "Intern",
                    "prospect_linkedin_url": "https://linkedin.com/in/nobody",
                    "prospect_email": "",
                    "country": "Brazil",
                    "company_size": "5000",
                    "manual_company_linkedin_text": "BadCorp has 5000 employees.",
                    "manual_person_linkedin_text": "Nobody is Intern at BadCorp.",
                }
            )

        batch = service.import_csv(
            file_path=str(csv_path),
            source_provider="apollo",
            promote_to_leads=True,
        )

        assert batch.imported_count == 1
        assert batch.rejected_count == 1

        leads = client.read_rows(tab_name=LEADS_TAB)
        assert len(leads) == 1
        assert leads[0].values["lead_id"] == "good"
