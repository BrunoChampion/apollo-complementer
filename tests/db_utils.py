from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.db.models import Base
from app.db.session import build_engine


def build_test_session() -> Generator[Session]:
    engine = build_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    with session_factory() as session:
        yield session
