# Rexha ⚡

> **A persistent, modular, voice-enabled Windows desktop assistant and personal computing platform.**

[![Platform](https://img.shields.io/badge/Platform-Windows%2011%20%2F%2010-0078D6.svg)](https://microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg)](https://python.org)
[![Native Core](https://img.shields.io/badge/Native%20Core-C%2B%2B20%20%2F%20Win32-blue.svg)]()
[![CMake](https://img.shields.io/badge/Build-CMake%203.25+-red.svg)](https://cmake.org)
[![GUI](https://img.shields.io/badge/GUI-PySide6%20Qt6-41CD52.svg)](https://qt.io)
[![Tests](https://img.shields.io/badge/Tests-80%20Passing-brightgreen.svg)]()

---

## What is Rexha?

**Rexha** (pronounced *"reck-zha"*) is a native Windows desktop assistant designed to operate your PC through spoken and typed natural language commands. Rather than living as an isolated chatbot in a web browser, Rexha lives natively on your desktop with a hybrid C++/Python architecture:

- **C++20 Native Core:** High-performance Windows systems service handling Win32 message pumps, zero-polling global hotkeys, window management (`EnumWindows`, `ShowWindow`, `WM_CLOSE`), process tracking, and system metrics (`GlobalMemoryStatusEx`, CPU).
- **Windows Named Pipe IPC:** Secure, length-prefixed binary JSON protocol (`\\.\pipe\rexha_ipc`) with Overlapped I/O connecting the native core and Python orchestrator.
- **Python Orchestrator:** Intent interpretation, pluggable LLM planning, 3-tier security policy enforcement, SQLite persistence, and PySide6 UI.
- **Persistent Industrial UI:** Always-on-top, draggable floating widget with custom geometric insignia, dark graphite surfaces (`#0B0D13`), and electric-lime status accents.

---

## Architecture Overview

```
+─────────────────────────────────────────────────────────────+
|                     PYTHON ORCHESTRATOR                     |
|  - Desktop UI (PySide6 Qt 6.8+)                             |
|  - 13-State Assistant State Machine & Typed Event Bus       |
|  - Deterministic Intent Parser + Pluggable LLM Planner      |
|  - 3-Tier Security Policy Engine (Safe, Standard, Tier 2)   |
|  - Action Execution Engine with Outcome Verification        |
|  - SQLite Persistence (WAL Mode)                            |
|  - NativeCoreClient (Overlapped Named Pipe IPC Client)      |
+──────────────────────────────┬──────────────────────────────+
                               │
            Windows Named Pipe: \\.\pipe\rexha_ipc
            Framing: 4-Byte Big-Endian Length + UTF-8 JSON
                               │
+──────────────────────────────▼──────────────────────────────+
|                      C++ NATIVE CORE                        |
|  - Win32 Named Pipe Server (Async Overlapped I/O)           |
|  - Global Hotkey Manager (Blocking GetMessageW pump)        |
|  - Window Manager (Enum, Foreground, State, WM_CLOSE)       |
|  - Process Supervisor (CreateProcessW, Job isolation)       |
|  - System Metrics Engine (RAM, CPU, PID, Uptime)            |
+─────────────────────────────────────────────────────────────+
```

---

## Quick Start (Windows 11 / 10 x64)

### 1. Prerequisites
- **Operating System:** Windows 11 or Windows 10 (64-bit).
- **Python:** Python 3.12+ (x64).
- **CMake:** CMake 3.25+.
- **C++ Compiler:** Visual Studio 2022 Community with C++ Desktop Development tools.

### 2. Automated Setup & Build

Clone the repository and run the automated PowerShell scripts:

```powershell
# 1. Setup Python dependencies and verify toolchains
.\scripts\setup.ps1

# 2. Build C++ Native Core (Release configuration via CMake)
.\scripts\build.ps1

# 3. Run full automated test suite (Native C++ + Python pytest)
.\scripts\test.ps1

# 4. Launch Rexha Desktop Assistant
.\scripts\run.ps1
```

---

## Development & Manual Commands

### Build Native Core Manually
```powershell
cmake -B native/build -S native -G "Visual Studio 17 2022" -A x64
cmake --build native/build --config Release
```

### Run Native C++ Tests
```powershell
.\native\build\Release\rexha_native_tests.exe
```

### Run Python Pytest Suite
```powershell
pytest
```

### Launch Flags
```powershell
# Standard hybrid launch (spawns native core automatically)
python -m rexha

# Fallback mode (runs pure Python without native core)
python -m rexha --no-native

# Custom database path
python -m rexha --db-path data/custom.sqlite
```

---

## Built-In Commands

When the interaction drawer is open (press `Ctrl+Space` or click the floating widget):

- `status` — Displays real-time assistant state, native core PID, RAM usage, CPU load, and foreground window.
- `windows` — Lists active top-level application windows.
- `open notepad` (or `launch <app>`) — Safely launches application with PID verification.
- `sleep` — Collapses assistant drawer back to compact floating pill.
- `help` — Shows available commands.
- `quit` — Gracefully terminates native core and desktop application.

---

## Architectural Documentation

- [HYBRID_ARCHITECTURE.md](file:///e:/Projects/Rexha/docs/HYBRID_ARCHITECTURE.md): Complete architectural audit and language boundaries (Sections A through Q).
- [IPC_PROTOCOL.md](file:///e:/Projects/Rexha/docs/IPC_PROTOCOL.md): Framing, JSON schema, error codes, and registered operations catalog.
- [PRODUCT_SPEC.md](file:///e:/Projects/Rexha/PRODUCT_SPEC.md): Full product vision and v0.1 requirements.
- [SECURITY.md](file:///e:/Projects/Rexha/SECURITY.md): 3-tier permission matrix, human confirmation, and path isolation.
- [IMPLEMENTATION_PLAN.md](file:///e:/Projects/Rexha/IMPLEMENTATION_PLAN.md): Milestone checklist and verification records.
