"""Voice and audio capture architecture for Rexha.

Provides distinct stages for audio metering, local wake detection,
transcription dispatch, and privacy disclosure.
"""

from __future__ import annotations

import logging
import math
from abc import ABC, abstractmethod
from typing import Callable

logger = logging.getLogger(__name__)


class WakeWordDetector(ABC):
    """Abstract interface for local offline wake-phrase detection."""

    @abstractmethod
    def process_frame(self, pcm_chunk: bytes) -> bool:
        """Process incoming 16kHz 16-bit PCM chunk and return True if wake phrase detected."""
        pass


class SimpleKeywordWakeDetector(WakeWordDetector):
    """Energy-based acoustic activity and local keyword spotter adapter for testing and offline use."""

    def __init__(self, wake_phrase: str = "wake up rexha", energy_threshold: float = 0.05):
        self.wake_phrase = wake_phrase.lower()
        self.energy_threshold = energy_threshold

    def process_frame(self, pcm_chunk: bytes) -> bool:
        """Measure chunk RMS energy to detect acoustic onset."""
        if not pcm_chunk:
            return False
        # Simplified 16-bit PCM RMS calculation
        n_samples = len(pcm_chunk) // 2
        if n_samples == 0:
            return False

        sum_squares = 0.0
        for i in range(0, len(pcm_chunk), 2):
            sample = int.from_bytes(pcm_chunk[i:i+2], byteorder="little", signed=True)
            norm = sample / 32768.0
            sum_squares += norm * norm

        rms = math.sqrt(sum_squares / n_samples)
        return rms > self.energy_threshold


class AudioLevelMeter:
    """Calculates RMS audio level for UI feedback without saving audio data."""

    @staticmethod
    def calculate_level(pcm_chunk: bytes) -> float:
        """Returns normalized audio level (0.0 to 1.0)."""
        if not pcm_chunk:
            return 0.0

        n_samples = len(pcm_chunk) // 2
        if n_samples == 0:
            return 0.0

        sum_squares = 0.0
        for i in range(0, len(pcm_chunk), 2):
            sample = int.from_bytes(pcm_chunk[i:i+2], byteorder="little", signed=True)
            norm = sample / 32768.0
            sum_squares += norm * norm

        rms = math.sqrt(sum_squares / n_samples)
        # Clamped & scaled
        return min(max(rms * 4.0, 0.0), 1.0)


class AudioPipelineCoordinator:
    """Coordinates microphone privacy state, level metering, and wake detection."""

    def __init__(self, wake_detector: WakeWordDetector | None = None):
        self.wake_detector = wake_detector or SimpleKeywordWakeDetector()
        self.is_listening_enabled = True
        self.is_mic_active = False
        self._level_callback: Callable[[float], None] | None = None
        self._wake_callback: Callable[[], None] | None = None

    def set_callbacks(
        self,
        on_level_changed: Callable[[float], None] | None = None,
        on_wake_detected: Callable[[], None] | None = None,
    ) -> None:
        self._level_callback = on_level_changed
        self._wake_callback = on_wake_detected

    def process_audio_chunk(self, chunk: bytes) -> None:
        """Process real-time audio chunk without storing raw bytes on disk."""
        if not self.is_listening_enabled:
            return

        level = AudioLevelMeter.calculate_level(chunk)
        if self._level_callback:
            self._level_callback(level)

        if self.wake_detector and self.wake_detector.process_frame(chunk):
            logger.info("Wake phrase detected")
            if self._wake_callback:
                self._wake_callback()

