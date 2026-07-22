"""Anti-Corruption Layer (ACL) projector mapping domain events to Web API payload schemas."""

from typing import Any
from pydantic import BaseModel
from shared_common.schemas.ai_agent import (
    AgentDomainEvent,
    AgentOutputProduced,
    AgentRunCompleted,
    AgentRunInterrupted,
    AgentRunFailed,
    AgentProgressReported,
    HumanInputRequested,
    AgentOutput,
    AgentOutputPart,
    TextPart,
    StructuredDataPart,
    SourcesPart,
)
from shared_common.schemas.ai_agent.human_input_schemas import (
    GetUserByEmailInputModel,
    GetOrdersByEmailInputModel,
    GetOrderDetailsByOrderIdInputModel,
    GetReturnsByOrderIdInputModel,
    GetReturnsByCustomerIdInputModel,
    CreateReturnRequestInputModel,
)
from app.schemas.chat_msg_payload import (
    WebUserEventKind,
    WebChatUserPayload,
    WebUserResumePayload,
    WebUserPayload,
    WebTextPart,
    WebStructuredDataPart,
    WebStructuredDataSchemaId,
    WebHumanInputSchemaId,
    WebGetUserByEmailInputModel,
    WebGetOrdersByEmailInputModel,
    WebGetOrderDetailsByOrderIdInputModel,
    WebGetReturnsByOrderIdInputModel,
    WebGetReturnsByCustomerIdInputModel,
    WebCreateReturnRequestInputModel,
    WebSourcesPart,
    WebSourceReference,
    WebAgentOutputPart,
    WebAgentOutput,
    WebAgentError,
    WebHumanInputRequest,
    WebAgentResumeCursor,
    WebAgentDomainEventBase,
    WebAgentOutputProduced,
    WebAgentRunCompleted,
    WebAgentRunInterrupted,
    WebAgentRunFailed,
    WebAgentProgressReported,
    WebHumanInputRequested,
    WebAgentDomainEvent,
)
from loguru import logger


