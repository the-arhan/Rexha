# Rexha — Product Specification

**Product Name:** Rexha  
**Pronunciation:** "reck-zha"  
**Platform:** Windows 10 / Windows 11 (64-bit Desktop)  
**Primary Language:** Python 3.12+  
**Primary GUI Framework:** PySide6 (Qt 6)  
**Current Target Version:** v0.1-alpha  

---

## 1. Product Vision

Rexha is a persistent, voice-enabled, AI-assisted personal Windows desktop automation platform. Unlike conventional browser-based chatbots or disposable prototypes, Rexha is a genuine native desktop resident designed to accept spoken or typed natural-language instructions, operate supported parts of Windows, execute multi-step tasks safely, verify outcomes, communicate progress, and remain quietly available in the background.

Rexha starts as a reliable desktop controller and expands modularly into developer workflows, study assistance, research automation, electronics project support, and multi-step task planning.

---

## 2. Core User Experience & Interaction Loop

### 2.1 The Persistent Floating Widget
- **Compact Resting State:** Rexha rests as a compact, frameless, semi-transparent, always-on-top desktop pill/widget displaying:
  ```text
  REXHA
  Sleeping...
  ```
- **Non-Intrusive:** Occupies minimal screen area, positionable anywhere on screen with drag-and-drop, and remembers its screen coordinates across restarts.
- **Visual State Indicator:** Distinct visual indicators (glow accents, status badges, microphone activity icons) reflecting current state.

### 2.2 Activation Methods
1. **Voice Wake Phrase:**
   - Standby local wake detection triggers on configurable phrases:
     - *"Wake up, Rexha"*
     - *"Hey, Rexha"*
     - *"Rexha, [command]"*
2. **Global Keyboard Shortcut:**
   - System-wide shortcut (`Ctrl+Space` by default), registered via native Windows hotkey API without requiring administrative elevation.
3. **Widget Click:**
   - Direct click on the compact widget immediately activates the assistant.
4. **System Tray:**
   - Tray icon context menu provides: *Open Interaction Panel*, *Mute/Unmute Wake Listening*, *Settings*, and *Quit Rexha*.

### 2.3 The Full Interaction Loop
1. **Startup:** Rexha boots, initializes state, checks configuration, loads SQLite storage, registers global hotkeys, starts background wake-detection thread, and displays the compact resting widget in `SLEEPING` state.
2. **Wake Detection:** When the user utters the wake phrase or triggers the hotkey, the widget smoothly expands into the interaction panel, transitioning to `WAKING` then `LISTENING`.
3. **Command Capture:** The voice subsystem records the spoken command with silence detection (VAD).
4. **Transcription:** Audio is transcribed locally (or via configured speech provider) and displayed live in the panel (`TRANSCRIBING`).
5. **Interpretation:** The command interpreter transforms the request into a structured action plan (`THINKING`). Routine commands match deterministic intent handlers; complex requests optionally route to a configured LLM planner.
6. **Clarification:** If a request is ambiguous or missing critical arguments, Rexha prompts the user with clarifying options (`AWAITING_CLARIFICATION`).
7. **Permission & Confirmation:** If an action modifies files, launches shell processes, or performs consequential system operations, Rexha halts and requests user confirmation (`AWAITING_CONFIRMATION`).
8. **Execution & Progress:** Approved actions execute through the task executor with live step-by-step progress reported in the GUI (`EXECUTING`).
9. **Outcome Verification:** The verification engine independently checks that the expected outcome occurred (e.g., verifying process existence, file creation, exit codes).
10. **Reporting:** Rexha delivers a clear visual and optional spoken report summarizing what succeeded or failed (`REPORTING`).
11. **Follow-Up State:** Rexha enters `FOLLOW_UP` state with a configurable timer (default: 30 seconds). The user can issue another command immediately without repeating the wake phrase.
12. **Return to Sleep:** If the follow-up timer expires without input, Rexha gracefully collapses back to the compact `SLEEPING` widget.

---

## 3. Explicit Assistant State Machine

The assistant state is governed by a strictly validated state machine:

