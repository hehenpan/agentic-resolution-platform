"""Supervisor graph assembly."""

from langgraph.graph import END, START, StateGraph

from agent.core.checkpoint import get_checkpointer
from agent.core.config import settings
from agent.supervisor.ecommerce_query.graph import ecommerce_query_graph
from agent.supervisor.ecommerce_action.graph import ecommerce_action_graph
from agent.supervisor.nodes import route_request, select_route
from agent.supervisor.policy_qa import policy_qa_graph
from agent.supervisor.state import (
    SelectRouteRoute,
    SupervisorGraphNames,
    SupervisorNodeNames,
    SupervisorOutput,
    SupervisorState,
)

builder = StateGraph(SupervisorState, output_schema=SupervisorOutput)
builder.add_node(SupervisorNodeNames.ROUTE_REQUEST, route_request)
builder.add_node(SupervisorNodeNames.POLICY_QA, policy_qa_graph)
builder.add_node(SupervisorNodeNames.ECOMMERCE_QUERY, ecommerce_query_graph)
builder.add_node(SupervisorNodeNames.ECOMMERCE_ACTION, ecommerce_action_graph)

builder.add_edge(START, SupervisorNodeNames.ROUTE_REQUEST)
builder.add_conditional_edges(
    SupervisorNodeNames.ROUTE_REQUEST,
    select_route,
    {
        SelectRouteRoute.POLICY_QA: SupervisorNodeNames.POLICY_QA,
        SelectRouteRoute.ECOMMERCE_QUERY: SupervisorNodeNames.ECOMMERCE_QUERY,
        SelectRouteRoute.ECOMMERCE_ACTION: SupervisorNodeNames.ECOMMERCE_ACTION,
    },
)
builder.add_edge(SupervisorNodeNames.POLICY_QA, END)
builder.add_edge(SupervisorNodeNames.ECOMMERCE_QUERY, END)
builder.add_edge(SupervisorNodeNames.ECOMMERCE_ACTION, END)

memory = get_checkpointer(settings.DB_FILE)

supervisor_graph = builder.compile(
    name=SupervisorGraphNames.SUPERVISOR.value,
    checkpointer=memory,
)
