from fastapi import Header, HTTPException

from app.core.config import get_settings


def verify_apps_script_secret(
    x_revenue_copilot_secret: str | None = Header(default=None),
) -> None:
    expected_secret = get_settings().apps_script_shared_secret
    if not expected_secret:
        return
    if x_revenue_copilot_secret != expected_secret:
        raise HTTPException(status_code=401, detail="Invalid Apps Script secret")
