import base64
from email import message_from_bytes

from app.integrations.gmail import build_raw_email


def test_build_raw_email_creates_gmail_api_payload() -> None:
    raw = build_raw_email(
        to="ana@example.com",
        subject="Idea para Pacific Data Co",
        body="Hola Ana, tiene sentido conversar?",
    )

    decoded = base64.urlsafe_b64decode(raw.encode("utf-8"))
    message = message_from_bytes(decoded)

    assert message["To"] == "ana@example.com"
    assert message["Subject"] == "Idea para Pacific Data Co"
    assert "Hola Ana" in message.get_payload()
