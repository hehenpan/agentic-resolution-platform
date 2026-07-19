from loguru import logger
from pydantic import BaseModel, EmailStr, Field, model_validator


from app.schemas.common import ResponseBase


class RegisterRequest(BaseModel):
    email: EmailStr = Field(description="Email address used to register the user.")
    password: str = Field(description="Password submitted for the new user account.")
    password_confirmation: str = Field(
        description="Password confirmation that must match the submitted password."
    )

    @model_validator(mode="after")
    def validate_passwords(self) -> "RegisterRequest":
        if self.password != self.password_confirmation:
            logger.error("Registration password confirmation does not match")
            raise ValueError("Passwords do not match")
        return self


class RegisterResponse(ResponseBase):
    pass


class LoginRequest(BaseModel):
    email: EmailStr = Field(description="Email address used for login.")
    password: str = Field(description="Password submitted for login.")


class LoginResponse(ResponseBase):
    pass
