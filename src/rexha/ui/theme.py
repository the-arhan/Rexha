"""Theme definitions, color palettes, and stylesheets for Rexha."""

from __future__ import annotations

from rexha.core.state_machine import AssistantState


class Theme:
    """Design system tokens for Rexha dark futuristic UI."""

    # Surfaces
    BG_BASE = "#0D0F18"
    BG_SURFACE = "#151824"
    BG_SURFACE_HOVER = "#1D2132"
    BG_CARD = "#1A1E2D"
    BORDER = "#252B40"
    BORDER_ACCENT = "#384160"

    # Accents
    CYAN = "#00E5FF"
    CYAN_HOVER = "#33EBFF"
    CYAN_DIM = "rgba(0, 229, 255, 0.15)"
    VIOLET = "#9D4EDD"
    VIOLET_HOVER = "#B366FF"
    VIOLET_DIM = "rgba(157, 78, 221, 0.15)"

    # Text
    TEXT_MAIN = "#F1F5F9"
    TEXT_MUTED = "#94A3B8"
    TEXT_DIM = "#64748B"

    # State Colors
    STATE_COLORS: dict[AssistantState, str] = {
        AssistantState.STARTING: "#F59E0B",
        AssistantState.SLEEPING: "#64748B",
        AssistantState.WAKING: "#A855F7",
        AssistantState.LISTENING: "#00E5FF",
        AssistantState.TRANSCRIBING: "#38BDF8",
        AssistantState.THINKING: "#F59E0B",
        AssistantState.AWAITING_CLARIFICATION: "#EC4899",
        AssistantState.AWAITING_CONFIRMATION: "#F97316",
        AssistantState.EXECUTING: "#3B82F6",
        AssistantState.REPORTING: "#10B981",
        AssistantState.FOLLOW_UP: "#8B5CF6",
        AssistantState.ERROR: "#EF4444",
        AssistantState.STOPPING: "#475569",
    }

    # User-facing state titles
    STATE_LABELS: dict[AssistantState, str] = {
        AssistantState.STARTING: "Starting...",
        AssistantState.SLEEPING: "Sleeping...",
        AssistantState.WAKING: "Waking up...",
        AssistantState.LISTENING: "Listening...",
        AssistantState.TRANSCRIBING: "Transcribing...",
        AssistantState.THINKING: "Thinking...",
        AssistantState.AWAITING_CLARIFICATION: "Needs Clarification",
        AssistantState.AWAITING_CONFIRMATION: "Awaiting Confirmation",
        AssistantState.EXECUTING: "Executing...",
        AssistantState.REPORTING: "Ready",
        AssistantState.FOLLOW_UP: "Anything else?",
        AssistantState.ERROR: "Notice",
        AssistantState.STOPPING: "Shutting down...",
    }

    @classmethod
    def get_state_color(cls, state: AssistantState) -> str:
        return cls.STATE_COLORS.get(state, cls.CYAN)

    @classmethod
    def get_state_label(cls, state: AssistantState) -> str:
        return cls.STATE_LABELS.get(state, state.value)

    @classmethod
    def get_compact_widget_stylesheet(cls, state: AssistantState) -> str:
        accent = cls.get_state_color(state)
        return f"""
        QWidget#FloatingWidgetRoot {{
            background-color: {cls.BG_BASE};
            border: 1px solid {accent};
            border-radius: 18px;
        }}
        QLabel#BrandLabel {{
            color: {cls.CYAN};
            font-family: 'Segoe UI', sans-serif;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
        }}
        QLabel#StatusLabel {{
            color: {cls.TEXT_MAIN};
            font-family: 'Segoe UI', sans-serif;
            font-size: 13px;
            font-weight: 500;
        }}
        QPushButton#ExpandBtn {{
            background-color: transparent;
            color: {cls.TEXT_MUTED};
            border: none;
            font-size: 14px;
        }}
        QPushButton#ExpandBtn:hover {{
            color: {cls.CYAN};
        }}
        """

    @classmethod
    def get_interaction_panel_stylesheet(cls) -> str:
        return f"""
        QWidget#InteractionPanelRoot {{
            background-color: {cls.BG_BASE};
            border: 1px solid {cls.BORDER_ACCENT};
            border-radius: 12px;
        }}
        QFrame#HeaderBar {{
            background-color: {cls.BG_SURFACE};
            border-bottom: 1px solid {cls.BORDER};
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        }}
        QLabel#PanelTitle {{
            color: {cls.TEXT_MAIN};
            font-family: 'Segoe UI', sans-serif;
            font-size: 14px;
            font-weight: 600;
        }}
        QLabel#StateBadge {{
            background-color: {cls.BG_SURFACE_HOVER};
            color: {cls.CYAN};
            border: 1px solid {cls.BORDER};
            border-radius: 10px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 600;
        }}
        QScrollArea {{
            background-color: transparent;
            border: none;
        }}
        QWidget#ScrollContent {{
            background-color: transparent;
        }}
        QLineEdit#CommandInput {{
            background-color: {cls.BG_SURFACE};
            color: {cls.TEXT_MAIN};
            border: 1px solid {cls.BORDER};
            border-radius: 8px;
            padding: 8px 12px;
            font-size: 13px;
            selection-background-color: {cls.CYAN_DIM};
        }}
        QLineEdit#CommandInput:focus {{
            border: 1px solid {cls.CYAN};
        }}
        QPushButton#SubmitBtn {{
            background-color: {cls.CYAN};
            color: #000000;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            font-size: 12px;
            padding: 8px 16px;
        }}
        QPushButton#SubmitBtn:hover {{
            background-color: {cls.CYAN_HOVER};
        }}
        QPushButton#MicBtn {{
            background-color: {cls.BG_SURFACE};
            color: {cls.CYAN};
            border: 1px solid {cls.BORDER};
            border-radius: 8px;
            font-size: 14px;
            padding: 6px 12px;
        }}
        QPushButton#MicBtn:hover {{
            border-color: {cls.CYAN};
            background-color: {cls.CYAN_DIM};
        }}
        QPushButton#CollapseBtn {{
            background-color: transparent;
            color: {cls.TEXT_MUTED};
            border: none;
            font-size: 16px;
            font-weight: bold;
            padding: 4px;
        }}
        QPushButton#CollapseBtn:hover {{
            color: {cls.TEXT_MAIN};
        }}
        """
