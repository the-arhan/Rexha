# Rexha ⚡

> **A persistent, voice-enabled, AI-assisted Windows desktop automation platform.**

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6.svg)](https://microsoft.com/windows)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB.svg)](https://python.org)
[![GUI](https://img.shields.io/badge/GUI-PySide6%20Qt6-41CD52.svg)](https://qt.io)
[![License](https://img.shields.io/badge/License-Proprietary%20%2F%20MIT-blue.svg)]()

---

## What is Rexha?

**Rexha** (pronounced *"reck-zha"*) is a native Windows desktop assistant designed to operate your PC through spoken and typed natural language commands. Rather than living as an isolated chatbot in a web browser, Rexha lives natively on your desktop as an always-on-top, compact floating widget that wakes up on voice activation or global hotkey, interprets tasks, requests confirmation for sensitive operations, executes multi-step workflows, and independently verifies the outcome.

---

## Key Features

- **Persistent Floating Widget:** Minimalist, draggable, always-on-top floating pill displaying assistant state (`Sleeping...`, `Listening...`, `Thinking...`).
- **Voice Activation (v0.1):** Standby local wake detection (*"Wake up, Rexha"*, *"Hey, Rexha"*), speech transcription, and silence detection.
- **Alternative Controls:** Native global hotkey (`Ctrl+Space`), interactive text command bar, and system tray menu.
- **Deterministic Desktop Automation:** Fast offline intent handlers for opening/closing applications, Windows Settings shortcuts, notes management, and system queries (CPU, RAM, disk).
- **Security & Sandboxing:** Independent 3-tier permission engine, path sandboxing (`PathGuard`), command execution allowlists, and human-in-the-loop confirmation for file overwrites or process termination.
- **Outcome Verification:** Confirms actual OS results (process running, window focused, file written) before reporting success.
- **Privacy by Default:** Standby audio remains 100% local; visual microphone indicators; zero secret logging.

---

## Quick Start (Windows)

### 1. Prerequisites
- **Operating System:** Windows 10 (Build 19041+) or Windows 11 (64-bit).
- **Python:** Python 3.12 or newer.

### 2. Environment Setup

Clone the repository and install dependencies:

```powershell
# Clone repository
git clone https://github.com/your-repo/rexha.git
cd rexha

# Create and activate virtual environment (recommended)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies and package in editable mode
pip install -r requirements.txt
pip install -e .
```

### 3. Launching Rexha

Run Rexha directly as a module:

```powershell
python -m rexha
```

- Rexha will launch as a compact pill in the bottom-right corner of your screen.
- Press **Ctrl+Space** or click the widget to open the command interaction panel.
- Enter a command or click the mic button to speak.

### 4. Running Automated Tests

```powershell
pytest
```

---

## Documentation

- 📐 [Architecture & Subsystem Design](file:///e:/Projects/Rexha/ARCHITECTURE.md)
- 📋 [Product Specification](file:///e:/Projects/Rexha/PRODUCT_SPEC.md)
- 🔒 [Security & Permission Model](file:///e:/Projects/Rexha/SECURITY.md)
- 🗺️ [Implementation Plan & Roadmap](file:///e:/Projects/Rexha/IMPLEMENTATION_PLAN.md)
- 🎙️ [Voice Subsystem Details](file:///e:/Projects/Rexha/docs/VOICE_SYSTEM.md)
- 🎨 [UI & Styling Guidelines](file:///e:/Projects/Rexha/docs/USER_INTERFACE.md)
- 🪟 [Windows Automation Internals](file:///e:/Projects/Rexha/docs/WINDOWS_AUTOMATION.md)
- 🧠 [AI Execution & Planning](file:///e:/Projects/Rexha/docs/AI_EXECUTION_SYSTEM.md)
- 🧪 [Testing Strategy](file:///e:/Projects/Rexha/docs/TESTING_STRATEGY.md)
