from sqlmodel import Session, select
from models.db_models import ECommerceOrder

class ECommerceOrderService:
    """
    Service encapsulating database actions for ECommerceOrder.
    """
    def __init__(self, session: Session):
        self.session = session

    def get_user_orders(self, email: str) -> list[ECommerceOrder]:
        """
        Queries the database for all orders matching the customer's email,
        sorted by created_ts descending.
        """
        statement = (
            select(ECommerceOrder)
            .where(ECommerceOrder.email == email)
            .order_by(ECommerceOrder.created_ts.desc())
        )
        return list(self.session.exec(statement).all())
