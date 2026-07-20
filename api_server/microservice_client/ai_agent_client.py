from abc import ABC, abstractmethod
from collections.abc import AsyncIterator

from ai_agent_sdk import AgentRunStream
from app.core.config import settings
from langgraph_sdk import get_client

from shared_common.schemas.ai_agent import (
    AgentCreateRunRequest,
    AgentCreateRunResponse,
    AgentDomainEvent,
    AgentGetStateEventsRequest,
    AgentJoinStreamRequest,
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
    async def create_run(
        self,
        request: AgentCreateRunRequest,
    ) -> AgentCreateRunResponse:
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

    @abstractmethod
    def join_stream(
        self,
        request: AgentJoinStreamRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        pass

    @abstractmethod
    def get_state_events(
        self,
        request: AgentGetStateEventsRequest,
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

    async def create_run(
        self,
        request: AgentCreateRunRequest,
    ) -> AgentCreateRunResponse:
        return await self.run_stream.create_run(request)

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

    def join_stream(
        self,
        request: AgentJoinStreamRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        return self.run_stream.join_stream(request)

    def get_state_events(
        self,
        request: AgentGetStateEventsRequest,
    ) -> AsyncIterator[AgentDomainEvent]:
        return self.run_stream.get_state_events(request)


def get_ai_agent_server_client() -> AIAgentServerInterface:
    return AIAgentServerLangGraph()

