from fastapi import Request, Depends, HTTPException, status
from loguru import logger
from sqlmodel import Session

from app.models.engines import engine as default_engine
from app.models.models import User, UserStatus
from app.services.user_service import UserService
from app.services.rbac_service import RBACServiceBase,RBACServiceSimple
from app.services.file_service import FileService
from app.core.constants import SESSION_INFO_KEY
from app.middleware.middleware import safe_get_context

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


def get_rbac_service() -> RBACServiceBase:
    """
    Dependency to get RBACServiceBase instance.
    Using RBACServiceSimple as the default implementation.
    """
    return RBACServiceSimple()


async def get_current_user(db: Session = Depends(get_db)) -> User:
    """
    Dependency to get the current active user from session info in starlette-context.
    """
    session_info = safe_get_context(SESSION_INFO_KEY)
    if not session_info:
        logger.error("Authentication failed because session context is missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    user = db.query(User).filter(User.email == session_info.email).first()
    if not user or user.status != UserStatus.ACTIVE:
        logger.error(
            "Authentication failed because user is missing or inactive: email={}",
            session_info.email,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    return user

def get_file_service(db: Session = Depends(get_db)) -> FileService:
    """
    Dependency to get FileService instance.
    """
    return FileService(dbsession=db)

