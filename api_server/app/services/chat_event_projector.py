"""Anti-Corruption Layer (ACL) projector mapping domain events to Web API payload schemas."""

from typing import Any
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
from app.schemas.chat_msg_payload import (
    WebUserEventKind,
    WebChatUserPayload,
    WebUserResumePayload,
    WebUserPayload,
    WebTextPart,
    WebStructuredDataPart,
    WebStructuredDataSchemaId,
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

    @staticmethod
    def project_user_message(content: str) -> WebChatUserPayload:
        """Project user text message parameters into WebChatUserPayload."""
        return WebChatUserPayload(
            content=content,
        )

    @staticmethod
    def project_user_resume(
        interrupt_id: str,
        action: str | None = None,
        response_data: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> WebUserResumePayload:
        """Project user resume response parameters into WebUserResumePayload."""
        return WebUserResumePayload(
            interrupt_id=interrupt_id,
            action=action,
            response_data=response_data,
            metadata=metadata or {},
        )

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
                schema_id=event.request.schema_id,
                input_schema=event.request.input_schema,
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
