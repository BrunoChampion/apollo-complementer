import shutil
from pathlib import Path

from app.core.config import Settings
from app.core.langfuse import InMemoryTracer, NoOpTracer, get_tracer
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
