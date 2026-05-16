import shutil
from pathlib import Path

from app.core.config import Settings
from app.core.langfuse import InMemoryTracer, NoOpTracer, get_tracer, mask_langfuse_data
from app.db.repositories import RunRepository
from app.services.run_service import RunService
from tests.db_utils import build_test_session

WORKING_TRACE = Path("tests/fixtures/leads_trace_working.csv")


def test_noop_tracer_is_default_without_langfuse_keys() -> None:
    tracer = get_tracer(Settings(langfuse_public_key=None, langfuse_secret_key=None))

    assert isinstance(tracer, NoOpTracer)


def test_run_service_emits_run_and_row_metadata() -> None:
    shutil.copyfile("tests/fixtures/leads_sample.csv", WORKING_TRACE)
    session = next(build_test_session())
    repository = RunRepository(session)
    service = RunService(repository)
    run = service.create_run(source="fake_sheet", sheet_id=str(WORKING_TRACE))
    tracer = InMemoryTracer()

    try:
        service.process_run(
            run.id,
            sheet_path=str(WORKING_TRACE),
            tracer=tracer,
        )

        run_span = next(span for span in tracer.spans if span.name == "run.process")
        row_span = next(
            span
            for span in tracer.spans
            if span.name == "row.process" and span.metadata["lead_id"] == "lead_good_001"
        )
        error_span = next(span for span in tracer.spans if span.name == "row.error")

        assert run_span.metadata["run_id"] == run.id
        assert run_span.metadata["source"] == "fake_sheet"
        assert run_span.metadata["batch_limit"] == 10
        assert row_span.metadata["action"] == "research_and_draft"
        assert row_span.metadata["company_name"] == "Andes ERP Partners"
        assert error_span.metadata["status"] == "error"
    finally:
        if WORKING_TRACE.exists():
            WORKING_TRACE.unlink()


def test_langfuse_mask_redacts_sensitive_fields_and_emails() -> None:
    masked = mask_langfuse_data(
        {
            "prospect_email": "ana@example.com",
            "manual_person_linkedin_text": "Very long LinkedIn profile",
            "message": "contact ana@example.com",
            "company_name": "Acme",
        }
    )

    assert masked["prospect_email"] == "[REDACTED]"
    assert masked["manual_person_linkedin_text"] == "[REDACTED]"
    assert masked["message"] == "contact [REDACTED_EMAIL]"
    assert masked["company_name"] == "Acme"


def test_in_memory_tracer_records_generation_metadata() -> None:
    tracer = InMemoryTracer()

    with tracer.generation(
        "draft.openai.responses",
        model="gpt-test",
        input={"lead_id": "lead-1"},
        metadata={"feature": "drafting"},
    ) as generation:
        generation.update(output={"ok": True}, usage={"input": 1, "output": 2})

    assert tracer.generations[0].name == "draft.openai.responses"
    assert tracer.generations[0].metadata["model"] == "gpt-test"
    assert tracer.generations[0].metadata["feature"] == "drafting"
