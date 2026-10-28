"""Assistant State Machine implementation for Rexha.

Manages all formal assistant states, transition validation, and listener notifications.
"""

from __future__ import annotations

import logging
import threading
import time
from enum import Enum
from typing import Callable

logger = logging.getLogger(__name__)


class AssistantState(str, Enum):
    """Formal states of the Rexha assistant."""

    STARTING = "STARTING"
    SLEEPING = "SLEEPING"
    WAKING = "WAKING"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    AWAITING_CLARIFICATION = "AWAITING_CLARIFICATION"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    EXECUTING = "EXECUTING"
    REPORTING = "REPORTING"
    FOLLOW_UP = "FOLLOW_UP"
    ERROR = "ERROR"
    STOPPING = "STOPPING"


class InvalidStateTransitionError(Exception):
    """Raised when an illegal state transition is attempted."""

    def __init__(self, from_state: AssistantState, to_state: AssistantState, reason: str = ""):
        self.from_state = from_state
        self.to_state = to_state
        self.reason = reason
        message = f"Illegal state transition from {from_state.value} to {to_state.value}"
        if reason:
            message += f" (Reason: {reason})"
        super().__init__(message)


# Directed graph of permissible state transitions
LEGAL_TRANSITIONS: dict[AssistantState, set[AssistantState]] = {
    AssistantState.STARTING: {
        AssistantState.SLEEPING,
        AssistantState.ERROR,
        AssistantState.STOPPING,
    },
    AssistantState.SLEEPING: {
        AssistantState.WAKING,
        AssistantState.LISTENING,
        AssistantState.THINKING,  # Direct text command submitted while sleeping
        AssistantState.STOPPING,
    },
    AssistantState.WAKING: {
        AssistantState.LISTENING,
        AssistantState.SLEEPING,
        AssistantState.ERROR,
        AssistantState.STOPPING,
    },
    AssistantState.LISTENING: {
        AssistantState.TRANSCRIBING,
        AssistantState.THINKING,
        AssistantState.SLEEPING,
        AssistantState.ERROR,
        AssistantState.STOPPING,
    },
    AssistantState.TRANSCRIBING: {
        AssistantState.THINKING,
        AssistantState.FOLLOW_UP,
        AssistantState.SLEEPING,
        AssistantState.ERROR,
        AssistantState.STOPPING,
    },
    AssistantState.THINKING: {
        AssistantState.AWAITING_CLARIFICATION,
        AssistantState.AWAITING_CONFIRMATION,
        AssistantState.EXECUTING,
        AssistantState.REPORTING,
        AssistantState.ERROR,
        AssistantState.STOPPING,
    },
    AssistantState.AWAITING_CLARIFICATION: {
        AssistantState.THINKING,
        AssistantState.FOLLOW_UP,
        AssistantState.SLEEPING,
        AssistantState.ERROR,
        AssistantState.STOPPING,
    },
    AssistantState.AWAITING_CONFIRMATION: {
        AssistantState.EXECUTING,
        AssistantState.FOLLOW_UP,
        AssistantState.SLEEPING,
        AssistantState.ERROR,
        AssistantState.STOPPING,
    },
    AssistantState.EXECUTING: {
        AssistantState.REPORTING,
        AssistantState.ERROR,
        AssistantState.STOPPING,
    },
    AssistantState.REPORTING: {
        AssistantState.FOLLOW_UP,
        AssistantState.SLEEPING,
        AssistantState.STOPPING,
    },
    AssistantState.FOLLOW_UP: {
        AssistantState.LISTENING,
        AssistantState.THINKING,
        AssistantState.SLEEPING,
        AssistantState.STOPPING,
    },
    AssistantState.ERROR: {
        AssistantState.FOLLOW_UP,
        AssistantState.SLEEPING,
        AssistantState.STOPPING,
    },
    AssistantState.STOPPING: {
        AssistantState.STOPPING,  # Idempotent terminal state
    },
}

StateListener = Callable[[AssistantState, AssistantState, str], None]


class AssistantStateMachine:
    """Thread-safe state coordinator for Rexha."""

    def __init__(self, initial_state: AssistantState = AssistantState.STARTING):
        self._lock = threading.RLock()
        self._current_state = initial_state
        self._previous_state: AssistantState | None = None
        self._last_transition_time = time.monotonic()
        self._listeners: list[StateListener] = []

    @property
    def current_state(self) -> AssistantState:
        with self._lock:
            return self._current_state

    @property
    def previous_state(self) -> AssistantState | None:
        with self._lock:
            return self._previous_state

    @property
    def time_in_current_state(self) -> float:
        with self._lock:
            return time.monotonic() - self._last_transition_time

    def add_listener(self, listener: StateListener) -> None:
        """Register a callback for state changes: fn(from_state, to_state, reason)."""
        with self._lock:
            if listener not in self._listeners:
                self._listeners.append(listener)

    def remove_listener(self, listener: StateListener) -> None:
        """Remove a previously registered state listener callback."""
        with self._lock:
            if listener in self._listeners:
                self._listeners.remove(listener)

    def can_transition_to(self, target_state: AssistantState) -> bool:
        """Check if transitioning to target_state is permissible."""
        with self._lock:
            if target_state == self._current_state:
                return True
            allowed = LEGAL_TRANSITIONS.get(self._current_state, set())
            return target_state in allowed

    def transition_to(self, target_state: AssistantState, reason: str = "") -> None:
        """Transition to target_state, notifying registered listeners.

        Raises:
            InvalidStateTransitionError: If the transition violates defined rules.
        """
        callbacks_to_invoke: list[StateListener] = []
        old_state: AssistantState

        with self._lock:
            if target_state == self._current_state:
                return  # No-op for identical state

            if not self.can_transition_to(target_state):
                logger.error(
                    "Invalid state transition attempted: %s -> %s (Reason: %s)",
                    self._current_state.value,
                    target_state.value,
                    reason,
                )
                raise InvalidStateTransitionError(self._current_state, target_state, reason)

            old_state = self._current_state
            self._previous_state = old_state
            self._current_state = target_state
            self._last_transition_time = time.monotonic()

            logger.info(
                "State changed: %s -> %s%s",
                old_state.value,
                target_state.value,
                f" [{reason}]" if reason else "",
            )
            callbacks_to_invoke = list(self._listeners)

        # Notify listeners outside lock to avoid deadlocks
        for listener in callbacks_to_invoke:
            try:
                listener(old_state, target_state, reason)
            except Exception as e:
                logger.exception("Error in state machine listener callback: %s", e)