| State | Description | Allowed Next States |
| :--- | :--- | :--- |
| `STARTING` | Initializing subsystems, database, and UI | `SLEEPING`, `ERROR` |
| `SLEEPING` | Compact widget displayed; low-power wake listening active | `WAKING`, `LISTENING`, `STOPPING` |
| `WAKING` | Wake word recognized; UI expanding, audio chime/visual cue | `LISTENING`, `ERROR` |
| `LISTENING` | Recording user spoken command; mic indicator active | `TRANSCRIBING`, `SLEEPING`, `ERROR` |
| `TRANSCRIBING` | Converting voice capture to text | `THINKING`, `FOLLOW_UP`, `ERROR` |
| `THINKING` | Resolving intent and generating structured action plan | `AWAITING_CLARIFICATION`, `AWAITING_CONFIRMATION`, `EXECUTING`, `REPORTING`, `ERROR` |
| `AWAITING_CLARIFICATION`| Displaying question and awaiting user input | `THINKING`, `FOLLOW_UP`, `SLEEPING` |
| `AWAITING_CONFIRMATION` | Prompting user approval for consequential action | `EXECUTING`, `FOLLOW_UP`, `SLEEPING` |
| `EXECUTING` | Running approved task steps via Task Executor | `REPORTING`, `ERROR`, `STOPPING` |
| `REPORTING` | Presenting result to user visually and via optional TTS | `FOLLOW_UP`, `SLEEPING` |
| `FOLLOW_UP` | Waiting for subsequent command within timeout window | `LISTENING`, `THINKING`, `SLEEPING` |
| `ERROR` | Handling failure, showing actionable message | `FOLLOW_UP`, `SLEEPING` |
| `STOPPING` | Releasing devices, saving state, exiting cleanly | *(Terminal)* |

---

## 4. Capability Matrix

### Phase 1 (Core Foundations — v0.1)
- Persistent floating widget + expanded interaction drawer in PySide6.
- System tray with status, toggle wake listening, settings, quit.
- Global hotkey (`Ctrl+Space`) + text input bar + clipboard paste.
- SQLite-backed settings, task history, and application aliases.
- Microphone device selector & audio level meter.
- Standby local wake-word detection & speech-to-text.
- Deterministic command interpreter for desktop actions:
  - Application launcher & graceful closer.
  - Windows Settings page shortcuts.
  - Basic file/folder creation, reading notes, and opening in Explorer.
  - Safe terminal command runner with output capture, timeouts, and cancellation.
  - System status inspector (CPU, RAM, disk, battery).
- Action confirmation dialog for consequential tasks.
- Spoken responses via local Windows SAPI5 (pyttsx3) with toggle.

### Phase 2 (Developer & Workflow Assistant — v0.2)
- Multi-step structured task engine with rollback/recovery.
- Camera subsystem: live preview, snapshot capture, safe folder storage.
- Project workspace management: open code editor, terminal in folder, git status.
- Named workflows: Coding Mode, Study Mode, Focus Mode.
- Provider-independent LLM planning (OpenAI, Gemini, Anthropic, Ollama).

### Phase 3 (Advanced Automation & Browser Control — v0.3+)
- Controlled browser automation (URL navigation, documentation retrieval).
- Electronics workbench support (serial port monitor, schematic directory shortcut).
- Voice model fine-tuning and offline custom wake word training.

---

## 5. Non-Functional Requirements

- **Responsiveness:** GUI must never freeze during background audio capture, model inference, subprocess execution, or camera streaming (all offloaded to worker threads).
- **Startup Time:** Cold start to `SLEEPING` widget in under 2.5 seconds on standard SSD hardware.
- **Resource Footprint:** Resting background RAM < 120 MB; resting CPU < 1.5% while standby wake listening is active.
- **Execution Safety:** Zero arbitrary remote shell execution; mandatory structured schema validation for every executed action; path traversal restrictions on all file operations.
- **Privacy:** Standby audio processed strictly locally; microphone active state prominently displayed; no raw audio persisted to disk unless user explicitly runs diagnostic recording.
