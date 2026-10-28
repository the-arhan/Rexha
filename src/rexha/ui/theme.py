"""Theme definitions, industrial graphite color tokens, and stylesheets for Rexha."""

from __future__ import annotations

from rexha.core.state_machine import AssistantState


class Theme:
    """Industrial minimalist design tokens for Rexha."""

    # Deep Graphite Surfaces
    BG_BASE = "#0B0D13"
    BG_SURFACE = "#12151F"
    BG_SURFACE_HOVER = "#181D2B"
    BG_CARD = "#161A26"
    BORDER = "#212738"
    BORDER_ACCENT = "#2E374D"

    # Restrained Electric-Lime / Green Accents
    LIME = "#10E599"
    LIME_HOVER = "#2CECA6"
    LIME_DIM = "rgba(16, 229, 153, 0.12)"
    CYAN = "#06B6D4"
    CYAN_HOVER = "#22D3EE"
    VIOLET = "#8B5CF6"
    VIOLET_HOVER = "#A78BFA"
    AMBER = "#F59E0B"
    RED = "#EF4444"

    # Typography & Hierarchy
    TEXT_MAIN = "#F3F4F6"
    TEXT_MUTED = "#9CA3AF"
    TEXT_DIM = "#6B7280"
    FONT_FAMILY = "Segoe UI, -apple-system, system-ui, sans-serif"

    # State Palette
    STATE_COLORS: dict[AssistantState, str] = {
        AssistantState.STARTING: "#F59E0B",
        AssistantState.SLEEPING: "#64748B",
        AssistantState.WAKING: "#10E599",
        AssistantState.LISTENING: "#00E5FF",
        AssistantState.TRANSCRIBING: "#06B6D4",
        AssistantState.THINKING: "#F59E0B",
        AssistantState.AWAITING_CLARIFICATION: "#EC4899",
        AssistantState.AWAITING_CONFIRMATION: "#F97316",
        AssistantState.EXECUTING: "#3B82F6",
        AssistantState.REPORTING: "#10E599",
        AssistantState.FOLLOW_UP: "#8B5CF6",
        AssistantState.ERROR: "#EF4444",
        AssistantState.STOPPING: "#374151",
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
        return cls.STATE_COLORS.get(state, cls.LIME)

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
            border-radius: 12px;
        }}
        QLabel#BrandLabel {{
            color: {cls.LIME};
            font-family: {cls.FONT_FAMILY};
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 2px;
        }}
        QLabel#StatusLabel {{
            color: {cls.TEXT_MAIN};
            font-family: {cls.FONT_FAMILY};
            font-size: 12px;
            font-weight: 500;
        }}
        QPushButton#ExpandBtn {{
            background-color: transparent;
            color: {cls.TEXT_MUTED};
            border: none;
            font-size: 12px;
        }}
        QPushButton#ExpandBtn:hover {{
            color: {cls.LIME};
        }}
        """

    @classmethod
    def get_interaction_panel_stylesheet(cls) -> str:
        return f"""
        QWidget#InteractionPanelRoot {{
            background-color: {cls.BG_BASE};
            border: 1px solid {cls.BORDER_ACCENT};
            border-radius: 14px;
        }}
        QFrame#HeaderBar {{
            background-color: {cls.BG_SURFACE};
            border-top-left-radius: 14px;
            border-top-right-radius: 14px;
            border-bottom: 1px solid {cls.BORDER};
        }}
        QLabel#PanelTitle {{
            color: {cls.LIME};
            font-family: {cls.FONT_FAMILY};
            font-size: 13px;
            font-weight: 800;
            letter-spacing: 2px;
        }}
        QPushButton#CollapseBtn {{
            background-color: transparent;
            color: {cls.TEXT_MUTED};
            border: none;
            font-size: 14px;
            font-weight: bold;
        }}
        QPushButton#CollapseBtn:hover {{
            color: {cls.RED};
        }}
        QScrollArea {{
            background-color: transparent;
            border: none;
        }}
        QWidget#ScrollContent {{
            background-color: transparent;
        }}
        QLineEdit#CommandInput {{
            background-color: {cls.BG_CARD};
            color: {cls.TEXT_MAIN};
            border: 1px solid {cls.BORDER};
            border-radius: 8px;
            padding: 8px 12px;
            font-family: {cls.FONT_FAMILY};
            font-size: 13px;
        }}
        QLineEdit#CommandInput:focus {{
            border: 1px solid {cls.LIME};
        }}
        QPushButton#SubmitBtn {{
            background-color: {cls.LIME};
            color: #000000;
            border: none;
            border-radius: 8px;
            padding: 0 16px;
            font-family: {cls.FONT_FAMILY};
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}
        QPushButton#SubmitBtn:hover {{
            background-color: {cls.LIME_HOVER};
        }}
        QPushButton#MicBtn {{
            background-color: {cls.BG_CARD};
            color: {cls.TEXT_MAIN};
            border: 1px solid {cls.BORDER};
            border-radius: 8px;
            font-size: 14px;
        }}
        QPushButton#MicBtn:hover {{
            border-color: {cls.LIME};
            color: {cls.LIME};
        }}
        """
