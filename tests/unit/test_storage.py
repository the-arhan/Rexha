"""Unit tests for Rexha persistence layers."""

from rexha.storage.repositories import SettingsRepository, AppAliasRepository, TaskHistoryRepository


def test_settings_default_values(settings_repo: SettingsRepository) -> None:
    wake_phrase = settings_repo.get("voice.wake_phrase")
    assert wake_phrase == "wake up rexha"

    timeout = settings_repo.get("voice.follow_up_timeout")
    assert timeout == 30

    unknown = settings_repo.get("custom.nonexistent", default="fallback")
    assert unknown == "fallback"


def test_settings_save_and_retrieve(settings_repo: SettingsRepository) -> None:
    settings_repo.set("widget.pos_x", 1200)
    settings_repo.set("widget.pos_y", 800)
    settings_repo.set("voice.tts_enabled", False)

    assert settings_repo.get("widget.pos_x") == 1200
    assert settings_repo.get("widget.pos_y") == 800
    assert settings_repo.get("voice.tts_enabled") is False


def test_app_aliases_crud(alias_repo: AppAliasRepository) -> None:
    # Create / update
    alias_repo.set_alias("code", r"C:\Program Files\VS Code\Code.exe", "Visual Studio Code")
    alias_repo.set_alias("browser", r"C:\Program Files\Edge\msedge.exe", "Edge Browser")

    # Read
    assert alias_repo.get_target("code") == r"C:\Program Files\VS Code\Code.exe"
    assert alias_repo.get_target("CODE") == r"C:\Program Files\VS Code\Code.exe"  # Case-insensitive
    assert alias_repo.get_target("nonexistent") is None

    all_aliases = alias_repo.list_aliases()
    assert len(all_aliases) == 2
    assert "code" in all_aliases
    assert "browser" in all_aliases

    # Delete
    deleted = alias_repo.delete_alias("code")
    assert deleted is True
    assert alias_repo.get_target("code") is None


def test_task_history_recording(task_repo: TaskHistoryRepository) -> None:
    task_repo.record_task(
        task_id="task-1001",
        description="Open VS Code and launch terminal",
        status="running",
        total_steps=2,
        completed_steps=0,
    )

    recent = task_repo.get_recent_tasks(limit=10)
    assert len(recent) == 1
    assert recent[0]["id"] == "task-1001"
    assert recent[0]["status"] == "running"
    assert recent[0]["completed_steps"] == 0

    # Update task
    task_repo.record_task(
        task_id="task-1001",
        description="Open VS Code and launch terminal",
        status="completed",
        total_steps=2,
        completed_steps=2,
        result_summary="Both steps succeeded",
    )

    updated = task_repo.get_recent_tasks(limit=10)
    assert len(updated) == 1
    assert updated[0]["status"] == "completed"
    assert updated[0]["completed_steps"] == 2
    assert updated[0]["result_summary"] == "Both steps succeeded"
