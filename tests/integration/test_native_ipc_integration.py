"""Integration tests for live C++ Native Core process, IPC pipe, and requests."""

import concurrent.futures
import ctypes
from ctypes import wintypes
import json
import os
import struct
import sys
import time
import pytest
from rexha.services.native_client import (
    NativeCoreClient,
    NativeCoreException,
    GENERIC_READ,
    GENERIC_WRITE,
    OPEN_EXISTING,
    INVALID_HANDLE_VALUE,
    MAX_FRAME_SIZE,
)
from rexha.services.process_supervisor import NativeProcessSupervisor
from rexha.orchestration.actions import ActionExecutionEngine, StructuredAction
from rexha.orchestration.policy import PolicyEngine, PermissionTier


@pytest.fixture(scope="module")
def native_supervisor():
    """Start a dedicated native core process for integration testing."""
    if sys.platform != "win32":
        pytest.skip("Windows Named Pipe integration requires Windows")

    supervisor = NativeProcessSupervisor()
    if not supervisor.is_available:
        pytest.skip("rexha_native_core.exe not yet built")

    pipe_name = rf"\\.\pipe\rexha_ipc_test_{os.getpid()}"
    supervisor.pipe_name = pipe_name

    started = supervisor.start()
    assert started is True
    assert supervisor.is_running is True

    # Give server a moment to spin up
    time.sleep(0.15)

    yield supervisor

    # Teardown
    supervisor.stop(timeout_sec=1.5)


def send_raw_frame(pipe_name: str, payload_bytes: bytes) -> bytes | None:
    """Helper to send a length-prefixed raw frame and read the response."""
    k32 = ctypes.windll.kernel32
    h = k32.CreateFileW(
        pipe_name,
        GENERIC_READ | GENERIC_WRITE,
        0,
        None,
        OPEN_EXISTING,
        0,
        None,
    )
    if h == INVALID_HANDLE_VALUE or h == 0:
        return None

    try:
        frame = struct.pack(">I", len(payload_bytes)) + payload_bytes
        written = wintypes.DWORD(0)
        ok = k32.WriteFile(h, frame, len(frame), ctypes.byref(written), None)
        if not ok or written.value != len(frame):
            return None

        # Read 4-byte response header
        header = ctypes.create_string_buffer(4)
        read = wintypes.DWORD(0)
        ok = k32.ReadFile(h, header, 4, ctypes.byref(read), None)
        if not ok or read.value < 4:
            return None

        resp_len = struct.unpack(">I", header.raw)[0]
        if resp_len > MAX_FRAME_SIZE:
            return None

        buf = ctypes.create_string_buffer(resp_len)
        ok = k32.ReadFile(h, buf, resp_len, ctypes.byref(read), None)
        if not ok or read.value != resp_len:
            return None

        return buf.raw[:resp_len]
    finally:
        k32.CloseHandle(h)


def test_live_native_core_ipc_lifecycle(native_supervisor):
    """Scenario 1: Happy-path IPC lifecycle, metrics, and window listing."""
    client = NativeCoreClient(pipe_name=native_supervisor.pipe_name, auto_fallback=False)
    try:
        connected = client.connect(timeout_sec=3.0)
        assert connected is True
        assert client.is_connected is True

        # Test system.ping
        assert client.ping() is True

        # Test system.get_status
        status = client.get_system_status()
        assert status.get("core_version") == "0.1.0"
        assert status.get("pid") > 0
        assert status.get("uptime_seconds", -1) >= 0

        # Test system.get_metrics
        metrics = client.get_system_metrics()
        assert metrics.get("ram_total_mb", 0) > 0
        assert metrics.get("ram_available_mb", 0) > 0
        assert 0.0 <= metrics.get("cpu_percent", -1.0) <= 100.0

        # Test hotkey registration & unregistration
        assert client.register_hotkey(999, ["ctrl", "alt"], 0x41) is True
        assert client.unregister_hotkey(999) is True

        # Test window listing
        windows = client.list_windows(visible_only=False, filter_empty_titles=False)
        assert isinstance(windows, list)
    finally:
        client.close()


def test_unknown_action_returns_code_1005(native_supervisor):
    """Scenario 2: Reject unknown actions with error code 1005."""
    client = NativeCoreClient(pipe_name=native_supervisor.pipe_name, auto_fallback=False)
    try:
        assert client.connect(timeout_sec=3.0) is True

        with pytest.raises(NativeCoreException) as exc_info:
            client.send_request("arbitrary.dangerous.action", {"cmd": "format"})

        assert exc_info.value.code == 1005
        assert "not registered" in exc_info.value.message.lower() or "not registered" in exc_info.value.details.lower()
    finally:
        client.close()


