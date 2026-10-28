"""Windows native global shortcut listener for Rexha."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import time
from typing import Callable
from PySide6.QtCore import QThread, Signal

logger = logging.getLogger(__name__)

# Windows Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

WM_HOTKEY = 0x0312
PM_REMOVE = 0x0001

VK_SPACE = 0x20
HOTKEY_ID = 101


class WindowsGlobalHotkeyThread(QThread):
    """Listens for system-wide Windows hotkey via native RegisterHotKey."""

    hotkey_triggered = Signal()
    registration_failed = Signal(str)

    def __init__(self, modifiers: int = MOD_CONTROL, vk: int = VK_SPACE):
        super().__init__()
        self.modifiers = modifiers
        self.vk = vk
        self._running = False
        self._user32 = ctypes.windll.user32

    def run(self) -> None:
        """Message pump thread for global hotkey."""
        self._running = True

        # Register hotkey for this thread's message queue
        success = self._user32.RegisterHotKey(
            None,
            HOTKEY_ID,
            self.modifiers | MOD_NOREPEAT,
            self.vk,
        )

        if not success:
            err = ctypes.GetLastError()
            msg = f"Failed to register global hotkey (Error code: {err}). Shortcut may already be in use."
            logger.warning(msg)
            self.registration_failed.emit(msg)
            return

        logger.info("Global hotkey registered successfully (Ctrl+Space)")

        msg = wintypes.MSG()
        while self._running:
            # Check for Windows messages without blocking indefinitely
            if self._user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    logger.debug("Global hotkey event received")
                    self.hotkey_triggered.emit()
                self._user32.TranslateMessage(ctypes.byref(msg))
                self._user32.DispatchMessageW(ctypes.byref(msg))
            else:
                self.msleep(25)  # 25ms polling to keep CPU consumption near 0%

        # Cleanup on thread exit
        self._user32.UnregisterHotKey(None, HOTKEY_ID)
        logger.info("Global hotkey unregistered cleanly")

    def stop(self) -> None:
        """Signal thread to stop and unregister."""
        self._running = False
        self.wait(1500)
