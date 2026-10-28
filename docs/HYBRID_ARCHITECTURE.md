# Project Rexha — Hybrid Native Rearchitecture Audit & Decision Report

**Document Version:** 1.0.0  
**Target Platform:** Windows 11, x64  
**Date:** 2026-10-28  
**Author:** Principal Software Architect & Systems Engineering Team  

---

## Executive Summary

Project Rexha is transitioning from a pure-Python prototype (Milestones 0–1) into a production-grade, modular, native-capable desktop platform. This report provides an exhaustive audit of the existing codebase, defines the boundaries between C, C++, and Python, establishes the Inter-Process Communication (IPC) and execution safety policies, and outlines the incremental staged migration roadmap.

---

## A. Existing Architecture

The v0.1 baseline comprises a pure-Python application built with PySide6 (Qt 6.6+), SQLite, and Windows APIs invoked via `ctypes`. The runtime operates within a single Python process where the Qt event loop (`QApplication.exec()`) drives both UI rendering and application lifecycle.

```
+─────────────────────────────────────────────────────────────+
|                     RexhaApp (Python)                       |
|  +──────────────────+   +────────────────────────────────+  |
|  | AssistantState   |   |           EventBus             |  |
|  |     Machine      |   |        (In-Process PubSub)     |  |
|  +─────────┬────────+   +───────────────┬────────────────+  |
|            │                            │                   |
|            ▼                            ▼                   |
|  +───────────────────────────────────────────────────────+  |
|  |                    UICoordinator                      |  |
|  |  +─────────────────+  +────────────────────────────+  |  |
|  |  | FloatingWidget  |  |      InteractionPanel      |  |  |
|  |  | (Compact Pill)  |  |      (Expanded Drawer)     |  |  |
|  |  +─────────────────+  +────────────────────────────+  |  |
|  |  +─────────────────+  +────────────────────────────+  |  |
|  |  | RexhaSystemTray |  | WindowsGlobalHotkeyThread  |  |  |
|  |  | (QSystemTray)   |  | (ctypes PeekMessage loop)  |  |  |
|  |  +─────────────────+  +────────────────────────────+  |  |
|  +──────────────────────────────┬────────────────────────+  |
|                                 ▼                           |
|  +───────────────────────────────────────────────────────+  |
|  |                 DatabaseManager (SQLite)              |  |
|  |  - SettingsRepo  - AppAliasRepo  - TaskHistoryRepo    |  |
|  +───────────────────────────────────────────────────────+  |
+─────────────────────────────────────────────────────────────+
```

### Architectural Strengths of Baseline:
1. **Clean separation of concerns:** UI, state machine, event bus, and storage repositories have distinct boundaries.
2. **Explicit state machine:** Transitions are strictly validated against a directed graph (`LEGAL_TRANSITIONS`).
3. **Comprehensive tests:** 19 automated tests covering unit logic, storage, UI widgets, and package launching with 100% pass rate.
4. **Persistent configuration:** SQLite stores window geometry, preferences, and task history with migration versioning.

### Architectural Bottlenecks & Limitations of Pure Python:
1. **Windows System & Message Hooking via `ctypes`:** Global hotkey registration uses a polling `PeekMessageW` loop sleeping 25ms inside a Python `QThread`. This wastes CPU cycles, risks GIL contention, and lacks robustness against thread suspension.
2. **Window & Process Management:** Performing window enumeration, foreground tracking, process creation tree monitoring, and graceful `WM_CLOSE` handling via Python `ctypes` is fragile, non-type-safe, and lacks atomic cancellation guarantees.
3. **Lack of Process Isolation:** A crash or native fault in audio capture, Windows API calls, or C extensions terminates the entire Python UI and assistant process.
4. **Long-running Service Demands:** As Rexha adds background wake-word listening, system event monitoring, and window tracking, running entirely inside an interpreted Python GUI process degrades battery life, memory footprint, and responsiveness.

---

## B. Existing Module Inventory

