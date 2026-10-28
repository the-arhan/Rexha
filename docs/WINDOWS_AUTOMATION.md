# Rexha — Windows Automation & Control Specification

This document details the techniques, Windows APIs, and safety controls used by Rexha for desktop interaction, process management, and window operations.

---

## 1. Application Discovery & Launching

### 1.1 Discovery Sources
Rexha discovers installed applications using multiple non-intrusive Windows mechanisms:
1. **Start Menu Shortcuts (`.lnk` files):**
   - User Programs: `%APPDATA%\Microsoft\Windows\Start Menu\Programs`
   - Common Programs: `%ALLUSERSPROFILE%\Microsoft\Windows\Start Menu\Programs`
2. **Windows App Paths Registry:**
   - `HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths`
   - `HKEY_CURRENT_USER\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths`
3. **User Aliases:**
   - Configurable friendly names in SQLite (e.g., `"code"` -> `"C:\Users\...\Code.exe"`, `"browser"` -> `"msedge.exe"`).

### 1.2 Safe Launch Procedure
- Applications are launched using `subprocess.Popen` with `DETACHED_PROCESS` or `os.startfile` for registered Windows shell verbs.
- Once launched, the PID is recorded, and the verification engine watches for the target process or window handle to confirm successful startup before reporting completion.

---

## 2. Window Operations & Graceful Closure

### 2.1 Window Discovery & State
Using native Windows `user32.dll` via Python's `ctypes`:
- **EnumWindows:** Enumerate top-level visible windows.
- **GetWindowTextW & GetWindowThreadProcessId:** Identify window titles and associated PIDs.
- **ShowWindow:**
  - `SW_MINIMIZE (6)`: Minimize window.
  - `SW_RESTORE (9)`: Restore minimized window.
  - `SW_MAXIMIZE (3)`: Maximize window.
- **SetForegroundWindow & BringWindowToTop:** Focus target window.

### 2.2 Graceful Application Close
- Rexha never immediately force-kills an application unless explicitly requested by the user during a deadlock.
- First, Rexha posts `WM_CLOSE (0x0010)` to the application's top-level window using `user32.PostMessageW`.
- This allows applications with unsaved work (such as Notepad, Word, or IDEs) to prompt the user to save changes normally.
- If the application does not close within a configured grace period (e.g., 5 seconds), Rexha reports that the application is waiting on user input or asks for confirmation before terminating.

---

## 3. Windows Settings Integration

Rexha opens native Windows 10/11 Settings pages instantly via registered URI schemes:
- Sound Settings: `ms-settings:sound`
- Display Settings: `ms-settings:display`
- Network Settings: `ms-settings:network`
- Apps & Features: `ms-settings:appsfeatures`
- Task Manager: Launched directly via `taskmgr.exe`

---

## 4. Controlled Terminal Execution

### 4.1 Safety Architecture
Terminal commands are executed under strict sandboxing:
- **No Arbitrary Shell Injection:** Commands are executed as argument lists (`[executable, arg1, arg2]`), bypassing shell parsing unless explicitly required.
- **Configurable Timeouts:** Default 30-second timeout prevents orphaned hanging processes.
- **Output Capping:** Stdout and stderr are limited to the first 500 lines or 64 KB to avoid GUI memory bloat.
- **Cancellation Handle:** Every active terminal runner holds an atomic cancellation flag to terminate the process tree on user request.
