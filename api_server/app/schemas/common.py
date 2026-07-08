from typing import Any
from pydantic import BaseModel
from enum import IntEnum



class BizCode(IntEnum):
    SUCCESS = 0
    SYSTEM_ERROR = 1
    PARAM_ERR = 2
    NO_AUTH = 3
    NOT_FOUND = 4
    NO_PERMMIT = 5
    DB_ERR = 6



class ResponseBase(BaseModel):
    code: BizCode
    message: str = ""
    data: dict[str, Any] = {} 