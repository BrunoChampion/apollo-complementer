import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_db
from app.core.config import get_settings
from app.db.models import Base
from app.db.session import build_engine
from app.main import app

TEST_ENGINE = build_engine("sqlite:///:memory:")
TestingSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    autocommit=False,
    autoflush=False,
    future=True,
)


def override_db() -> Session:
    with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_db


def _headers() -> dict[str, str]:
    settings = get_settings()
    headers = {}
    if settings.apps_script_shared_secret:
        headers["x-revenue-copilot-secret"] = settings.apps_script_shared_secret
    return headers


class TestOrchestrateEndToEnd:
    def setup_method(self) -> None:
        Base.metadata.drop_all(bind=TEST_ENGINE)
        Base.metadata.create_all(bind=TEST_ENGINE)

    def test_orchestrate_by_job_run_id(self) -> None:
        client = TestClient(app)
        with patch("app.api.routes.orchestration.OrchestrationService") as MockService:
            instance = MagicMock()
            instance.run_end_to_end.return_value = {
                "candidates_processed": 3,
                "promoted": 2,
                "rejected": 1,
                "enrichment_results": 2,
                "drafts_created": 1,
                "job_run_id": "run_abc123",
                "run_id": "test_e2e",
            }
            MockService.return_value = instance

            response = client.post(
                "/orchestrate",
                json={"job_run_id": "run_abc123", "run_id": "test_e2e"},
                headers=_headers(),
            )
            assert response.status_code == 200
            body = response.json()
            assert body["candidates_processed"] == 3
            assert body["promoted"] == 2
            assert body["rejected"] == 1
            assert body["drafts_created"] == 1
            assert body["job_run_id"] == "run_abc123"
            instance.run_end_to_end.assert_called_once_with(
                job_run_id="run_abc123",
                candidate_ids=None,
                run_id="test_e2e",
            )

    def test_orchestrate_by_candidate_ids(self) -> None:
        client = TestClient(app)
        with patch("app.api.routes.orchestration.OrchestrationService") as MockService:
            instance = MagicMock()
            instance.run_end_to_end.return_value = {
                "candidates_processed": 1,
                "promoted": 1,
                "rejected": 0,
                "enrichment_results": 1,
                "drafts_created": 0,
                "job_run_id": None,
                "run_id": "test_ids",
            }
            MockService.return_value = instance

            response = client.post(
                "/orchestrate",
                json={
                    "candidate_ids": ["cand_x1"],
                    "run_id": "test_ids",
                },
                headers=_headers(),
            )
            assert response.status_code == 200
            body = response.json()
            assert body["candidates_processed"] == 1
            assert body["promoted"] == 1
            instance.run_end_to_end.assert_called_once_with(
                job_run_id=None,
                candidate_ids=["cand_x1"],
                run_id="test_ids",
            )

    def test_orchestrate_requires_auth(self) -> None:
        client = TestClient(app)
        settings = get_settings()
        response = client.post("/orchestrate", json={})
        if settings.apps_script_shared_secret:
            assert response.status_code == 401
        else:
            assert response.status_code == 200


class TestOrchestrationServiceUnit:
    def setup_method(self) -> None:
        from app.integrations.sheets.fake_multi_tab import MultiTabFakeSheetClient

        self.temp_dir = Path("C:/Users/bruno/AppData/Local/Temp/opencode/orchestration_unit")
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.sheet_client = MultiTabFakeSheetClient(directory=self.temp_dir)

    def test_run_end_to_end_with_job_run_id(self) -> None:
        from unittest.mock import patch

        from app.services.orchestration_service import OrchestrationService

        service = OrchestrationService(self.sheet_client)

        # Mock promotion and enrichment to avoid slow LLM/web calls
        with patch.object(
            service.promotion_service, "evaluate_and_promote", return_value=(2, 1)
        ) as mock_promote:
            with patch.object(
                service.enrich_service,
                "enrich_and_draft_leads",
                return_value=[
                    {"status": "draft_ready", "email_draft": "Hello"},
                    {"status": "needs_manual_research"},
                ],
            ) as mock_enrich:
                result = service.run_end_to_end(
                    job_run_id="run_123",
                    candidate_ids=None,
                    run_id="unit_test",
                )

        assert result["promoted"] == 2
        assert result["rejected"] == 1
        assert result["drafts_created"] == 1
        mock_promote.assert_called_once()
        mock_enrich.assert_called_once_with(lead_ids=None, run_id="unit_test")

    def test_run_end_to_end_with_candidate_ids(self) -> None:
        from unittest.mock import patch

        from app.services.orchestration_service import OrchestrationService

        service = OrchestrationService(self.sheet_client)

        with patch.object(
            service.promotion_service, "evaluate_and_promote", return_value=(1, 0)
        ):
            with patch.object(
                service.enrich_service,
                "enrich_and_draft_leads",
                return_value=[{"status": "draft_ready", "email_draft": "Hi"}],
            ):
                result = service.run_end_to_end(
                    candidate_ids=["cand_a"],
                    run_id="unit_test",
                )

        assert result["promoted"] == 1
        assert result["rejected"] == 0
        assert result["drafts_created"] == 1
