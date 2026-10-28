"""Application lifecycle controller for Rexha."""

from __future__ import annotations

import logging
import signal
import sys
from pathlib import Path
from PySide6.QtWidgets import QApplication

from rexha.core.state_machine import AssistantStateMachine, AssistantState
from rexha.core.events import EventBus
from rexha.storage.database import DatabaseManager, DEFAULT_DB_FILE
from rexha.storage.repositories import SettingsRepository, AppAliasRepository, TaskHistoryRepository
from rexha.ui.coordinator import UICoordinator

logger = logging.getLogger(__name__)


class RexhaApp:
    """Encapsulates the complete application lifecycle, resources, and UI."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_FILE):
        self.db_path = db_path
        self._setup_logging()

        logger.info("Initializing Rexha Desktop Assistant")
        self.qapp = QApplication.instance() or QApplication(sys.argv)
        self.qapp.setQuitOnLastWindowClosed(False)  # Allow running in tray/widget
        self.qapp.setApplicationName("Rexha")
        self.qapp.setOrganizationName("RexhaAI")

        # Core subsystems
        self.state_machine = AssistantStateMachine(AssistantState.STARTING)
        self.event_bus = EventBus()
        self.db_manager = DatabaseManager(self.db_path)
        self.settings_repo = SettingsRepository(self.db_manager.connection)
        self.alias_repo = AppAliasRepository(self.db_manager.connection)
        self.task_repo = TaskHistoryRepository(self.db_manager.connection)

        # UI Coordinator
        self.ui_coordinator = UICoordinator(
            state_machine=self.state_machine,
            settings_repo=self.settings_repo,
            event_bus=self.event_bus,
        )

        # Handle OS interrupt signals cleanly
        signal.signal(signal.SIGINT, self._handle_os_signal)
        signal.signal(signal.SIGTERM, self._handle_os_signal)

    def _setup_logging(self) -> None:
        """Configure structured application logging."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def _handle_os_signal(self, signum: int, frame) -> None:
        """Handle SIGINT / SIGTERM for graceful exit."""
        logger.info("Received termination signal %s; shutting down cleanly", signum)
        self.shutdown()

    def run(self) -> int:
        """Start Rexha and enter the Qt application event loop."""
        self.ui_coordinator.start()
        exit_code = self.qapp.exec()
        self.shutdown()
        return exit_code

    def shutdown(self) -> None:
        """Release devices, close database, and clean up threads."""
        logger.info("Shutting down Rexha resources")
        try:
            self.ui_coordinator.quit_application()
        except Exception as e:
            logger.debug("Coordinator shutdown note: %s", e)

        try:
            self.db_manager.close()
        except Exception as e:
            logger.debug("Database close note: %s", e)

        logger.info("Rexha shutdown complete")
