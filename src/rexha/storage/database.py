"""SQLite database connection and session management for Rexha."""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

from rexha.storage.migrations import apply_migrations

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path("data")
DEFAULT_DB_FILE = DEFAULT_DATA_DIR / "rexha.sqlite"


class DatabaseManager:
    """Manages SQLite connection lifecycle and migrations."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_FILE):
        self.db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None
        self._ensure_storage_directory()
        self.initialize()

    def _ensure_storage_directory(self) -> None:
        """Create parent directory if using a file path."""
        if self.db_path != ":memory:":
            path = Path(self.db_path)
            path.parent.mkdir(parents=True, exist_ok=True)

    def initialize(self) -> None:
        """Open database connection and apply migrations."""
        logger.info("Initializing SQLite database at: %s", self.db_path)
        self._conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=10.0,
        )
        self._conn.row_factory = sqlite3.Row

        # Optimize for desktop app responsiveness
        if self.db_path != ":memory:":
            self._conn.execute("PRAGMA journal_mode = WAL;")
            self._conn.execute("PRAGMA synchronous = NORMAL;")
        self._conn.execute("PRAGMA foreign_keys = ON;")

        # Apply schema migrations
        apply_migrations(self._conn)

    @property
    def connection(self) -> sqlite3.Connection:
        """Get the active database connection."""
        if self._conn is None:
            self.initialize()
        assert self._conn is not None
        return self._conn

    def close(self) -> None:
        """Close database connection cleanly."""
        if self._conn:
            try:
                self._conn.close()
                logger.info("Database connection closed cleanly")
            except Exception as e:
                logger.exception("Error closing database connection: %s", e)
            finally:
                self._conn = None
