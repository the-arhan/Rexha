"""Unit tests for Rexha AssistantStateMachine."""

import pytest
from rexha.core.state_machine import (
    AssistantState,
    AssistantStateMachine,
    InvalidStateTransitionError,
)


def test_initial_state(state_machine: AssistantStateMachine) -> None:
    assert state_machine.current_state == AssistantState.STARTING
    assert state_machine.previous_state is None


def test_legal_startup_flow(state_machine: AssistantStateMachine) -> None:
    events: list[tuple[AssistantState, AssistantState, str]] = []

    def on_change(from_s: AssistantState, to_s: AssistantState, reason: str) -> None:
        events.append((from_s, to_s, reason))

    state_machine.add_listener(on_change)

    # STARTING -> SLEEPING
    state_machine.transition_to(AssistantState.SLEEPING, reason="Startup complete")
    assert state_machine.current_state == AssistantState.SLEEPING
    assert state_machine.previous_state == AssistantState.STARTING

    # SLEEPING -> WAKING
    state_machine.transition_to(AssistantState.WAKING, reason="Wake phrase detected")
    assert state_machine.current_state == AssistantState.WAKING

    # WAKING -> LISTENING
    state_machine.transition_to(AssistantState.LISTENING, reason="UI expanded")
    assert state_machine.current_state == AssistantState.LISTENING

    # LISTENING -> TRANSCRIBING
    state_machine.transition_to(AssistantState.TRANSCRIBING, reason="Silence detected")
    assert state_machine.current_state == AssistantState.TRANSCRIBING

    # TRANSCRIBING -> THINKING
    state_machine.transition_to(AssistantState.THINKING, reason="Text ready")
    assert state_machine.current_state == AssistantState.THINKING

    # THINKING -> EXECUTING
    state_machine.transition_to(AssistantState.EXECUTING, reason="Action plan approved")
    assert state_machine.current_state == AssistantState.EXECUTING

    # EXECUTING -> REPORTING
    state_machine.transition_to(AssistantState.REPORTING, reason="Execution complete")
    assert state_machine.current_state == AssistantState.REPORTING

    # REPORTING -> FOLLOW_UP
    state_machine.transition_to(AssistantState.FOLLOW_UP, reason="Awaiting next command")
    assert state_machine.current_state == AssistantState.FOLLOW_UP

    # FOLLOW_UP -> SLEEPING
    state_machine.transition_to(AssistantState.SLEEPING, reason="Timeout reached")
    assert state_machine.current_state == AssistantState.SLEEPING

    assert len(events) == 9
    assert events[0] == (AssistantState.STARTING, AssistantState.SLEEPING, "Startup complete")


def test_illegal_transition_raises_error(state_machine: AssistantStateMachine) -> None:
    # STARTING -> EXECUTING is not allowed directly
    with pytest.raises(InvalidStateTransitionError) as exc_info:
        state_machine.transition_to(AssistantState.EXECUTING)

    assert exc_info.value.from_state == AssistantState.STARTING
    assert exc_info.value.to_state == AssistantState.EXECUTING
    assert state_machine.current_state == AssistantState.STARTING


def test_remove_listener(state_machine: AssistantStateMachine) -> None:
    calls = []

    def callback(from_s, to_s, reason):
        calls.append(to_s)

    state_machine.add_listener(callback)
    state_machine.transition_to(AssistantState.SLEEPING)
    assert len(calls) == 1

    state_machine.remove_listener(callback)
    state_machine.transition_to(AssistantState.WAKING)
    assert len(calls) == 1  # No new call after removal


def test_idempotent_same_state(state_machine: AssistantStateMachine) -> None:
    calls = []
    state_machine.add_listener(lambda f, t, r: calls.append(t))
    state_machine.transition_to(AssistantState.STARTING)
    assert len(calls) == 0  # No listener invocation for duplicate state
