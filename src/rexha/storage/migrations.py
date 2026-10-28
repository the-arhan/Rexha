"""Database schema migrations for Rexha SQLite persistence."""

from __future__ import annotations

import logging
import sqlite3

logger = logging.getLogger(__name__)

MIGRATION_V1 = """
-- Version 1 Initial Schema

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS app_aliases (
    alias TEXT PRIMARY KEY,
    target_path TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS task_history (
    id TEXT PRIMARY KEY,
    task_description TEXT NOT NULL,
    status TEXT NOT NULL,
    total_steps INTEGER NOT NULL,
    completed_steps INTEGER NOT NULL,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    result_summary TEXT,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    action_type TEXT,
    details TEXT,
    severity TEXT DEFAULT 'info',
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

MIGRATIONS: list[tuple[int, str]] = [
    (1, MIGRATION_V1),
]


def apply_migrations(conn: sqlite3.Connection) -> None:
    """Apply any pending database migrations."""
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_version (
            version INTEGER PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()

    cursor.execute("SELECT MAX(version) FROM schema_version;")
    row = cursor.fetchone()
    current_version = row[0] if row and row[0] is not None else 0

    for version, sql_script in MIGRATIONS:
        if version > current_version:
            logger.info("Applying database migration to version %d", version)
            cursor.executescript(sql_script)
            cursor.execute("INSERT INTO schema_version (version) VALUES (?);", (version,))
            conn.commit()
            logger.info("Database migration to version %d completed successfully", version)
