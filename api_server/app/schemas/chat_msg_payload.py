"""Web Frontend Payload Schemas for Chat Messages and Domain Events."""

from enum import Enum
import json
from typing import Annotated, Any, Literal
from pydantic import BaseModel, Field

from shared_common.schemas.ai_agent import (
    AgentDomainEventBase,
    AgentReturnReason,
    AgentItemCondition,
)


class WebUserEventKind(str, Enum):
    """Event kind discriminator for user input events."""
    USER_MESSAGE = "user_message"
    USER_RESUME = "user_resume"


class WebStructuredDataSchemaId(str, Enum):
    """Supported Web frontend structured data schema identifiers."""
    UNKNOWN = "unknown"
    RAG_FILE_IMPORT_RESULT_V1 = "rag.file_import.result.v1"
    ECOMMERCE_USER_RESULT_V1 = "ecommerce.user_result.v1"
    ECOMMERCE_ORDERS_RESULT_V1 = "ecommerce.orders_result.v1"
    ECOMMERCE_ORDER_DETAILS_RESULT_V1 = "ecommerce.order_details_result.v1"
    ECOMMERCE_RETURNS_BY_ORDER_RESULT_V1 = "ecommerce.returns_by_order_result.v1"
    ECOMMERCE_RETURNS_BY_CUSTOMER_RESULT_V1 = "ecommerce.returns_by_customer_result.v1"
    ECOMMERCE_CREATE_RETURN_RESULT_V1 = "ecommerce.create_return_result.v1"


class WebHumanInputSchemaId(str, Enum):
    """Supported Web frontend human input schema identifiers."""
    UNKNOWN = "unknown"
    GET_USER_INPUT_V1 = "human_input.get_user.v1"
    GET_ORDERS_INPUT_V1 = "human_input.get_orders.v1"
    GET_ORDER_DETAILS_INPUT_V1 = "human_input.get_order_details.v1"
    GET_RETURNS_BY_ORDER_INPUT_V1 = "human_input.get_returns_by_order.v1"
    GET_RETURNS_BY_CUSTOMER_INPUT_V1 = "human_input.get_returns_by_customer.v1"
    CREATE_RETURN_REQUEST_INPUT_V1 = "human_input.create_return_request.v1"


class WebGetUserByEmailInputModel(BaseModel):
    """Web schema representing user lookup parameters."""
    email: str | None = Field(
        default=None,
        description="Customer email address for user lookup.",
    )
    llm_text: str | None = Field(
        default=None,
        description="Raw natural language text response containing customer email details.",
    )


class WebGetOrdersByEmailInputModel(BaseModel):
    """Web schema representing orders lookup parameters."""
    email: str | None = Field(
        default=None,
        description="Customer email address for orders query.",
    )
    llm_text: str | None = Field(
        default=None,
        description="Raw natural language text response containing customer email details.",
    )


class WebGetOrderDetailsByOrderIdInputModel(BaseModel):
    """Web schema representing order details parameters."""
    order_id: int | None = Field(
        default=None,
        gt=0,
        description="Positive order identifier for lookup.",
    )
    llm_text: str | None = Field(
        default=None,
        description="Raw natural language text response containing order identifier.",
    )


class WebGetReturnsByOrderIdInputModel(BaseModel):
    """Web schema representing return-by-order parameters."""
    order_id: int | None = Field(
        default=None,
        gt=0,
        description="Positive order identifier for return lookup.",
    )
    llm_text: str | None = Field(
        default=None,
        description="Raw natural language text response containing order identifier.",
    )


class WebGetReturnsByCustomerIdInputModel(BaseModel):
    """Web schema representing return-by-customer parameters."""
    customer_id: int | None = Field(
        default=None,
        gt=0,
        description="Positive customer identifier for return lookup.",
    )
    llm_text: str | None = Field(
        default=None,
        description="Raw natural language text response containing customer identifier.",
    )


class WebCreateReturnRequestInputModel(BaseModel):
    """Web schema representing create return request parameters."""
    order_id: int | None = Field(
        default=None,
        gt=0,
        description="Positive order identifier to return.",
    )
    customer_id: int | None = Field(
        default=None,
        gt=0,
        description="Positive customer identifier for return.",
    )
    reason_code: AgentReturnReason | None = Field(
        default=None,
        description="Reason code for return (CHANGE_OF_MIND, DAMAGED, WRONG_ITEM, NOT_AS_DESCRIBED, LATE_DELIVERY).",
    )
    reason_text: str | None = Field(
        default=None,
        description="Additional reason explanation text.",
    )
    item_condition: AgentItemCondition | None = Field(
        default=None,
        description="Product condition (UNOPENED, OPENED, USED, DAMAGED).",
    )
    created_by: int | None = Field(
        default=None,
        description="User ID of operator creating return request.",
    )
    llm_text: str | None = Field(
        default=None,
        description="Raw natural language text response containing return details.",
    )




