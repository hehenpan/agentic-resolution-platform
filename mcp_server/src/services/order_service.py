from sqlmodel import Session, select
from models.db_models import ECommerceOrder, ECommerceOrderItem

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

    def get_order_with_items(self, order_id: int) -> tuple[ECommerceOrder | None, list[ECommerceOrderItem]]:
        """
        Retrieves the ECommerceOrder record and its associated ECommerceOrderItem list by order_id.
        """
        order = self.session.get(ECommerceOrder, order_id)
        if order is None:
            return None, []
        
        statement = (
            select(ECommerceOrderItem)
            .where(ECommerceOrderItem.order_id == order_id)
        )
        items = list(self.session.exec(statement).all())
        return order, items

