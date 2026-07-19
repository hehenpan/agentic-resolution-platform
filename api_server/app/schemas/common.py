from typing import Any
from enum import IntEnum

from pydantic import BaseModel, Field


class BizCode(IntEnum):
    SUCCESS = 0
    SYSTEM_ERROR = 1
    PARAM_ERR = 2
    NO_AUTH = 3
    NOT_FOUND = 4
    NO_PERMMIT = 5
    DB_ERR = 6



class ResponseBase(BaseModel):
    code: BizCode = Field(description="Business status code for the response.")
    message: str = Field(
        default="",
        description="Human-readable response message.",
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Response payload data.",
    )
