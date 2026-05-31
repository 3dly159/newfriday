# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Friday** is a voice-first proactive AI assistant with a layered cognitive memory system and a cinematic 3D holographic interface. It combines:
- Always-listening wake-word detection (Whisper-based STT)
- Streaming LLM responses (Anthropic/OpenAI)
- Text-to-speech synthesis (Edge-TTS)
- Proactive intelligence that initiates conversations
- Multi-agent orchestration via the "Legion Protocol"
- A 7-layer memory architecture for deep personalization
- A Three.js-powered holographic HUD with glassmorphism design

The project uses **FastAPI** with **WebSockets** for real-time bidirectional voice communication between the browser UI and the Python backend.

## Core Architecture

### Backend (Python/FastAPI)
- **`core/main.py`** — FastAPI app entry point. Handles WebSocket connections for voice streaming, API endpoints for config/permissions, and lifespan management.
- **`core/brain.py`** — The central intelligence. Routes requests to the appropriate LLM (Anthropic or OpenAI), manages personality, memory layers, and streaming responses.
- **`core/memory.py`** — The 7-layer memory system: Bio, Lore, Skill, Script, Social, Task, Episodic. Persisted to `data/memory.json`.
- **`core/proactive.py`** — ProactiveEngine that periodically generates contextual messages to initiate conversations with the user.
- **`core/agents.py`** — Multi-agent orchestration (Legion Protocol). Allows Friday to delegate complex tasks to specialized sub-agents.
- **`core/personality.py`** — Personality traits, mood states, and contextual response patterns.
- **`core/bridge.py`** — Bridge to system-level operations (file I/O, mouse/keyboard control, permissions, system vitals).
- **`core/skills.py`** — Clawhub skills manager. Loads skill manifests from `config/skills.json`.
- **`core/persona.py`** — The Friday persona contract: single versioned source of truth for personality, tool discipline, voice brevity, and lore. `FridayPersonality.get_system_prompt` delegates here. Also selects/formats few-shot exemplars from `data/persona/exemplars.jsonl`.
- **`core/structured.py`** — Tool-call argument validation (`validate_tool_args`) and tolerant JSON repair (`repair_json`) for rock-solid tool-calling. `core/proactive.py` reuses `repair_json`.
- **`core/dataset.py`** — Opt-in, local-only capture of interactions to `data/dataset/friday_sft.jsonl` for Stage 2 fine-tuning. Toggle with `config.system.capture_dataset`.
- **`core/stt.py`** — Speech-to-Text wrapper using Faster-Whisper.
- **`core/tts.py`** — Text-to-Speech wrapper using Edge-TTS.
- **`core/quest.py`** — Quest/ARG (Augmented Reality Game) engine for unlocking narrative content.

### Frontend (HTML/CSS/JavaScript)
- **`ui/index.html`** — Main UI page. Establishes WebSocket connection to `/ws/voice`, renders the holographic interface.
- **`ui/js/`** — Three.js-based 3D orb, real-time waveform visualization, telemetry panels, and interaction handlers.
- **`ui/css/`** — Glassmorphism styling, theme colors (controllable via `config/registry.json`).

### Configuration & Data
- **`config/registry.json`** — Central configuration. Contains AI model choice, voice profile, proactive interval, theme color, and interaction modes. Generated with defaults on first run.
- **`config/skills.json`** — Manifest of available Clawhub skills.
- **`config/permissions.json`** — User-granted permissions for system operations (file access, script execution, etc.).
- **`data/memory.json`** — Persistent memory state (7 layers).
- **`data/vector_db/`** — ChromaDB vector store for semantic memory retrieval.
- **`data/logs/`** — Temporary audio files during voice processing.

## Development Commands

### Running
```bash
# Start Friday (full stack: FastAPI backend + WebSocket server on :8000)
python launcher.py

# Navigate to http://localhost:8000 in your browser to access the holographic interface.
```

### Testing
```bash
# Run all tests
pytest

# Run a specific test file (e.g., phase 1 foundation tests)
pytest tests/test_phase1.py

# Run a specific test function
pytest tests/test_phase1.py::test_brain_response

# Run async tests with proper event loop
pytest tests/test_phase1.py::test_brain_response --asyncio-mode=auto

# Run tests matching a pattern
pytest -k "brain_response"

# Verbose output
pytest -v
```

**Note:** Tests that call LLM endpoints (e.g., `test_brain_response`) require `ANTHROPIC_API_KEY` to be set and will skip if it's not.

### Environment
Create a `.env` file (or export directly):
```bash
export ANTHROPIC_API_KEY='sk-ant-...'
export OPENAI_API_KEY='sk-...'  # Optional, if using OpenAI fallback
```

Alternatively, copy `.env.example` and fill in your keys:
```bash
cp .env.example .env
```

## Key Flows

