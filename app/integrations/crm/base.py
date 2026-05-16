from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CompanyRecord:
    name: str
    website: str | None = None
    country: str | None = None
    industry: str | None = None


@dataclass(frozen=True)
class ContactRecord:
    email: str
    first_name: str | None = None
    last_name: str | None = None
    job_title: str | None = None
    company_name: str | None = None


@dataclass(frozen=True)
class TaskRecord:
    title: str
    body: str | None = None


@dataclass(frozen=True)
class CRMResult:
    external_id: str
    url: str | None = None
    raw: dict | None = None


class CRMAdapter(Protocol):
    def upsert_company(self, company: CompanyRecord) -> CRMResult: ...

    def upsert_contact(self, contact: ContactRecord) -> CRMResult: ...

    def create_note(self, contact_id: str, note: str) -> CRMResult: ...

    def create_task(self, contact_id: str, task: TaskRecord) -> CRMResult: ...
