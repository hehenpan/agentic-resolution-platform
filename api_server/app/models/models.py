from sqlmodel import SQLModel, Field
import enum 
from enum import Enum
from utils.commons import get_current_ts, generate_user_id, generate_random_id
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
    email: str = Field(primary_key=True,max_length=DB_CHAR_FIELD_MEDIUM_MAX_LEN)
    user_id: int = Field(default_factory=generate_user_id, unique=True)
    pwd_md5: str = Field(max_length=DB_CHAR_FIELD_SHORT_MAX_LEN)
    create_ts: int = Field(default_factory=get_current_ts)
    status: UserStatus = Field(default=UserStatus.ACTIVE)
    user_type: UserType = Field(default=UserType.USER)
    tenant_id: int = Field(default=1)


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


class FileStorageType(int, Enum):
    LOCAL = 0
    S3 = 1

class FileStatus(int, Enum):
    ACTIVE = 1
    INVALID = 0

class FileSyncStatus(int, Enum):
    PENDING = 0
    SYNCED = 1
    FAILED = 2

class FileInfo(SQLModel, table = True):
    file_id: int = Field(primary_key=True, default_factory=generate_random_id)
    tenant_id: int = Field()
    owner_user_id: int = Field()
    owner_email: str = Field(max_length=DB_CHAR_FIELD_MEDIUM_MAX_LEN)
    file_name: str = Field(max_length=DB_CHAR_FIELD_MEDIUM_MAX_LEN)
    file_type: str = Field(max_length=DB_CHAR_FIELD_SHORT_MAX_LEN)  #file_type in html, pdf, txt, doc, docx, etc
    file_md5_hash: str = Field(max_length=DB_CHAR_FIELD_MEDIUM_MAX_LEN)
    file_storage_location: str = Field(max_length=DB_CHAR_FIELD_MEDIUM_MAX_LEN)
    file_storage_type: FileStorageType = Field(default=FileStorageType.S3)
    file_size: int = Field()
    create_ts: int = Field(default_factory=get_current_ts)
    status: FileStatus = Field(default=FileStatus.ACTIVE)
    vector_db_sync_status: FileSyncStatus = Field(default=FileSyncStatus.PENDING) 


    