| Module Path | Primary Responsibility | Lines of Code | Assessment |
| :--- | :--- | :--- | :--- |
| `src/rexha/__init__.py` | Package version and metadata | 7 | Retain. |
| `src/rexha/__main__.py` | CLI entry point and path bootstrap | 21 | Refactor to support native core coordination and CLI flags. |
| `src/rexha/app.py` | Application lifecycle orchestrator | 85 | Refactor to manage native core lifecycle alongside Qt GUI. |
| `src/rexha/core/state_machine.py`| Thread-safe 13-state coordinator | 217 | Retain & harden. Core state model remains in Python orchestrator. |
| `src/rexha/core/events.py` | Strongly-typed dataclass event bus | 106 | Retain & expand with IPC bridge events. |
| `src/rexha/storage/database.py` | SQLite connection, PRAGMA, WAL mode | 68 | Retain. Serves as single source of truth for persistent state. |
| `src/rexha/storage/migrations.py`| Schema versioning and DDL execution | 81 | Retain. |
| `src/rexha/storage/repositories.py`| Settings, AppAliases, TaskHistory | 180 | Retain. |
| `src/rexha/ui/theme.py` | Design tokens, color palette, QSS | 190 | Refactor to align with industrial graphite & electric-green visual identity. |
| `src/rexha/ui/floating_widget.py`| Frameless, draggable compact widget | 194 | Retain & refine visual style. |
| `src/rexha/ui/interaction_panel.py`| Expanded drawer with history & input | 241 | Retain & refine visual style and action confirmation dialogs. |
| `src/rexha/ui/system_tray.py` | QSystemTrayIcon with context menu | 84 | Retain. |
| `src/rexha/ui/coordinator.py` | Signal wiring and layout management | 272 | Refactor to route system actions through Native Core client. |
| `src/rexha/ui/hotkey.py` | `ctypes` global hotkey thread | 81 | **Replace.** Delegate to C++ Native Core Windows message pump. |

---

## C. Current Application Entry Point and Launch Behavior

The existing entry point is `src/rexha/__main__.py::main()`.
- Resolves `src` path into `sys.path` to allow execution as `python -m rexha` or direct execution.
- Instantiates `RexhaApp(db_path=DEFAULT_DB_FILE)`.
- `RexhaApp` initializes logging, `QApplication`, `AssistantStateMachine(STARTING)`, `EventBus`, `DatabaseManager`, and `UICoordinator`.
- Installs OS signal handlers (`SIGINT`, `SIGTERM`).
- Calls `RexhaApp.run()` which triggers `ui_coordinator.start()`, transitions state to `SLEEPING`, shows the floating widget and system tray, starts the hotkey thread, and invokes `qapp.exec()`.
- On exit, invokes `shutdown()` closing database connections and releasing UI.

---

## D. Current Python Packaging and Import Configuration

- Configuration defined in `pyproject.toml` with `setuptools>=61.0`.
- Package declared as `rexha` under `src/`.
- Entry point declared as `rexha = "rexha.__main__:main"`.
- Pytest configured with `pythonpath = ["src", "."]`.
- Packaging is standard and functional; however, it lacks native CMake build triggers, binary artifact placement, and packaging for bundled native binaries.

---

## E. Existing UI Architecture

The current UI is implemented using **PySide6 (Qt for Python 6.6+)**:
1. **`FloatingWidget`:** Frameless `Qt.Tool | Qt.WindowStaysOnTopHint` widget (160x56 px) displaying the glowing state dot, REXHA typography, collapse/expand toggle, status label, and a 2px audio level meter. Supports mouse drag-repositioning clamped to the active screen boundary.
2. **`InteractionPanel`:** Frameless drawer (400x520 px) aligned dynamically above the floating widget. Contains header bar with state badge and close button, scrollable conversation history with formatted `MessageCard` items, confirmation prompt banner for tier-2 actions, and command input bar with microphone toggle and send button.
3. **`RexhaSystemTray`:** Standard Windows notification tray icon with menu actions ("Open Rexha", "Mute Wake Listening", "Settings", "Quit") and balloon notification support.
4. **`UICoordinator`:** QObject centralizing signal routing between widgets, persistent storage (widget position persistence), state machine transitions, follow-up inactivity timer (30s), and basic text command evaluation.

---

## F. Current State Machine and Event System

