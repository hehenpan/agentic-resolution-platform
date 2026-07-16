"""Nodes for policy retrieval and response generation."""

from enum import Enum
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage

from agent.core import embedding, llm, vectordb
from agent.core.constants import QDRANT_COLLECTION_RAG
from agent.core.logger import logger
from agent.supervisor.policy_qa.prompts import (
    POLICY_DRAFT_PROMPT,
    PolicyDraftPromptInput,
)
from agent.supervisor.policy_qa.state import (
    BuildResponseUpdate,
    GenerateDraftUpdate,
    PolicyChunk,
    PolicyQAState,
    RetrievePolicyUpdate,
)

POLICY_RETRIEVAL_LIMIT = 3


class PolicyQANodes(str, Enum):
    """Define node identifiers for the Policy QA subgraph."""

    RETRIEVE_POLICY = "retrieve_policy"
    GENERATE_DRAFT = "generate_draft"
    BUILD_RESPONSE = "build_response"


class RouteAfterRetrievalRoute(str, Enum):
    """Define branches returned by route_after_retrieval."""

    GENERATE_DRAFT = "generate_draft"
    BUILD_RESPONSE = "build_response"


def _latest_customer_question(state: PolicyQAState) -> str:
    for message in reversed(state.messages):
        if isinstance(message, HumanMessage):
            question = message.text.strip()
            if question:
                return question

    logger.error("Policy retrieval requires a non-empty HumanMessage")
    raise ValueError("Policy retrieval requires a customer question")


async def retrieve_policy(state: PolicyQAState) -> dict[str, Any]:
    """Retrieve policy chunks relevant to the latest customer question."""
    question = _latest_customer_question(state)

    try:
        query_vector = await embedding.get_embedding_model().aembed_query(
            question
        )
        results = vectordb.get_vector_db().search(
            collection_name=QDRANT_COLLECTION_RAG,
            query_vector=query_vector,
            limit=POLICY_RETRIEVAL_LIMIT,
        )
        chunks = [
            PolicyChunk(
                point_id=result.id,
                score=result.score,
                file_name=result.payload["file_name"],
                text=result.payload["text"],
                payload=result.payload,
            )
            for result in results
        ]
    except Exception as error:
        logger.error(
            "Failed to retrieve policy chunks from the RAG store: {}",
            type(error).__name__,
        )
        raise

    update = RetrievePolicyUpdate(
        query=question,
        policy_chunks=chunks,
    )
    return update.model_dump(exclude_unset=True)


def route_after_retrieval(state: PolicyQAState) -> RouteAfterRetrievalRoute:
    """Skip draft generation when no policy chunks were found."""
    if state.policy_chunks:
        return RouteAfterRetrievalRoute.GENERATE_DRAFT
    return RouteAfterRetrievalRoute.BUILD_RESPONSE


def _format_policy_context(chunks: list[PolicyChunk]) -> str:
    return "\n\n".join(
        f"Source file: {chunk.file_name}\n{chunk.text}"
        for chunk in chunks
    )


async def generate_draft(state: PolicyQAState) -> dict[str, Any]:
    """Generate a polished customer-service draft from retrieved policies."""
    if state.query is None:
        logger.error("Policy draft generation requires a customer question")
        update = GenerateDraftUpdate(
            generation_error="Failed to generate a polished policy response"
        )
        return update.model_dump(exclude_unset=True)

    try:
        prompt_input = PolicyDraftPromptInput(
            question=state.query,
            context=_format_policy_context(state.policy_chunks),
        )
        prompt_value = await POLICY_DRAFT_PROMPT.ainvoke(
            prompt_input.model_dump()
        )
        response = await llm.get_llm_model().ainvoke(prompt_value)
        if not isinstance(response, AIMessage):
            raise TypeError("Policy draft LLM must return an AIMessage")

        draft = response.text.strip()
        if not draft:
            raise ValueError("Policy draft LLM returned empty content")
    except Exception as error:
        logger.error(
            "Failed to generate a polished policy response: {}",
            type(error).__name__,
        )
        update = GenerateDraftUpdate(
            generation_error="Failed to generate a polished policy response"
        )
        return update.model_dump(exclude_unset=True)

    update = GenerateDraftUpdate(draft=draft)
    return update.model_dump(exclude_unset=True)


def _format_policy_references(chunks: list[PolicyChunk]) -> str:
    references = [
        f"[{index}] {chunk.file_name}\n{chunk.text}"
        for index, chunk in enumerate(chunks, start=1)
    ]
    return "Policy references:\n\n" + "\n\n".join(references)


async def build_response(state: PolicyQAState) -> dict[str, Any]:
    """Build the final answer with exact policy excerpts and metadata."""
    if not state.policy_chunks:
        content = (
            "I could not find a relevant policy for this question. "
            "Please review the request manually."
        )
    else:
        references = _format_policy_references(state.policy_chunks)
        if state.draft:
            content = f"{state.draft}\n\n{references}"
        else:
            content = (
                "I could not prepare a polished response, but the relevant "
                f"policy excerpts are included below.\n\n{references}"
            )

    response = AIMessage(
        content=content,
        type="ai",
        response_metadata={
            "policy_chunks": [
                chunk.model_dump(mode="json")
                for chunk in state.policy_chunks
            ]
        },
    )
    update = BuildResponseUpdate(messages=[response])
    return update.model_dump(exclude_unset=True)
