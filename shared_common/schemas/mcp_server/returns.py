from pydantic import BaseModel, Field
from typing import List, Optional
from shared_common.schemas.mcp_server.enums import (
    ReturnStatus,
    ReturnReasonCode,
    ItemCondition,
    ReturnResolutionType,
)

class GetReturnRequestRecord(BaseModel):
    """
    Pydantic schema representing a single return request record in responses.
    """
    id: int = Field(..., description="The unique return request ID")
    order_id: int = Field(..., description="The associated order ID")
    customer_id: int = Field(..., description="The associated customer ID")
    status: ReturnStatus = Field(..., description="The status of the return")
    reason_code: ReturnReasonCode = Field(..., description="The code indicating return reason")
    reason_text: str = Field(..., description="Customer reason text")
    item_condition: ItemCondition = Field(..., description="Overall condition of returned items")
    requested_at: int = Field(..., description="Timestamp when return was requested")
    approved_at: Optional[int] = Field(default=None, description="Timestamp when return was approved")
    rejected_at: Optional[int] = Field(default=None, description="Timestamp when return was rejected")
    received_at: Optional[int] = Field(default=None, description="Timestamp when returned items were received")
    closed_at: Optional[int] = Field(default=None, description="Timestamp when return process closed")
    resolution_type: Optional[ReturnResolutionType] = Field(default=None, description="Resolution outcome type")
    created_by: Optional[int] = Field(default=None, description="The user_id of the agent who handled this return")
    created_at: int = Field(..., description="Creation timestamp")
    updated_at: int = Field(..., description="Last update timestamp")


class GetReturnRequestsByOrderRequest(BaseModel):
    """
    Pydantic schema representing the request parameters to query return requests by order_id.
    """
    order_id: int = Field(..., description="The unique ID of the order to query returns for")


class GetReturnRequestsByOrderResponse(BaseModel):
    """
    Pydantic schema representing the query result of returns associated with an order.
    """
    returns: Optional[GetReturnRequestRecord] = Field(default=None, description="The return request associated with this order")


class GetReturnRequestsByCustomerRequest(BaseModel):
    """
    Pydantic schema representing the request parameters to query return requests by customer_id.
    """
    customer_id: int = Field(..., description="The unique ID of the customer to query returns for")


class GetReturnRequestsByCustomerResponse(BaseModel):
    """
    Pydantic schema representing the query result of returns associated with a customer.
    """
    returns: List[GetReturnRequestRecord] = Field(default_factory=list, description="The return requests for this customer, sorted by created_at descending")


class CreateReturnRequestInput(BaseModel):
    """
    Pydantic schema representing the input to create a return request.
    """
    order_id: int = Field(..., description="The unique ID of the order to return")
    customer_id: int = Field(..., description="The ID of the customer associated with the return")
    reason_code: ReturnReasonCode = Field(..., description="The reason code for the return")
    reason_text: Optional[str] = Field(default="", description="Additional reason explanation text")
    item_condition: ItemCondition = Field(..., description="The condition of the product being returned")
    created_by: Optional[int] = Field(default=None, description="The user_id of the agent who operates this return request creation")


class CreateReturnRequestResponse(BaseModel):
    """
    Pydantic schema representing the output of a return request creation.
    """
    success: bool = Field(..., description="Whether the return request was successfully created")
    return_request: Optional[GetReturnRequestRecord] = Field(default=None, description="The created return request details if successful")
    error_message: Optional[str] = Field(default=None, description="An error explanation if success is False")
