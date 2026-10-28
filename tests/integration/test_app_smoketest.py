"""Integration smoke test for full RexhaApp lifecycle."""

import time
from PySide6.QtCore import QTimer
from rexha.app import RexhaApp
from rexha.core.state_machine import AssistantState


def test_full_app_boot_and_shutdown(tmp_path) -> None:
    db_file = tmp_path / "rexha_test.sqlite"
    app = RexhaApp(db_path=db_file, enable_native_core=True)

    # Schedule shutdown after 500ms
    def delayed_check_and_quit():
        # Verify app is in SLEEPING state
        assert app.state_machine.current_state == AssistantState.SLEEPING
        assert app.ui_coordinator.floating_widget.isVisible() is True
        # Clean quit
        app.ui_coordinator.quit_application()

    QTimer.singleShot(500, delayed_check_and_quit)

    exit_code = app.run()
    assert exit_code == 0
    assert db_file.exists()


def test_app_boot_no_native_fallback(tmp_path) -> None:
    db_file = tmp_path / "rexha_fallback_test.sqlite"
    app = RexhaApp(db_path=db_file, enable_native_core=False)

    def delayed_check_and_quit():
        assert app.state_machine.current_state == AssistantState.SLEEPING
        assert app.ui_coordinator.floating_widget.isVisible() is True
        # In fallback mode, hotkey_thread is active
        assert app.ui_coordinator.hotkey_thread is not None
        assert app.ui_coordinator.hotkey_thread.isRunning() is True
        app.ui_coordinator.quit_application()

    QTimer.singleShot(500, delayed_check_and_quit)

    exit_code = app.run()
    assert exit_code == 0
    assert db_file.exists()
