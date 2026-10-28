# Project Rexha — Inter-Process Communication (IPC) Protocol Specification

**Document Version:** 1.0.0  
**Transport:** Windows Named Pipe (`\\.\pipe\rexha_ipc`)  
**Framing:** 4-Byte Big-Endian Unsigned Integer Length Prefix + UTF-8 JSON Payload  
**Target Platform:** Windows 11, x64  
**Date:** 2026-10-28  

---

## 1. Overview & Transport Layer

Rexha's hybrid architecture connects the Python Application Orchestrator and the C++ Native Core across a dedicated, local, bidirectional Windows Named Pipe:

```
\\.\pipe\rexha_ipc
```

### 1.1 Security and Access Control
- **Pipe Mode:** `PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT`
- **Security Descriptor:** The named pipe is secured with a discretionary access control list (DACL) that grants access exclusively to the current user token SID (`GetCurrentUserSid`). Network callers and unprivileged local user accounts are denied connection.
- **Buffer Size:** 64 KB kernel buffer for input and output queues.
- **Maximum Frame Size:** 1,048,576 bytes (1 MB). Any incoming frame advertising a length greater than 1 MB is rejected, and the client connection is immediately severed to prevent memory exhaustion attacks.

---

## 2. Message Framing

Every transmission across the pipe uses a strict length-prefixed framing format:

```
+───────────────────────────+──────────────────────────────────────────────+
|  Length (4 Bytes, uint32) |              UTF-8 JSON Payload              |
|       Big-Endian          |             (Length bytes long)              |
+───────────────────────────+──────────────────────────────────────────────+
```

### 2.1 Reading Algorithm
1. Read exactly 4 bytes from the pipe.
2. Decode the length as an unsigned 32-bit big-endian integer:  
   `length = (b[0] << 24) | (b[1] << 16) | (b[2] << 8) | b[3]`.
3. If `length > 1048576`, log a security violation and close the pipe.
4. Read exactly `length` bytes from the pipe.
5. Parse the buffer as valid UTF-8 JSON.

---

## 3. Protocol Envelope Structure

All messages adhere to a standardized JSON schema.

### 3.1 Request Envelope (Client -> Native Core)
```json
{
  "protocol_version": 1,
  "request_id": "req-9b84a205-d142-4f36-a36c-95240bc1c7e9",
  "type": "system.get_status",
  "arguments": {}
}
```

- `protocol_version` (*integer*, required): Must equal `1`.
- `request_id` (*string*, required): Unique correlation UUID assigned by the caller.
- `type` (*string*, required): Registered action name (`namespace.action`).
- `arguments` (*object*, required): Strongly-typed parameters specific to the operation.

### 3.2 Response Envelope (Native Core -> Client)
```json
{
  "protocol_version": 1,
  "request_id": "req-9b84a205-d142-4f36-a36c-95240bc1c7e9",
  "type": "result",
  "success": true,
  "data": {
    "status": "online",
    "uptime_seconds": 142.5
  },
  "error": null
}
```

- `protocol_version` (*integer*, required): Must equal `1`.
- `request_id` (*string*, required): Matches the originating request's `request_id`.
- `type` (*string*, required): `"result"` for normal responses, `"event"` for unsolicited notifications.
- `success` (*boolean*, required): `true` if operation completed successfully, `false` otherwise.
- `data` (*object*, optional): Payload returned on success.
- `error` (*object*, optional): Error details on failure (`code`, `message`, `details`).

### 3.3 Event / Notification Envelope (Native Core -> Client)
Unsolicited asynchronous events (e.g., global hotkey trigger, process termination notification):
```json
{
  "protocol_version": 1,
  "request_id": "",
  "type": "event",
  "event_name": "hotkey.triggered",
  "data": {
    "hotkey_id": 101,
    "timestamp": 1730129400.124
  }
}
```

---

## 4. Error Code Specification