- **States (13):** `STARTING`, `SLEEPING`, `WAKING`, `LISTENING`, `TRANSCRIBING`, `THINKING`, `AWAITING_CLARIFICATION`, `AWAITING_CONFIRMATION`, `EXECUTING`, `REPORTING`, `FOLLOW_UP`, `ERROR`, `STOPPING`.
- **Validation:** Enforced via `LEGAL_TRANSITIONS` directed graph. Attempted illegal transitions raise `InvalidStateTransitionError`.
- **Thread Safety:** Protected via `threading.RLock`. Listeners are invoked outside the lock to eliminate re-entrant deadlocks.
- **Event Bus:** In-process publish-subscribe system with strongly-typed dataclasses (`StateChangedEvent`, `AudioLevelEvent`, `TranscriptionEvent`, `CommandSubmittedEvent`, `TaskProgressEvent`, `NotificationEvent`).

---

## G. Existing Persistence and Database Schema

- SQLite database located at `data/rexha.sqlite` with WAL mode enabled (`PRAGMA journal_mode = WAL; PRAGMA synchronous = NORMAL; PRAGMA foreign_keys = ON;`).
- **Tables:**
  - `schema_version`: Version tracking (`version INTEGER PRIMARY KEY, applied_at TIMESTAMP`).
  - `settings`: Key-value JSON store (`key TEXT PRIMARY KEY, value TEXT NOT NULL, updated_at TIMESTAMP`).
  - `app_aliases`: Mapping friendly names to paths (`alias TEXT PRIMARY KEY, target_path TEXT NOT NULL, description TEXT, created_at TIMESTAMP`).
  - `task_history`: Audit trail for multi-step tasks (`id TEXT PRIMARY KEY, task_description TEXT, status TEXT, total_steps INTEGER, completed_steps INTEGER, started_at TIMESTAMP, completed_at TIMESTAMP, result_summary TEXT, error_message TEXT`).
  - `audit_log`: Security and operation logs (`id INTEGER PRIMARY KEY AUTOINCREMENT, event_type TEXT, action_type TEXT, details TEXT, severity TEXT, timestamp TIMESTAMP`).

---

## H. Existing Execution and Permission Boundaries

- Milestone 1 implements a rudimentary in-memory command matcher (`_handle_basic_command`) handling `sleep`, `status`, `help`, and `quit`.
- Milestone 6 specifications establish a 3-tier security model:
  - **Tier 0 (Safe):** Read-only system queries, window status, settings retrieval. Automatically approved.
  - **Tier 1 (Standard):** Application launch, window minimize/restore, note creation in approved folders. Executed with user awareness.
  - **Tier 2 (Consequential):** Destructive file writes/deletions, process termination, terminal execution, system modifications. Requires explicit interactive confirmation.
- The UI contains an interactive `confirm_frame` banner ready to wire to Tier 2 action verification.

---

## I. Current Dependencies and Their Actual Availability

### Installed & Verified in Active Environment:
- Python 3.12.6 (x64)
- PySide6 6.8.0.2 (Qt 6.8.0)
- psutil 6.1.0
- pydantic 2.10.2
- pytest 9.1.1
- CMake 4.4.4 (`C:\Program Files\CMake\bin\cmake.exe`)
- MSVC C++ Compiler / Toolset (Visual Studio 2022 Community at `C:\Program Files\Microsoft Visual Studio\2022\Community`)
- GCC / UCRT64 (`C:\msys64\ucrt64\bin\gcc.exe`)

---

## J. Recommended Language for Each Subsystem

