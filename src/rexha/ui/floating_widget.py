"""Compact persistent always-on-top floating widget for Rexha."""

from __future__ import annotations

import logging
from PySide6.QtCore import Qt, QPoint, QPointF, Signal, QRect
from PySide6.QtGui import QMouseEvent, QPainter, QColor, QPen, QBrush, QPolygonF, QGuiApplication
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QGraphicsDropShadowEffect,
)

from rexha.core.state_machine import AssistantState
from rexha.ui.theme import Theme

logger = logging.getLogger(__name__)


class GeometricInsignia(QWidget):
    """Custom geometric chevron/diamond insignia for Rexha brand identity."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(14, 14)
        self._accent_color = QColor(Theme.LIME)

    def set_color(self, hex_color: str) -> None:
        self._accent_color = QColor(hex_color)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Draw minimalist sharp geometric polygon
        points = [
            QPointF(7.0, 1.0),   # Top
            QPointF(13.0, 7.0),  # Right
            QPointF(7.0, 13.0),  # Bottom
            QPointF(1.0, 7.0),   # Left
        ]
        poly = QPolygonF(points)

        pen = QPen(self._accent_color, 1.5)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(18, 21, 31, 200)))
        painter.drawPolygon(poly)

        # Inner electric point
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._accent_color))
        painter.drawRect(5, 5, 4, 4)
        painter.end()


class StateIndicatorDot(QWidget):
    """Glowing circular indicator showing current state color."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._color = QColor(Theme.STATE_COLORS[AssistantState.SLEEPING])

    def set_color(self, hex_color: str) -> None:
        self._color = QColor(hex_color)
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Outer subtle glow
        glow_color = QColor(self._color)
        glow_color.setAlpha(45)
        painter.setBrush(QBrush(glow_color))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, 12, 12)

        # Inner solid dot
        painter.setBrush(QBrush(self._color))
        painter.drawEllipse(2, 2, 8, 8)
        painter.end()


class FloatingWidget(QWidget):
    """Frameless, draggable, always-on-top compact assistant pill."""

    clicked = Signal()
    position_changed = Signal(int, int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("FloatingWidgetRoot")

        # Window flags: Frameless, Always on Top, Tool window
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._drag_position: QPoint | None = None
        self._is_dragging = False
        self._current_state = AssistantState.SLEEPING

        self._build_ui()
        self.set_state(AssistantState.SLEEPING)

    def _build_ui(self) -> None:
        """Create the compact widget layout."""
        self.setFixedSize(170, 58)

        # Drop shadow for depth
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 220))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 6)
        main_layout.setSpacing(3)

        # Top row: Insignia + Brand + Dot + Expand Button
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(6)

        self.insignia = GeometricInsignia(self)
        top_row.addWidget(self.insignia)

        self.brand_label = QLabel("REXHA", self)
        self.brand_label.setObjectName("BrandLabel")
        top_row.addWidget(self.brand_label)

        self.dot = StateIndicatorDot(self)
        top_row.addWidget(self.dot)

        top_row.addStretch()

        self.expand_btn = QPushButton("▲", self)
        self.expand_btn.setObjectName("ExpandBtn")
        self.expand_btn.setFixedSize(16, 16)
        self.expand_btn.setToolTip("Open Rexha Panel (Ctrl+Space)")
        self.expand_btn.clicked.connect(self.clicked.emit)
        top_row.addWidget(self.expand_btn)

        main_layout.addLayout(top_row)

        # Bottom row: State Text
        self.status_label = QLabel("Sleeping...", self)
        self.status_label.setObjectName("StatusLabel")
        main_layout.addWidget(self.status_label)

        # Audio Level Bar (Restrained 2px line)
        self.audio_meter = QProgressBar(self)
        self.audio_meter.setFixedHeight(2)
        self.audio_meter.setRange(0, 100)
        self.audio_meter.setValue(0)
        self.audio_meter.setTextVisible(False)
        self.audio_meter.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: {Theme.BORDER};
                border: none;
                border-radius: 1px;
            }}
            QProgressBar::chunk {{
                background-color: {Theme.LIME};
                border-radius: 1px;
            }}
            """
        )
        main_layout.addWidget(self.audio_meter)

    def set_state(self, state: AssistantState) -> None:
        """Update widget display according to state."""
        self._current_state = state
        color = Theme.get_state_color(state)
        label = Theme.get_state_label(state)

        self.dot.set_color(color)
        self.insignia.set_color(color)
        self.status_label.setText(label)
        self.setStyleSheet(Theme.get_compact_widget_stylesheet(state))

        if state != AssistantState.LISTENING:
            self.audio_meter.setValue(0)

    def set_audio_level(self, level: float) -> None:
        """Update audio level meter (0.0 to 1.0)."""
        if self._current_state == AssistantState.LISTENING:
            val = int(min(max(level, 0.0), 1.0) * 100)
            self.audio_meter.setValue(val)

    # Mouse Drag Handling
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_dragging = False
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() == Qt.LeftButton and self._drag_position is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_position
            screen = QGuiApplication.screenAt(event.globalPosition().toPoint())
            if screen:
                geom: QRect = screen.availableGeometry()
                clamped_x = max(geom.left(), min(new_pos.x(), geom.right() - self.width()))
                clamped_y = max(geom.top(), min(new_pos.y(), geom.bottom() - self.height()))
                self.move(clamped_x, clamped_y)
            else:
                self.move(new_pos)
            self._is_dragging = True
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.LeftButton:
            if not self._is_dragging:
                self.clicked.emit()
            else:
                pos = self.pos()
                self.position_changed.emit(pos.x(), pos.y())
            self._drag_position = None
            self._is_dragging = False
            event.accept()
