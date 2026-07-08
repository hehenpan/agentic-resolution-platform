from fastapi import Request, Depends
from sqlmodel import Session

from app.services.user_service import UserService

def get_db(request: Request):
    """
    Dependency to get database session.
    Automatically handles session close.
    """
    db_engine = getattr(request.app.state, "db_engine", default_engine)
    with Session(db_engine) as session:
        yield session  # yields control to the route, and closes session afterward


def get_user_service(db: Session = Depends(get_db)) -> UserService:
    """
    Dependency to get UserService service instance.
    """
    return UserService(dbsession=db)

