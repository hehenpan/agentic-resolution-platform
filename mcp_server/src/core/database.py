from contextlib import contextmanager
from typing import Generator
from loguru import logger
from sqlmodel import create_engine, Session, SQLModel
from config import settings, BASE_DIR

db_file = settings.DB_FILE
# Resolve database URL
if not db_file.startswith("sqlite") and not db_file.startswith("postgresql"):
    db_path = BASE_DIR / db_file
    DATABASE_URL = f"sqlite:///{db_path}"
else:
    DATABASE_URL = db_file

# Create engine
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def init_db() -> None:
    """
    Initializes database tables by creating metadata.
    """
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Context manager for managing database session lifecycle.
    Handles transaction commits, rollbacks, and connection closing.
    """
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("Database session transaction failed and was rolled back")
        raise
    finally:
        session.close()