class WebChatUserPayload(BaseModel):
    """Web frontend payload schema for standard user text messages."""
    kind: Literal[WebUserEventKind.USER_MESSAGE] = Field(
        default=WebUserEventKind.USER_MESSAGE,
        description="Discriminator for standard user text message.",
    )
    content: str = Field(..., description="User message text content.")


class WebUserResumePayload(BaseModel):
    """Web frontend payload schema for user resume / interrupt response."""
    kind: Literal[WebUserEventKind.USER_RESUME] = Field(
        default=WebUserEventKind.USER_RESUME,
        description="Discriminator for user resume response.",
    )
    interrupt_id: str = Field(..., description="Interrupt ID being resolved.")
    schema_id: WebHumanInputSchemaId = Field(
        ...,
        description="Mapped safe human input schema identifier.",
    )
    action: str | None = Field(default=None, description="Action selected by operator.")
    response_data: Any = Field(default=None, description="Validated human input response data.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional resume metadata.")



WebUserPayload = Annotated[
    WebChatUserPayload | WebUserResumePayload,
    Field(discriminator="kind"),
]


class WebTextPart(BaseModel):
    """Web frontend textual output part schema."""
    kind: Literal["text"] = Field(default="text", description="Discriminator identifying text output part.")
    text: str = Field(..., description="Human-readable text content.")


class WebStructuredDataPart(BaseModel):
    """Web frontend structured data output part schema."""
    kind: Literal["structured_data"] = Field(default="structured_data", description="Discriminator identifying structured data part.")
    schema_id: WebStructuredDataSchemaId = Field(..., description="Mapped safe schema identifier.")
    data: Any = Field(..., description="Structured JSON payload.")


class WebSourceReference(BaseModel):
    """Web frontend source reference schema."""
    source_id: str = Field(..., description="Source identifier.")
    source_type: str = Field(..., description="Category of system supplying the source.")
    title: str | None = Field(default=None, description="Human-readable label for the source.")
    uri: str | None = Field(default=None, description="Location URI of the source.")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Source metadata and evidence.")


class WebSourcesPart(BaseModel):
    """Web frontend sources part schema."""
    kind: Literal["sources"] = Field(default="sources", description="Discriminator identifying sources collection.")
    sources: list[WebSourceReference] = Field(default_factory=list, description="List of source references.")


WebAgentOutputPart = Annotated[
    WebTextPart | WebStructuredDataPart | WebSourcesPart,
    Field(discriminator="kind"),
]


class WebAgentOutput(BaseModel):
    """Web frontend representation of public agent output."""
    output_id: str = Field(..., description="Stable public identifier for the output.")
    parts: list[WebAgentOutputPart] = Field(default_factory=list, description="Ordered heterogeneous content parts.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional output metadata.")


class WebAgentError(BaseModel):
    """Web frontend representation of safe agent error."""
    code: str = Field(..., description="Machine-readable error category code.")
    message: str = Field(..., description="Human-readable error message.")
    retryable: bool = Field(default=False, description="Whether operation can be retried.")
    details: dict[str, Any] = Field(default_factory=dict, description="Diagnostic details.")


class WebHumanInputRequest(BaseModel):
    """Web frontend representation of human input request prompt and schema."""
    prompt: str = Field(..., description="Instruction presented to operator.")
    schema_id: WebHumanInputSchemaId = Field(..., description="Mapped safe human input schema identifier.")
    input_schema: dict[str, Any] = Field(default_factory=dict, description="JSON Schema for input.")
    context: dict[str, Any] = Field(default_factory=dict, description="Additional context data.")
    allowed_actions: list[str] = Field(default_factory=list, description="Allowed operator actions.")


class WebAgentResumeCursor(BaseModel):
    """Web frontend representation of resume cursor."""
    checkpoint_id: str = Field(..., description="LangGraph checkpoint identifier.")
    checkpoint_ns: str = Field(default="", description="Checkpoint namespace scope.")
    checkpoint_map: dict[str, str] = Field(default_factory=dict, description="Namespace-to-checkpoint mapping.")


