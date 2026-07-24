"""Ecommerce Action subgraph assembly."""

from enum import Enum

from langgraph.graph import END, START, StateGraph

from agent.core.checkpoint import get_checkpointer
from agent.core.config import settings
from agent.supervisor.ecommerce_action.nodes import (
    action_agent,
    build_action_response,
    execute_create_return,
)
from agent.supervisor.ecommerce_action.state import (
    EcommerceActionOutput,
    EcommerceActionState,
)
from agent.supervisor.state import SupervisorGraphNames, SupervisorSubgraphInput


class EcommerceActionNodeNames(str, Enum):
    """Define node identifiers for the Ecommerce Action subgraph."""

    ACTION_AGENT = "action_agent"
    EXECUTE_CREATE_RETURN = "execute_create_return"
    BUILD_RESPONSE = "build_action_response"


class RouteAfterActionRoute(str, Enum):
    """Define branches returned by route_after_action."""

    EXECUTE_CREATE_RETURN = "execute_create_return"
    BUILD_RESPONSE = "build_action_response"


def route_after_action(state: EcommerceActionState) -> RouteAfterActionRoute:
    """Route execution to specific action execution nodes or terminate."""
    if not state.messages:
        return RouteAfterActionRoute.BUILD_RESPONSE

    last_message = state.messages[-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return RouteAfterActionRoute.BUILD_RESPONSE

    for tool_call in last_message.tool_calls:
        name = tool_call.get("name")
        if name == "create_ecommerce_return_request":
            return RouteAfterActionRoute.EXECUTE_CREATE_RETURN

    return RouteAfterActionRoute.BUILD_RESPONSE


builder = StateGraph(
    EcommerceActionState,
    input_schema=SupervisorSubgraphInput,
    output_schema=EcommerceActionOutput,
)
builder.add_node(EcommerceActionNodeNames.ACTION_AGENT.value, action_agent)
builder.add_node(EcommerceActionNodeNames.EXECUTE_CREATE_RETURN.value, execute_create_return)
builder.add_node(EcommerceActionNodeNames.BUILD_RESPONSE.value, build_action_response)

builder.add_edge(START, EcommerceActionNodeNames.ACTION_AGENT.value)

builder.add_conditional_edges(
    EcommerceActionNodeNames.ACTION_AGENT.value,
    route_after_action,
    {
        RouteAfterActionRoute.EXECUTE_CREATE_RETURN.value: EcommerceActionNodeNames.EXECUTE_CREATE_RETURN.value,
        RouteAfterActionRoute.BUILD_RESPONSE.value: EcommerceActionNodeNames.BUILD_RESPONSE.value,
    },
)

builder.add_edge(EcommerceActionNodeNames.EXECUTE_CREATE_RETURN.value, EcommerceActionNodeNames.ACTION_AGENT.value)
builder.add_edge(EcommerceActionNodeNames.BUILD_RESPONSE.value, END)

memory = get_checkpointer(settings.DB_FILE)

ecommerce_action_graph = builder.compile(
    name=SupervisorGraphNames.ECOMMERCE_ACTION.value,
    checkpointer=memory,
)
