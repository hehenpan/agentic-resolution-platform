from sqlmodel import Session, select
from typing import Optional
from models.db_models import ECommerceUser

class ECommerceUserService:
    """
    Service class responsible for carrying out queries on the ECommerceUser database table.
    Accepts DB session via Dependency Injection.
    """
    def __init__(self, session: Session):
        self.session = session

    def get_user(self, email: str) -> Optional[ECommerceUser]:
        """
        Queries and returns ECommerceUser by email.
        """
        statement = select(ECommerceUser).where(ECommerceUser.email == email)
        return self.session.exec(statement).first()
