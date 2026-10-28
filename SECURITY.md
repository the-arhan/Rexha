# Rexha — Security, Privacy, and Permission Model

This document specifies the security policies, privacy guarantees, permission tiers, and verification requirements governing **Rexha**.

---

## 1. Core Principles

1. **Defense in Depth:** The natural-language interpreter and LLM are treated as untrusted generators. They may propose structured action plans, but they possess zero inherent authority to execute actions on the host operating system.
2. **Independent Permission Enforcement:** All permissions, file boundaries, and confirmation rules are evaluated by a dedicated policy subsystem completely outside of and decoupled from AI models.
3. **Explicit User Consent for Consequential Operations:** Any action that modifies, overwrites, or deletes files, launches non-whitelisted processes, or modifies system settings requires explicit human confirmation.
4. **Privacy by Default:** Standby voice audio is analyzed entirely on the local machine and never written to persistent storage or streamed to external cloud servers.

---

## 2. Permission Tiers

Every structured action capability belongs to one of three permission tiers:

| Tier | Name | Description | Policy Enforcement | Examples |
| :--- | :--- | :--- | :--- | :--- |
| **Tier 0** | **Read-Only / Safe** | Informational queries, safe UI state changes, opening benign standard system settings | Executed automatically without confirmation prompt | Query CPU/RAM, open Windows Sound Settings, list directory contents in Projects |
| **Tier 1** | **Standard Operations** | Opening user-installed applications, creating a new note file, opening a web URL | Executed automatically if destination path/application is approved in configuration | Launch VS Code, create a timestamped note in Notes directory |
| **Tier 2** | **Consequential Operations** | Modifying existing files, deleting files, running terminal scripts, terminating processes | **Mandatory user confirmation required in UI** before execution | Overwrite a file, execute `git clean`, terminate an active application process |

---

## 3. Path Security & Sandboxing

All file and directory operations must pass through the `PathGuard` validator:

1. **Approved Roots:** Operations are strictly constrained to pre-configured and user-approved directories:
   - Notes Directory (defaults to `%USERPROFILE%\Documents\Rexha\Notes`)
   - Projects Directory (defaults to `%USERPROFILE%\Projects` or user configured path)
   - Temporary Output Directory (`%USERPROFILE%\Documents\Rexha\Scratch`)
2. **Canonicalization & Traversal Prevention:**
   - Every path is resolved using `Path.resolve()` to resolve symbolic links and eliminate relative directory traversal segments (`..`).
   - The resolved target must start with an approved root path. Any target attempting to escape approved roots is immediately rejected with a `SecurityViolationError`.
3. **Protected Locations:**
   - System directories (`C:\Windows`, `C:\Program Files`, `AppData\Local\Temp`, etc.) are unconditionally locked against write or delete actions unless explicitly approved via elevated administrative user confirmation.
4. **Content Neutrality:**
   - Text read from files is treated strictly as plain text data. The system will never parse text inside user files as executable commands or instruction prompts.

---

## 4. Terminal & Process Execution Policies

1. **No Arbitrary Shell Passthrough:** Rexha does not expose `cmd.exe /c [untrusted_string]` or `powershell.exe -Command [untrusted_string]` to the interpreter.
2. **Command Whitelist:** Supported terminal commands are declared with explicit schemas:
   - e.g., `git status`, `git diff`, `python -m pytest`, `dir`, `echo`.
3. **Argument Validation:** Arguments are strictly sanitized. Flags containing command-chaining operators (`&`, `|`, `;`, `&&`, `||`, `` ` ``, `$()`) are blocked.
4. **Resource Constraints & Timeouts:**
   - Every subprocess has a mandatory timeout (default: 30 seconds).
   - Subprocess stdout and stderr buffers are capped to prevent memory exhaustion from runaway loops.
5. **Non-Elevation:** Rexha will never silently elevate privileges or call `runas` without clear user notification and the standard Windows UAC prompt.

---

## 5. Audio and Visual Privacy

1. **Local Wake-Word Processing:**
   - Wake-word scanning operates continuously on local CPU memory buffers.
   - Raw audio frames in standby mode are held in circular in-memory buffers and discarded immediately upon processing. No audio is ever recorded to disk during standby.
2. **Microphone Status Indicator:**
   - The UI provides an unmistakable visual indicator whenever the microphone is capturing speech (glowing active badge and live sound level meter).
   - A global toggle in the UI and tray permits immediate hardware listening mute.
3. **Camera Device Safeguards:**
   - The camera is deactivated by default.
   - Any camera usage requires an explicit, active user command.
   - While the camera is running, a prominent on-screen indicator and preview is displayed.
   - Camera handles are unconditionally released immediately after snapshot capture or when the user closes the preview.

---

## 6. Secret Management

1. **No Hardcoded Credentials:** Real API keys, tokens, or personal identifiers are strictly forbidden from source code and version control.
2. **Environment Isolation:** Local configuration keys are loaded from an untracked `.env` file or Windows Credential Manager.
3. **Log Scrubbing:** The logger automatically scrubs common secret formats (e.g., keys matching `sk-[a-zA-Z0-9]{32,}`, authorization headers, passwords) before writing to log files.