| Subsystem | Target Language | Justification |
| :--- | :--- | :--- |
| **Native Windows Core & Service** | **C++ (C++20)** | Direct access to Win32 SDK (`user32`, `kernel32`, `psapi`, `dwmapi`). Robust RAII handle wrappers (`HANDLE`, `HWND`, `HHOOK`). Zero-overhead message pump. Real-time window and process monitoring without GIL overhead. |
| **IPC Transport Layer** | **C++ / Python** | C++ implements the high-performance Windows Named Pipe server (`\\.\pipe\rexha_ipc`). Python implements the client connector with JSON framing, async dispatch, and auto-reconnect. |
| **Global Hotkey Manager** | **C++ (C++20)** | Native message pump (`GetMessageW` with thread-id dispatch) eliminates Python `ctypes` polling loops and CPU waste. |
| **Process & Window Automation** | **C++ (C++20)** | High-performance window enumeration (`EnumWindows`), foreground tracking, window state manipulation, graceful `WM_CLOSE` delivery, and process tree inspection. |
| **Audio Capture & Wake Detection** | **C / C++ / Python** | Audio capture and low-level DSP (RMS energy, ring buffers) benefit from C/C++ native audio backends (WASAPI / PortAudio). Wake-word model inference (ONNX / Vosk) and STT orchestrate cleanly in Python. |
| **AI Orchestration & Planning** | **Python (3.12)** | Rapidly evolving LLM provider adapters (OpenAI, Gemini, Claude, Ollama), structured JSON schema validation (Pydantic), multi-step workflow logic, prompt templates. |
| **Desktop User Interface** | **Python (PySide6)** | PySide6 provides a responsive, native-looking Qt desktop interface with rapid iteration and complete styling control. Retaining PySide6 preserves all existing verified UI code and allows immediate visual polish. |
| **Persistent Storage & Repositories** | **Python / SQLite** | SQLite with WAL mode provides single-file persistence, atomic transactions, and zero setup. Python SQLite driver handles thread safety cleanly. |

---

## K. Modules to Retain Without Changes

1. `src/rexha/storage/database.py`: Fully functional SQLite manager with WAL mode and foreign key constraints.
2. `src/rexha/storage/migrations.py`: Robust versioned migration engine.
3. `src/rexha/storage/repositories.py`: Complete repositories for settings, aliases, and task history.
4. `src/rexha/core/state_machine.py`: Rock-solid state transition coordinator.
5. `src/rexha/core/events.py`: Typed event bus dataclasses.

---

## L. Modules to Refactor

1. `src/rexha/ui/theme.py`: Update palette to strict industrial graphite (`#0B0D13`, `#12151F`, `#181C2A`) and electric-green/lime (`#10E599` / `#22C55E`) accent tokens.
2. `src/rexha/ui/floating_widget.py`: Update stylesheet, styling, and ensure responsive state feedback.
3. `src/rexha/ui/interaction_panel.py`: Modernize visual hierarchy, card rendering, and wire confirmation flows.
4. `src/rexha/ui/coordinator.py`: Replace direct `ctypes` calls with IPC client calls to the Native Core.
5. `src/rexha/app.py`: Supervise native core process lifecycle (spawn, monitor, health check, graceful terminate).
6. `src/rexha/__main__.py`: Support flags (`--native-core-path`, `--no-native`, `--dev`).

---

## M. Modules that Genuinely Benefit from C or C++

### 1. Global Hotkey & Windows Message Pump (`native/src/windows/hotkey_manager.cpp`)
- **Existing Problem:** `src/rexha/ui/hotkey.py` registers `RegisterHotKey` via Python `ctypes` and polls `PeekMessageW` with a 25ms sleep in a loop.
- **Why C++ is Superior:** A native thread executes a blocking `GetMessageW` loop waiting for system messages with 0% CPU consumption while idle. Native RAII guarantees hotkey unregistration even on unhandled crash.
- **Interface:** Exposes registration, unregistration, and hotkey trigger events over the IPC pipe.

### 2. Window Enumeration, Metadata & State Control (`native/src/windows/window_manager.cpp`)
- **Existing Problem:** Enumerating windows, retrieving process IDs, window titles, class names, and z-order via `ctypes` requires dozens of manual Win32 API struct definitions and marshaling.
- **Why C++ is Superior:** Direct Win32 C++ access to `EnumWindows`, `GetWindowTextW`, `GetWindowThreadProcessId`, `IsWindowVisible`, `GetForegroundWindow`, `SetForegroundWindow`, `ShowWindow`, and `PostMessageW(..., WM_CLOSE)`.
- **Interface:** JSON-RPC operations: `window.list`, `window.get_foreground`, `window.set_state`, `window.close`.

### 3. Application Launcher & Process Supervisor (`native/src/process/process_manager.cpp`)
- **Existing Problem:** Tracking child processes, detecting exit codes, and terminating process trees cleanly on Windows requires complex Win32 Job Object manipulation.
- **Why C++ is Superior:** Native Win32 `CreateProcessW`, Job Objects (`CreateJobObjectW`, `AssignProcessToJobObject`), and `TerminateJobObject` provide atomic process isolation and cancellation.
- **Interface:** JSON-RPC operations: `process.launch`, `process.get_status`, `process.terminate`, `system.get_metrics`.

