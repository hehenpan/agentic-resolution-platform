import json
import os
from datetime import datetime, timezone

import pytest
from langchain_core.messages import HumanMessage

from agent.core.config import settings
from agent.supervisor.policy_qa.nodes import generate_draft, retrieve_policy
from agent.supervisor.policy_qa.state import PolicyQAState

pytestmark = pytest.mark.anyio

POLICY_QUESTION = (
    "how many working days for products typically arrive for North Island?"
)


@pytest.mark.skipif(
    os.getenv("RUN_REAL_LLM") != "1",
    reason="Set RUN_REAL_LLM=1 to call the real Policy QA LLM",
)
async def test_policy_qa_real_llm_generates_grounded_draft(
    prebuilt_qdrant_env,
) -> None:
    messages = [HumanMessage(content=POLICY_QUESTION)]
    retrieval_update = await retrieve_policy(PolicyQAState(messages=messages))
    state = PolicyQAState(messages=messages, **retrieval_update)

    draft_update = await generate_draft(state)

    assert draft_update.get("generation_error") is None
    assert draft_update["draft"]
    record = {
        "model": settings.LLM_CHAT_MODEL,
        "question": POLICY_QUESTION,
        "draft": draft_update["draft"],
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    print(  # noqa: T201 - this opt-in test emits the record for persistence.
        "POLICY_QA_RECORD=" + json.dumps(record, ensure_ascii=True)
    )
