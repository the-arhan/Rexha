"""UI Coordinator connecting widgets, state machine, hotkey, tray, and native core."""

from __future__ import annotations

import logging
from PySide6.QtCore import QObject, QTimer, QPoint, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from rexha.core.state_machine import AssistantStateMachine, AssistantState
from rexha.core.events import EventBus, CommandSubmittedEvent, StateChangedEvent
from rexha.storage.repositories import SettingsRepository
from rexha.ui.floating_widget import FloatingWidget
from rexha.ui.interaction_panel import InteractionPanel
from rexha.ui.system_tray import RexhaSystemTray
from rexha.ui.hotkey import WindowsGlobalHotkeyThread
from rexha.services.native_client import NativeCoreClient

logger = logging.getLogger(__name__)


class UICoordinator(QObject):
    """Coordinates lifecycle, geometry, and events for all desktop UI elements."""

    hotkey_signal = Signal()

    def __init__(
        self,
        state_machine: AssistantStateMachine,
        settings_repo: SettingsRepository,
        event_bus: EventBus,
        native_client: NativeCoreClient | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.state_machine = state_machine
        self.settings_repo = settings_repo
        self.event_bus = event_bus
        self.native_client = native_client or NativeCoreClient(auto_fallback=True)

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
        self.hotkey_thread: WindowsGlobalHotkeyThread | None = None

        # Cross-thread signal for native events
        self.hotkey_signal.connect(self._on_hotkey_triggered)

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
        """Start UI components and global hotkey."""
        logger.info("Starting UI Coordinator")
        self.tray.show()
        self.floating_widget.show()

        # Connect hotkey via Native Core IPC or Python fallback thread
        if self.native_client.is_connected:
            logger.info("Registering hotkey via Native Core IPC")
            self.native_client.register_event_handler("hotkey.triggered", lambda _: self.hotkey_signal.emit())
            self.native_client.register_hotkey(101, ["ctrl"], 0x20)
        else:
            logger.info("Native Core not connected; starting in-process hotkey fallback thread")
            self.hotkey_thread = WindowsGlobalHotkeyThread()
            self.hotkey_thread.hotkey_triggered.connect(self._on_hotkey_triggered)
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
            "Settings are stored in SQLite database (rexha.sqlite). Configure keys or paths in Settings.",
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

        # Evaluate command with Native Core integration
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
        """Deterministic command parser connecting native system metrics and controls."""
        cmd_lower = command.lower().strip()

        if "sleep" in cmd_lower or "minimize" in cmd_lower or "hide" in cmd_lower:
            QTimer.singleShot(700, self.collapse_to_widget)
            return "Going to sleep. Press Ctrl+Space or say 'Wake up, Rexha' when you need me."

        if "status" in cmd_lower or "metrics" in cmd_lower or "sys" in cmd_lower:
            status = self.native_client.get_system_status()
            metrics = self.native_client.get_system_metrics()
            fg = self.native_client.get_foreground_window()

            core_ver = status.get("core_version", "0.1.0")
            pid = status.get("pid", 0)
            uptime = status.get("uptime_seconds", 0)
            ram_used = metrics.get("ram_used_mb", 0)
            ram_total = metrics.get("ram_total_mb", 0)
            cpu = metrics.get("cpu_percent", 0.0)
            fg_title = fg.get("title") or "None active"

            return (
                f"Rexha Desktop Platform v0.1.0\n"
                f"• State: {self.state_machine.current_state.value}\n"
                f"• Native Core: Online (PID {pid}, Uptime {int(uptime)}s)\n"
                f"• RAM: {ram_used} MB / {ram_total} MB ({metrics.get('ram_used_percent', 0)}%)\n"
                f"• System CPU: {cpu:.1f}%\n"
                f"• Active Window: {fg_title}\n"
                f"• Shortcut: Ctrl+Space"
            )

        if "window" in cmd_lower:
            windows = self.native_client.list_windows(visible_only=True, filter_empty_titles=True)
            if not windows:
                return "No top-level application windows detected in active session."
            lines = ["Active Windows:"]
            for w in windows[:6]:
                lines.append(f"• [{w.get('pid')}] {w.get('title')[:35]} ({w.get('process_name')})")
            return "\n".join(lines)

        if cmd_lower.startswith("open ") or cmd_lower.startswith("launch "):
            app_name = command.split(" ", 1)[1].strip()
            # Check aliases first
            target = self.settings_repo.get(f"alias.{app_name.lower()}")
            if not target:
                target = app_name
            try:
                pid = self.native_client.launch_process(target)
                if pid > 0:
                    return f"Launched '{target}' successfully (PID: {pid})."
                return f"Could not launch '{target}'."
            except Exception as e:
                return f"Launch error: {e}"

        if "quit" in cmd_lower or "exit" in cmd_lower:
            QTimer.singleShot(800, self.quit_application)
            return "Shutting down Rexha cleanly. Goodbye!"

        return (
            f"Command received: '{command}'.\n"
            "Tip: Try 'status', 'windows', 'open notepad', or 'sleep'."
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
        if self.hotkey_thread:
            self.hotkey_thread.stop()
            self.hotkey_thread = None

        if self.state_machine.can_transition_to(AssistantState.STOPPING):
            self.state_machine.transition_to(
                AssistantState.STOPPING, reason="Application shutdown"
            )
        self.floating_widget.close()
        self.interaction_panel.close()
        self.tray.hide()
        QApplication.instance().quit()
