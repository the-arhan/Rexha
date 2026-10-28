"""Typed event definitions and application event coordinator for Rexha."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, TypeVar

from rexha.core.state_machine import AssistantState

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppEvent:
    """Base class for all Rexha events."""

    timestamp: datetime = field(default_factory=datetime.now)


@dataclass(frozen=True)
class StateChangedEvent(AppEvent):
    """Fired when assistant state changes."""

    from_state: AssistantState = AssistantState.STARTING
    to_state: AssistantState = AssistantState.SLEEPING
    reason: str = ""


@dataclass(frozen=True)
class AudioLevelEvent(AppEvent):
    """Fired when microphone input RMS level changes."""

    level: float = 0.0  # Normalized 0.0 to 1.0


@dataclass(frozen=True)
class TranscriptionEvent(AppEvent):
    """Fired when speech is transcribed."""

    text: str = ""
    is_final: bool = True
    confidence: float = 1.0


@dataclass(frozen=True)
class CommandSubmittedEvent(AppEvent):
    """Fired when a user submits a command via text or voice."""

    raw_command: str = ""
    source: str = "text"  # "text" or "voice"


@dataclass(frozen=True)
class TaskProgressEvent(AppEvent):
    """Fired during multi-step task execution."""

    task_id: str = ""
    step_index: int = 0
    total_steps: int = 1
    step_description: str = ""
    status: str = "running"  # "running", "success", "failed", "cancelled"
    message: str = ""


@dataclass(frozen=True)
class NotificationEvent(AppEvent):
    """Fired to display an in-app notification banner or tooltip."""

    title: str = ""
    message: str = ""
    severity: str = "info"  # "info", "warning", "error", "success"


T = TypeVar("T", bound=AppEvent)
EventHandler = Callable[[Any], None]


class EventBus:
    """Thread-safe in-process publish/subscribe event bus."""

    def __init__(self) -> None:
        self._subscribers: dict[type[AppEvent], list[EventHandler]] = {}

    def subscribe(self, event_type: type[T], handler: Callable[[T], None]) -> None:
        """Subscribe a callable to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: type[T], handler: Callable[[T], None]) -> None:
        """Unsubscribe a callable from an event type."""
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    def publish(self, event: AppEvent) -> None:
        """Publish an event to all subscribers."""
        event_type = type(event)
        handlers = list(self._subscribers.get(event_type, []))
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.exception("Error in event handler %s for %s: %s", handler, event_type.__name__, e)
