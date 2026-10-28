"""UI Coordinator connecting widgets, state machine, hotkey, and tray."""

from __future__ import annotations

import logging
from PySide6.QtCore import QObject, QTimer, QPoint
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from rexha.core.state_machine import AssistantStateMachine, AssistantState
from rexha.core.events import EventBus, CommandSubmittedEvent, StateChangedEvent
from rexha.storage.repositories import SettingsRepository
from rexha.ui.floating_widget import FloatingWidget
from rexha.ui.interaction_panel import InteractionPanel
from rexha.ui.system_tray import RexhaSystemTray
from rexha.ui.hotkey import WindowsGlobalHotkeyThread

logger = logging.getLogger(__name__)


class UICoordinator(QObject):
    """Coordinates lifecycle, geometry, and events for all desktop UI elements."""

    def __init__(
        self,
        state_machine: AssistantStateMachine,
        settings_repo: SettingsRepository,
        event_bus: EventBus,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.state_machine = state_machine
        self.settings_repo = settings_repo
        self.event_bus = event_bus

        # Follow-up timeout timer
        self.follow_up_timer = QTimer(self)
        self.follow_up_timer.setSingleShot(True)
        timeout_seconds = self.settings_repo.get("voice.follow_up_timeout", 30)
        self.follow_up_timer.setInterval(timeout_seconds * 1000)
        self.follow_up_timer.timeout.connect(self._on_follow_up_timeout)

        # UI Components
        self.floating_widget = FloatingWidget()
        self.interaction_panel = InteractionPanel()
        self.tray = RexhaSystemTray(self)
        self.hotkey_thread = WindowsGlobalHotkeyThread()

        self._wire_signals()
        self._restore_geometry()

    def _wire_signals(self) -> None:
        """Connect UI signals, hotkeys, tray, and state machine."""
        # Widget events
        self.floating_widget.clicked.connect(self.expand_panel)
        self.floating_widget.position_changed.connect(self._on_widget_moved)

        # Panel events
        self.interaction_panel.collapse_requested.connect(self.collapse_to_widget)
        self.interaction_panel.command_submitted.connect(self._on_command_submitted)
        self.interaction_panel.mic_toggled.connect(self._on_mic_toggle)

        # Tray events
        self.tray.open_requested.connect(self.expand_panel)
        self.tray.mute_toggled.connect(self._on_mute_toggled)
        self.tray.settings_requested.connect(self._on_settings_requested)
        self.tray.quit_requested.connect(self.quit_application)

        # Hotkey events
        self.hotkey_thread.hotkey_triggered.connect(self._on_hotkey_triggered)
        self.hotkey_thread.registration_failed.connect(
            lambda msg: logger.warning("Global shortcut note: %s", msg)
        )

        # State machine listener
        self.state_machine.add_listener(self._on_state_changed)

    def _restore_geometry(self) -> None:
        """Position the floating widget using saved coordinates or defaults."""
        pos_x = self.settings_repo.get("widget.pos_x", -1)
        pos_y = self.settings_repo.get("widget.pos_y", -1)

        primary_screen = QGuiApplication.primaryScreen()
        screen_geom = primary_screen.availableGeometry() if primary_screen else None

        if pos_x < 0 or pos_y < 0 or screen_geom is None:
            # Default to bottom-right corner
            if screen_geom:
                pos_x = screen_geom.right() - self.floating_widget.width() - 24
                pos_y = screen_geom.bottom() - self.floating_widget.height() - 24
            else:
                pos_x, pos_y = 100, 100

        self.floating_widget.move(pos_x, pos_y)
        self._update_panel_position()

    def _update_panel_position(self) -> None:
        """Position interaction panel directly aligned with floating widget."""
        w_pos = self.floating_widget.pos()
        panel_w = self.interaction_panel.width()
        panel_h = self.interaction_panel.height()

        primary_screen = QGuiApplication.primaryScreen()
        screen_geom = primary_screen.availableGeometry() if primary_screen else None

        # Position panel above widget by default
        x = w_pos.x() + self.floating_widget.width() - panel_w
        y = w_pos.y() - panel_h - 10

        if screen_geom:
            x = max(screen_geom.left(), min(x, screen_geom.right() - panel_w))
            y = max(screen_geom.top(), min(y, screen_geom.bottom() - panel_h))

        self.interaction_panel.move(x, y)

    def _on_widget_moved(self, x: int, y: int) -> None:
        """Save new widget position to persistent storage."""
        self.settings_repo.set("widget.pos_x", x)
        self.settings_repo.set("widget.pos_y", y)
        self._update_panel_position()

    def start(self) -> None:
        """Start UI components and global hotkey thread."""
        logger.info("Starting UI Coordinator")
        self.tray.show()
        self.floating_widget.show()

        # Start hotkey listener thread
        self.hotkey_thread.start()

        # Transition state to SLEEPING
        self.state_machine.transition_to(AssistantState.SLEEPING, reason="UI initialized")

    def expand_panel(self) -> None:
        """Open expanded interaction panel and focus text input."""
        self._update_panel_position()
        self.interaction_panel.show()
        self.interaction_panel.raise_()
        self.interaction_panel.activateWindow()
        self.interaction_panel.focus_input()

        if self.state_machine.current_state in (
            AssistantState.SLEEPING,
            AssistantState.FOLLOW_UP,
        ):
            self.state_machine.transition_to(AssistantState.LISTENING, reason="User opened panel")

    def collapse_to_widget(self) -> None:
        """Collapse expanded interaction panel back to compact resting pill."""
        self.interaction_panel.hide()
        self.floating_widget.show()
        if self.state_machine.current_state != AssistantState.SLEEPING:
            self.state_machine.transition_to(
                AssistantState.SLEEPING, reason="User collapsed panel"
            )

    def _on_hotkey_triggered(self) -> None:
        """Handle global hotkey press (Ctrl+Space)."""
        logger.info("Global hotkey triggered")
        if self.interaction_panel.isVisible():
            self.collapse_to_widget()
        else:
            self.expand_panel()

    def _on_mic_toggle(self) -> None:
        """Handle microphone toggle button click."""
        if self.state_machine.current_state == AssistantState.LISTENING:
            self.state_machine.transition_to(
                AssistantState.FOLLOW_UP, reason="User stopped listening"
            )
        else:
            self.state_machine.transition_to(
                AssistantState.LISTENING, reason="User activated mic"
            )

    def _on_mute_toggled(self, muted: bool) -> None:
        """Handle system tray wake listening toggle."""
        self.settings_repo.set("voice.wake_listening_enabled", not muted)
        msg = "Wake listening muted" if muted else "Wake listening active"
        self.tray.notify("Rexha", msg)

    def _on_settings_requested(self) -> None:
        """Handle Settings menu selection."""
        self.expand_panel()
        self.interaction_panel.add_message(
            "Rexha",
            "Settings are stored in SQLite database (rexha.sqlite). Settings UI editor will expand in Milestone 2.",
            is_user=False,
        )

    def _on_command_submitted(self, command: str) -> None:
        """Process user text command."""
        self.interaction_panel.add_message("You", command, is_user=True)
        self.event_bus.publish(CommandSubmittedEvent(raw_command=command, source="text"))

        # Transition to THINKING
        if self.state_machine.can_transition_to(AssistantState.THINKING):
            self.state_machine.transition_to(
                AssistantState.THINKING, reason=f"Command received: {command}"
            )

        # Routine command evaluation (Milestone 1 basic handling)
        response_text = self._handle_basic_command(command)
        self.interaction_panel.add_message("Rexha", response_text, is_user=False)

        # Transition to REPORTING -> FOLLOW_UP
        if self.state_machine.can_transition_to(AssistantState.REPORTING):
            self.state_machine.transition_to(AssistantState.REPORTING, reason="Command responded")
        if self.state_machine.can_transition_to(AssistantState.FOLLOW_UP):
            self.state_machine.transition_to(
                AssistantState.FOLLOW_UP, reason="Awaiting follow-up"
            )

        # Start follow-up inactivity timer
        self.follow_up_timer.start()

    def _handle_basic_command(self, command: str) -> str:
        """Deterministic basic command parser for Milestone 1."""
        cmd_lower = command.lower().strip()

        if "sleep" in cmd_lower or "minimize" in cmd_lower or "hide" in cmd_lower:
            QTimer.singleShot(800, self.collapse_to_widget)
            return "Going to sleep. Press Ctrl+Space or say 'Wake up, Rexha' when you need me."

        if "status" in cmd_lower or "help" in cmd_lower:
            return (
                "Rexha v0.1 is active.\n"
                "• Compact floating widget: Ready\n"
                "• Global hotkey: Ctrl+Space\n"
                "• Interaction panel: Online\n"
                "• State: " + self.state_machine.current_state.value
            )

        if "quit" in cmd_lower or "exit" in cmd_lower:
            QTimer.singleShot(1000, self.quit_application)
            return "Shutting down Rexha cleanly. Goodbye!"

        return (
            f"Command received: '{command}'.\n"
            "Full desktop automation actions will execute via Task Executor in Milestone 3."
        )

    def _on_follow_up_timeout(self) -> None:
        """Handle follow-up expiration."""
        if self.state_machine.current_state == AssistantState.FOLLOW_UP:
            logger.info("Follow-up timeout expired; returning to SLEEPING")
            self.collapse_to_widget()

    def _on_state_changed(
        self, from_state: AssistantState, to_state: AssistantState, reason: str
    ) -> None:
        """Update all UI components on state change."""
        self.floating_widget.set_state(to_state)
        self.interaction_panel.set_state(to_state)
        self.tray.update_state(to_state)
        self.event_bus.publish(
            StateChangedEvent(from_state=from_state, to_state=to_state, reason=reason)
        )

    def quit_application(self) -> None:
        """Initiate clean shutdown of threads, state machine, and Qt app."""
        logger.info("Quitting Rexha application")
        self.follow_up_timer.stop()
        self.hotkey_thread.stop()
        if self.state_machine.can_transition_to(AssistantState.STOPPING):
            self.state_machine.transition_to(
                AssistantState.STOPPING, reason="Application shutdown"
            )
        self.floating_widget.close()
        self.interaction_panel.close()
        self.tray.hide()
        QApplication.instance().quit()
