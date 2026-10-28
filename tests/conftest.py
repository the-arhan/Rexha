"""Shared pytest fixtures for Rexha test suite."""

import sqlite3
import pytest

from rexha.storage.database import DatabaseManager
from rexha.storage.repositories import SettingsRepository, AppAliasRepository, TaskHistoryRepository
from rexha.core.state_machine import AssistantStateMachine, AssistantState
from rexha.core.events import EventBus


@pytest.fixture
def memory_db() -> DatabaseManager:
    """Provide an in-memory initialized SQLite DatabaseManager."""
    db = DatabaseManager(":memory:")
    yield db
    db.close()


@pytest.fixture
def settings_repo(memory_db: DatabaseManager) -> SettingsRepository:
    """Provide a SettingsRepository backed by an in-memory database."""
    return SettingsRepository(memory_db.connection)


@pytest.fixture
def alias_repo(memory_db: DatabaseManager) -> AppAliasRepository:
    """Provide an AppAliasRepository backed by an in-memory database."""
    return AppAliasRepository(memory_db.connection)


@pytest.fixture
def task_repo(memory_db: DatabaseManager) -> TaskHistoryRepository:
    """Provide a TaskHistoryRepository backed by an in-memory database."""
    return TaskHistoryRepository(memory_db.connection)


@pytest.fixture
def state_machine() -> AssistantStateMachine:
    """Provide an AssistantStateMachine starting in STARTING state."""
    return AssistantStateMachine(AssistantState.STARTING)


@pytest.fixture
def event_bus() -> EventBus:
    """Provide a clean EventBus."""
    return EventBus()
