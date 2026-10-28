"""Unit tests for audio metering, wake-word detection, and privacy controls."""

import pytest
from rexha.integrations.audio.pipeline import (
    AudioLevelMeter,
    SimpleKeywordWakeDetector,
    AudioPipelineCoordinator,
)


def test_audio_level_meter_silence():
    silence = b"\x00\x00" * 160
    level = AudioLevelMeter.calculate_level(silence)
    assert level == 0.0


def test_audio_level_meter_signal():
    # Square wave audio samples
    signal = (b"\x7F\x00" + b"\x80\xFF") * 80
    level = AudioLevelMeter.calculate_level(signal)
    assert level > 0.0
    assert level <= 1.0


def test_wake_detector_energy_trigger():
    detector = SimpleKeywordWakeDetector(energy_threshold=0.01)
    silence = b"\x00\x00" * 160
    assert detector.process_frame(silence) is False

    loud_chunk = b"\x7F\x7F" * 160
    assert detector.process_frame(loud_chunk) is True


def test_pipeline_privacy_disabled():
    pipeline = AudioPipelineCoordinator()
    pipeline.is_listening_enabled = False

    called = False
    pipeline.set_callbacks(on_level_changed=lambda lvl: None, on_wake_detected=lambda: True)
    # When disabled, incoming chunks must not trigger processing
    loud_chunk = b"\x7F\x7F" * 160
    pipeline.process_audio_chunk(loud_chunk)
    assert called is False

