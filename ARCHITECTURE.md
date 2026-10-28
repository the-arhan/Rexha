# Rexha — System Architecture

This document defines the high-level architecture, module boundaries, threading model, and data flow of **Rexha**.

---

## 1. Architectural Philosophy

Rexha is organized around strict separation of concerns, defensive security boundaries, and asynchronous UI isolation:

1. **GUI Isolation:** The PySide6 UI runs exclusively on the main Qt GUI thread. No voice recording, transcription inference, subprocess execution, or database I/O is permitted to block the main event loop.
2. **Explicit State Machine:** Assistant states are formal enum values managed by an observable state coordinator. State transitions are verified before being accepted.
3. **Deterministic Core Before AI:** Routine desktop commands are handled by fast, deterministic parsers and action handlers. The LLM is an optional higher-tier planner for complex or unfamiliar natural-language instructions, never an unrestricted execution engine.
4. **Independent Permission Enforcement:** The permission layer inspects structured action descriptors independently of the model or interpreter that generated them.
5. **Verified Execution:** Task execution requires verification hooks that independently inspect the Windows operating system state to confirm success.

---

## 2. Subsystem Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                                 USER INTERFACES                                   |
|   +---------------------------------------+  +--------------------------------+   |
|   | Compact Floating Widget (Always-on-top)|  | Expanded Interaction Panel     |   |
|   +---------------------------------------+  +--------------------------------+   |
|   +-------------------+  +--------------------+  +----------------------------+   |
|   | System Tray Menu  |  | Text Command Input |  | Native Hotkey (Ctrl+Space) |   |
|   +-------------------+  +--------------------+  +----------------------------+   |
+------------------------------------------^----------------------------------------+
                                           | Qt Signals / Slots
+------------------------------------------v----------------------------------------+
|                            ASSISTANT STATE COORDINATOR                            |
|        [STARTING -> SLEEPING -> WAKING -> LISTENING -> TRANSCRIBING -> ...]        |
+-------------------^----------------------^-----------------------^----------------+
                    |                      |                       |
+-------------------v-----+  +-------------v-----------+  +--------v----------------+
|     VOICE SUBSYSTEM     |  |   COMMAND INTERPRETER   |  |   STORAGE & CONFIG      |
|  - Mic Enumerator       |  |  - Deterministic Intent |  |  - SQLite Database      |
|  - Local Wake Detector  |  |    Registry             |  |  - Schema Migrations    |
|  - Audio Capture / VAD  |  |  - Optional LLM Planner |  |  - Settings Repository  |
|  - Speech-to-Text (STT) |  |  - Clarification Handler|  |  - Task & Audit Log     |
|  - Spoken TTS (SAPI5)   |  |  - Structured Action    |  |  - App Aliases          |
+-------------------------+  |    Generator            |  +-------------------------+
                             +-------------+-----------+
                                           | Structured Action Plan
                             +-------------v-----------+
                             |   POLICY & PERMISSIONS  |
                             |  - Path Sandboxing      |
                             |  - Shell Command Policy |
                             |  - Confirmation Manager |
                             +-------------+-----------+
                                           | Approved Actions
                             +-------------v-----------+
                             |      TASK EXECUTOR      |
                             |  - Step-by-Step Runner  |
                             |  - Timeout & Cancel     |
                             |  - Progress Broadcaster |
                             +-------------+-----------+
                                           |
                    +----------------------+----------------------+
                    |                                             |
         +----------v-----------+                      +----------v-----------+
         |     INTEGRATIONS     |                      |     VERIFICATION     |
         |  - Windows Apps      |                      |  - Process Detector  |
         |  - Terminal Runner   |                      |  - File System Check |
         |  - Files & Folders   |                      |  - Exit Code Check   |
         |  - System Awareness  |                      |  - State Comparator  |
         |  - Camera Device     |                      +----------------------+
         |  - Browser Launcher  |
         +----------------------+
