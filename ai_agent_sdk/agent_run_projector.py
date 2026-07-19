"""Project LangGraph transport events into stable agent domain events."""

from collections.abc import Callable, Mapping, Sequence
from time import time
from uuid import UUID, uuid5

from loguru import logger
from pydantic import ValidationError
from shared_common.schemas.ai_agent import (
    AgentCustomStreamEventKind,
    AgentDomainEvent,
    AgentDomainEventKind,
    AgentError,
    AgentOutput,
    AgentOutputProduced,
    AgentProgressReported,
    AgentProgressStreamEvent,
    AgentResumeCursor,
    AgentRunCompleted,
    AgentRunFailed,
    AgentRunInterrupted,
    HumanInputRequest,
    HumanInputRequested,
)

AGENT_EVENT_NAMESPACE = UUID("507db244-9336-55f5-a55f-146301c9b928")


def _unix_time() -> int:
    return int(time())


def build_event_id(
    kind: AgentDomainEventKind,
    thread_id: str,
    subject_key: str,
) -> str:
    """Build a replay-stable UUID string for a non-output domain event."""
    return str(uuid5(AGENT_EVENT_NAMESPACE, f"{kind.value}:{thread_id}:{subject_key}"))


class AgentRunProjector:
    """Convert one agent run's raw stream and final state into domain events."""

    def __init__(
        self,
        thread_id: str,
        clock: Callable[[], int] = _unix_time,
    ) -> None:
        """Initialize projection state for one agent thread operation."""
        self._thread_id = thread_id
        self._clock = clock
        self._next_sequence = 0
        self._published_output_ids: set[str] = set()
        self._published_progress_ids: set[str] = set()
        self._published_interrupt_ids: set[str] = set()
        self._outputs: dict[str, AgentOutput] = {}
        self._resume_cursor: AgentResumeCursor | None = None
        self._terminal_event: AgentDomainEvent | None = None

    def process(
        self,
        raw_event: Mapping[str, object],
        source_sequence: int | None = None,
    ) -> list[AgentDomainEvent]:
        """Project one raw SDK v2 stream event into zero or more events."""
        event_type = raw_event.get("type")
        data = raw_event.get("data")

        if event_type == "checkpoints":
            self._update_resume_cursor_from_checkpoint_payload(data)
            return []

        if event_type in {"updates", "values"}:
            return self._publish_outputs(data, source_sequence)

        if event_type == "custom":
            return self._project_custom_event(data, source_sequence)

        return []

    def finalize(
        self,
        thread_state: Mapping[str, object],
    ) -> list[AgentDomainEvent]:
        """Publish remaining outputs and exactly one authoritative terminal event."""
        if self._terminal_event is not None:
            return []

        self._update_resume_cursor_from_thread_state(thread_state)
        events = self._publish_outputs(thread_state.get("values"), None)
        interrupts = self._extract_interrupts(thread_state)

        if interrupts:
            events.extend(self._publish_interrupts(interrupts))
            terminal: AgentRunCompleted | AgentRunInterrupted = (
                self._build_interrupted_event(interrupts)
            )
        else:
            terminal = self._build_completed_event()

        self._terminal_event = terminal
        events.append(terminal)
        return events

    def fail(self, error: Exception) -> list[AgentDomainEvent]:
        """Convert a transport failure into one safe terminal failure event."""
        logger.error(f"Agent run stream failed: error={type(error).__name__}")
        if self._terminal_event is not None:
            return []

        event = AgentRunFailed(
            event_id=build_event_id(
                AgentDomainEventKind.RUN_FAILED,
                self._thread_id,
                self._terminal_subject(type(error).__name__),
            ),
            thread_id=self._thread_id,
            sequence=self._take_sequence(),
            created_at=self._clock(),
            error=AgentError(
                code="AGENT_RUN_FAILED",
                message="The agent run could not be completed.",
                retryable=True,
            ),
        )
        self._terminal_event = event
        return [event]

    def _publish_outputs(
        self,
        value: object,
        source_sequence: int | None,
    ) -> list[AgentDomainEvent]:
        events: list[AgentDomainEvent] = []
        for output_payload in self._find_output_payloads(value):
            try:
                output = AgentOutput.model_validate(output_payload)
            except ValidationError as error:
                logger.error(f"Invalid AgentOutput in agent stream: {error}")
                continue

            self._outputs[output.output_id] = output
            if output.output_id in self._published_output_ids:
                continue

            source_sequences = [source_sequence] if source_sequence is not None else []
            events.append(
                AgentOutputProduced(
                    event_id=output.output_id,
                    thread_id=self._thread_id,
                    sequence=self._take_sequence(),
                    source_sequences=source_sequences,
                    created_at=self._clock(),
                    output=output,
                )
            )
            self._published_output_ids.add(output.output_id)
        return events

    def _project_custom_event(
        self,
        value: object,
        source_sequence: int | None,
    ) -> list[AgentDomainEvent]:
        if not isinstance(value, Mapping):
            logger.error("Agent custom stream event is not a mapping; skipping")
            return []
        kind = value.get("kind")
        if kind != AgentCustomStreamEventKind.PROGRESS.value:
            logger.error(f"Unknown agent custom stream event kind; skipping: {kind}")
            return []
        if source_sequence is None:
            logger.error("Agent progress event has no raw source sequence; skipping")
            return []

        try:
            progress = AgentProgressStreamEvent.model_validate(value)
            if progress.progress_id in self._published_progress_ids:
                return []
            event = AgentProgressReported(
                event_id=progress.progress_id,
                thread_id=self._thread_id,
                sequence=self._take_sequence(),
                source_sequences=[source_sequence],
                created_at=self._clock(),
                operation=progress.operation,
                status=progress.status,
                current=progress.progress_current,
                total=progress.progress_total,
                details=progress.details,
            )
        except ValidationError as error:
            logger.error(f"Invalid agent progress event; skipping: {error}")
            return []
        self._published_progress_ids.add(event.event_id)
        return [event]

    def _publish_interrupts(
        self,
        interrupts: Sequence[Mapping[str, object]],
    ) -> list[AgentDomainEvent]:
        events: list[AgentDomainEvent] = []
        if self._resume_cursor is None:
            logger.error("Interrupted agent run has no resume cursor")
            return events

        for interrupt in interrupts:
            interrupt_id = interrupt.get("id")
            if (
                not isinstance(interrupt_id, str)
                or interrupt_id in self._published_interrupt_ids
            ):
                continue
            request = self._parse_human_input_request(interrupt.get("value"))
            if request is None:
                continue
            events.append(
                HumanInputRequested(
                    event_id=build_event_id(
                        AgentDomainEventKind.HUMAN_INPUT_REQUESTED,
                        self._thread_id,
                        interrupt_id,
                    ),
                    thread_id=self._thread_id,
                    sequence=self._take_sequence(),
                    created_at=self._clock(),
                    interrupt_id=interrupt_id,
                    request=request,
                    resume_cursor=self._resume_cursor,
                )
            )
            self._published_interrupt_ids.add(interrupt_id)
        return events

    def _build_completed_event(self) -> AgentRunCompleted:
        return AgentRunCompleted(
            event_id=build_event_id(
                AgentDomainEventKind.RUN_COMPLETED,
                self._thread_id,
                self._terminal_subject("completed"),
            ),
            thread_id=self._thread_id,
            sequence=self._take_sequence(),
            created_at=self._clock(),
            output_ids=sorted(self._outputs, key=str),
        )

    def _build_interrupted_event(
        self,
        interrupts: Sequence[Mapping[str, object]],
    ) -> AgentRunInterrupted:
        interrupt_ids = sorted(
            interrupt_id
            for interrupt in interrupts
            if isinstance((interrupt_id := interrupt.get("id")), str)
        )
        return AgentRunInterrupted(
            event_id=build_event_id(
                AgentDomainEventKind.RUN_INTERRUPTED,
                self._thread_id,
                ",".join(interrupt_ids),
            ),
            thread_id=self._thread_id,
            sequence=self._take_sequence(),
            created_at=self._clock(),
            interrupt_ids=interrupt_ids,
        )

    def _update_resume_cursor_from_checkpoint_payload(self, value: object) -> None:
        if not isinstance(value, Mapping):
            return
        self._set_resume_cursor(value.get("config"))

    def _update_resume_cursor_from_thread_state(
        self,
        thread_state: Mapping[str, object],
    ) -> None:
        self._set_resume_cursor(thread_state.get("checkpoint"))

    def _set_resume_cursor(self, checkpoint: object) -> None:
        configurable = checkpoint
        if isinstance(checkpoint, Mapping) and isinstance(
            checkpoint.get("configurable"), Mapping
        ):
            configurable = checkpoint["configurable"]
        if not isinstance(configurable, Mapping):
            return

        checkpoint_id = configurable.get("checkpoint_id")
        if not isinstance(checkpoint_id, str):
            return
        checkpoint_ns = configurable.get("checkpoint_ns", "")
        checkpoint_map = configurable.get("checkpoint_map", {})
        try:
            self._resume_cursor = AgentResumeCursor(
                checkpoint_id=checkpoint_id,
                checkpoint_ns=checkpoint_ns,
                checkpoint_map=checkpoint_map or {},
            )
        except ValidationError as error:
            logger.error(f"Invalid agent checkpoint cursor; skipping: {error}")

    @staticmethod
    def _find_output_payloads(value: object) -> list[object]:
        found: list[object] = []
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key == "outputs":
                    if isinstance(child, Sequence) and not isinstance(
                        child, (str, bytes)
                    ):
                        found.extend(child)
                    continue
                found.extend(AgentRunProjector._find_output_payloads(child))
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for child in value:
                found.extend(AgentRunProjector._find_output_payloads(child))
        return found

    @staticmethod
    def _extract_interrupts(
        thread_state: Mapping[str, object],
    ) -> list[Mapping[str, object]]:
        value = thread_state.get("interrupts", [])
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
            return []
        return [item for item in value if isinstance(item, Mapping)]

    @staticmethod
    def _parse_human_input_request(value: object) -> HumanInputRequest | None:
        try:
            return HumanInputRequest.model_validate(value)
        except ValidationError as error:
            logger.error(f"Invalid human input request; skipping: {error}")
            return None

    def _terminal_subject(self, terminal: str) -> str:
        checkpoint_id = (
            self._resume_cursor.checkpoint_id
            if self._resume_cursor is not None
            else "no-checkpoint"
        )
        output_ids = ",".join(str(output_id) for output_id in sorted(self._outputs))
        return f"{terminal}:{checkpoint_id}:{output_ids}"

    def _take_sequence(self) -> int:
        sequence = self._next_sequence
        self._next_sequence += 1
        return sequence
