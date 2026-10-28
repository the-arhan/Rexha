"""Unit tests for Rexha EventBus and event models."""

from rexha.core.events import EventBus, StateChangedEvent, AudioLevelEvent
from rexha.core.state_machine import AssistantState


def test_event_bus_publish_subscribe(event_bus: EventBus) -> None:
    received = []

    def handler(evt: StateChangedEvent) -> None:
        received.append(evt)

    event_bus.subscribe(StateChangedEvent, handler)

    event_bus.publish(
        StateChangedEvent(
            from_state=AssistantState.STARTING,
            to_state=AssistantState.SLEEPING,
            reason="Boot complete",
        )
    )

    assert len(received) == 1
    assert received[0].to_state == AssistantState.SLEEPING
    assert received[0].reason == "Boot complete"


def test_event_bus_unsubscribe(event_bus: EventBus) -> None:
    received = []

    def handler(evt: AudioLevelEvent) -> None:
        received.append(evt.level)

    event_bus.subscribe(AudioLevelEvent, handler)
    event_bus.publish(AudioLevelEvent(level=0.5))
    assert received == [0.5]

    event_bus.unsubscribe(AudioLevelEvent, handler)
    event_bus.publish(AudioLevelEvent(level=0.8))
    assert received == [0.5]  # Unchanged
