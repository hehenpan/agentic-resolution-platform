"""Ecommerce Query subgraph assembly."""

from enum import Enum
from langgraph.graph import END, START, StateGraph

from agent.supervisor.ecommerce_query.nodes import (
    query_agent,
    retrieve_orders,
    retrieve_user,
)
from agent.supervisor.ecommerce_query.state import EcommerceQueryOutput, EcommerceQueryState
from agent.supervisor.state import SupervisorGraphNames


class EcommerceQueryNodeNames(str, Enum):
    """Define node identifiers for the Ecommerce Query subgraph."""

    QUERY_AGENT = "query_agent"
    RETRIEVE_USER = "retrieve_user"
    RETRIEVE_ORDERS = "retrieve_orders"


class RouteAfterQueryRoute(str, Enum):
    """Define branches returned by route_after_query."""

    RETRIEVE_USER = "retrieve_user"
    RETRIEVE_ORDERS = "retrieve_orders"
    END = "__end__"


def route_after_query(state: EcommerceQueryState) -> RouteAfterQueryRoute:
    """Route execution to specific tool nodes or terminate."""
    if not state.messages:
        return RouteAfterQueryRoute.END

    last_message = state.messages[-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return RouteAfterQueryRoute.END

    for tool_call in last_message.tool_calls:
        name = tool_call.get("name")
        if name == "get_ecommerce_user":
            return RouteAfterQueryRoute.RETRIEVE_USER
        if name == "get_ecommerce_orders":
            return RouteAfterQueryRoute.RETRIEVE_ORDERS

    return RouteAfterQueryRoute.END


builder = StateGraph(
    EcommerceQueryState,
    output_schema=EcommerceQueryOutput,
)
builder.add_node(EcommerceQueryNodeNames.QUERY_AGENT.value, query_agent)
builder.add_node(EcommerceQueryNodeNames.RETRIEVE_USER.value, retrieve_user)
builder.add_node(EcommerceQueryNodeNames.RETRIEVE_ORDERS.value, retrieve_orders)

builder.add_edge(START, EcommerceQueryNodeNames.QUERY_AGENT.value)

builder.add_conditional_edges(
    EcommerceQueryNodeNames.QUERY_AGENT.value,
    route_after_query,
    {
        RouteAfterQueryRoute.RETRIEVE_USER.value: EcommerceQueryNodeNames.RETRIEVE_USER.value,
        RouteAfterQueryRoute.RETRIEVE_ORDERS.value: EcommerceQueryNodeNames.RETRIEVE_ORDERS.value,
        RouteAfterQueryRoute.END.value: END,
    },
)

builder.add_edge(EcommerceQueryNodeNames.RETRIEVE_USER.value, EcommerceQueryNodeNames.QUERY_AGENT.value)
builder.add_edge(EcommerceQueryNodeNames.RETRIEVE_ORDERS.value, EcommerceQueryNodeNames.QUERY_AGENT.value)

from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()

ecommerce_query_graph = builder.compile(
    name=SupervisorGraphNames.ECOMMERCE_QUERY.value,
    checkpointer=memory,
)
