"""Unit tests for Rexha UI components."""

import sys
import pytest
from PySide6.QtWidgets import QApplication

from rexha.core.state_machine import AssistantState, AssistantStateMachine
from rexha.core.events import EventBus
from rexha.storage.database import DatabaseManager
from rexha.storage.repositories import SettingsRepository
from rexha.ui.theme import Theme
from rexha.ui.floating_widget import FloatingWidget
from rexha.ui.interaction_panel import InteractionPanel
from rexha.ui.coordinator import UICoordinator


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """Session-scoped QApplication instance for UI tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_theme_state_mappings() -> None:
    assert Theme.get_state_color(AssistantState.SLEEPING) == "#64748B"
    assert Theme.get_state_color(AssistantState.LISTENING) == "#00E5FF"
    assert Theme.get_state_label(AssistantState.SLEEPING) == "Sleeping..."
    assert Theme.get_state_label(AssistantState.LISTENING) == "Listening..."


def test_floating_widget_creation(qapp: QApplication) -> None:
    widget = FloatingWidget()
    assert widget.status_label.text() == "Sleeping..."
    assert widget.brand_label.text() == "REXHA"

    # State update
    widget.set_state(AssistantState.LISTENING)
    assert widget.status_label.text() == "Listening..."

    # Audio level
    widget.set_audio_level(0.75)
    assert widget.audio_meter.value() == 75

    widget.close()


def test_interaction_panel_creation(qapp: QApplication) -> None:
    panel = InteractionPanel()
    assert panel.title_label.text() == "REXHA"
    assert panel.state_badge.text() == "SLEEPING..."

    # Add message
    panel.add_message("User", "Hello Rexha", is_user=True)
    panel.add_message("Rexha", "Hello! How can I assist?", is_user=False)
    # Check that messages were inserted
    assert panel.history_layout.count() >= 3

    # Confirmation frame
    panel.show()
    panel.request_confirmation("Delete file temp.txt")
    assert panel.confirm_frame.isVisible() is True
    assert "Delete file temp.txt" in panel.confirm_text.text()

    panel.close()


def test_ui_coordinator_lifecycle(
    qapp: QApplication,
    memory_db: DatabaseManager,
    state_machine: AssistantStateMachine,
    event_bus: EventBus,
) -> None:
    settings_repo = SettingsRepository(memory_db.connection)
    coordinator = UICoordinator(
        state_machine=state_machine,
        settings_repo=settings_repo,
        event_bus=event_bus,
    )

    # Initial state transition on start
    coordinator.start()
    assert state_machine.current_state == AssistantState.SLEEPING
    assert coordinator.floating_widget.isVisible() is True

    # Expand panel
    coordinator.expand_panel()
    assert coordinator.interaction_panel.isVisible() is True
    assert state_machine.current_state == AssistantState.LISTENING

    # Command submission flow
    coordinator._on_command_submitted("status")
    assert state_machine.current_state == AssistantState.FOLLOW_UP

    # Collapse
    coordinator.collapse_to_widget()
    assert coordinator.interaction_panel.isVisible() is False
    assert state_machine.current_state == AssistantState.SLEEPING

    # Position saving
    coordinator._on_widget_moved(500, 600)
    assert settings_repo.get("widget.pos_x") == 500
    assert settings_repo.get("widget.pos_y") == 600

    coordinator.quit_application()
