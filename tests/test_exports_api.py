from fastapi.testclient import TestClient

from app.main import app


def test_smartlead_export_endpoint_returns_csv() -> None:
    client = TestClient(app)

    response = client.post(
        "/exports/smartlead-csv",
        json={"source": "fake_sheet", "sheet_path": "tests/fixtures/leads_export.csv"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "camila@andeserp.example.com" in response.text
    assert "luis@localshop.example.com" not in response.text
