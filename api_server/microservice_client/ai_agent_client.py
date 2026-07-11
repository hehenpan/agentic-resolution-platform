from abc import ABC, abstractmethod


def get_ai_agent_server_client()->AIAgentServerInterface:
    return AIAgentServerLangGraph()

class AIAgentServerInterface(ABC):
    @abstractmethod
    def start(self):
        pass
    
    @abstractmethod
    def stop(self):
        pass


class AIAgentServerLangGraph(AIAgentServerInterface):
    pass
    

