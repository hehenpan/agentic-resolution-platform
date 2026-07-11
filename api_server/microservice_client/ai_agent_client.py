from abc import ABC, abstractmethod
from langgraph_sdk import get_client
from loguru import logger
from app.core.config import settings
from shared_common.schemas_ai_agent import RAGFileImportPayload

class AIAgentServerInterface(ABC):
    @abstractmethod
    def start(self):
        pass
    
    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    async def rag_file_import(self, payload: RAGFileImportPayload) -> bool:
        pass

class AIAgentServerLangGraph(AIAgentServerInterface):
    def __init__(self):
        self.client = get_client(url=settings.AI_AGENT_URL)

    def start(self):
        pass

    def stop(self):
        pass

    async def rag_file_import(self, payload: RAGFileImportPayload) -> bool:
        try:
            # We trigger the run on the file_ingester assistant graph
            await self.client.runs.create(
                thread_id=None,
                assistant_id="file_ingester",
                input=payload.model_dump()
            )
            logger.info(f"Successfully triggered RAG file import for file_id={payload.file_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to trigger RAG file import for file_id={payload.file_id}: {e}")
            return False

def get_ai_agent_server_client() -> AIAgentServerInterface:
    return AIAgentServerLangGraph()
    