### 4. Native Core IPC Server (`native/src/core/ipc_server.cpp`)
- **Implementation:** Windows Named Pipe server (`\\.\pipe\rexha_ipc`) using overlapped asynchronous I/O and security descriptors restricting access to the current user session.
- **Interface:** Length-prefixed JSON protocol with request IDs, structured error codes, and heartbeats.

---

## N. Proposed Communication Boundaries

```
+─────────────────────────────────────────────────────────────+
|                     PYTHON ORCHESTRATOR                     |
|  - UI (PySide6)                                             |
|  - State Machine & Event Bus                                |
|  - Task Planner & Policy Engine                             |
|  - SQLite Persistence                                       |
|  - NativeCoreClient (Named Pipe Client)                     |
+──────────────────────────────┬──────────────────────────────+
                               │
            Windows Named Pipe: \\.\pipe\rexha_ipc
            Framing: 4-byte Big-Endian Length + UTF-8 JSON
                               │
+──────────────────────────────▼──────────────────────────────+
|                      C++ NATIVE CORE                        |
|  - Named Pipe Server (Async Overlapped I/O)                 |
|  - Windows Global Hotkey Manager (Native Message Pump)      |
|  - Window Manager (Enum, Focus, State, WM_CLOSE)            |
|  - Process Supervisor (CreateProcess, Job Objects)          |
|  - System Metrics Engine (GlobalMemoryStatusEx, CPU)        |
+─────────────────────────────────────────────────────────────+
```

---

## O. Build and Packaging Strategy

- **Build Tool:** CMake 3.25+ configuring MSVC C++20 (`Visual Studio 17 2022`).
- **Native Target:** `native/CMakeLists.txt` builds `rexha_native_core.exe` (the native service) and `rexha_native_tests.exe` (native unit test suite).
- **Output Directory:** Binaries output to `native/build/bin/Release` (or `Debug`), copied/linked to `src/rexha/bin/` for runtime discovery by Python.
- **Automation Scripts:**
  - `scripts/setup.ps1`: Initializes Python venv, installs dependencies, verifies CMake and MSVC.
  - `scripts/build.ps1`: Configures and compiles CMake native core in Release mode.
  - `scripts/test.ps1`: Executes both `pytest` test suite and native C++ test suite.
  - `scripts/run.ps1`: Launches the hybrid application.

---

## P. Migration Risks and Mitigation

| Risk | Impact | Mitigation Strategy |
| :--- | :--- | :--- |
| **Named Pipe connection failure / crash** | UI cannot control windows or hotkeys | Python `NativeCoreClient` implements automatic process spawning, reconnect with exponential backoff, and fallback to mock/in-process modes for unit testing. |
| **IPC security vulnerability** | Unprivileged processes send commands | Restrict named pipe security descriptor to the current user SID (`PSECURITY_DESCRIPTOR`). Reject requests exceeding maximum frame size (1 MB). |
| **Build toolchain mismatch** | Build fails on machines without VS 2022 | Support both MSVC and MinGW/UCRT GCC in CMake; detect compiler via PowerShell scripts. Provide fallback stub mode when native binary is absent. |
| **UI freezing during IPC calls** | Widget stutters during window enumeration | IPC client runs requests asynchronously on a background worker thread with `QObject` signal responses. |

---

## Q. Test and Acceptance Criteria

1. **Native Unit Tests:** C++ unit test suite validates IPC framing, JSON parser, window manager data structures, and process supervisor logic.
2. **Python Unit Tests:** Pytest suite passes all 19 baseline tests + new tests for IPC client, action executor, and policy guard.
3. **Integration Tests:** End-to-end test spawns native core, connects IPC client, registers hotkey, queries system status, enumerates windows, and shuts down cleanly.
4. **Security Tests:** Validates rejection of malformed JSON, oversized payloads, invalid action names, and unauthorized directory path traversals.
5. **No Regressions:** Application remains launchable via `python -m rexha` and `scripts/run.ps1`.