### Voice Processing Pipeline
1. **Browser captures audio** → sends WebM/Opus chunks via WebSocket to `/ws/voice`
2. **STT (Faster-Whisper)** → transcribes audio to text
3. **Wake-word check** → verifies if addressed (keywords: "friday", "hey friday", "computer") or if it's a greeting
4. **Memory update** → adds episodic memory; checks for ARG unlocks
5. **LLM streaming** → `brain.get_streaming_response()` streams tokens; filters system notifications
6. **Streaming pipelining** — buffers tokens into sentence segments; holds one sentence ahead for lower latency
7. **TTS for each segment** → Edge-TTS generates audio; sent back to browser
8. **UI playback** → browser synthesizes audio with animation

### Proactive Initiation
1. `ProactiveEngine` wakes up every N seconds (configured in `config/registry.json`)
2. Samples current system state, user context, and memory layers
3. Decides whether to initiate conversation (e.g., "You haven't checked emails in 2 hours")
4. Generates speech, broadcasts to all connected WebSockets via `broadcast_proactive_message()`

### Multi-Agent Delegation (Legion Protocol)
When Friday receives a complex task:
1. **LegionBroker** in `core/agents.py` analyzes the request
2. Delegates to specialized sub-agents (e.g., WriterAgent, AnalystAgent, etc.)
3. Collects results and synthesizes a cohesive response

### ARG System
- Episodic memory events can unlock ARG flags
- When a flag is unlocked, a JSON message `{"type": "arg_unlocked", "flags": [...]}` is sent to the UI
- The UI may reveal hidden UI elements, play special effects, or unlock narrative content

## Important Notes

### Configuration & Initialization
- `launcher.py` checks dependencies and auto-creates `config/registry.json` with sensible defaults if missing
- The registry can be hot-reloaded via POST `/api/config`
- Interaction mode (wake-word vs. always-listening) is controlled by `config.speech.interaction_mode`

### Model Switching
The model/provider is swapped at runtime via `config/registry.json`:
```json
{
  "ai_logic": {
    "model_provider": "anthropic",  // or "openai" or "ollama"
    "llm_model": "claude-3-5-sonnet-20241022"
  }
}
```

### Permissions & Security
- Risky operations (file deletion, mouse/keyboard control) are gated by `core/bridge.py` and require explicit user permission
- Permissions are stored in `config/permissions.json` and can be revoked via the UI

### System Vitals
- The bridge exposes system metrics (CPU, memory, disk) via GET `/api/vitals`
- Used by the telemetry panel in the holographic UI

### Streaming & Latency
The hold-one-ahead pipelining in `main.py` (lines 204–233) buffers sentences to reduce latency:
- Sentence N is held while sentence N+1 is being generated
- As soon as sentence N+1 completes, sentence N is dispatched to TTS
- This allows audio playback to start before the full response is ready

### Logs & Debugging
- Terminal output shows transcriptions (`[TRANSCRIPTION]`), user input (`[USER]`), and Friday's responses (`[FRIDAY]`)
- Background awareness events (not addressed to Friday) are logged as `[BACKGROUND]`
- Temporary audio files are cleaned up from `data/logs/` after each interaction
- Server logs are written to `server.log`

## Files to Modify When...

| Goal | Files |
|------|-------|
| Change AI model/provider | `config/registry.json` (or POST `/api/config`) |
| Adjust personality (wit, sarcasm, tone) | `core/personality.py` |
| Add new memory layer or adjust 7-layer system | `core/memory.py`, `data/memory.json` |
| Implement new skill/capability | `config/skills.json`, `core/skills.py` |
| Modify proactive interval or logic | `core/proactive.py`, `config/registry.json` |
| Change wake words or greeting triggers | `core/main.py` (lines 184–187) |
| Design UI layout, colors, 3D orb | `ui/index.html`, `ui/js/`, `ui/css/`, `config/registry.json` (theme_color) |
| Add system-level operations (file I/O, script execution) | `core/bridge.py` |
| Extend multi-agent orchestration | `core/agents.py`, `core/quest.py` |

## Common Gotchas

1. **Missing ANTHROPIC_API_KEY**: Friday will run in "Blackout" mode with limited intelligence. Set the env var before running `launcher.py`.
2. **WebSocket connection fails**: Ensure localhost:8000 is accessible and no other service is bound to port 8000.
3. **Audio playback stops**: Check browser console for WebSocket errors. Verify `data/logs/` is writable.
4. **STT fails on .webm files**: Faster-Whisper may struggle with some WebM encodings. Consider adding ffmpeg conversion in `core/stt.py` if needed.
5. **GUI automation (mouse/keyboard) disabled on Linux headless**: The bridge will still work for file operations, but UI control requires `DISPLAY` and `tkinter`.

## Phases & Roadmap

The project includes 7 development phases documented in `Phase1_Foundation.md` through `Phase7_Narrative.md`:
- **Phase 1**: Foundation (STT, TTS, basic response)
- **Phase 2**: Interaction (wake words, contextual replies)
- **Phase 3**: System Mastery (file I/O, mouse/keyboard)
- **Phase 4**: Cognitive Architecture (7-layer memory)
- **Phase 5**: Evolution (self-improvement, ARG unlocks)
- **Phase 6**: Hardening (security, permissions, kill-switch)
- **Phase 7**: Narrative (lore, personality, easter eggs)

Tests are organized by phase (e.g., `tests/test_phase1.py`, `tests/test_phase4.py`), so features can be validated incrementally.
