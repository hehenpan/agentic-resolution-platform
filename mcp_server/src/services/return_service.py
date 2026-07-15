from sqlmodel import Session, select
from models.db_models import (
    ECommerceReturnRequest,
    ReturnStatus,
    ReturnReasonCode,
    ItemCondition,
)

class ECommerceReturnService:
    """
    Service encapsulating database actions for return policies and return requests.
    """
    def __init__(self, session: Session):
        self.session = session

    def get_return_by_order(self, order_id: int) -> ECommerceReturnRequest | None:
        """
        Retrieves the latest return request associated with the given order_id.
        """
        statement = (
            select(ECommerceReturnRequest)
            .where(ECommerceReturnRequest.order_id == order_id)
            .order_by(ECommerceReturnRequest.created_at.desc())
        )
        return self.session.exec(statement).first()

    def get_returns_by_customer(self, customer_id: int) -> list[ECommerceReturnRequest]:
        """
        Queries all return requests associated with the given customer_id,
        sorted by created_at descending.
        """
        statement = (
            select(ECommerceReturnRequest)
            .where(ECommerceReturnRequest.customer_id == customer_id)
            .order_by(ECommerceReturnRequest.created_at.desc())
        )
        return list(self.session.exec(statement).all())

    def create_return_request(
        self,
        order_id: int,
        customer_id: int,
        reason_code: ReturnReasonCode,
        reason_text: str,
        item_condition: ItemCondition,
        created_by: int | None,
    ) -> ECommerceReturnRequest:
        """
        Creates a new ECommerceReturnRequest record in the database.
        """
        request = ECommerceReturnRequest(
            order_id=order_id,
            customer_id=customer_id,
            status=ReturnStatus.REQUESTED,
            reason_code=reason_code,
            reason_text=reason_text,
            item_condition=item_condition,
            created_by=created_by,
        )
        self.session.add(request)
        self.session.commit()
        self.session.refresh(request)
        return request

