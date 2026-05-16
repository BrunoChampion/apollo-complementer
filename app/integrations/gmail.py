import base64
from email.message import EmailMessage
from typing import Any, Protocol

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core.config import get_settings

GMAIL_COMPOSE_SCOPE = "https://www.googleapis.com/auth/gmail.compose"


class GmailDraftResult(Protocol):
    gmail_draft_id: str
    gmail_draft_url: str | None


class GmailDraft:
    def __init__(self, gmail_draft_id: str, gmail_draft_url: str | None = None) -> None:
        self.gmail_draft_id = gmail_draft_id
        self.gmail_draft_url = gmail_draft_url


class GmailClientProtocol(Protocol):
    def create_draft(self, *, to: str, subject: str, body: str) -> GmailDraft: ...


class GmailClient:
    def __init__(self, service: Any | None = None) -> None:
        self._service = service

    def create_draft(self, *, to: str, subject: str, body: str) -> GmailDraft:
        raw = build_raw_email(to=to, subject=subject, body=body)
        result = (
            self._gmail()
            .users()
            .drafts()
            .create(userId="me", body={"message": {"raw": raw}})
            .execute()
        )
        draft_id = result["id"]
        return GmailDraft(
            gmail_draft_id=draft_id,
            gmail_draft_url=f"https://mail.google.com/mail/u/0/#drafts/{draft_id}",
        )

    def _gmail(self):
        if self._service is None:
            settings = get_settings()
            if not (
                settings.google_client_id
                and settings.google_client_secret
                and settings.google_refresh_token
            ):
                raise ValueError("Gmail OAuth credentials are not configured.")
            credentials = Credentials(
                token=None,
                refresh_token=settings.google_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                scopes=[GMAIL_COMPOSE_SCOPE],
            )
            self._service = build("gmail", "v1", credentials=credentials)
        return self._service


def build_raw_email(*, to: str, subject: str, body: str) -> str:
    message = EmailMessage()
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    return base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
