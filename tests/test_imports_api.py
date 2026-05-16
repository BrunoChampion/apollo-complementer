import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import app

TEMP_DIR = Path("C:/Users/bruno/AppData/Local/Temp/opencode/imports_api_test")


def setup_module() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)


def teardown_module() -> None:
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)


def _copy_fixture(name: str) -> str:
    src = Path(f"tests/fixtures/{name}")
    dst = TEMP_DIR / name
    shutil.copyfile(src, dst)
    return str(dst)


def test_imports_csv_requires_auth() -> None:
    client = TestClient(app)
    path = _copy_fixture("candidates_sample.csv")
    response = client.post(
        "/imports/csv",
        json={
            "source_provider": "apollo",
            "file_path": path,
        },
    )
    settings = get_settings()
    if settings.apps_script_shared_secret:
        assert response.status_code == 401
    else:
        assert response.status_code == 200


def test_imports_csv_returns_batch() -> None:
    client = TestClient(app)
    headers = {}
    settings = get_settings()
    if settings.apps_script_shared_secret:
        headers["x-revenue-copilot-secret"] = settings.apps_script_shared_secret

    path = _copy_fixture("candidates_sample.csv")
    response = client.post(
        "/imports/csv",
        json={
            "source_provider": "apollo",
            "file_path": path,
            "source": "fake_sheet",
        },
        headers=headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["import_batch_id"].startswith("batch_")
    assert body["source_provider"] == "apollo"
    assert body["status"] in ("completed", "completed_with_errors")
    assert body["total_rows"] >= 0


def test_imports_csv_invalid_provider_returns_400() -> None:
    client = TestClient(app)
    headers = {}
    settings = get_settings()
    if settings.apps_script_shared_secret:
        headers["x-revenue-copilot-secret"] = settings.apps_script_shared_secret

    path = _copy_fixture("candidates_sample.csv")
    response = client.post(
        "/imports/csv",
        json={
            "source_provider": "linkedin_scraper",
            "file_path": path,
        },
        headers=headers,
    )

    assert response.status_code == 400
    assert "Invalid source_provider" in response.json()["detail"]
