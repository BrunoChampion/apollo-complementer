from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from smtplib import SMTP
from typing import Protocol

from app.core.config import Settings, get_settings
from app.db.models import Run

TEMPLATE_PATH = Path("app/templates/run_summary_email.txt")


class EmailSender(Protocol):
    def send(self, *, to_email: str, subject: str, body: str) -> None: ...


class NoOpEmailSender:
    def send(self, *, to_email: str, subject: str, body: str) -> None:
        return None


class SmtpEmailSender:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def send(self, *, to_email: str, subject: str, body: str) -> None:
        if not (self.settings.smtp_host and self.settings.summary_email_from):
            return

        message = EmailMessage()
        message["To"] = to_email
        message["From"] = self.settings.summary_email_from
        message["Subject"] = subject
        message.set_content(body)

        with SMTP(self.settings.smtp_host, self.settings.smtp_port) as smtp:
            if self.settings.smtp_use_tls:
                smtp.starttls()
            if self.settings.smtp_username and self.settings.smtp_password:
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
            smtp.send_message(message)


@dataclass(frozen=True)
class RenderedEmailSummary:
    to_email: str
    subject: str
    body: str


def build_email_sender(settings: Settings | None = None) -> EmailSender:
    settings = settings or get_settings()
    if not (settings.summary_email_to and settings.summary_email_from and settings.smtp_host):
        return NoOpEmailSender()
    return SmtpEmailSender(settings)


def render_run_summary_email(
    run: Run,
    *,
    to_email: str,
    template_path: Path = TEMPLATE_PATH,
) -> RenderedEmailSummary:
    summary = run.summary or {}
    skipped_count = summary.get("skipped_count", 0)
    subject = (
        f"Revenue Copilot: {run.total_rows} filas procesadas, "
        f"{run.success_count} OK, {run.error_count} errores"
    )
    body = template_path.read_text(encoding="utf-8").format(
        run_id=run.id,
        status=run.status,
        source=run.source,
        sheet_link=_sheet_link(run),
        total_rows=run.total_rows,
        success_count=run.success_count,
        error_count=run.error_count,
        skipped_count=skipped_count,
        pending_rows=", ".join(str(row) for row in summary.get("pending_rows", [])) or "-",
        rejected_rows=", ".join(str(row) for row in summary.get("rejected_rows", [])) or "-",
        notes=_summary_notes(summary),
    )
    return RenderedEmailSummary(to_email=to_email, subject=subject, body=body)


def send_run_summary_email(
    run: Run,
    *,
    sender: EmailSender | None = None,
    settings: Settings | None = None,
) -> None:
    settings = settings or get_settings()
    to_email = settings.summary_email_to or run.created_by
    if not to_email:
        return

    sender = sender or build_email_sender(settings)
    rendered = render_run_summary_email(run, to_email=to_email)
    sender.send(to_email=rendered.to_email, subject=rendered.subject, body=rendered.body)


def _sheet_link(run: Run) -> str:
    if run.source == "google_sheets" and run.sheet_id:
        return f"https://docs.google.com/spreadsheets/d/{run.sheet_id}"
    return str((run.summary or {}).get("sheet_path") or run.sheet_id or "-")


def _summary_notes(summary: dict) -> str:
    notes = []
    if summary.get("skipped_due_to_limit"):
        notes.append(f"Skipped due to batch limit: {summary['skipped_due_to_limit']}")
    if summary.get("batch_limit"):
        notes.append(f"Batch limit: {summary['batch_limit']}")
    return "\n".join(notes) if notes else "-"
