import pytest

from agent import example_graph
from agent.core.logger import logger

pytestmark = pytest.mark.anyio


async def test_agent_simple_passthrough() -> None:
    inputs = {"changeme": "some_val"}
    config = {"configurable": {"thread_id": "test-thread-id"}}
    
    res = await example_graph.ainvoke(inputs, config=config)
    assert res is not None
    logger.info(f"test_agent_simple_passthrough result: {res}")