class ChatEventProjector:
    """Anti-Corruption Layer service transforming domain events into Web Chat Payload schemas."""

    _HUMAN_INPUT_SCHEMA_MAP: dict[WebHumanInputSchemaId, dict[str, Any]] = {
        WebHumanInputSchemaId.GET_USER_INPUT_V1: WebGetUserByEmailInputModel.model_json_schema(),
        WebHumanInputSchemaId.GET_ORDERS_INPUT_V1: WebGetOrdersByEmailInputModel.model_json_schema(),
        WebHumanInputSchemaId.GET_ORDER_DETAILS_INPUT_V1: WebGetOrderDetailsByOrderIdInputModel.model_json_schema(),
        WebHumanInputSchemaId.GET_RETURNS_BY_ORDER_INPUT_V1: WebGetReturnsByOrderIdInputModel.model_json_schema(),
        WebHumanInputSchemaId.GET_RETURNS_BY_CUSTOMER_INPUT_V1: WebGetReturnsByCustomerIdInputModel.model_json_schema(),
        WebHumanInputSchemaId.CREATE_RETURN_REQUEST_INPUT_V1: WebCreateReturnRequestInputModel.model_json_schema(),
    }

    @staticmethod
    def project_user_message(content: str) -> WebChatUserPayload:
        """Project user text message parameters into WebChatUserPayload."""
        return WebChatUserPayload(
            content=content,
        )

    @staticmethod
    def project_user_resume(
        interrupt_id: str,
        schema_id: WebHumanInputSchemaId,
        action: str | None = None,
        response_data: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> WebUserResumePayload:
        """Project user resume response parameters into WebUserResumePayload."""
        return WebUserResumePayload(
            interrupt_id=interrupt_id,
            schema_id=schema_id,
            action=action,
            response_data=response_data,
            metadata=metadata or {},
        )

    @staticmethod
    def project_web_input_to_domain_input(
        schema_id: WebHumanInputSchemaId,
        web_input: BaseModel,
    ) -> BaseModel:
        """
        Anti-Corruption Layer: Project Web DTO input models into downstream ai_agent domain input models.
        Decouples external Web API contract from internal ai_agent domain models.
        """
        if isinstance(web_input, WebGetUserByEmailInputModel):
            return GetUserByEmailInputModel(
                email=web_input.email,
                llm_text=web_input.llm_text,
            )
        elif isinstance(web_input, WebGetOrdersByEmailInputModel):
            return GetOrdersByEmailInputModel(
                email=web_input.email,
                llm_text=web_input.llm_text,
            )
        elif isinstance(web_input, WebGetOrderDetailsByOrderIdInputModel):
            return GetOrderDetailsByOrderIdInputModel(
                order_id=web_input.order_id,
                llm_text=web_input.llm_text,
            )
        elif isinstance(web_input, WebGetReturnsByOrderIdInputModel):
            return GetReturnsByOrderIdInputModel(
                order_id=web_input.order_id,
                llm_text=web_input.llm_text,
            )
        elif isinstance(web_input, WebGetReturnsByCustomerIdInputModel):
            return GetReturnsByCustomerIdInputModel(
                customer_id=web_input.customer_id,
                llm_text=web_input.llm_text,
            )
        elif isinstance(web_input, WebCreateReturnRequestInputModel):
            return CreateReturnRequestInputModel(
                order_id=web_input.order_id,
                customer_id=web_input.customer_id,
                reason_code=web_input.reason_code,
                reason_text=web_input.reason_text,
                item_condition=web_input.item_condition,
                created_by=web_input.created_by,
                llm_text=web_input.llm_text,
            )
        return web_input

    @staticmethod
    def project_schema_id(domain_schema_id: str) -> WebStructuredDataSchemaId:
        """
        Safely project domain schema_id string into WebStructuredDataSchemaId enum.
        If mapping fails (unrecognized schema_id), log error and fallback to UNKNOWN.
        """
        try:
            return WebStructuredDataSchemaId(domain_schema_id)
        except ValueError as exc:
            logger.error(
                f"Failed to map domain schema_id '{domain_schema_id}' to WebStructuredDataSchemaId. "
                f"Falling back to UNKNOWN schema. Cause: {exc}"
            )
            return WebStructuredDataSchemaId.UNKNOWN

    @staticmethod
    def project_human_input_schema_id(domain_schema_id: str) -> WebHumanInputSchemaId:
        """
        Safely project domain human input schema_id string into WebHumanInputSchemaId enum.
        If mapping fails (unrecognized schema_id), log error and fallback to UNKNOWN.
        """
        try:
            return WebHumanInputSchemaId(domain_schema_id)
        except ValueError as exc:
            logger.error(
                f"Failed to map domain human input schema_id '{domain_schema_id}' to WebHumanInputSchemaId. "
                f"Falling back to UNKNOWN schema. Cause: {exc}"
            )
            return WebHumanInputSchemaId.UNKNOWN

    @classmethod
    def project_human_input_schema(
        cls,
        schema_id: str | WebHumanInputSchemaId,
        domain_input_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Project human input JSON Schema using api_server defined Web Models based on schema_id.
        Decouples frontend from internal ai_agent Pydantic model schemas using pre-cached lookup dict.
        """
        web_schema_id = (
            schema_id
            if isinstance(schema_id, WebHumanInputSchemaId)
            else cls.project_human_input_schema_id(schema_id)
        )
        cached_schema = cls._HUMAN_INPUT_SCHEMA_MAP.get(web_schema_id)
        if cached_schema is not None:
            return cached_schema
        return domain_input_schema or {}





    @staticmethod
    def project_output_part(part: AgentOutputPart) -> WebAgentOutputPart:
        """Map domain AgentOutputPart to corresponding WebAgentOutputPart Pydantic model."""
        if isinstance(part, TextPart):
            return WebTextPart(text=part.text)
        elif isinstance(part, StructuredDataPart):
            return WebStructuredDataPart(
                schema_id=ChatEventProjector.project_schema_id(part.schema_id),
                data=part.data,
            )
        elif isinstance(part, SourcesPart):
            sources_list = [
                WebSourceReference(
                    source_id=src.source_id,
                    source_type=str(src.source_type),
                    title=src.title,
                    uri=src.uri,
                    attributes=src.attributes,
                )
                for src in part.sources
            ]
            return WebSourcesPart(sources=sources_list)
        else:
            return WebTextPart(text=str(part))

    @staticmethod
    def project_agent_output(output_obj: AgentOutput) -> WebAgentOutput:
        """Map domain AgentOutput object to WebAgentOutput Pydantic model."""
        web_parts = [ChatEventProjector.project_output_part(part) for part in output_obj.parts]
        return WebAgentOutput(
            output_id=output_obj.output_id,
            parts=web_parts,
        )

    @staticmethod
    def project_domain_event(event: AgentDomainEvent) -> WebAgentDomainEvent:
        """
        Project an AgentDomainEvent field-by-field into corresponding Web domain event objects
        (WebAgentDomainEvent) defined in app/schemas/chat_msg_payload.py.
        """
        base_event = WebAgentDomainEventBase.from_domain_event(event)

        if isinstance(event, AgentOutputProduced):
            web_output = ChatEventProjector.project_agent_output(event.output)
            return WebAgentOutputProduced.from_base(
                base_event,
                output=web_output,
            )

        elif isinstance(event, AgentRunCompleted):
            return WebAgentRunCompleted.from_base(
                base_event,
                output_ids=event.output_ids,
            )

        elif isinstance(event, AgentRunInterrupted):
            return WebAgentRunInterrupted.from_base(
                base_event,
                interrupt_ids=event.interrupt_ids,
            )

        elif isinstance(event, AgentRunFailed):
            web_err = WebAgentError(
                code=event.error.code,
                message=event.error.message,
                retryable=event.error.retryable,
                details=event.error.details,
            )
            return WebAgentRunFailed.from_base(
                base_event,
                error=web_err,
            )

        elif isinstance(event, AgentProgressReported):
            status_str = event.status.value if hasattr(event.status, "value") else str(event.status)
            return WebAgentProgressReported.from_base(
                base_event,
                operation=event.operation,
                status=status_str,
                current=event.current,
                total=event.total,
                details=event.details,
            )

        elif isinstance(event, HumanInputRequested):
            web_req = WebHumanInputRequest(
                prompt=event.request.prompt,
                schema_id=ChatEventProjector.project_human_input_schema_id(event.request.schema_id),
                input_schema=ChatEventProjector.project_human_input_schema(
                    event.request.schema_id,
                    event.request.input_schema,
                ),
                context=event.request.context,
                allowed_actions=event.request.allowed_actions,
            )
            web_cursor = WebAgentResumeCursor(
                checkpoint_id=event.resume_cursor.checkpoint_id,
                checkpoint_ns=event.resume_cursor.checkpoint_ns,
                checkpoint_map=event.resume_cursor.checkpoint_map,
            )
            return WebHumanInputRequested.from_base(
                base_event,
                interrupt_id=event.interrupt_id,
                request=web_req,
                resume_cursor=web_cursor,
            )

        else:
            logger.error(f"Unknown domain event type: {event}")
            web_output = WebAgentOutput(
                output_id=event.event_id,
                parts=[],
                metadata=event.model_dump(mode="json"),
            )
            return WebAgentOutputProduced.from_base(
                base_event,
                output=web_output,
            )
