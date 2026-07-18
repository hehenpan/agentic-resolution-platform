"""Map File Ingest results to the public agent output protocol."""

from shared_common.schemas.ai_agent import (
    AgentOutput,
    AgentOutputPartKind,
    AgentOutputSchemaId,
    RAGFileImportResult,
    StructuredDataPart,
)

from agent.core.output_identity import AgentOutputKey, build_output_id


def build_rag_file_import_output(
    *,
    identity_scope: str,
    file_id: int,
    file_name: str,
) -> AgentOutput:
    """Build the public output for one successful RAG file import."""
    result = RAGFileImportResult(
        file_id=file_id,
        file_name=file_name,
    )
    return AgentOutput(
        output_id=build_output_id(
            identity_scope=identity_scope,
            output_key=AgentOutputKey.RAG_FILE_IMPORT_RESULT,
            subject_id=str(file_id),
        ),
        parts=[
            StructuredDataPart(
                kind=AgentOutputPartKind.STRUCTURED_DATA,
                schema_id=AgentOutputSchemaId.RAG_FILE_IMPORT_RESULT_V1.value,
                data=result.model_dump(mode="json"),
            )
        ],
    )
