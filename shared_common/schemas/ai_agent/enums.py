"""Enums used by public AI Agent schemas."""

from enum import Enum


class AgentOutputPartKind(str, Enum):
    """Identify the shape of an agent output part."""

    TEXT = "text"
    STRUCTURED_DATA = "structured_data"
    SOURCES = "sources"


class AgentSourceType(str, Enum):
    """Identify the system that supplied an output source."""

    POLICY_RAG = "policy_rag"


class AgentDomainEventKind(str, Enum):
    """Identify stable event types exposed by the agent domain protocol."""

    OUTPUT_PRODUCED = "agent.output_produced"
    PROGRESS_REPORTED = "agent.progress_reported"
    HUMAN_INPUT_REQUESTED = "agent.human_input_requested"
    RUN_COMPLETED = "agent.run_completed"
    RUN_INTERRUPTED = "agent.run_interrupted"
    RUN_FAILED = "agent.run_failed"


class AgentCustomStreamEventKind(str, Enum):
    """Identify typed events emitted through LangGraph custom streaming."""

    PROGRESS = "agent.progress"


class AgentProgressStatus(str, Enum):
    """Identify the lifecycle status of a reported operation."""

    STARTED = "started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class AgentReturnReason(str, Enum):
    """Identify return reason codes in agent contract."""

    CHANGE_OF_MIND = "change_of_mind"
    DAMAGED = "damaged"
    WRONG_ITEM = "wrong_item"
    NOT_AS_DESCRIBED = "not_as_described"
    LATE_DELIVERY = "late_delivery"


class AgentItemCondition(str, Enum):
    """Identify returned item conditions in agent contract."""

    UNOPENED = "unopened"
    OPENED = "opened"
    USED = "used"
    DAMAGED = "damaged"


class AgentRunStatus(str, Enum):
    """Identify the status of an agent run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    INTERRUPTED = "interrupted"


