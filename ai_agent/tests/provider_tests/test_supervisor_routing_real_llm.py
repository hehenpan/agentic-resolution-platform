import json
import os
from datetime import datetime, timezone

import pytest
from langchain_core.messages import HumanMessage

from agent.core.constants import GEMINI_CHAT_MODEL
from agent.supervisor.nodes import route_request
from agent.supervisor.state import SelectRouteRoute, SupervisorState

pytestmark = pytest.mark.anyio

POLICY_QUESTION = (
    "how many working days for products typically arrive for North Island?"
)


@pytest.mark.skipif(
    os.getenv("RUN_REAL_LLM") != "1",
    reason="Set RUN_REAL_LLM=1 to call the real supervisor LLM",
)
async def test_supervisor_real_llm_routes_policy_question() -> None:
    state = SupervisorState(messages=[HumanMessage(content=POLICY_QUESTION)])

    update = await route_request(state)

    assert update["route"] == SelectRouteRoute.POLICY_QA
    record = {
        "model": GEMINI_CHAT_MODEL,
        "question": POLICY_QUESTION,
        "route": update["route"].value,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    print(  # noqa: T201 - this opt-in test emits the record for persistence.
        "SUPERVISOR_ROUTE_RECORD=" + json.dumps(record, ensure_ascii=True)
    )
