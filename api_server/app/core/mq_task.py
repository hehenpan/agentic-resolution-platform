from __future__ import annotations
import os
import asyncio
from enum import Enum
from pydantic import BaseModel
from typing import Any, Literal, Union, Annotated
from loguru import logger
from microservice_client import ai_agent_client
from app.core.config import settings
from shared_common.schemas_ai_agent import RAGFileImportPayload


def get_mq_task_manager()->MQTaskManagerBase:
    '''
    
    '''

    return MQTaskManagerImpLocal()


class EventType(str, Enum):
    UPLOAD_FILE_FINISH = "upload_file_finish"



class MSGContextData(BaseModel):
    request_id: str
    extra_context: dict[str, Any]
    pass

class MSGMetaData(BaseModel):
    producer_svc_name: str
    produce_time_ts: int
    operator_user_id: int
    extra_meta: dict[str, Any]
    
    pass



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




class MQTaskManagerBase(object):
    def __init__(self):
        pass

    def send_message(self, topic: str, partition_key: str, msg: MQMessageBase):
        raise NotImplementedError("Method not implemented")

    
class MQTaskManagerImpLocal(MQTaskManagerBase):
    def __init__(self):
        super().__init__()
        pass

    def send_message(self, topic: str, partition_key: str, msg: MQMessageBase):
        match msg:
            case MQMessageUploadFileFinish():
                asyncio.create_task(self.local_task_upload_file_finish(msg))
            case _:
                raise ValueError(f"Unknown event type: {msg.event_type}")
        pass


    async def local_task_upload_file_finish(self, msg: MQMessageUploadFileFinish):
        ai_agent_server_client = ai_agent_client.get_ai_agent_server_client()
            
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
        
        await ai_agent_server_client.rag_file_import(payload)
        logger.info(f"Local async task processing completed for file: {msg.file_name}")