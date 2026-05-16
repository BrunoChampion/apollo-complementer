import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

TEMP_DIR = Path("C:/Users/bruno/AppData/Local/Temp/opencode/sheet_imports_test")


def setup_module() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def teardown_module() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)


def _headers() -> dict[str, str]:
    settings = get_settings()
    headers = {}
    if settings.apps_script_shared_secret:
        headers["x-revenue-copilot-secret"] = settings.apps_script_shared_secret
    return headers


class TestImportFromSheetTab:
    def test_import_from_sheet_tab_requires_auth(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/imports/from_sheet_tab",
            json={"source_provider": "apollo", "temp_tab_name": "CSV Import Temp"},
        )
        settings = get_settings()
        if settings.apps_script_shared_secret:
            assert response.status_code == 401
        else:
            assert response.status_code == 200

    def test_import_from_sheet_tab_returns_batch(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/imports/from_sheet_tab",
            json={
                "source_provider": "generic",
                "temp_tab_name": "CSV Import Temp",
                "source": "fake_sheet",
            },
            headers=_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert "import_batch_id" in body
        assert body["status"] in (
            "completed",
            "completed_with_errors",
            "failed",
        )


class TestPromoteCandidates:
    def test_promote_candidates_requires_auth(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/candidates/promote",
            json={"candidate_ids": ["c1"]},
        )
        settings = get_settings()
        if settings.apps_script_shared_secret:
            assert response.status_code == 401
        else:
            assert response.status_code == 200

    def test_promote_all_candidates(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/candidates/promote",
            json={"source": "fake_sheet"},
            headers=_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert "promoted_count" in body
        assert "rejected_count" in body
        assert "total_candidates" in body


class TestEnrichmentRun:
    def test_enrichment_run_requires_auth(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/enrichment/run",
            json={"lead_ids": ["l1"]},
        )
        settings = get_settings()
        if settings.apps_script_shared_secret:
            assert response.status_code == 401
        else:
            assert response.status_code == 200

    def test_enrichment_run_processes_leads(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/enrichment/run",
            json={"source": "fake_sheet", "run_id": "test-run"},
            headers=_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert "processed_count" in body
        assert isinstance(body["results"], list)


class TestEnrichAndDraft:
    def test_enrich_and_draft_requires_auth(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/enrichment/enrich_and_draft",
            json={"lead_ids": ["l1"]},
        )
        settings = get_settings()
        if settings.apps_script_shared_secret:
            assert response.status_code == 401
        else:
            assert response.status_code == 200

    def test_enrich_and_draft_processes_leads(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/enrichment/enrich_and_draft",
            json={"source": "fake_sheet", "run_id": "test-run"},
            headers=_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert "processed_count" in body
        assert isinstance(body["results"], list)

    def test_force_requires_explicit_lead_ids(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/enrichment/enrich_and_draft",
            json={"source": "fake_sheet", "run_id": "test-run", "force": True},
            headers=_headers(),
        )

        assert response.status_code == 400
        assert "requires explicit lead_ids" in response.json()["detail"]

    def test_force_limits_selected_leads(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/enrichment/enrich_and_draft",
            json={
                "source": "fake_sheet",
                "run_id": "test-run",
                "force": True,
                "lead_ids": ["l1", "l2", "l3", "l4"],
            },
            headers=_headers(),
        )

        assert response.status_code == 400
        assert "limited to" in response.json()["detail"]
