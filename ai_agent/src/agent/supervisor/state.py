"""State and routing models for the supervisor graph."""

from enum import Enum
from typing import Annotated

from langchain_core.messages import AnyMessage, BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field


class SelectRouteRoute(str, Enum):
    """Define branches returned by the select_route function."""

    POLICY_QA = "policy_qa"


class SupervisorNodes(str, Enum):
    """Define node identifiers for the supervisor graph."""

    ROUTE_REQUEST = "route_request"
    POLICY_QA = "policy_qa"


class SupervisorGraphNames(str, Enum):
    """Define compiled graph identifiers."""

    SUPERVISOR = "supervisor_graph"
    POLICY_QA = "policy_qa_graph"


class SupervisorState(BaseModel):
    """Represent shared conversation state managed by the supervisor."""

    messages: Annotated[list[AnyMessage], add_messages] = Field(
        default_factory=list
    )
    route: SelectRouteRoute | None = None


class SupervisorDecision(BaseModel):
    """Constrain the route selected by the supervisor LLM."""

    route: SelectRouteRoute


class RouteRequestUpdate(BaseModel):
    """Represent the state update returned by route_request."""

    route: SelectRouteRoute


class SupervisorOutput(BaseModel):
    """Represent the externally relevant supervisor graph output."""

    messages: list[BaseMessage]
    route: SelectRouteRoute | None = None
