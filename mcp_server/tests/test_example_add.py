import pytest
from sqlmodel import select
from schemas.example import ExampleAddRequest
from tools.example import example_add
from core.database import get_session
from models.db_models import CalculationHistory

pytestmark = pytest.mark.anyio

async def test_example_add_success() -> None:
    """
    Test case verifying that example_add correctly returns the sum 
    and inserts the calculation history record into the isolated SQLite database.
    """
    # 1. Arrange
    req = ExampleAddRequest(a=15.0, b=27.5)
    
    # 2. Act
    res = await example_add(req)
    
    # 3. Assert response values
    assert res is not None
    assert res.result == 42.5
    
    # 4. Assert database entry existence
    with get_session() as session:
        records = session.exec(select(CalculationHistory)).all()
        assert len(records) == 1
        record = records[0]
        assert record.a == 15.0
        assert record.b == 27.5
        assert record.result == 42.5
        assert record.created_ts > 0
