"""Windows Named Pipe IPC Client for Rexha Native Core using Overlapped I/O."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import json
import logging
import os
import struct
import sys
import threading
import time
import uuid
from typing import Any, Callable

logger = logging.getLogger(__name__)

PIPE_NAME = r"\\.\pipe\rexha_ipc"
PROTOCOL_VERSION = 1
MAX_FRAME_SIZE = 1048576  # 1 MB

GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
OPEN_EXISTING = 3
FILE_FLAG_OVERLAPPED = 0x40000000
INVALID_HANDLE_VALUE = -1
ERROR_IO_PENDING = 997
WAIT_OBJECT_0 = 0


class OVERLAPPED(ctypes.Structure):
    _fields_ = [
        ("Internal", ctypes.c_void_p),
        ("InternalHigh", ctypes.c_void_p),
        ("Offset", wintypes.DWORD),
        ("OffsetHigh", wintypes.DWORD),
        ("hEvent", wintypes.HANDLE),
    ]


class NativeCoreException(Exception):
    """Raised when native core reports an error."""

    def __init__(self, code: int, message: str, details: str = ""):
        self.code = code
        self.message = message
        self.details = details
        super().__init__(f"[{code}] {message}" + (f" - {details}" if details else ""))


class NativeCoreClient:
    """Thread-safe client communicating with rexha_native_core via Windows Named Pipe."""

    def __init__(self, pipe_name: str = PIPE_NAME, auto_fallback: bool = True):
        self.pipe_name = pipe_name
        self.auto_fallback = auto_fallback
        self._handle = None
        self._lock = threading.Lock()
        self._write_lock = threading.Lock()
        self._pending_requests: dict[str, tuple[threading.Event, dict[str, Any] | None]] = {}
        self._event_handlers: dict[str, list[Callable[[dict[str, Any]], None]]] = {}
        self._listener_thread: threading.Thread | None = None
        self._stop_event = None
        self._running = False
        self._is_connected = False
        self._k32 = ctypes.windll.kernel32 if sys.platform == "win32" else None

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    def connect(self, timeout_sec: float = 3.0) -> bool:
        """Attempt connection to named pipe with Overlapped I/O."""
        if sys.platform != "win32" or not self._k32:
            logger.info("Non-Windows host: NativeCoreClient running in fallback mode")
            return False

        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout_sec:
            h = self._k32.CreateFileW(
                self.pipe_name,
                GENERIC_READ | GENERIC_WRITE,
                0,
                None,
                OPEN_EXISTING,
                FILE_FLAG_OVERLAPPED,
                None,
            )
            if h != INVALID_HANDLE_VALUE and h != 0:
                self._handle = h
                self._running = True
                self._is_connected = True
                self._stop_event = self._k32.CreateEventW(None, True, False, None)
                logger.info("Connected to Rexha Native Core at %s (handle: %s)", self.pipe_name, h)

                # Start background reader thread
                self._listener_thread = threading.Thread(
                    target=self._reader_loop, daemon=True, name="RexhaIpcReader"
                )
                self._listener_thread.start()
                return True
            time.sleep(0.08)

        logger.warning("Could not connect to Native Core named pipe at %s", self.pipe_name)
        return False

    def close(self) -> None:
        """Close connection to native core."""
        self._running = False
        self._is_connected = False

        if self._stop_event and self._k32:
            self._k32.SetEvent(self._stop_event)

        with self._lock:
            h = self._handle
            self._handle = None
            if h and h != INVALID_HANDLE_VALUE and self._k32:
                try:
                    self._k32.CancelIo(h)
                    self._k32.CloseHandle(h)
                except Exception as e:
                    logger.debug("Pipe close notice: %s", e)

            if self._stop_event and self._k32:
                self._k32.CloseHandle(self._stop_event)
                self._stop_event = None

        if self._listener_thread and self._listener_thread.is_alive():
            self._listener_thread.join(timeout=0.8)
        logger.info("NativeCoreClient closed cleanly")

    def register_event_handler(
        self, event_name: str, handler: Callable[[dict[str, Any]], None]
    ) -> None:
        """Register a callback for unsolicited native events."""
        with self._lock:
            if event_name not in self._event_handlers:
                self._event_handlers[event_name] = []
            if handler not in self._event_handlers[event_name]:
                self._event_handlers[event_name].append(handler)

    def _read_exact_overlapped(self, handle: Any, n_bytes: int) -> bytes | None:
        """Read exactly n_bytes using Windows Overlapped I/O."""
        buf = ctypes.create_string_buffer(n_bytes)
        bytes_read = wintypes.DWORD(0)
        total_read = 0

        hEvent = self._k32.CreateEventW(None, True, False, None)
        try:
            while total_read < n_bytes and self._running:
                ov = OVERLAPPED()
                ov.hEvent = hEvent
                self._k32.ResetEvent(hEvent)

                needed = n_bytes - total_read
                chunk_target = ctypes.byref(buf, total_read)
                success = self._k32.ReadFile(handle, chunk_target, needed, ctypes.byref(bytes_read), ctypes.byref(ov))

                if not success:
                    err = self._k32.GetLastError()
                    if err == ERROR_IO_PENDING:
                        # Wait indefinitely on either read event or stop event (0% CPU idle)
                        INFINITE = 0xFFFFFFFF
                        wait_handles = (wintypes.HANDLE * 2)(hEvent, self._stop_event)
                        wait_res = self._k32.WaitForMultipleObjects(2, wait_handles, False, INFINITE)
                        if wait_res == WAIT_OBJECT_0:
                            # Read completed
                            if not self._k32.GetOverlappedResult(handle, ctypes.byref(ov), ctypes.byref(bytes_read), False):
                                return None
                        else:
                            # Stop signaled: cancel pending I/O and wait for kernel completion before freeing ov
                            self._k32.CancelIo(handle)
                            self._k32.GetOverlappedResult(handle, ctypes.byref(ov), ctypes.byref(bytes_read), True)
                            return None
                    else:
                        return None

                if bytes_read.value == 0:
                    return None
                total_read += bytes_read.value

            return buf.raw[:n_bytes] if total_read == n_bytes else None
        finally:
            self._k32.CloseHandle(hEvent)

    def _reader_loop(self) -> None:
        """Continuous background message reader."""
        while self._running:
            handle = self._handle
            if not handle or handle == INVALID_HANDLE_VALUE:
                break

            # Read 4-byte big-endian length prefix
            header = self._read_exact_overlapped(handle, 4)
            if not header or len(header) < 4:
                break

            length = struct.unpack(">I", header)[0]
            if length > MAX_FRAME_SIZE or length == 0:
                logger.error("Received illegal frame length: %s", length)
                break

            payload_bytes = self._read_exact_overlapped(handle, length)
            if not payload_bytes or len(payload_bytes) != length:
                break

            try:
                payload_str = payload_bytes.decode("utf-8")
                msg = json.loads(payload_str)
                self._handle_incoming_message(msg)
            except Exception as e:
                logger.warning("Error parsing IPC payload: %s", e)

        self._is_connected = False

    def _handle_incoming_message(self, msg: dict[str, Any]) -> None:
        """Route message to awaiting request future or event handler."""
        msg_type = msg.get("type", "result")

        if msg_type == "event":
            event_name = msg.get("event_name", "")
            data = msg.get("data", {})
            handlers: list[Callable[[dict[str, Any]], None]] = []
            with self._lock:
                handlers = list(self._event_handlers.get(event_name, []))

            for h in handlers:
                try:
                    h(data)
                except Exception as ex:
                    logger.exception("Error in native event handler '%s': %s", event_name, ex)
            return

        req_id = msg.get("request_id")
        if req_id:
            with self._lock:
                if req_id in self._pending_requests:
                    evt, _ = self._pending_requests[req_id]
                    self._pending_requests[req_id] = (evt, msg)
                    evt.set()

    def send_request(
        self, action_type: str, arguments: dict[str, Any] | None = None, timeout_sec: float = 5.0
    ) -> dict[str, Any]:
        """Send a structured request to Native Core and wait for response."""
        if not self._is_connected or not self._handle or self._handle == INVALID_HANDLE_VALUE:
            if self.auto_fallback:
                return self._fallback_action(action_type, arguments or {})
            raise NativeCoreException(1001, "Native Core is not connected")

        req_id = f"req-{uuid.uuid4()}"
        req_payload = {
            "protocol_version": PROTOCOL_VERSION,
            "request_id": req_id,
            "type": action_type,
            "arguments": arguments or {},
        }
        json_bytes = json.dumps(req_payload).encode("utf-8")
        frame = struct.pack(">I", len(json_bytes)) + json_bytes

        done_event = threading.Event()
        with self._lock:
            self._pending_requests[req_id] = (done_event, None)

        hWriteEvent = self._k32.CreateEventW(None, True, False, None)
        try:
            with self._write_lock:
                if not self._handle or self._handle == INVALID_HANDLE_VALUE:
                    raise NativeCoreException(1001, "Pipe handle invalid")

                ov = OVERLAPPED()
                ov.hEvent = hWriteEvent
                bytes_written = wintypes.DWORD(0)

                success = self._k32.WriteFile(
                    self._handle, frame, len(frame), ctypes.byref(bytes_written), ctypes.byref(ov)
                )
                if not success:
                    err = self._k32.GetLastError()
                    if err == ERROR_IO_PENDING:
                        if not self._k32.GetOverlappedResult(self._handle, ctypes.byref(ov), ctypes.byref(bytes_written), True):
                            raise NativeCoreException(1001, "WriteFile overlapped error")
                    else:
                        raise NativeCoreException(1001, f"Failed to write frame to named pipe (Error: {err})")

            if not done_event.wait(timeout=timeout_sec):
                raise NativeCoreException(2001, f"Operation '{action_type}' timed out after {timeout_sec}s")

            with self._lock:
                _, response = self._pending_requests.pop(req_id, (done_event, None))

            if not response:
                raise NativeCoreException(5000, "Empty response from Native Core")

            if not response.get("success", False):
                err = response.get("error") or {}
                raise NativeCoreException(
                    err.get("code", 5000),
                    err.get("message", "Operation failed"),
                    err.get("details", ""),
                )

            return response.get("data") or {}

        finally:
            self._k32.CloseHandle(hWriteEvent)
            with self._lock:
                self._pending_requests.pop(req_id, None)

    def _fallback_action(self, action_type: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Pure-Python fallback when Native Core is offline or on non-Windows test runners."""
        logger.debug("Invoking fallback handler for action: %s", action_type)
        if action_type == "system.ping":
            return {"pong": True, "fallback": True}
        if action_type == "system.get_status":
            return {
                "core_version": "0.1.0-python-fallback",
                "pid": os.getpid(),
                "uptime_seconds": 0.0,
            }
        if action_type == "system.get_metrics":
            import psutil
            mem = psutil.virtual_memory()
            return {
                "cpu_percent": psutil.cpu_percent(interval=None),
                "ram_total_mb": mem.total // (1024 * 1024),
                "ram_available_mb": mem.available // (1024 * 1024),
                "ram_used_percent": mem.percent,
            }
        if action_type == "hotkey.register":
            return {"registered": True, "fallback": True}
        if action_type == "hotkey.unregister":
            return {"unregistered": True, "fallback": True}
        if action_type == "window.get_foreground":
            return {"hwnd": 0, "title": "Desktop Fallback", "process_name": "python.exe", "pid": os.getpid()}
        if action_type == "window.list":
            return {"windows": []}
        if action_type == "process.get_status":
            return {"pid": arguments.get("pid", 0), "is_running": True, "exit_code": 0}
        return {"status": "fallback_ok"}

    # Convenience API methods
    def ping(self) -> bool:
        res = self.send_request("system.ping")
        return bool(res.get("pong", False))

    def get_system_metrics(self) -> dict[str, Any]:
        return self.send_request("system.get_metrics")

    def get_system_status(self) -> dict[str, Any]:
        return self.send_request("system.get_status")

    def register_hotkey(self, hotkey_id: int = 101, modifiers: list[str] | None = None, vk: int = 0x20) -> bool:
        mods = modifiers or ["ctrl"]
        res = self.send_request("hotkey.register", {"id": hotkey_id, "modifiers": mods, "vk": vk})
        return bool(res.get("registered", False))

    def unregister_hotkey(self, hotkey_id: int = 101) -> bool:
        res = self.send_request("hotkey.unregister", {"id": hotkey_id})
        return bool(res.get("unregistered", False))

    def get_foreground_window(self) -> dict[str, Any]:
        return self.send_request("window.get_foreground")

    def list_windows(self, visible_only: bool = True, filter_empty_titles: bool = True) -> list[dict[str, Any]]:
        res = self.send_request("window.list", {"visible_only": visible_only, "filter_empty_titles": filter_empty_titles})
        return res.get("windows", [])

    def set_window_state(self, hwnd: int, state: str) -> bool:
        res = self.send_request("window.set_state", {"hwnd": hwnd, "state": state})
        return bool(res.get("success", False))

    def close_window(self, hwnd: int, graceful: bool = True, timeout_ms: int = 3000) -> bool:
        res = self.send_request("window.close", {"hwnd": hwnd, "graceful": graceful, "timeout_ms": timeout_ms})
        return bool(res.get("closed", False))

    def launch_process(self, executable_path: str, arguments: list[str] | None = None, working_dir: str = "") -> int:
        res = self.send_request("process.launch", {
            "executable_path": executable_path,
            "arguments": arguments or [],
            "working_directory": working_dir,
        })
        return int(res.get("pid", 0))

    def shutdown_native_core(self) -> None:
        try:
            self.send_request("system.shutdown", timeout_sec=1.5)
        except Exception:
            pass
