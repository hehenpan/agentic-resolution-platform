from __future__ import annotations

import asyncio
from enum import Enum
from typing import Literal

from loguru import logger
from pydantic import BaseModel, Field, JsonValue

from app.models.engines import get_session
from app.services.rag_file_import_service import RAGFileImportService
from microservice_client import ai_agent_client
from shared_common.schemas.ai_agent import RAGFileImportPayload, RAGFileImportResult


def get_mq_task_manager() -> MQTaskManagerBase:
    return MQTaskManagerImpLocal()


class EventType(str, Enum):
    UPLOAD_FILE_FINISH = "upload_file_finish"


class MSGContextData(BaseModel):
    request_id: str = Field(description="Request ID associated with the MQ event.")
    extra_context: dict[str, JsonValue] = Field(
        description="Additional execution context carried by the MQ event."
    )


class MSGMetaData(BaseModel):
    producer_svc_name: str = Field(
        description="Service name that produced the MQ event."
    )
    produce_time_ts: int = Field(
        description="Unix timestamp when the MQ event was produced."
    )
    operator_user_id: int = Field(
        description="User ID of the operator that triggered the event."
    )
    extra_meta: dict[str, JsonValue] = Field(
        description="Additional metadata carried by the MQ event."
    )


class MQMessageBase(BaseModel):
    topic_name: str = Field(description="Topic name for the MQ message.")
    partition_key: str = Field(description="Partition key for message ordering.")
    event_type: str = Field(description="Business event type carried by the message.")
    meta_data: MSGMetaData = Field(description="MQ message metadata.")
    context_data: MSGContextData = Field(description="MQ message context data.")


class MQMessageUploadFileFinish(MQMessageBase):
    event_type: Literal[EventType.UPLOAD_FILE_FINISH] = Field(
        default=EventType.UPLOAD_FILE_FINISH,
        description="Upload completion event type.",
    )
    file_id: int = Field(description="Uploaded file ID.")
    file_name: str = Field(description="Uploaded file name.")
    file_type: str = Field(description="Uploaded file type.")
    file_size: int = Field(description="Uploaded file size in bytes.")
    file_content: bytes = Field(description="Uploaded file content bytes.")
    tenant_id: int = Field(description="Tenant ID that owns the uploaded file.")


class MQTaskManagerBase:
    def send_message(
        self,
        topic: str,
        partition_key: str,
        msg: MQMessageBase,
    ) -> None:
        logger.error(
            f"MQTaskManagerBase.send_message is not implemented: "
            f"topic={topic}, partition_key={partition_key}"
        )
        raise NotImplementedError("Method not implemented")


class MQTaskManagerImpLocal(MQTaskManagerBase):
    def send_message(
        self,
        topic: str,
        partition_key: str,
        msg: MQMessageBase,
    ) -> None:
        match msg:
            case MQMessageUploadFileFinish():
                asyncio.create_task(self.local_task_upload_file_finish(msg))
            case _:
                logger.error(
                    f"Unknown MQ event type: event_type={msg.event_type}, "
                    f"topic={topic}, partition_key={partition_key}"
                )
                raise ValueError(f"Unknown event type: {msg.event_type}")

    async def local_task_upload_file_finish(
        self,
        msg: MQMessageUploadFileFinish,
    ) -> RAGFileImportResult | None:
        payload = RAGFileImportPayload(
            file_id=msg.file_id,
            file_name=msg.file_name,
            file_size=msg.file_size,
            file_owner_id=msg.meta_data.operator_user_id,
            file_tenant_id=msg.tenant_id,
            file_content=msg.file_content,
            extra_meta=msg.meta_data.extra_meta,
            extra_context=msg.context_data.extra_context,
        )

        try:
            with get_session() as session:
                service = RAGFileImportService(
                    dbsession=session,
                    agent_client=ai_agent_client.get_ai_agent_server_client(),
                )
                result = await service.import_file(
                    payload=payload,
                    operation_id=msg.context_data.request_id,
                )
        except Exception as error:
            logger.error(
                f"Local RAG file import task failed: file_id={msg.file_id}, "
                f"error={type(error).__name__}: {error}"
            )
            return None

        logger.info(
            f"Local RAG file import task completed: "
            f"file_id={msg.file_id}, file_name={msg.file_name}"
        )
        return result
