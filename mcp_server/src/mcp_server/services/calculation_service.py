import time
from sqlmodel import Session
from mcp_server.models.db_models import CalculationHistory

class CalculationService:
    """
    Service class responsible for carrying out calculation business logic
    and database storage. Accepts db session via Dependency Injection.
    """
    def __init__(self, session: Session):
        self.session = session

    def add_and_record(self, a: float, b: float) -> float:
        """
        Computes the sum of a and b, saves the record into the database,
        and returns the computed result.
        """
        res = a + b
        history = CalculationHistory(
            a=a,
            b=b,
            result=res,
            created_ts=int(time.time())
        )
        self.session.add(history)
        return res
