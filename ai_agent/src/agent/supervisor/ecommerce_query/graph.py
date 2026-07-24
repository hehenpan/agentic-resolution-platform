"""Ecommerce Query subgraph assembly."""

from enum import Enum

from langgraph.graph import END, START, StateGraph

from agent.core.checkpoint import get_checkpointer
from agent.core.config import settings
from agent.supervisor.ecommerce_query.nodes import (
    build_query_response,
    query_agent,
    retrieve_order_details,
    retrieve_orders,
    retrieve_returns_by_customer,
    retrieve_returns_by_order,
    retrieve_user,
)
from agent.supervisor.ecommerce_query.state import (
    EcommerceQueryOutput,
    EcommerceQueryState,
)
from agent.supervisor.state import SupervisorGraphNames, SupervisorSubgraphInput


class EcommerceQueryNodeNames(str, Enum):
    """Define node identifiers for the Ecommerce Query subgraph."""

    QUERY_AGENT = "query_agent"
    RETRIEVE_USER = "retrieve_user"
    RETRIEVE_ORDERS = "retrieve_orders"
    RETRIEVE_ORDER_DETAILS = "retrieve_order_details"
    RETRIEVE_RETURNS_BY_ORDER = "retrieve_returns_by_order"
    RETRIEVE_RETURNS_BY_CUSTOMER = "retrieve_returns_by_customer"
    BUILD_RESPONSE = "build_query_response"


class RouteAfterQueryRoute(str, Enum):
    """Define branches returned by route_after_query."""

    RETRIEVE_USER = "retrieve_user"
    RETRIEVE_ORDERS = "retrieve_orders"
    RETRIEVE_ORDER_DETAILS = "retrieve_order_details"
    RETRIEVE_RETURNS_BY_ORDER = "retrieve_returns_by_order"
    RETRIEVE_RETURNS_BY_CUSTOMER = "retrieve_returns_by_customer"
    BUILD_RESPONSE = "build_query_response"


def route_after_query(state: EcommerceQueryState) -> RouteAfterQueryRoute:
    """Route execution to specific tool nodes or terminate."""
    if not state.messages:
        return RouteAfterQueryRoute.BUILD_RESPONSE

    last_message = state.messages[-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return RouteAfterQueryRoute.BUILD_RESPONSE

    for tool_call in last_message.tool_calls:
        name = tool_call.get("name")
        if name == "get_ecommerce_user":
            return RouteAfterQueryRoute.RETRIEVE_USER
        if name == "get_ecommerce_orders":
            return RouteAfterQueryRoute.RETRIEVE_ORDERS
        if name == "get_ecommerce_order_details":
            return RouteAfterQueryRoute.RETRIEVE_ORDER_DETAILS
        if name == "get_return_requests_by_order":
            return RouteAfterQueryRoute.RETRIEVE_RETURNS_BY_ORDER
        if name == "get_return_requests_by_customer":
            return RouteAfterQueryRoute.RETRIEVE_RETURNS_BY_CUSTOMER

    return RouteAfterQueryRoute.BUILD_RESPONSE


builder = StateGraph(
    EcommerceQueryState,
    input_schema=SupervisorSubgraphInput,
    output_schema=EcommerceQueryOutput,
)
builder.add_node(EcommerceQueryNodeNames.QUERY_AGENT.value, query_agent)
builder.add_node(EcommerceQueryNodeNames.RETRIEVE_USER.value, retrieve_user)
builder.add_node(EcommerceQueryNodeNames.RETRIEVE_ORDERS.value, retrieve_orders)
builder.add_node(
    EcommerceQueryNodeNames.RETRIEVE_ORDER_DETAILS.value,
    retrieve_order_details,
)
builder.add_node(
    EcommerceQueryNodeNames.RETRIEVE_RETURNS_BY_ORDER.value,
    retrieve_returns_by_order,
)
builder.add_node(
    EcommerceQueryNodeNames.RETRIEVE_RETURNS_BY_CUSTOMER.value,
    retrieve_returns_by_customer,
)
builder.add_node(
    EcommerceQueryNodeNames.BUILD_RESPONSE.value,
    build_query_response,
)

builder.add_edge(START, EcommerceQueryNodeNames.QUERY_AGENT.value)

builder.add_conditional_edges(
    EcommerceQueryNodeNames.QUERY_AGENT.value,
    route_after_query,
    {
        RouteAfterQueryRoute.RETRIEVE_USER.value: EcommerceQueryNodeNames.RETRIEVE_USER.value,
        RouteAfterQueryRoute.RETRIEVE_ORDERS.value: EcommerceQueryNodeNames.RETRIEVE_ORDERS.value,
        RouteAfterQueryRoute.RETRIEVE_ORDER_DETAILS.value: (
            EcommerceQueryNodeNames.RETRIEVE_ORDER_DETAILS.value
        ),
        RouteAfterQueryRoute.RETRIEVE_RETURNS_BY_ORDER.value: (
            EcommerceQueryNodeNames.RETRIEVE_RETURNS_BY_ORDER.value
        ),
        RouteAfterQueryRoute.RETRIEVE_RETURNS_BY_CUSTOMER.value: (
            EcommerceQueryNodeNames.RETRIEVE_RETURNS_BY_CUSTOMER.value
        ),
        RouteAfterQueryRoute.BUILD_RESPONSE.value: (
            EcommerceQueryNodeNames.BUILD_RESPONSE.value
        ),
    },
)

builder.add_edge(EcommerceQueryNodeNames.RETRIEVE_USER.value, EcommerceQueryNodeNames.QUERY_AGENT.value)
builder.add_edge(EcommerceQueryNodeNames.RETRIEVE_ORDERS.value, EcommerceQueryNodeNames.QUERY_AGENT.value)
builder.add_edge(
    EcommerceQueryNodeNames.RETRIEVE_ORDER_DETAILS.value,
    EcommerceQueryNodeNames.QUERY_AGENT.value,
)
builder.add_edge(
    EcommerceQueryNodeNames.RETRIEVE_RETURNS_BY_ORDER.value,
    EcommerceQueryNodeNames.QUERY_AGENT.value,
)
builder.add_edge(
    EcommerceQueryNodeNames.RETRIEVE_RETURNS_BY_CUSTOMER.value,
    EcommerceQueryNodeNames.QUERY_AGENT.value,
)
builder.add_edge(EcommerceQueryNodeNames.BUILD_RESPONSE.value, END)

memory = get_checkpointer(settings.DB_FILE)

ecommerce_query_graph = builder.compile(
    name=SupervisorGraphNames.ECOMMERCE_QUERY.value,
    checkpointer=memory,
)
