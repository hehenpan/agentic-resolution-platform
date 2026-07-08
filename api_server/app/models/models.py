from sqlmodel import SQLModel, Field
import enum 
from enum import Enum
from utils.commons import get_current_ts, generate_user_id
from app.core.constants import (
    DB_CHAR_FIELD_SHORT_MAX_LEN, 
    DB_CHAR_FIELD_MEDIUM_MAX_LEN, 
    DB_CHAR_FIELD_LONG_MAX_LEN,
    SESSION_EXPIRE_SECONDS
)



class UserStatus(int, Enum):
    INACTIVE = 0
    ACTIVE = 1

class UserType(int, Enum):
    ADMIN = 0
    USER = 1
    TENANT_ADMIN = 2
    

#user table
class User(SQLModel, table = True):
    email: str = Field(primary_key=True)
    user_id: int = Field(default_factory=generate_user_id, unique=True)
    pwd_md5: str = Field(max_length=DB_CHAR_FIELD_SHORT_MAX_LEN)
    create_ts: int = Field(default_factory=get_current_ts)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    user_type: UserType = Field(default=UserType.USER)
    tenant_id: int = Field(default=0)


class SessionStatus(int, Enum):
    ACTIVE = 1
    INVALID = 0

class SessionInfo(SQLModel, table = True):
    sessionid: str = Field(primary_key=True)
    user_id: int = Field()
    tenant_id: int = Field()
    email: str = Field(max_length=DB_CHAR_FIELD_SHORT_MAX_LEN)
    create_ts: int = Field(default_factory=get_current_ts)
    expire_ts: int = Field(default_factory=lambda: get_current_ts() + SESSION_EXPIRE_SECONDS)
    status: SessionStatus = Field(default=SessionStatus.ACTIVE)