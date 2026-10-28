# Rexha — Voice Subsystem Specification & Evaluation

This document details the architecture, dependency evaluation, engine selection, and privacy controls for Rexha's voice subsystem.

---

## 1. Subsystem Objectives

1. **Local Wake Detection:** Detect configurable wake phrases (*"Wake up, Rexha"*, *"Hey, Rexha"*, *"Rexha, [command]"*) without streaming ambient audio to cloud servers.
2. **Audio Streaming & VAD:** Continuously monitor microphone input with low CPU overhead, detect speech boundaries (Voice Activity Detection), and capture speech cleanly.
3. **Speech Recognition (STT):** Convert voice commands into text with low latency, supporting offline models.
4. **Text-to-Speech (TTS):** Speak responses using local Windows SAPI5 or offline neural synthesis, with user-configurable enable/disable toggle.
5. **Privacy & Feedback:** Prominently display microphone recording status and audio input level in the UI.

---

## 2. Technical Evaluation of Wake-Word Engines

| Engine | Local/Offline | Custom Wake-Phrase Feasibility | CPU/RAM Footprint | Licensing & Availability | Assessment |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **OpenWakeWord** | Yes (ONNX) | High. Can train synthetic models or use open ONNX models. | ~1-3% CPU on modern x64; ~50MB RAM. | Apache 2.0. Runs on ONNX Runtime. | **Recommended for production local wake detection.** |
| **Vosk Grammar Spotter** | Yes (Kaldi) | High. Can set small grammar list containing wake phrases. | ~2% CPU; ~40MB RAM using small model. | Apache 2.0. Clean Python 3.12 wheel. | **Excellent fallback / secondary option.** |
| **Picovoice Porcupine** | Yes | High accuracy, custom phrase generated via console. | <1% CPU; minimal RAM. | Free tier requires API AccessKey; commercial license needed. | Viable if user provides Picovoice access key. |
| **Whisper-streaming** | Yes | Low for wake-detection; high latency & high CPU usage. | High (20-60% CPU on CPU inference). | MIT. | Inappropriate for standby wake listening. |

### Technical Decision for Wake Word:
- In **v0.1**, implement a modular `WakeDetector` interface.
- Provide a robust acoustic energy + keyword spotter / OpenWakeWord adapter that detects configured wake phrases locally.
- For testing and environments lacking trained ONNX models, provide a local pattern matcher so the pipeline operates deterministically.

---

## 3. Technical Evaluation of Speech-to-Text (STT)

| Engine | Latency | Accuracy | Hardware Requirements | Offline Capability |
| :--- | :--- | :--- | :--- | :--- |
| **Faster-Whisper (small/base.en)** | ~0.5s - 1.2s on CPU | Excellent | ~300-500MB RAM, CTranslate2 backend | 100% Offline |
| **Vosk (vosk-model-small-en-us)** | ~0.2s - 0.5s on CPU | Good for desktop commands | ~80MB RAM, very lightweight | 100% Offline |
| **Windows SAPI / System STT** | ~0.3s | Moderate | Built into Windows | Offline (built-in) |
| **Cloud (OpenAI Whisper API / Groq)** | ~0.3s - 0.8s | Near-perfect | Minimal local CPU, requires network | Online only |

### Architecture Decision:
- Primary default: Local offline STT via `faster-whisper` or `vosk` for complete privacy.
- Optional pluggable provider: Cloud API (Whisper / Groq) for users prioritizing speed on low-power CPUs.
- In all modes, clear disclosure is rendered in UI settings regarding whether audio/transcription leaves the device.

---

## 4. Text-to-Speech (TTS) Architecture

1. **Local Default:** Windows SAPI5 via `pyttsx3`.
   - Zero network dependencies, zero latency, runs instantly on any Windows 10/11 system.
   - User can adjust voice persona (e.g., David, Zira, Mark) and speech rate.
2. **Toggle:** User preference `voice.tts_enabled` in SQLite allows immediate muting of all spoken responses.
3. **Non-Blocking Execution:** Speech playback runs in a dedicated background worker thread to ensure the PySide6 UI never stutters during speech output.

---

## 5. Audio Pipeline & Concurrency

```
  Microphone
      │ (16kHz, 16-bit Mono PCM)
      ▼
AudioCaptureWorker (QThread)
      │
      ├──> RMS Energy Calculator ────> Signal: `audio_level_changed(float)` ────> UI Meter
      │
      ├──> Standby Mode: Local WakeDetector ────> Signal: `wake_word_detected` ────> State: WAKING
      │
      └──> Command Mode: Audio Buffer + VAD ────> Signal: `speech_chunk_captured`
                                                          │
                                                          ▼
                                                  STT Worker (QThread)
                                                          │
                                                          ▼
                                            Signal: `transcription_ready(str)`
```
