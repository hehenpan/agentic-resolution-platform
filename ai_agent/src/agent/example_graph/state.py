from __future__ import annotations
from dataclasses import dataclass
from typing_extensions import TypedDict

class Context(TypedDict):
    """Context parameters for the agent.

    Set these when creating assistants OR when invoking the graph.
    """
    my_configurable_param: str


@dataclass
class State:
    """Input state for the agent.

    Defines the initial structure of incoming data.
    """
    changeme: str = "example"
