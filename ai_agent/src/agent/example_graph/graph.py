from langgraph.graph import StateGraph
from agent.core.config import settings
from agent.core.checkpoint import LazyAsyncSqliteSaver
from agent.example_graph.state import State, Context
from agent.example_graph.nodes import call_model

memory = LazyAsyncSqliteSaver(settings.DB_FILE)

example_graph = (
    StateGraph(State, context_schema=Context)
    .add_node(call_model)
    .add_edge("__start__", "call_model")
    .compile(name="example graph", checkpointer=memory)
)
