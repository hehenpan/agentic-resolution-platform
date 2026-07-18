from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from ai_agent_sdk import AgentRunStream
from app.core.config import settings
from langgraph_sdk import get_client

from shared_common.schemas.ai_agent import (
    AgentDomainEvent,
    AgentRAGFileImportRequest,
    AgentResumeRequest,
    AgentTurnRequest,
)


class AIAgentServerInterface(ABC):
    @abstractmethod
    def start(self):
        pass

    @abstractmethod
    def stop(self):
        pass

    @abstractmethod
    def stream_turn(
        self,
        request: AgentTurnRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        pass

    @abstractmethod
    def resume_turn(
        self,
        request: AgentResumeRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        pass

    @abstractmethod
    def stream_rag_file_import(
        self,
        request: AgentRAGFileImportRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        pass


class AIAgentServerLangGraph(AIAgentServerInterface):
    def __init__(self):
        self.client = get_client(url=settings.AI_AGENT_URL)
        self.run_stream = AgentRunStream(self.client)

    def start(self):
        pass

    def stop(self):
        pass

    def stream_turn(
        self,
        request: AgentTurnRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        return self.run_stream.stream_turn(request)

    def resume_turn(
        self,
        request: AgentResumeRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        return self.run_stream.resume_turn(request)

    def stream_rag_file_import(
        self,
        request: AgentRAGFileImportRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        return self.run_stream.stream_rag_file_import(request)


def get_ai_agent_server_client() -> AIAgentServerInterface:
    return AIAgentServerLangGraph()
