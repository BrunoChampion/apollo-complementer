from app.core.config import get_settings
from app.db.repositories import RunRepository
from app.services.run_service import RunService


class Worker:
    def __init__(self, repository: RunRepository) -> None:
        self.repository = repository

    def process_run(
        self,
        run_id: str,
        *,
        sheet_path: str | None = None,
        source: str = "fake_sheet",
        sheet_id: str | None = None,
        tab_name: str | None = None,
        scheduled: bool = False,
    ):
        settings = get_settings()
        service = RunService(self.repository)
        return service.process_run(
            run_id,
            sheet_path=sheet_path or settings.fake_sheet_path,
            source=source,
            sheet_id=sheet_id,
            tab_name=tab_name,
            scheduled=scheduled,
        )
