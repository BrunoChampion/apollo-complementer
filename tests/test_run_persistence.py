from app.db.repositories import RunRepository
from tests.db_utils import build_test_session


def test_run_repository_persists_run_and_lead_run() -> None:
    session = next(build_test_session())
    repository = RunRepository(session)

    run = repository.create_run(source="fake_sheet", sheet_id="tests/fixtures/leads_sample.csv")
    lead_run = repository.create_lead_run(
        run_id=run.id,
        lead_id="lead_001",
        row_number=2,
        action="research_and_draft",
        status="completed",
        input_snapshot={"lead_id": "lead_001"},
        output_snapshot={"status": "processing"},
        finished=True,
    )
    finished = repository.finish_run(
        run.id,
        status="completed",
        total_rows=1,
        success_count=1,
        error_count=0,
        summary={"ok": True},
    )

    assert repository.get_run(run.id) is not None
    assert finished.status == "completed"
    assert finished.success_count == 1
    assert lead_run.run_id == run.id
    assert repository.list_lead_runs(run.id)[0].lead_id == "lead_001"
