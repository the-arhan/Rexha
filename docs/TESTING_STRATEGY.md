# Rexha — Testing Strategy & Verification Procedures

This document details the automated testing framework, test suite structure, mock boundaries, and manual verification procedures for hardware and OS integrations.

---

## 1. Testing Philosophy

1. **No Unverified Claims:** Functionality is not labeled as implemented until validated by automated tests or verified manual tests.
2. **Defensive Isolation:** Automated tests must never modify real user files, terminate user applications, or execute dangerous shell commands on the host machine.
3. **Hardware Independence:** CI and headless test runs use mock adapters for audio capture, camera streams, and external LLM APIs.

---

## 2. Test Suite Structure

```text
tests/
├── conftest.py               # Shared fixtures, temporary SQLite db, mock bus
├── unit/
│   ├── test_state_machine.py # State machine transitions, invalid transitions
│   ├── test_storage.py       # SQLite migrations, settings repo, app aliases
│   ├── test_path_guard.py    # Path sandboxing, directory traversal attacks
│   ├── test_command_policy.py# Terminal command whitelist & argument sanitizing
│   ├── test_intent_parser.py # Deterministic intent parsing & regex matching
│   └── test_action_plan.py   # Schema validation of structured actions
├── integration/
│   ├── test_task_executor.py # Step-by-step task execution with mock handlers
│   └── test_verification.py  # Verification hooks (process, file check)
└── manual/
    └── CHECKLIST_V0_1.md     # Step-by-step manual test checklist
```

---

## 3. Manual Hardware Verification Checklist

### 3.1 Global Hotkey (`Ctrl+Space`)
1. Launch Rexha. Ensure widget displays in `SLEEPING` state.
2. Press `Ctrl+Space` anywhere on Windows (with browser or editor in focus).
3. Verify: Rexha smoothly expands its interaction panel and focuses the text command input.
4. Press `Escape` or click collapse. Verify Rexha returns to compact sleeping widget.

### 3.2 Floating Widget Drag & Dock
1. Click and drag the compact widget to any position on the desktop.
2. Release mouse button.
3. Close and relaunch Rexha.
4. Verify: The widget restores to the exact `(x, y)` coordinate where it was dropped.

### 3.3 Audio Level & Microphone
1. Open Rexha Settings panel.
2. Speak into microphone.
3. Verify: Live audio RMS meter fluctuates smoothly in response to voice.
4. Toggle "Mute Wake Listening" in tray.
5. Verify: Microphone state badge displays muted icon.
