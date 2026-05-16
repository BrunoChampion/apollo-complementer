from collections.abc import Generator

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


def override_db() -> Generator[Session]:
    with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_db


def _headers() -> dict[str, str]:
    settings = get_settings()
    headers = {}
    if settings.apps_script_shared_secret:
        headers["x-revenue-copilot-secret"] = settings.apps_script_shared_secret
    return headers


class TestSourcingJobsCRUD:
    def setup_method(self) -> None:
        Base.metadata.drop_all(bind=TEST_ENGINE)
        Base.metadata.create_all(bind=TEST_ENGINE)

    def test_create_job(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/sourcing/jobs",
            json={
                "name": "LATAM Operations",
                "description": "Find COOs and Heads of Ops in LATAM",
                "provider": "apollo",
                "query_params": {
                    "countries": ["Argentina", "Colombia"],
                    "titles": ["COO", "Head of Operations"],
                },
                "max_candidates": 10,
                "enrich_emails": False,
            },
            headers=_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "LATAM Operations"
        assert body["provider"] == "apollo"
        assert body["max_candidates"] == 10
        assert body["is_active"] is True

    def test_list_jobs(self) -> None:
        client = TestClient(app)
        client.post(
            "/sourcing/jobs",
            json={"name": "Test Job", "provider": "apollo"},
            headers=_headers(),
        )
        response = client.get("/sourcing/jobs", headers=_headers())
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, list)
        assert len(body) >= 1

    def test_get_job(self) -> None:
        client = TestClient(app)
        create_resp = client.post(
            "/sourcing/jobs",
            json={"name": "Get Me", "provider": "apollo"},
            headers=_headers(),
        )
        job_id = create_resp.json()["id"]
        response = client.get(f"/sourcing/jobs/{job_id}", headers=_headers())
        assert response.status_code == 200
        assert response.json()["id"] == job_id

    def test_get_job_not_found(self) -> None:
        client = TestClient(app)
        response = client.get("/sourcing/jobs/nonexistent", headers=_headers())
        assert response.status_code == 404

    def test_update_job(self) -> None:
        client = TestClient(app)
        create_resp = client.post(
            "/sourcing/jobs",
            json={"name": "Before", "provider": "apollo"},
            headers=_headers(),
        )
        job_id = create_resp.json()["id"]
        response = client.patch(
            f"/sourcing/jobs/{job_id}",
            json={"name": "After", "max_candidates": 25},
            headers=_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "After"
        assert body["max_candidates"] == 25


class TestSourcingJobRun:
    def setup_method(self) -> None:
        Base.metadata.drop_all(bind=TEST_ENGINE)
        Base.metadata.create_all(bind=TEST_ENGINE)

    def test_run_job(self) -> None:
        client = TestClient(app)
        create_resp = client.post(
            "/sourcing/jobs",
            json={
                "name": "Run Test",
                "provider": "apollo",
                "query_params": {"titles": ["CEO"]},
                "max_candidates": 5,
                "enrich_emails": False,
            },
            headers=_headers(),
        )
        job_id = create_resp.json()["id"]
        response = client.post(
            f"/sourcing/jobs/{job_id}/run",
            headers=_headers(),
        )
        assert response.status_code == 200
        body = response.json()
        assert body["job_id"] == job_id
        assert body["status"] == "completed"
        assert body["total_found"] <= 5
        assert "imported" in body
        assert "emails_enriched" in body

    def test_run_job_not_found(self) -> None:
        client = TestClient(app)
        response = client.post(
            "/sourcing/jobs/nonexistent/run",
            headers=_headers(),
        )
        assert response.status_code == 404
