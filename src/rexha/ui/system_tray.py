"""System Tray icon and context menu controller for Rexha."""

from __future__ import annotations

import logging
from PySide6.QtCore import QObject, Signal, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont, QAction
from PySide6.QtWidgets import QSystemTrayIcon, QMenu

from rexha.core.state_machine import AssistantState
from rexha.ui.theme import Theme

logger = logging.getLogger(__name__)


def create_tray_icon_pixmap(state: AssistantState = AssistantState.SLEEPING) -> QIcon:
    """Create a crisp, programmatic icon for the Windows system tray."""
    size = 32
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # Background circle
    painter.setBrush(QColor(Theme.BG_BASE))
    color = QColor(Theme.get_state_color(state))
    painter.setPen(color)
    painter.drawEllipse(2, 2, size - 4, size - 4)

    # Letter 'R'
    painter.setPen(color)
    font = QFont("Segoe UI", 14, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, "R")
    painter.end()

    return QIcon(pixmap)


class RexhaSystemTray(QObject):
    """Manages Rexha's presence in the Windows taskbar system notification area."""

    open_requested = Signal()
    mute_toggled = Signal(bool)
    settings_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(create_tray_icon_pixmap())
        self.tray_icon.setToolTip("Rexha Desktop Assistant")

        self._menu = QMenu()
        self._build_menu()
        self.tray_icon.setContextMenu(self._menu)

        self.tray_icon.activated.connect(self._on_tray_activated)

    def _build_menu(self) -> None:
        """Construct the context menu."""
        self._menu.clear()

        # Open
        self.action_open = QAction("Open Rexha (Ctrl+Space)", self)
        self.action_open.triggered.connect(self.open_requested.emit)
        self._menu.addAction(self.action_open)

        self._menu.addSeparator()

        # Mute wake listening toggle
        self.action_mute = QAction("Mute Wake Listening", self)
        self.action_mute.setCheckable(True)
        self.action_mute.setChecked(False)
        self.action_mute.toggled.connect(self.mute_toggled.emit)
        self._menu.addAction(self.action_mute)

        self._menu.addSeparator()

        # Settings
        self.action_settings = QAction("Settings...", self)
        self.action_settings.triggered.connect(self.settings_requested.emit)
        self._menu.addAction(self.action_settings)

        # Quit
        self.action_quit = QAction("Quit Rexha", self)
        self.action_quit.triggered.connect(self.quit_requested.emit)
        self._menu.addAction(self.action_quit)

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle single/double click on system tray icon."""
        if reason in (QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick):
            self.open_requested.emit()

    def update_state(self, state: AssistantState) -> None:
        """Update icon appearance and tooltip based on assistant state."""
        self.tray_icon.setIcon(create_tray_icon_pixmap(state))
        status_label = Theme.get_state_label(state)
        self.tray_icon.setToolTip(f"Rexha — {status_label}")

    def show(self) -> None:
        """Make system tray visible."""
        self.tray_icon.show()

    def hide(self) -> None:
        """Hide system tray icon."""
        self.tray_icon.hide()

    def notify(self, title: str, message: str, is_error: bool = False) -> None:
        """Display a Windows notification balloon."""
        icon = QSystemTrayIcon.Critical if is_error else QSystemTrayIcon.Information
        self.tray_icon.showMessage(title, message, icon, 3000)
