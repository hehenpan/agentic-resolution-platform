"""Tests for stable public agent output identities."""

from uuid import UUID

import pytest

from agent.core.output_identity import (
    AgentOutputKey,
    build_output_id,
)

IDENTITY_SCOPE_ONE = "task-1"
IDENTITY_SCOPE_TWO = "task-2"


def test_build_output_id_is_stable_for_same_logical_output() -> None:
    first = build_output_id(
        identity_scope=IDENTITY_SCOPE_ONE,
        output_key=AgentOutputKey.POLICY_QA_FINAL_RESPONSE,
        subject_id="subject-1",
    )
    replayed = build_output_id(
        identity_scope=IDENTITY_SCOPE_ONE,
        output_key=AgentOutputKey.POLICY_QA_FINAL_RESPONSE,
        subject_id="subject-1",
    )

    assert replayed == first
    assert isinstance(first, str)
    assert UUID(first).version == 5


def test_build_output_id_changes_for_different_identity_scope() -> None:
    first = build_output_id(
        identity_scope=IDENTITY_SCOPE_ONE,
        output_key=AgentOutputKey.POLICY_QA_FINAL_RESPONSE,
    )
    second = build_output_id(
        identity_scope=IDENTITY_SCOPE_TWO,
        output_key=AgentOutputKey.POLICY_QA_FINAL_RESPONSE,
    )

    assert second != first


def test_build_output_id_changes_for_different_subject() -> None:
    first = build_output_id(
        identity_scope=IDENTITY_SCOPE_ONE,
        output_key=AgentOutputKey.POLICY_QA_FINAL_RESPONSE,
        subject_id="subject-1",
    )
    second = build_output_id(
        identity_scope=IDENTITY_SCOPE_ONE,
        output_key=AgentOutputKey.POLICY_QA_FINAL_RESPONSE,
        subject_id="subject-2",
    )

    assert second != first


def test_build_output_id_rejects_string_output_key() -> None:
    with pytest.raises(TypeError):
        build_output_id(
            identity_scope=IDENTITY_SCOPE_ONE,
            output_key="policy_qa.final_response",  # type: ignore[arg-type]
        )
