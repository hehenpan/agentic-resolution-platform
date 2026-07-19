"""State and routing models for the supervisor graph."""

import operator
from enum import Enum
from typing import Annotated

from langchain_core.messages import AnyMessage, BaseMessage
from langgraph.graph.message import add_messages
from pydantic import BaseModel, Field
from shared_common.schemas.ai_agent import AgentOutput


class SelectRouteRoute(str, Enum):
    """Define branches returned by the select_route function."""

    POLICY_QA = "policy_qa"
    ECOMMERCE_QUERY = "ecommerce_query"
    ECOMMERCE_ACTION = "ecommerce_action"


class SupervisorNodeNames(str, Enum):
    """Define node identifiers for the supervisor graph."""

    ROUTE_REQUEST = "route_request"
    POLICY_QA = "policy_qa"
    ECOMMERCE_QUERY = "ecommerce_query"
    ECOMMERCE_ACTION = "ecommerce_action"


class SupervisorGraphNames(str, Enum):
    """Define compiled graph identifiers."""

    SUPERVISOR = "supervisor_graph"
    POLICY_QA = "policy_qa_graph"
    ECOMMERCE_QUERY = "ecommerce_query_graph"
    ECOMMERCE_ACTION = "ecommerce_action_graph"


class SupervisorState(BaseModel):
    """Represent shared conversation state managed by the supervisor."""

    messages: Annotated[list[AnyMessage], add_messages] = Field(
        default_factory=list,
        description="Conversation messages accumulated by the supervisor graph.",
    )
    outputs: Annotated[list[AgentOutput], operator.add] = Field(
        default_factory=list,
        description="Domain outputs accumulated during the supervisor run.",
    )
    route: SelectRouteRoute | None = Field(
        default=None,
        description="Route selected for the current supervisor turn.",
    )


class SupervisorDecision(BaseModel):
    """Constrain the route selected by the supervisor LLM."""

    route: SelectRouteRoute = Field(
        description="Route selected by the supervisor LLM."
    )


class RouteRequestUpdate(BaseModel):
    """Represent the state update returned by route_request."""

    route: SelectRouteRoute = Field(
        description="Route selected for the incoming request."
    )


class SupervisorOutput(BaseModel):
    """Represent the externally relevant supervisor graph output."""

    messages: list[BaseMessage] = Field(
        description="Conversation messages exposed by the supervisor graph."
    )
    outputs: list[AgentOutput] = Field(
        default_factory=list,
        description="Domain outputs exposed by the supervisor graph.",
    )
    route: SelectRouteRoute | None = Field(
        default=None,
        description="Final route selected for the supervisor turn.",
    )
