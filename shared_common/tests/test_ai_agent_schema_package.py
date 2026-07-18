"""Tests for the consolidated AI Agent schema package."""

import pytest
from pydantic import ValidationError

from shared_common.schemas.ai_agent import RAGFileImportPayload, RAGFileImportResult


def test_rag_file_import_payload_is_exported_by_ai_agent_package() -> None:
    payload = RAGFileImportPayload(
        file_id=1,
        file_name="policy.md",
        file_size=10,
        file_owner_id=2,
        file_tenant_id=3,
        file_content=b"policy",
        extra_meta={"source": "test"},
    )

    restored = RAGFileImportPayload.model_validate_json(payload.model_dump_json())

    assert restored == payload


def test_rag_file_import_payload_rejects_non_json_metadata() -> None:
    with pytest.raises(ValidationError):
        RAGFileImportPayload(
            file_id=1,
            file_name="policy.md",
            file_size=10,
            file_owner_id=2,
            file_tenant_id=3,
            file_content=b"policy",
            extra_meta={"invalid": object()},
        )


def test_rag_file_import_result_is_exported_and_round_trips() -> None:
    result = RAGFileImportResult(
        file_id=1,
        file_name="policy.md",
    )

    restored = RAGFileImportResult.model_validate_json(result.model_dump_json())

    assert restored == result
    assert restored.status == "success"


def test_rag_file_import_result_rejects_empty_file_name() -> None:
    with pytest.raises(ValidationError):
        RAGFileImportResult(file_id=1, file_name="")


def test_rag_file_import_result_rejects_non_success_status() -> None:
    with pytest.raises(ValidationError):
        RAGFileImportResult(
            file_id=1,
            file_name="policy.md",
            status="failed",  # type: ignore[arg-type]
        )
