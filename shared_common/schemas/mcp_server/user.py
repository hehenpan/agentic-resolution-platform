from pydantic import BaseModel, Field
from typing import Optional
from shared_common.schemas.mcp_server.enums import UserStatus

class GetECommerceUserRequest(BaseModel):
    """
    Pydantic schema representing the request parameters to query ECommerceUser.
    """
    email: str = Field(..., description="The unique email of the user")


class GetECommerceUserResponse(BaseModel):
    """
    Pydantic schema representing the query result of ECommerceUser.
    """
    exists: bool = Field(..., description="Whether the user exists. Check this field first before accessing other fields.")
    user_id: Optional[int] = Field(default=None, description="The unique user ID")
    user_name: Optional[str] = Field(default=None, description="The username")
    email: Optional[str] = Field(default=None, description="The user email")
    status: Optional[UserStatus] = Field(default=None, description="Account status: 1 for ACTIVE, 0 for INACTIVE")
    phone: Optional[str] = Field(default=None, description="The user's contact phone number")
    create_ts: Optional[int] = Field(default=None, description="Account creation timestamp (Unix epoch)")
