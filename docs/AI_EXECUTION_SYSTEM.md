# Rexha — AI Execution & Planning Specification

This document details the hybrid command interpretation architecture, structured action schemas, and safety boundaries between language models and Windows execution.

---

## 1. Hybrid Interpretation Architecture

Rexha uses a two-tier interpretation engine:

```
User Input (Voice or Text)
           │
           ▼
+─────────────────────────────────────────+
|      DETERMINISTIC INTENT PARSER        |
|  - Fast pattern matching                |
|  - Zero network latency                 |
|  - 100% offline predictability          |
|  - Matches: "Open [app]", "Close [app]" |
|    "System status", "Create note ...",  |
|    "Volume / settings ...", etc.        |
+────────────────────┬────────────────────+
                     │
          Matched?   │
          ├── YES ───┼──> Generates Structured Action Plan
          │          │
          └── NO ────▼
+─────────────────────────────────────────+
|          LLM PLANNER (OPTIONAL)         |
|  - Provider-agnostic client adapter     |
|  - Interprets multi-step or fuzzy intent|
|  - Emits JSON structured action plan    |
|  - Constrained strictly to registered   |
|    action capability schemas            |
+────────────────────┬────────────────────+
                     │
                     ▼
          Validation & Policy Guard
```

If no LLM provider is configured or available, Rexha continues to function reliably for all supported deterministic commands, cleanly communicating when a query falls outside the recognized command catalog.

---

## 2. Structured Action Schema

Every intent transforms into one or more `StructuredAction` items before entering the policy and executor layers:

```python
class ActionType(str, Enum):
    LAUNCH_APP = "launch_app"
    CLOSE_APP = "close_app"
    WINDOW_CONTROL = "window_control"
    OPEN_SETTINGS = "open_settings"
    CREATE_NOTE = "create_note"
    READ_NOTE = "read_note"
    OPEN_FOLDER = "open_folder"
    RUN_COMMAND = "run_command"
    SYSTEM_QUERY = "system_query"
    CAMERA_CAPTURE = "camera_capture"
    OPEN_URL = "open_url"

@dataclass
class StructuredAction:
    action_id: str
    action_type: ActionType
    parameters: dict[str, Any]
    permission_tier: int  # 0 = Safe, 1 = Standard, 2 = Consequential
    requires_confirmation: bool
    timeout_seconds: float
    description: str
    expected_outcome: str
    verification_strategy: str  # e.g., "process_running", "file_exists"
```

---

## 3. Provider-Independent LLM Adapter

Rexha provides an abstract `LLMProvider` interface:

```python
class LLMProvider(ABC):
    @abstractmethod
    def plan_task(self, prompt: str, catalog: list[dict[str, Any]]) -> list[StructuredAction]:
        pass

    @abstractmethod
    def clarify_request(self, prompt: str, ambiguities: list[str]) -> str:
        pass
```

Implementations:
- `OpenAIProvider`: OpenAI GPT-4o / GPT-4o-mini with structured outputs.
- `GeminiProvider`: Google Gemini 1.5 / 2.0 Flash with JSON schema mode.
- `AnthropicProvider`: Claude 3.5 Sonnet / Haiku with tool use.
- `OllamaProvider`: Local offline LLM (e.g., Llama 3, Mistral) for privacy-conscious users.
