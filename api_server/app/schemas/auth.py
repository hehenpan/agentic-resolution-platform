from pydantic import BaseModel, EmailStr, Field, model_validator


from app.schemas.common import ResponseBase
from typing import Annotated

class RegisterRequest(BaseModel):
    email: Annotated[EmailStr, Field(..., description="User email address")]
    password: Annotated[str, Field(..., description="User password")]
    password_confirmation: Annotated[str, Field(..., description="User password confirmation")]

    @model_validator(mode="after")
    def validate_passwords(self) -> "RegisterRequest":
        if self.password != self.password_confirmation:
            raise ValueError("Passwords do not match")
        return self
    

class RegisterResponse(ResponseBase):
    pass



class LoginRequest(BaseModel):
    email: Annotated[EmailStr, Field(..., description="User email address")]
    password: Annotated[str, Field(..., description="User password")]


class LoginResponse(ResponseBase):
    pass