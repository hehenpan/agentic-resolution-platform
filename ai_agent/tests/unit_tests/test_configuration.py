from langgraph.pregel import Pregel

from agent.example_graph import example_graph


def test_placeholder() -> None:
    # TODO: You can add actual unit tests
    # for your graph and other logic here.
    assert isinstance(example_graph, Pregel)
