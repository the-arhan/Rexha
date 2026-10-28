"""Unit tests for Native Core client and process supervisor fallback behaviors."""

import pytest
from pathlib import Path
from rexha.services.native_client import NativeCoreClient, NativeCoreException
from rexha.services.process_supervisor import NativeProcessSupervisor


def test_supervisor_binary_resolution():
    supervisor = NativeProcessSupervisor(binary_path="nonexistent_binary.exe")
    assert not supervisor.is_running
    # Should resolve to discovered binary if present or None
    assert isinstance(supervisor.is_available, bool)


def test_client_fallback_mode():
    client = NativeCoreClient(pipe_name=r"\\.\pipe\nonexistent_pipe_12345", auto_fallback=True)
    assert not client.is_connected

    # Ping fallback
    assert client.ping() is True

    # Status fallback
    status = client.get_system_status()
    assert "core_version" in status
    assert "pid" in status

    # Metrics fallback
    metrics = client.get_system_metrics()
    assert "ram_total_mb" in metrics
    assert "cpu_percent" in metrics
    assert metrics["ram_total_mb"] > 0

    # Hotkey fallback
    assert client.register_hotkey(101) is True
    assert client.unregister_hotkey(101) is True

    # Window fallback
    assert isinstance(client.list_windows(), list)
    fg = client.get_foreground_window()
    assert "hwnd" in fg

    # Process status fallback
    p_status = client.send_request("process.get_status", {"pid": 123})
    assert p_status.get("is_running") is True


def test_client_error_without_fallback():
    client = NativeCoreClient(pipe_name=r"\\.\pipe\nonexistent_pipe_12345", auto_fallback=False)
    with pytest.raises(NativeCoreException) as exc_info:
        client.send_request("system.ping")
    assert exc_info.value.code == 1001

