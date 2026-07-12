from sqlmodel import SQLModel, Field
from typing import Optional

class CalculationHistory(SQLModel, table=True):
    """
    SQLModel database table representing calculation execution history.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    a: float
    b: float
    result: float
    created_ts: int



class ECommerceUser(SQLModel, table=True):
    user_id: int = Field(default=None, primary_key=True)
    user_name: str = Field(default="")
    pwd: str = Field(default="")
    email: str = Field(default="", unique=True)
    status: int = Field(default=1)
    create_ts: int = Field(default=0)
    
    