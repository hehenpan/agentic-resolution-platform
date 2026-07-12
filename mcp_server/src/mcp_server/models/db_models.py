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
