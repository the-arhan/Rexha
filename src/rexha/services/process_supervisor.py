"""Process supervisor for managing the Rexha Native Core background executable."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_BINARY_PATHS = [
    Path(__file__).resolve().parent.parent / "bin" / "rexha_native_core.exe",
    Path("native/build/Release/rexha_native_core.exe"),
    Path("native/build/bin/Release/rexha_native_core.exe"),
    Path("native/build/rexha_native_core.exe"),
]


class NativeProcessSupervisor:
    """Spawns, monitors, and gracefully terminates the C++ Native Core process."""

    def __init__(self, binary_path: Path | str | None = None, pipe_name: str = r"\\.\pipe\rexha_ipc"):
        self.binary_path = self._resolve_binary_path(binary_path)
        self.pipe_name = pipe_name
        self._process: subprocess.Popen | None = None

    def _resolve_binary_path(self, explicit_path: Path | str | None) -> Path | None:
        """Locate the native executable across candidate directories."""
        if explicit_path:
            p = Path(explicit_path)
            if p.is_file():
                return p.resolve()

        for candidate in DEFAULT_BINARY_PATHS:
            if candidate.is_file():
                return candidate.resolve()

        return None

    @property
    def is_available(self) -> bool:
        """Check if native binary exists on disk."""
        return self.binary_path is not None and self.binary_path.is_file()

    @property
    def is_running(self) -> bool:
        """Check if the supervised process is currently active."""
        if self._process is None:
            return False
        return self._process.poll() is None

    def start(self, timeout_sec: float = 3.0) -> bool:
        """Spawn the native core process."""
        if sys.platform != "win32":
            logger.info("Non-Windows host: skipping Native Core process spawn")
            return False

        if not self.is_available:
            logger.warning("Native Core executable not found; running in Python fallback mode")
            return False

        if self.is_running:
            logger.info("Native Core is already running (PID: %s)", self._process.pid)
            return True

        assert self.binary_path is not None
        cmd = [str(self.binary_path), "--pipe", self.pipe_name]
        logger.info("Spawning Native Core: %s", " ".join(cmd))

        try:
            # CREATE_NO_WINDOW = 0x08000000 to keep it cleanly in background without popping a console window
            flags = 0x08000000 if os.name == "nt" else 0
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
            )

            # Wait briefly to confirm it didn't immediately crash
            time.sleep(0.15)
            if self._process.poll() is not None:
                _, stderr = self._process.communicate()
                logger.error("Native Core terminated immediately: %s", stderr.decode("utf-8", errors="replace"))
                return False

            logger.info("Native Core successfully spawned (PID: %s)", self._process.pid)
            return True
        except Exception as e:
            logger.exception("Failed to spawn Native Core process: %s", e)
            return False

    def stop(self, timeout_sec: float = 2.0) -> None:
        """Terminate the supervised process cleanly."""
        if self._process is None or not self.is_running:
            return

        pid = self._process.pid
        logger.info("Terminating Native Core process (PID: %s)", pid)

        try:
            self._process.terminate()
            try:
                self._process.wait(timeout=timeout_sec)
            except subprocess.TimeoutExpired:
                logger.warning("Native Core did not exit within %ss; killing forcefully", timeout_sec)
                self._process.kill()
                self._process.wait(timeout=1.0)
        except Exception as e:
            logger.debug("Process termination notice: %s", e)
        finally:
            self._process = None
            logger.info("Native Core process stopped")
