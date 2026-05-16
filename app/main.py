from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes.candidates import router as candidates_router
from app.api.routes.enrichment import router as enrichment_router
from app.api.routes.exports import router as exports_router
from app.api.routes.imports import router as imports_router
from app.api.routes.orchestration import router as orchestration_router
from app.api.routes.runs import router as runs_router
from app.api.routes.sheet_imports import router as sheet_imports_router
from app.api.routes.sourcing import router as sourcing_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.session import init_db

settings = get_settings()
configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(candidates_router)
app.include_router(enrichment_router)
app.include_router(exports_router)
app.include_router(imports_router)
app.include_router(runs_router)
app.include_router(sheet_imports_router)
app.include_router(sourcing_router)
app.include_router(orchestration_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
