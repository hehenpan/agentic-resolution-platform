from sqlmodel import Session
from app.models.models import User, UserStatus, SessionInfo, SessionStatus
from utils.commons import get_md5, get_current_ts, generate_sessionid
from loguru import logger


class UserService(object):
    def __init__(self, dbsession: Session):
        self.dbsession = dbsession

    def create_user(self, email:str,
                    password:str,
                    user_type:int,
                    ) -> bool:

        user = User()
        user.email = email
        user.pwd_md5 = get_md5(password)
        user.user_type = user_type
        user.status = UserStatus.ACTIVE
        user.create_ts = get_current_ts()
        try:
            self.dbsession.add(user)
            self.dbsession.commit()
            self.dbsession.refresh(user)
            return True
        except Exception as e:
            self.dbsession.rollback()
            logger.exception("Failed to create user: email={}", email)
            raise e
        

    def verify_user(self, email:str, password:str) -> bool:
        user = self.dbsession.query(User).filter(User.email == email, User.pwd_md5 == get_md5(password)).first()
        if user:
            if user.status != UserStatus.ACTIVE:
                logger.error(f"user {email} is not active")
                return False
            return True
        return False
    

    def create_session(self, email:str) -> str:
        sessionid = generate_sessionid()
        
        user = self.dbsession.query(User).filter(User.email == email).first()
        if not user:
            logger.error("Cannot create session for unknown user: email={}", email)
            raise ValueError(f"User with email {email} not found when creating session")

        session_info = SessionInfo()
        session_info.sessionid = sessionid
        session_info.email = email
        session_info.user_id = user.user_id
        session_info.tenant_id = user.tenant_id

        try:
            self.dbsession.add(session_info)
            self.dbsession.commit()
            return sessionid
        except Exception as e:
            logger.error(f"user create session error {e}")
            self.dbsession.rollback()
            raise e

        
    
    def get_session_info(self, sessionid:str) -> SessionInfo:
        session_info = self.dbsession.query(SessionInfo).filter(SessionInfo.sessionid == sessionid).first()
        if session_info is None:
            return None
        if session_info.expire_ts < get_current_ts():
            return None
        if session_info.status != SessionStatus.ACTIVE:
            return None
        return session_info
