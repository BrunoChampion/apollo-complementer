import csv
import shutil
from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.dependencies import get_db
from app.core.config import get_settings
from app.db.models import Base
from app.db.session import build_engine
from app.main import app

API_FIXTURE = Path("tests/fixtures/leads_sample_api.csv")
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


def test_runs_api_creates_and_processes_run_with_fake_sheet() -> None:
    shutil.copyfile("tests/fixtures/leads_sample.csv", API_FIXTURE)
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)
    app.dependency_overrides[get_db] = override_db

    try:
        client = TestClient(app)
        headers = {}
        if get_settings().apps_script_shared_secret:
            headers["x-revenue-copilot-secret"] = get_settings().apps_script_shared_secret
        create_response = client.post(
            "/runs",
            json={
                "source": "fake_sheet",
                "sheet_path": str(API_FIXTURE),
                "process_async": False,
                "created_by": "test",
            },
            headers=headers,
        )

        assert create_response.status_code == 200
        body = create_response.json()
        assert body["status"] == "queued"

        get_response = client.get(f"/runs/{body['run_id']}")
        assert get_response.status_code == 200
        run = get_response.json()
        assert run["status"] == "completed"
        assert run["success_count"] == 2
        assert run["error_count"] == 2
        assert len(run["lead_runs"]) == 4

        with API_FIXTURE.open(encoding="utf-8", newline="") as file:
            rows = [row for row in csv.DictReader(file) if row.get("lead_id")]

        assert rows[0]["status"] == "drafted"
        assert rows[0]["run_id"] == body["run_id"]
        assert rows[0]["email_draft"]
        assert rows[-1]["status"] == "error"
    finally:
        app.dependency_overrides.clear()
        if API_FIXTURE.exists():
            API_FIXTURE.unlink()
