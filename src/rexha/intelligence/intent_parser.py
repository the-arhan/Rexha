"""Hybrid intent parsing engine for Rexha (Deterministic matcher + Pluggable LLM planner)."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import Any

from rexha.orchestration.actions import StructuredAction
from rexha.orchestration.policy import PermissionTier

logger = logging.getLogger(__name__)


class LLMPlanner(ABC):
    """Abstract interface for multi-step AI planning adapters (Gemini, OpenAI, Claude, Ollama)."""

    @abstractmethod
    def plan_task(self, prompt: str) -> list[StructuredAction]:
        """Convert natural language prompt into ordered structured actions."""
        pass


class IntentParser:
    """Interprets user commands deterministically with fallback to optional LLM planner."""

    def __init__(self, llm_planner: LLMPlanner | None = None):
        self.llm_planner = llm_planner

    def parse(self, text: str) -> list[StructuredAction]:
        """Parse natural language command into structured action plans."""
        cleaned = text.strip()
        lower = cleaned.lower()

        # 1. System Status / Metrics
        if lower in ("status", "system status", "metrics", "sysinfo", "specs"):
            return [
                StructuredAction(
                    action_name="system.get_status",
                    description="Query system status and metrics",
                    tier=PermissionTier.SAFE,
                )
            ]

        # 2. Window listing
        if lower in ("windows", "list windows", "show windows", "running apps"):
            return [
                StructuredAction(
                    action_name="window.list",
                    arguments={"visible_only": True, "filter_empty_titles": True},
                    description="List active desktop windows",
                    tier=PermissionTier.SAFE,
                )
            ]

        # 3. Active foreground window
        if lower in ("active window", "foreground", "current app", "where am i"):
            return [
                StructuredAction(
                    action_name="window.get_foreground",
                    description="Get active foreground window info",
                    tier=PermissionTier.SAFE,
                )
            ]

        # 4. App launching (open / launch <target>)
        match = re.match(r"^(?:open|launch|start|run)\s+(.+)$", lower)
        if match:
            target = match.group(1).strip()
            return [
                StructuredAction(
                    action_name="application.open",
                    arguments={"executable": target},
                    description=f"Launch application '{target}'",
                    tier=PermissionTier.STANDARD,
                )
            ]

        # 5. Ping
        if lower == "ping":
            return [
                StructuredAction(
                    action_name="system.ping",
                    description="Ping Native Core",
                    tier=PermissionTier.SAFE,
                )
            ]

        # 6. Sleep / UI Minimize
        if lower in ("sleep", "minimize", "hide", "collapse"):
            return [
                StructuredAction(
                    action_name="ui.sleep",
                    description="Collapse assistant to compact resting widget",
                    tier=PermissionTier.SAFE,
                )
            ]

        # 7. Fallback to pluggable LLM planner if configured
        if self.llm_planner:
            try:
                return self.llm_planner.plan_task(cleaned)
            except Exception as e:
                logger.warning("LLM planning error: %s", e)

        return []

