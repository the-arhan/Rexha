# Rexha Development Rules

## Product integrity

- Rexha is a persistent Windows desktop assistant, not a web-only chatbot.
- Python and PySide6 are the default technology choices.
- Voice activation is required in v0.1.
- Preserve the compact, always-on-top sleeping widget and the voice-driven interaction loop.
- Maintain the long-term product vision when implementing the current milestone.

## Engineering

- Inspect the existing implementation before changing it.
- Keep modules small, cohesive, and testable.
- Separate the GUI, voice system, interpreter, permissions, executor, integrations, and storage.
- Avoid unnecessary dependencies and oversized abstractions.
- Keep the application runnable after each implementation batch.
- Add tests for meaningful behavior.
- Update documentation when implementation changes.

## Execution safety

- Never expose unrestricted shell execution to an LLM.
- Validate structured action plans before execution.
- Apply permissions independently of the AI model.
- Confirm consequential operations.
- Validate file paths and restrict operations to approved locations.
- Do not silently elevate privileges or bypass Windows security.
- Never overwrite unrelated user files without authorization.

## Privacy

- Do not save raw audio by default.
- Make microphone and camera activity visible.
- Disclose external processing of audio, transcriptions, images, or sensitive content.
- Never commit secrets or real API keys.
- Exclude local credentials and runtime data from version control.

## Verification

- Do not claim a feature works without appropriate evidence.
- Distinguish implemented, tested, partially implemented, and planned functionality.
- Test failure paths and cancellation where appropriate.
- Never represent a mock or placeholder as a completed integration.

## Working style

- Prefer incremental, reviewable changes.
- Explain required manual setup precisely.
- Avoid asking the project owner to write complex code manually.
- Do not ask for approval for every ordinary code edit.
- Ask before destructive operations or consequential changes outside the project.
- Maintain IMPLEMENTATION_PLAN.md and report concrete progress.
