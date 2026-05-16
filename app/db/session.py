from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.db.models import Base


def build_engine(database_url: str):
    engine_kwargs = {"future": True}
    if database_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
        if database_url == "sqlite:///:memory:":
            engine_kwargs["poolclass"] = StaticPool
    return create_engine(database_url, **engine_kwargs)


engine = build_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db_session() -> Generator[Session]:
    with SessionLocal() as session:
        yield session