class WebAgentDomainEventBase(BaseModel):
    """Base envelope for Web domain events served to frontend."""
    event_id: str = Field(..., description="Unique event identifier.")
    kind: str = Field(..., description="Event kind discriminator.")
    schema_version: str = Field(default="1", description="Contract version.")
    thread_id: str = Field(..., description="LangGraph thread ID.")
    run_id: str = Field(..., description="Agent run ID.")
    sequence: int = Field(default=0, description="Event sequence number.")
    source_sequences: list[int] = Field(default_factory=list, description="Raw source event sequence numbers.")
    created_at: int = Field(..., description="Unix timestamp in seconds.")

    @classmethod
    def from_domain_event(cls, event: AgentDomainEventBase) -> "WebAgentDomainEventBase":
        """Construct WebAgentDomainEventBase envelope directly from a domain event object."""
        kind = event.kind
        kind_str = kind.value if hasattr(kind, "value") else str(kind)
        return cls(
            event_id=event.event_id,
            kind=kind_str,
            schema_version=str(getattr(event, "schema_version", "1")),
            thread_id=event.thread_id,
            run_id=event.run_id,
            sequence=event.sequence,
            source_sequences=list(event.source_sequences),
            created_at=event.created_at,
        )

    @classmethod
    def from_base(cls, base: "WebAgentDomainEventBase", **kwargs: Any) -> Any:
        """Construct subclass instance directly from a WebAgentDomainEventBase instance."""
        return cls(
            event_id=base.event_id,
            kind=base.kind,
            schema_version=base.schema_version,
            thread_id=base.thread_id,
            run_id=base.run_id,
            sequence=base.sequence,
            source_sequences=base.source_sequences,
            created_at=base.created_at,
            **kwargs,
        )


class WebAgentOutputProduced(WebAgentDomainEventBase):
    """Web frontend event for produced agent output."""
    kind: Literal["agent.output_produced"] = Field(default="agent.output_produced", description="Event kind discriminator.")
    output: WebAgentOutput = Field(..., description="Mapped agent output object.")


class WebAgentProgressReported(WebAgentDomainEventBase):
    """Web frontend event for progress reports."""
    kind: Literal["agent.progress_reported"] = Field(default="agent.progress_reported", description="Event kind discriminator.")
    operation: str = Field(..., description="Operation name.")
    status: str = Field(..., description="Progress status.")
    current: int | None = Field(default=None, description="Current completed unit count.")
    total: int | None = Field(default=None, description="Total unit count.")
    details: dict[str, Any] = Field(default_factory=dict, description="Progress details.")


class WebHumanInputRequested(WebAgentDomainEventBase):
    """Web frontend event for human input requests."""
    kind: Literal["agent.human_input_requested"] = Field(default="agent.human_input_requested", description="Event kind discriminator.")
    interrupt_id: str = Field(..., description="Interrupt ID.")
    request: WebHumanInputRequest = Field(..., description="Human input prompt and schema.")
    resume_cursor: WebAgentResumeCursor = Field(..., description="Resume cursor information.")


class WebAgentRunCompleted(WebAgentDomainEventBase):
    """Web frontend event for successful run completion."""
    kind: Literal["agent.run_completed"] = Field(default="agent.run_completed", description="Event kind discriminator.")
    output_ids: list[str] = Field(default_factory=list, description="Output IDs produced.")


class WebAgentRunInterrupted(WebAgentDomainEventBase):
    """Web frontend event for run interruption."""
    kind: Literal["agent.run_interrupted"] = Field(default="agent.run_interrupted", description="Event kind discriminator.")
    interrupt_ids: list[str] = Field(default_factory=list, description="Interrupt IDs awaiting human input.")


class WebAgentRunFailed(WebAgentDomainEventBase):
    """Web frontend event for run failure."""
    kind: Literal["agent.run_failed"] = Field(default="agent.run_failed", description="Event kind discriminator.")
    error: WebAgentError = Field(..., description="Mapped error details.")


WebAgentDomainEvent = Annotated[
    WebAgentOutputProduced
    | WebAgentProgressReported
    | WebHumanInputRequested
    | WebAgentRunCompleted
    | WebAgentRunInterrupted
    | WebAgentRunFailed,
    Field(discriminator="kind"),
]
