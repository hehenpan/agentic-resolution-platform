"""Map Policy QA results to the public agent output protocol."""

from shared_common.schemas.ai_agent import (
    AgentOutput,
    AgentOutputPartKind,
    AgentSourceType,
    SourceReference,
    SourcesPart,
    TextPart,
)

from agent.core.output_identity import AgentOutputKey, build_output_id
from agent.supervisor.policy_qa.state import PolicyChunk


def build_policy_qa_output(
    *,
    identity_scope: str,
    text: str,
    policy_chunks: list[PolicyChunk],
) -> AgentOutput:
    """Build the public output for one Policy QA response."""
    sources = []
    for chunk in policy_chunks:
        serialized_chunk = chunk.model_dump(mode="json")
        sources.append(
            SourceReference(
                source_id=str(chunk.point_id),
                source_type=AgentSourceType.POLICY_RAG,
                title=chunk.file_name,
                attributes={
                    "score": serialized_chunk["score"],
                    "text": serialized_chunk["text"],
                    "payload": serialized_chunk["payload"],
                },
            )
        )

    return AgentOutput(
        output_id=build_output_id(
            identity_scope=identity_scope,
            output_key=AgentOutputKey.POLICY_QA_FINAL_RESPONSE,
        ),
        parts=[
            TextPart(
                kind=AgentOutputPartKind.TEXT,
                text=text,
            ),
            SourcesPart(
                kind=AgentOutputPartKind.SOURCES,
                sources=sources,
            ),
        ],
    )
