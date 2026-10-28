# Rexha — Implementation Roadmap & Status

This document tracks progress across all development milestones. It serves as the single source of truth for implementation status, acceptance criteria, and next steps.

---

## Progress Overview

| Milestone | Title | Status | Completion Target |
| :--- | :--- | :--- | :--- |
| **Milestone 0** | Repository & Architecture | **Implemented & Verified** | Complete |
| **Milestone 1** | Desktop Foundation | **Implemented & Tested** | Complete (16 tests passing) |
| **Milestone 2** | Voice Foundation | **Next Sprint** | v0.1 Voice Activation |
| **Milestone 3** | Basic Desktop Control | Planned | Following |
| **Milestone 4** | Files and Terminal | Planned | Following |
| **Milestone 5** | Camera Subsystem | Planned | Following |
| **Milestone 6** | Task Engine & Permissions | Planned | Following |
| **Milestone 7** | AI Interpretation | Planned | Following |
| **Milestone 8** | Workflows & Dev Tools | Planned | Following |
| **Milestone 9** | Hardening & Packaging | Planned | Release candidate |

---

## Detailed Milestone Checklist

### Milestone 0 — Repository & Architecture
- [x] Inspect existing workspace, Python 3.12 environment, and Windows system tools.
- [x] Initialize Git version control with `.gitignore`.
- [x] Author comprehensive [PRODUCT_SPEC.md](file:///e:/Projects/Rexha/PRODUCT_SPEC.md).
- [x] Author system architecture in [ARCHITECTURE.md](file:///e:/Projects/Rexha/ARCHITECTURE.md).
- [x] Author security, privacy, and permission policies in [SECURITY.md](file:///e:/Projects/Rexha/SECURITY.md).
- [x] Evaluate dependency compatibility (PySide6, audio, STT, win32).
- [x] Establish modular folder structure under `src/rexha/` and `tests/`.
- [x] Create project dependencies in `pyproject.toml` / `requirements.txt`.
- [x] Author [README.md](file:///e:/Projects/Rexha/README.md) and environment instructions.

### Milestone 1 — Desktop Foundation (Complete & Tested)
- [x] Create persistent SQLite database schema for application preferences, window geometry, and state.
- [x] Implement explicit Assistant State Machine with typed transitions (`STARTING`, `SLEEPING`, `WAKING`, `LISTENING`, etc.).
- [x] Implement frameless, draggable, always-on-top compact floating widget with visual status badge (`Sleeping...`).
- [x] Implement expanded interaction drawer/panel with state banner, conversation history view, and text input box.
- [x] Implement System Tray icon with context menu (Open, Mute Wake Listening, Settings, Quit).
- [x] Implement native Windows global shortcut (`Ctrl+Space`) via `ctypes.windll.user32` hotkey worker thread.
- [x] Implement clean application shutdown and resource cleanup handlers.
- [x] Implement settings repository to persist widget position and preferences across restarts.
- [x] Create automated unit tests for state machine, database settings, and UI components.
- [x] Verify acceptance criteria on Windows 11 host (16 automated tests passing).

### Milestone 2 — Voice Foundation
- [ ] Microphone device enumeration and selection with fallback detection.
- [ ] Local standby wake-word detection pipeline (evaluating OpenWakeWord / Vosk / Picovoice).
- [ ] Audio capture worker thread with live RMS audio level metering for UI.
- [ ] Voice Activity Detection (VAD) and silence timeout detection.
- [ ] Local Speech-to-Text engine integration (Faster-Whisper / Vosk / Windows STT).
- [ ] Live transcription emission and UI display.
- [ ] Voice state indicators in floating widget and interaction panel.
- [ ] Follow-up listening loop with configurable inactivity timer (default: 30s).
- [ ] Offline Text-to-Speech (TTS) integration using Windows SAPI5 (`pyttsx3`).
- [ ] Audio unit and mock tests.

### Milestone 3 — Basic Desktop Control
- [ ] Windows application discovery via Start Menu shortcuts and App Paths registry.
- [ ] Application launcher with process tracking and friendly alias support.
- [ ] Graceful application closure (sending `WM_CLOSE` before force termination).
- [ ] Windows state management (minimize, maximize, bring to front via `user32`).
- [ ] Windows Settings shortcuts (Display, Sound, Network, Apps).
- [ ] System awareness collector (CPU usage, RAM, disk space, battery status via `psutil`).
- [ ] Deterministic command intent parsing for system and app commands.
- [ ] Unit tests and verification checks for application control.

### Milestone 4 — Files and Terminal
- [ ] `PathGuard` sandboxed file manager restricted to configured roots.
- [ ] Note creator and append functionality (Markdown / text).
- [ ] Folder browser and File Explorer launcher for approved directories.
- [ ] Controlled terminal command executor with strict whitelist and argument sanitizer.
- [ ] Process stdout/stderr streaming capture with line limits and timeouts.
- [ ] Cancellation handle for running subprocesses.
- [ ] Comprehensive path traversal security tests.

### Milestone 5 — Camera Subsystem
- [ ] Camera hardware discovery and selection using OpenCV.
- [ ] On-demand camera preview widget in expanded panel.
- [ ] Snapshot capture with timestamped file saving to approved Pictures/Rexha directory.
- [ ] Visible camera active privacy indicator.
- [ ] Reliable camera hardware release on close or error.
- [ ] Camera error handling and mock tests.

### Milestone 6 — Task Engine & Permissions
- [ ] Structured action plan schema (Pydantic / dataclasses).
- [ ] Action registry and handler dispatcher.
- [ ] Policy engine with 3 permission tiers (Safe, Standard, Consequential).
- [ ] Interactive UI confirmation dialog for Consequential actions.
- [ ] Multi-step task runner with ordered step execution, progress events, and cancellation.
- [ ] Outcome verification engine (checking processes, file existence, exit codes).
- [ ] Task execution history logging in SQLite.
- [ ] Unit and integration tests for task lifecycle and cancellation.

### Milestone 7 — AI Interpretation
- [ ] Provider-agnostic LLM interface (OpenAI, Anthropic, Gemini, Ollama).
- [ ] Structured action plan generator prompt with JSON schema enforcement.
- [ ] Fallback to deterministic intent handlers when LLM is unavailable or unconfigured.
- [ ] Clarification dialogue generator for ambiguous instructions.
- [ ] Untrusted content sanitizer for web/file data ingested by LLM.

### Milestone 8 — Workflows & Developer Tools
- [ ] Workflow definitions: Coding Mode, Study Mode, Focus Mode.
- [ ] Developer helpers: project directory open in editor + terminal + git status.
- [ ] Safe browser URL opener for documentation and local development servers.
- [ ] Workflow storage and user customization in SQLite.

### Milestone 9 — Hardening & Packaging
- [ ] Accessibility features and keyboard navigation polish.
- [ ] Comprehensive error recovery and crash reporting.
- [ ] End-to-end test suite coverage.
- [ ] Windows packaging (PyInstaller / Inno Setup).
- [ ] Startup configuration (safe user-opt-in run on boot).
- [ ] Final user documentation and user manual.