| Code | Name | Description |
| :--- | :--- | :--- |
| `1001` | `INVALID_FRAME` | Frame size exceeded 1MB or malformed byte stream. |
| `1002` | `INVALID_JSON` | Payload could not be parsed as UTF-8 JSON. |
| `1003` | `UNSUPPORTED_PROTOCOL` | `protocol_version` does not match server version. |
| `1004` | `MISSING_FIELD` | Required field (`request_id`, `type`, `arguments`) is missing. |
| `1005` | `UNKNOWN_ACTION` | The requested action `type` is not registered. |
| `1006` | `INVALID_ARGUMENTS` | Parameters failed schema validation. |
| `2001` | `OPERATION_TIMEOUT` | The operation exceeded its allocated execution timeout. |
| `2002` | `OPERATION_CANCELLED` | The operation was cancelled before completion. |
| `3001` | `HOTKEY_REGISTRATION_FAILED`| Failed to register hotkey (already claimed by another process). |
| `3002` | `WINDOW_NOT_FOUND` | Specified window handle (`HWND`) does not exist or has closed. |
| `3003` | `PROCESS_SPAWN_FAILED` | Windows `CreateProcessW` failed for the target executable. |
| `3004` | `ACCESS_DENIED` | Windows returned `ERROR_ACCESS_DENIED` (insufficient privileges). |
| `5000` | `INTERNAL_ERROR` | Unhandled native exception during operation execution. |

---

## 5. Registered Operations Catalog

### 5.1 System Subsystem
- **`system.ping`**
  - *Arguments:* `{}`
  - *Response:* `{"pong": true, "timestamp": 1730129400.0}`
- **`system.get_status`**
  - *Arguments:* `{}`
  - *Response:* `{"core_version": "0.1.0", "pid": 12844, "uptime_seconds": 45.2, "active_connections": 1}`
- **`system.get_metrics`**
  - *Arguments:* `{}`
  - *Response:* `{"cpu_percent": 1.2, "ram_total_mb": 32768, "ram_available_mb": 18450, "ram_used_percent": 43.7}`
- **`system.shutdown`**
  - *Arguments:* `{"reason": "User requested exit"}`
  - *Response:* `{"shutting_down": true}`

### 5.2 Hotkey Subsystem
- **`hotkey.register`**
  - *Arguments:* `{"id": 101, "modifiers": ["ctrl"], "vk": 32}` (Ctrl+Space)
  - *Response:* `{"registered": true, "id": 101}`
- **`hotkey.unregister`**
  - *Arguments:* `{"id": 101}`
  - *Response:* `{"unregistered": true}`

### 5.3 Window Subsystem
- **`window.get_foreground`**
  - *Arguments:* `{}`
  - *Response:* `{"hwnd": 65824, "title": "Visual Studio Code", "process_name": "Code.exe", "pid": 19488, "is_maximized": true}`
- **`window.list`**
  - *Arguments:* `{"visible_only": true, "filter_empty_titles": true}`
  - *Response:* `{"windows": [{"hwnd": 65824, "title": "Visual Studio Code", "pid": 19488}, ...]}`
- **`window.set_state`**
  - *Arguments:* `{"hwnd": 65824, "state": "minimize" | "maximize" | "restore" | "bring_to_front"}`
  - *Response:* `{"success": true}`
- **`window.close`**
  - *Arguments:* `{"hwnd": 65824, "graceful": true, "timeout_ms": 3000}`
  - *Response:* `{"closed": true, "method": "WM_CLOSE"}`

### 5.4 Process Subsystem
- **`process.launch`**
  - *Arguments:* `{"executable_path": "notepad.exe", "arguments": [], "working_directory": ""}`
  - *Response:* `{"pid": 23412, "launched": true}`
- **`process.get_status`**
  - *Arguments:* `{"pid": 23412}`
  - *Response:* `{"running": true, "exit_code": null, "cpu_percent": 0.0, "memory_mb": 14.2}`
- **`process.terminate`**
  - *Arguments:* `{"pid": 23412, "force": false}`
  - *Response:* `{"terminated": true}`

---

## 6. Lifecycle, Timeouts & Fault Recovery

1. **Heartbeat:** The Python orchestrator sends `system.ping` every 5,000 ms. If no response is received within 2,500 ms, the connection is flagged degraded.
2. **Crash Recovery:** If the C++ Native Core process exits unexpectedly, the Python orchestrator:
   - Detects the broken pipe `ERROR_BROKEN_PIPE (109)`.
   - Transitions internal native features to offline fallback mode.
   - Spawns a fresh `rexha_native_core.exe` process.
   - Reconnects with exponential backoff (100ms, 250ms, 500ms, 1000ms up to 3 attempts).
   - Re-registers active hotkeys and subscriptions.
3. **Graceful Shutdown:** The Python orchestrator sends `system.shutdown` with a 2-second timeout before terminating the child process.

