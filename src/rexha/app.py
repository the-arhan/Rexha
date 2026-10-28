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
from rexha.services.native_client import NativeCoreClient
from rexha.services.process_supervisor import NativeProcessSupervisor

logger = logging.getLogger(__name__)


class RexhaApp:
    """Encapsulates the complete application lifecycle, native supervisor, and UI."""

    def __init__(self, db_path: Path | str = DEFAULT_DB_FILE, enable_native_core: bool = True):
        self.db_path = db_path
        self.enable_native_core = enable_native_core
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

        # Native Core Supervisor & IPC Client
        self.native_supervisor: NativeProcessSupervisor | None = None
        self.native_client = NativeCoreClient(auto_fallback=True)

        if self.enable_native_core:
            self.native_supervisor = NativeProcessSupervisor()

        # UI Coordinator
        self.ui_coordinator = UICoordinator(
            state_machine=self.state_machine,
            settings_repo=self.settings_repo,
            event_bus=self.event_bus,
            native_client=self.native_client,
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
        """Start Native Core, UI coordinator, and enter Qt application event loop."""
        if self.native_supervisor and self.native_supervisor.is_available:
            logger.info("Starting Native Core process")
            if self.native_supervisor.start():
                self.native_client.connect(timeout_sec=2.5)

        self.ui_coordinator.start()
        exit_code = self.qapp.exec()
        self.shutdown()
        return exit_code

    def shutdown(self) -> None:
        """Release devices, stop native core, close database, and clean up."""
        logger.info("Shutting down Rexha resources")
        try:
            self.ui_coordinator.quit_application()
        except Exception as e:
            logger.debug("Coordinator shutdown note: %s", e)

        try:
            self.native_client.shutdown_native_core()
            self.native_client.close()
        except Exception as e:
            logger.debug("Native client close note: %s", e)

        if self.native_supervisor:
            try:
                self.native_supervisor.stop(timeout_sec=1.5)
            except Exception as e:
                logger.debug("Native supervisor stop note: %s", e)

        try:
            self.db_manager.close()
        except Exception as e:
            logger.debug("Database close note: %s", e)

        logger.info("Rexha shutdown complete")