def test_malformed_json_returns_code_1002(native_supervisor):
    """Scenario 3: Reject malformed JSON request envelope with error code 1002 without server crash."""
    bad_json = b"{\"protocol_version\": 1, \"request_id\": \"test-1\", \"type\": \"system.ping\"," # unclosed
    resp_bytes = send_raw_frame(native_supervisor.pipe_name, bad_json)
    assert resp_bytes is not None

    resp = json.loads(resp_bytes.decode("utf-8"))
    assert resp.get("success") is False
    assert resp.get("type") == "error"
    err = resp.get("error", {})
    assert err.get("code") == 1002
    assert "INVALID_JSON" in err.get("message", "")

    # Verify server is still alive by connecting standard client
    client = NativeCoreClient(pipe_name=native_supervisor.pipe_name, auto_fallback=False)
    try:
        assert client.connect(timeout_sec=3.0) is True
        assert client.ping() is True
    finally:
        client.close()


def test_oversized_payload_rejection(native_supervisor):
    """Scenario 4: Reject payloads exceeding 1MB limit without allocating excessive memory or crashing."""
    k32 = ctypes.windll.kernel32
    h = k32.CreateFileW(
        native_supervisor.pipe_name,
        GENERIC_READ | GENERIC_WRITE,
        0,
        None,
        OPEN_EXISTING,
        0,
        None,
    )
    assert h != INVALID_HANDLE_VALUE and h != 0

    try:
        # Claim a 16MB payload
        fake_len = 16 * 1024 * 1024
        header = struct.pack(">I", fake_len)
        written = wintypes.DWORD(0)
        k32.WriteFile(h, header, len(header), ctypes.byref(written), None)

        # Server should detect len > MAX_FRAME_SIZE and drop the connection
        read_buf = ctypes.create_string_buffer(4)
        read = wintypes.DWORD(0)
        res = k32.ReadFile(h, read_buf, 4, ctypes.byref(read), None)
        # ReadFile should return False / 0 bytes as pipe is broken by server
        assert not res or read.value == 0
    finally:
        k32.CloseHandle(h)

    # Verify server is still running and accepts new client
    client = NativeCoreClient(pipe_name=native_supervisor.pipe_name, auto_fallback=False)
    try:
        assert client.connect(timeout_sec=3.0) is True
        assert client.ping() is True
    finally:
        client.close()


def test_concurrent_client_requests(native_supervisor):
    """Scenario 5: Multi-threaded request multiplexing over single IPC connection."""
    client = NativeCoreClient(pipe_name=native_supervisor.pipe_name, auto_fallback=False)
    try:
        assert client.connect(timeout_sec=3.0) is True

        def worker(idx: int) -> bool:
            for _ in range(5):
                ping_ok = client.ping()
                if not ping_ok:
                    return False
                metrics = client.get_system_metrics()
                if metrics.get("ram_total_mb", 0) <= 0:
                    return False
            return True

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(worker, i) for i in range(4)]
            results = [f.result(timeout=10.0) for f in futures]

        assert all(results) is True
    finally:
        client.close()


def test_process_lifecycle_and_verified_termination(native_supervisor):
    """Scenario 6: Launch target process and verify outcome upon termination."""
    client = NativeCoreClient(pipe_name=native_supervisor.pipe_name, auto_fallback=False)
    try:
        assert client.connect(timeout_sec=3.0) is True

        # Launch background cmd.exe with a timeout
        pid = client.launch_process(r"C:\Windows\System32\cmd.exe", ["/c", "timeout /t 30 >nul"])
        assert pid > 0

        # Verify process is running
        status = client.send_request("process.get_status", {"pid": pid})
        assert status.get("is_running") is True
        assert status.get("pid") == pid

        # Terminate process
        term_res = client.send_request("process.terminate", {"pid": pid, "force": True})
        assert term_res.get("terminated") is True

        # Give Windows a moment to clean up process table
        time.sleep(0.2)

        # Verified outcome: process is no longer running (either status reports is_running: False, or raises PROCESS_NOT_FOUND)
        try:
            status_after = client.send_request("process.get_status", {"pid": pid})
            assert status_after.get("is_running") is False
        except NativeCoreException as e:
            assert e.code == 3004  # PROCESS_NOT_FOUND
    finally:
        client.close()
