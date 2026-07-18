from collections.abc import Iterator
from contextlib import contextmanager

from sqlmodel import SQLModel, Session, create_engine

from app.core.config import settings

sqlite_file_name = settings.DB_FILE
sqlite_url = f"sqlite:///{sqlite_file_name}"


connect_args = {"check_same_thread": False}


engine = create_engine(sqlite_url, connect_args=connect_args)


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session


def create_table() -> None:
    SQLModel.metadata.create_all(engine)