```

---

## 3. Module Boundaries & Package Layout

Rexha code is organized in `src/rexha/` with modular packages:

```text
e:/Projects/Rexha/
├── assets/                  # Icons, sound effects, images
├── data/                    # Runtime databases, local cache
├── docs/                    # Detailed subsystem specifications
├── logs/                    # Application audit and execution logs
├── references/              # Research notes, engine benchmarks
├── scripts/                 # Development and packaging scripts
├── tests/                   # Automated unit, integration, and mock tests
└── src/
    └── rexha/
        ├── __init__.py
        ├── __main__.py      # CLI / Application entry point
        ├── core/            # Core state machine, signals, and event bus
        │   ├── state_machine.py
        │   ├── events.py
        │   └── context.py
        ├── ui/              # PySide6 desktop interface
        │   ├── floating_widget.py
        │   ├── interaction_panel.py
        │   ├── system_tray.py
        │   ├── components/  # Buttons, waveforms, badges, inputs
        │   └── theme.py     # Dark futuristic cyan/violet palette
        ├── voice/           # Voice activation and audio pipeline
        │   ├── audio_device.py
        │   ├── wake_detector.py
        │   ├── speech_to_text.py
        │   ├── voice_activity.py
        │   └── text_to_speech.py
        ├── interpreter/     # Intent extraction & plan construction
        │   ├── intent_parser.py
        │   ├── rules/       # Deterministic rule handlers
        │   ├── llm/         # Optional LLM planners
        │   └── action_plan.py
        ├── policy/          # Security, validation, and permissions
        │   ├── permissions.py
        │   ├── path_guard.py
        │   └── command_policy.py
        ├── executor/        # Action execution engine
        │   ├── task_executor.py
        │   ├── action_registry.py
        │   └── handlers/    # Action handlers for apps, files, shell, system
        ├── verification/    # Independent execution verification
        │   ├── process_verifier.py
        │   ├── file_verifier.py
        │   └── verifier.py
        ├── integrations/    # External interfaces
        │   ├── windows_apps.py
        │   ├── terminal.py
        │   ├── file_ops.py
        │   ├── system_info.py
        │   ├── camera.py
        │   └── browser.py
        └── storage/         # Database persistence
            ├── database.py
            ├── migrations.py
            └── repositories.py
```

---

## 4. Concurrency & Threading Model

1. **Qt Main Thread (GUI):**
   - Handles all widget rendering, animations, user keyboard/mouse events, and system tray interactions.
   - Never calls blocking OS functions (e.g., `subprocess.run(wait=True)`, `time.sleep()`, audio streaming loops).
2. **Audio Worker Thread (`QThread`):**
   - Continuously captures microphone input frames in a dedicated audio thread.
   - Runs streaming wake detection or buffers speech for transcription.
   - Emits Qt signals (`wake_word_detected`, `audio_level_changed`, `transcription_ready`).
3. **Execution Worker Thread Pool (`QThreadPool`):**
   - Tasks executed by the Task Executor run on background worker threads (`QRunnable`).
   - Dispatches step progress, verification checks, and final summaries via thread-safe Qt signals.
4. **HotKey Worker Thread:**
   - Dedicated Windows message pump loop for native `RegisterHotKey` calls, avoiding interference with Qt's own keyboard focus.

---

## 5. Security & Isolation

- **Zero Arbitrary Execution:** Incoming requests cannot execute unvalidated shell commands. The terminal executor only accepts approved commands and arguments validated against an allowlist policy.
- **Path Sandboxing:** File operations check target paths against resolved, canonical allowed roots (e.g., user's Notes directory, Projects directory). Path traversal attempts (`../`) are detected and rejected.
- **Destructive Operation Gates:** Overwrites, file removals, or critical process terminations trigger mandatory visual confirmation prompts in the UI.
- **Privacy By Design:** Standby microphone audio is never written to disk or sent outside the host machine.
