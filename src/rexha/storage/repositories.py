"""Repository abstractions for Rexha persistence."""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS: dict[str, Any] = {
    "widget.pos_x": -1,
    "widget.pos_y": -1,
    "widget.always_on_top": True,
    "widget.start_expanded": False,
    "voice.wake_phrase": "wake up rexha",
    "voice.wake_listening_enabled": True,
    "voice.tts_enabled": True,
    "voice.tts_rate": 175,
    "voice.follow_up_timeout": 30,
    "hotkey.global_shortcut": "Ctrl+Space",
    "paths.notes_dir": "",
    "paths.projects_dir": "",
}


class SettingsRepository:
    """Manages application preferences with fallback to default values."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a setting value, falling back to provided default or system default."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = ?;", (key,))
        row = cursor.fetchone()
        if row is not None:
            raw_value = row[0]
            try:
                return json.loads(raw_value)
            except (json.JSONDecodeError, TypeError):
                return raw_value

        if default is not None:
            return default
        return DEFAULT_SETTINGS.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set a setting value, serializing complex types to JSON."""
        cursor = self._conn.cursor()
        serialized = json.dumps(value)
        cursor.execute(
            """
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (key, serialized),
        )
        self._conn.commit()

    def get_all(self) -> dict[str, Any]:
        """Return all settings merged with default values."""
        results = dict(DEFAULT_SETTINGS)
        cursor = self._conn.cursor()
        cursor.execute("SELECT key, value FROM settings;")
        for row in cursor.fetchall():
            key, raw_value = row[0], row[1]
            try:
                results[key] = json.loads(raw_value)
            except (json.JSONDecodeError, TypeError):
                results[key] = raw_value
        return results


class AppAliasRepository:
    """Manages friendly application alias mappings (e.g., 'code' -> 'C:\\...\\Code.exe')."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def set_alias(self, alias: str, target_path: str, description: str = "") -> None:
        """Register or update an application alias."""
        clean_alias = alias.strip().lower()
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO app_aliases (alias, target_path, description)
            VALUES (?, ?, ?)
            ON CONFLICT(alias) DO UPDATE SET
                target_path = excluded.target_path,
                description = excluded.description;
            """,
            (clean_alias, target_path, description),
        )
        self._conn.commit()

    def get_target(self, alias: str) -> str | None:
        """Lookup executable path by alias."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT target_path FROM app_aliases WHERE alias = ?;", (alias.strip().lower(),))
        row = cursor.fetchone()
        return row[0] if row else None

    def list_aliases(self) -> dict[str, str]:
        """Return all registered aliases."""
        cursor = self._conn.cursor()
        cursor.execute("SELECT alias, target_path FROM app_aliases ORDER BY alias ASC;")
        return {row[0]: row[1] for row in cursor.fetchall()}

    def delete_alias(self, alias: str) -> bool:
        """Delete an alias."""
        cursor = self._conn.cursor()
        cursor.execute("DELETE FROM app_aliases WHERE alias = ?;", (alias.strip().lower(),))
        self._conn.commit()
        return cursor.rowcount > 0


class TaskHistoryRepository:
    """Logs task executions and step progress for audit and recovery."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def record_task(
        self,
        task_id: str,
        description: str,
        status: str,
        total_steps: int,
        completed_steps: int = 0,
        result_summary: str = "",
        error_message: str = "",
    ) -> None:
        """Record or update a task run."""
        cursor = self._conn.cursor()
        cursor.execute(
            """
            INSERT INTO task_history (
                id, task_description, status, total_steps, completed_steps,
                result_summary, error_message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status = excluded.status,
                completed_steps = excluded.completed_steps,
                completed_at = CURRENT_TIMESTAMP,
                result_summary = excluded.result_summary,
                error_message = excluded.error_message;
            """,
            (
                task_id,
                description,
                status,
                total_steps,
                completed_steps,
                result_summary,
                error_message,
            ),
        )
        self._conn.commit()

    def get_recent_tasks(self, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve recent task execution records."""
        cursor = self._conn.cursor()
        cursor.execute(
            """
            SELECT id, task_description, status, total_steps, completed_steps,
                   started_at, completed_at, result_summary, error_message
            FROM task_history
            ORDER BY started_at DESC
            LIMIT ?;
            """,
            (limit,),
        )
        return [dict(row) for row in cursor.fetchall()]
