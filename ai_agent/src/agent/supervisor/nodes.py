"""Nodes for LLM-based supervisor routing."""

from typing import Any

from langchain_core.messages import HumanMessage

from agent.core import llm
from agent.core.logger import logger
from agent.supervisor.prompts import (
    SUPERVISOR_ROUTING_PROMPT,
    SupervisorRoutingPromptInput,
)
from agent.supervisor.state import (
    RouteRequestUpdate,
    SelectRouteRoute,
    SupervisorDecision,
    SupervisorState,
)


def _latest_customer_question(state: SupervisorState) -> str:
    for message in reversed(state.messages):
        if isinstance(message, HumanMessage):
            question = message.text.strip()
            if question:
                return question

    logger.error("Supervisor routing requires a non-empty HumanMessage")
    raise ValueError("Supervisor routing requires a customer question")


async def route_request(state: SupervisorState) -> dict[str, Any]:
    """Ask the LLM to select the next specialist subgraph."""
    question = _latest_customer_question(state)

    try:
        prompt_input = SupervisorRoutingPromptInput(
            question=question,
        )
        prompt_value = await SUPERVISOR_ROUTING_PROMPT.ainvoke(
            prompt_input.model_dump()
        )
        model = llm.get_llm_model()
        router = model.with_structured_output(SupervisorDecision)
        raw_decision = await router.ainvoke(prompt_value)
        decision = SupervisorDecision.model_validate(raw_decision)
    except Exception as error:
        logger.error(
            "Failed to route customer request with the LLM: {}",
            type(error).__name__,
        )
        raise

    update = RouteRequestUpdate(route=decision.route)
    return update.model_dump(exclude_unset=True)


def select_route(state: SupervisorState) -> SelectRouteRoute:
    """Return the validated route used by conditional graph edges."""
    if state.route is None:
        logger.error("Supervisor route is missing after LLM routing")
        raise ValueError("Supervisor route is missing")
    return state.route
