import asyncio
from enum import Enum
from pydantic import BaseModel
from typing import Any, Literal, Union, Annotated
from loguru import logger
from ai_agent.interface import get_ai_agent_server_client
from microservice_client.ai_agent_client import get_ai_agent_server_client


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
    file_name: str
    file_type: str
    file_size: int
    file_content: bytes
    pass




class MQTaskManagerBase(object):
    def __init__(self):
        pass

    def send_message(self, msg: MQMessageBase):
        raise NotImplementedError("Method not implemented")

    
class MQTaskManagerImpLocal(MQTaskManagerBase):
    def __init__(self):
        super().__init__()
        pass

    def send_message(self, msg: MQMessageBase):
        match msg:
            case MQMessageUploadFileFinish():
                asyncio.create_task(self.local_task_upload_file_finish(msg))
            case _:
                raise ValueError(f"Unknown event type: {msg.event_type}")
        pass


    async def local_task_upload_file_finish(self, msg: MQMessageUploadFileFinish):
        ai_agent_server_client = get_ai_agent_server_client()
        #ai_agent_server.rag_file_import(msg.file)
        logger.info(f"Local async task processing completed for file: {msg.file_name}")