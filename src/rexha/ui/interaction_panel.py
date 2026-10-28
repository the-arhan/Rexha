"""Expanded interaction panel for Rexha desktop assistant."""

from __future__ import annotations

import logging
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QGuiApplication, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QScrollArea,
    QFrame,
    QGraphicsDropShadowEffect,
)

from rexha.core.state_machine import AssistantState
from rexha.ui.theme import Theme

logger = logging.getLogger(__name__)


class MessageCard(QFrame):
    """Visual card for user commands and assistant responses."""

    def __init__(self, sender: str, text: str, is_user: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # Header
        header = QLabel(sender, self)
        color = Theme.LIME if is_user else Theme.VIOLET
        header.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: 700; letter-spacing: 0.8px;")
        layout.addWidget(header)

        # Body
        body = QLabel(text, self)
        body.setWordWrap(True)
        body.setStyleSheet(f"color: {Theme.TEXT_MAIN}; font-size: 13px; line-height: 1.45;")
        layout.addWidget(body)

        bg = Theme.BG_SURFACE if is_user else Theme.BG_CARD
        border = Theme.BORDER
        self.setStyleSheet(
            f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
            """
        )


class InteractionPanel(QWidget):
    """Expanded window for interaction, conversation history, and command input."""

    command_submitted = Signal(str)
    mic_toggled = Signal()
    collapse_requested = Signal()
    action_confirmed = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("InteractionPanelRoot")

        # Window flags: Frameless, Always on Top, Tool window
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._build_ui()
        self.set_state(AssistantState.SLEEPING)

    def _build_ui(self) -> None:
        """Construct the panel layout."""
        self.setFixedSize(420, 540)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 230))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Header Bar
        header = QFrame(self)
        header.setObjectName("HeaderBar")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)

        self.title_label = QLabel("REXHA", header)
        self.title_label.setObjectName("PanelTitle")
        header_layout.addWidget(self.title_label)

        self.state_badge = QLabel("SLEEPING", header)
        self.state_badge.setObjectName("StateBadge")
        header_layout.addWidget(self.state_badge)

        header_layout.addStretch()

        self.collapse_btn = QPushButton("✕", header)
        self.collapse_btn.setObjectName("CollapseBtn")
        self.collapse_btn.setToolTip("Collapse (Esc)")
        self.collapse_btn.clicked.connect(self.collapse_requested.emit)
        header_layout.addWidget(self.collapse_btn)

        main_layout.addWidget(header)

        # 2. Conversation Scroll Area
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_content.setObjectName("ScrollContent")
        self.history_layout = QVBoxLayout(self.scroll_content)
        self.history_layout.setContentsMargins(16, 12, 16, 12)
        self.history_layout.setSpacing(10)
        self.history_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        main_layout.addWidget(self.scroll_area, 1)

        # 3. Confirmation Prompt Banner (Hidden by default)
        self.confirm_frame = QFrame(self)
        self.confirm_frame.setStyleSheet(
            f"background-color: {Theme.BG_SURFACE}; border-top: 1px solid {Theme.AMBER}; padding: 10px;"
        )
        confirm_layout = QVBoxLayout(self.confirm_frame)
        self.confirm_text = QLabel("Action requires your approval:", self.confirm_frame)
        self.confirm_text.setWordWrap(True)
        self.confirm_text.setStyleSheet(f"color: {Theme.TEXT_MAIN}; font-size: 12px; font-weight: bold;")
        confirm_layout.addWidget(self.confirm_text)

        btn_row = QHBoxLayout()
        self.btn_approve = QPushButton("Approve", self.confirm_frame)
        self.btn_approve.setStyleSheet(f"background-color: {Theme.LIME}; color: #000000; border-radius: 6px; padding: 5px 14px; font-weight: bold;")
        self.btn_approve.clicked.connect(lambda: self._handle_confirmation(True))
        btn_row.addWidget(self.btn_approve)

        self.btn_cancel = QPushButton("Cancel", self.confirm_frame)
        self.btn_cancel.setStyleSheet(f"background-color: {Theme.BG_CARD}; color: {Theme.TEXT_MAIN}; border: 1px solid {Theme.BORDER}; border-radius: 6px; padding: 5px 14px;")
        self.btn_cancel.clicked.connect(lambda: self._handle_confirmation(False))
        btn_row.addWidget(self.btn_cancel)

        confirm_layout.addLayout(btn_row)
        self.confirm_frame.hide()
        main_layout.addWidget(self.confirm_frame)

        # 4. Command Input Bar
        input_container = QFrame(self)
        input_container.setStyleSheet(f"background-color: {Theme.BG_SURFACE}; border-top: 1px solid {Theme.BORDER}; padding: 8px;")
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(12, 8, 12, 8)
        input_layout.setSpacing(8)

        self.mic_btn = QPushButton("🎙", input_container)
        self.mic_btn.setObjectName("MicBtn")
        self.mic_btn.setFixedSize(36, 36)
        self.mic_btn.setToolTip("Toggle Voice Listening")
        self.mic_btn.clicked.connect(self.mic_toggled.emit)
        input_layout.addWidget(self.mic_btn)

        self.command_input = QLineEdit(input_container)
        self.command_input.setObjectName("CommandInput")
        self.command_input.setPlaceholderText("Command or question... (e.g. 'status', 'open notepad', 'sleep')")
        self.command_input.returnPressed.connect(self._on_submit)
        input_layout.addWidget(self.command_input, 1)

        self.submit_btn = QPushButton("Send", input_container)
        self.submit_btn.setObjectName("SubmitBtn")
        self.submit_btn.setFixedHeight(36)
        self.submit_btn.clicked.connect(self._on_submit)
        input_layout.addWidget(self.submit_btn)

        main_layout.addWidget(input_container)
        self.setStyleSheet(Theme.get_interaction_panel_stylesheet())

    def _on_submit(self) -> None:
        """Handle submit button or enter press."""
        text = self.command_input.text().strip()
        if text:
            self.command_submitted.emit(text)
            self.command_input.clear()

    def _handle_confirmation(self, approved: bool) -> None:
        """Handle confirmation dialog click."""
        self.confirm_frame.hide()
        self.action_confirmed.emit(approved)

    def request_confirmation(self, action_description: str) -> None:
        """Display confirmation prompt for Tier-2 consequential operations."""
        self.confirm_text.setText(f"Confirmation Required:\n{action_description}")
        self.confirm_frame.show()

    def add_message(self, sender: str, text: str, is_user: bool = False) -> None:
        """Append a message card to conversation history."""
        card = MessageCard(sender, text, is_user, self.scroll_content)
        self.history_layout.insertWidget(self.history_layout.count() - 1, card)
        QGuiApplication.processEvents()
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )

    def set_state(self, state: AssistantState) -> None:
        """Update header state badge."""
        label = Theme.get_state_label(state)
        color = Theme.get_state_color(state)
        self.state_badge.setText(label.upper())
        self.state_badge.setStyleSheet(
            f"background-color: {Theme.BG_CARD}; color: {color}; border: 1px solid {color}; border-radius: 10px; padding: 3px 10px; font-size: 11px; font-weight: bold;"
        )

        if state == AssistantState.LISTENING:
            self.mic_btn.setStyleSheet(f"background-color: {Theme.LIME}; color: #000000; border-radius: 8px; font-size: 14px;")
        else:
            self.mic_btn.setStyleSheet("")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Collapse on Escape key."""
        if event.key() == Qt.Key_Escape:
            self.collapse_requested.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

    def focus_input(self) -> None:
        """Focus the text input field."""
        self.command_input.setFocus()
