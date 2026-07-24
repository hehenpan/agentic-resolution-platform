"""Policy QA subgraph assembly."""

from langgraph.graph import END, START, StateGraph

from agent.supervisor.policy_qa.nodes import (
    PolicyQANodes,
    RouteAfterRetrievalRoute,
    build_response,
    generate_draft,
    retrieve_policy,
    route_after_retrieval,
)
from agent.supervisor.policy_qa.state import PolicyQAOutput, PolicyQAState
from agent.supervisor.state import SupervisorGraphNames, SupervisorSubgraphInput

builder = StateGraph(
    PolicyQAState,
    input_schema=SupervisorSubgraphInput,
    output_schema=PolicyQAOutput,
)
builder.add_node(PolicyQANodes.RETRIEVE_POLICY, retrieve_policy)
builder.add_node(PolicyQANodes.GENERATE_DRAFT, generate_draft)
builder.add_node(PolicyQANodes.BUILD_RESPONSE, build_response)

builder.add_edge(START, PolicyQANodes.RETRIEVE_POLICY)
builder.add_conditional_edges(
    PolicyQANodes.RETRIEVE_POLICY,
    route_after_retrieval,
    {
        RouteAfterRetrievalRoute.GENERATE_DRAFT: (
            PolicyQANodes.GENERATE_DRAFT
        ),
        RouteAfterRetrievalRoute.BUILD_RESPONSE: PolicyQANodes.BUILD_RESPONSE,
    },
)
builder.add_edge(PolicyQANodes.GENERATE_DRAFT, PolicyQANodes.BUILD_RESPONSE)
builder.add_edge(PolicyQANodes.BUILD_RESPONSE, END)

policy_qa_graph = builder.compile(name=SupervisorGraphNames.POLICY_QA.value)
