from __future__ import annotations

import asyncio
from enum import Enum
from typing import Literal

from loguru import logger
from pydantic import BaseModel, JsonValue

from app.models.engines import get_session
from app.services.rag_file_import_service import RAGFileImportService
from microservice_client import ai_agent_client
from shared_common.schemas.ai_agent import RAGFileImportPayload, RAGFileImportResult


def get_mq_task_manager() -> MQTaskManagerBase:
    return MQTaskManagerImpLocal()


class EventType(str, Enum):
    UPLOAD_FILE_FINISH = "upload_file_finish"


class MSGContextData(BaseModel):
    request_id: str
    extra_context: dict[str, JsonValue]


class MSGMetaData(BaseModel):
    producer_svc_name: str
    produce_time_ts: int
    operator_user_id: int
    extra_meta: dict[str, JsonValue]


class MQMessageBase(BaseModel):
    topic_name: str
    partition_key: str
    event_type: str
    meta_data: MSGMetaData
    context_data: MSGContextData


class MQMessageUploadFileFinish(MQMessageBase):
    event_type: Literal[EventType.UPLOAD_FILE_FINISH] = EventType.UPLOAD_FILE_FINISH
    file_id: int
    file_name: str
    file_type: str
    file_size: int
    file_content: bytes
    tenant_id: int


class MQTaskManagerBase:
    def send_message(
        self,
        topic: str,
        partition_key: str,
        msg: MQMessageBase,
    ) -> None:
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
