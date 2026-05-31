# FRIDAY v2 — UI Rebuild, Conversation Experience & Real-World Agency

**Date:** 2026-05-31
**Goal:** Recreate the whole FRIDAY interface as the best JARVIS-style UI we can build,
nail the conversation experience, and expand Friday's real-world agency — designed as
one system with three clean layers, built in sequence.

## Decisions locked (from brainstorming)

- **Layout archetype:** **Hybrid** — idle is a pure cinematic centered orb; during a turn
  a glass transcript panel slides in (right), then recedes after idle. Movie look by
  default, full chat history on demand.
- **Visual identity:** **Adaptive orb** — arc-reactor-blue base, color shifts with
  Friday's mood (reusing `core/personality.py` mood states) plus a runtime state channel.
- **Input modes:** **Voice + text** — voice primary; a text command bar over the same
  WebSocket; Friday replies in text + voice.
- **Captions:** **Karaoke word-sync** — words illuminate in time with TTS via Edge-TTS
  WordBoundary events. Fallback: sentence-by-sentence (already supported by the backend).
- **Agency:** all four sets — web search/fetch, files/clipboard, app/system control,
  comms/calendar. Comms/calendar is last (needs account setup).

## Context (verified)

- Backend: FastAPI + WebSocket `/ws/voice`; brain via Ollama (`nemotron-3-super:cloud`),
  no `ANTHROPIC_API_KEY`. Stage-1 brain layer is in place (`core/persona.py`,
  `core/structured.py`, `core/dataset.py`). Tool-calling validated on the Ollama path.
- Frontend today: two large JS files (`ui/js/app.js` ~440 lines, `ui/js/orb.js`) plus
  `neural.js`; Three.js orb with bloom; glassmorphism panels; sentence-pipelined TTS;
  barge-in. No transcript, no streaming text, placeholder panels, dummy neural map.
- Run with `python3` + `PYTHONPATH=.`; `python` not on PATH. Tests: pytest, run with
  `-p no:cacheprovider`.

## Architecture — three layers over the existing WebSocket

```
UI shell (ui/)  <—WebSocket events—>  Conversation engine (core/)  <—tool calls—>  Agency layer (core/agency/)
```

### Layer A — UI shell (`ui/`)
Rebuild the frontend into focused modules (replace the two-big-files structure):
- `ui/js/orb.js` — adaptive Three.js orb (arc-reactor base; color from mood+state;
  reactive to voice amplitude). Keeps the bloom/nebula/starfield foundation.
- `ui/js/conversation.js` — transcript model + Hybrid panel show/recede choreography.
- `ui/js/captions.js` — karaoke word-sync renderer (consumes word-timing events).
- `ui/js/hud.js` — header, vitals, action chips, status, settings/permission modals.
- `ui/js/app.js` — WebSocket client, mic/text input, audio playback, event routing.
- `ui/css/style.css` — restyled for the adaptive theme and Hybrid layout.
- `ui/index.html` — restructured markup for the above.

Orb **state channel** (independent of mood color): `idle | listening | thinking |
speaking | acting`, each with motion/intensity behavior.

### Layer B — Conversation engine (`core/`)
- New `core/voice_session.py` — owns one turn end-to-end: input (audio or text) →
  brain stream → segment/word-timed TTS → ordered WebSocket events. Extracts the turn
  logic currently inline in `core/main.py`'s websocket handler so `main.py` stays thin.
- `core/tts.py` — add a `generate_speech_timed()` that returns audio **plus** word
  boundaries `[{word, offset_ms, duration_ms}]` from Edge-TTS `WordBoundary` events.
- `core/main.py` — `/ws/voice` accepts both audio (bytes) and text/control (JSON, incl.
  the existing `interrupt`); delegates the turn to `voice_session`.

**WebSocket event contract (server → UI):**
- `{type:"state", state:"listening|thinking|speaking|acting|idle"}`
- `{type:"transcript", role:"user|friday", text, final:bool}`
- `{type:"caption", words:[{word, offset_ms, duration_ms}], segment_id}` + audio bytes
- `{type:"action", tool, phase:"start|done|error", label}` (drives action chips)
- `{type:"mood", mood, orb_color}` and existing `{type:"arg_unlocked", flags}`

**UI → server:** audio bytes (as today); `{type:"text", content}`; `{type:"interrupt"}`.

### Layer C — Agency layer (`core/agency/`)
New package; each module exposes isolated, permission-gated tool functions registered
into the brain's tool list. Each has a pure, unit-testable core where possible.
- `core/agency/web.py` — `web_search(query)`, `fetch_page(url)` → cleaned/summarized text.
- `core/agency/files.py` — search/read files, open folder, clipboard get/set, screenshot.
- `core/agency/system.py` — open/close apps, volume/media keys, hardened shell run.
- `core/agency/comms.py` *(last phase)* — draft/send message, calendar/reminders.
- `core/agency/registry.py` — assembles agency tool schemas + dispatch, consumed by
  `core/brain.py` (brain imports the registry instead of hand-listing every tool).

Permissions: extend `config/permissions.json` with new categories (e.g. `web_access`,
`file_read`, `clipboard`, `screenshot`, `app_control`, `comms`); reuse the existing
`PermissionManager` "allow/ask/deny" flow and the UI approval toast.

## Data flow (one turn)
1. UI sends audio bytes or `{type:"text"}`.
2. `voice_session` resolves input text (STT for audio, gated by interaction mode/wake).
3. Emits `state: thinking`; streams `brain.get_streaming_response`.
4. On tool use: emits `action: start` → runs agency tool (permission-gated) → `action: done`.
5. Buffers into sentence segments; for each, calls `generate_speech_timed` → emits
   `caption` (+ word timings) and audio bytes; emits `state: speaking`.
6. UI plays audio, illuminates words in sync, grows the transcript panel.
7. On `interrupt` (barge-in), stops streaming/queued audio; emits `state: idle`.

## Error handling
- Word timings unavailable/unreliable → emit caption with empty `words` and a `mode:
  "sentence"` flag; UI fades the sentence in (graceful fallback, no failure).
- Brain unreachable → existing in-character message path; emit `state: idle`.
- Agency tool failure → `action: error` chip + tool-result fed back to the model
  (reuses Stage-1 validate/repair pattern); never raises into the turn loop.
- Permission "ask"/"deny" → existing toast; tool returns the pending/denied sentinel.

## Testing
- **Backend (pytest, no live LLM):** `generate_speech_timed` word-boundary parsing
  (mock Edge-TTS events); agency tool pure cores (web result cleaning, file search,
  path-safety, system command building); event-shaping helpers in `voice_session`;
  agency registry schema/dispatch.
- **UI:** verified by running the app (`python3 launcher.py`) — orb states, panel
  choreography, karaoke sync, text input, action chips.
- Live smoke: a full voice turn and a full text turn through Ollama.

## Build phasing (one effort, sequential)
1. **UI shell rebuild** — adaptive orb + Hybrid layout + state choreography + module split.
2. **Conversation engine** — `voice_session`, word-timed TTS, caption/transcript/text-input,
   action chips.
3. **Agency (local)** — `web.py`, `files.py`, `system.py` + registry + permissions + chips.
4. **Agency (comms/calendar)** — `comms.py`, after account setup.

Each phase produces a working, demoable app. Phases 1–2 may share one implementation
plan; phases 3–4 may each get their own plan when reached.

## Out of scope
- Real neural-map data viz (keep current placeholder or hide; revisit later).
- Stage-2 local model fine-tune (separate track, already specced).
- Mobile/responsive layout (desktop-first).
- Cloud/account provisioning for comms until phase 4.

## Success criteria
- A rebuilt, cohesive JARVIS UI: adaptive arc-reactor orb with mood/state behavior,
  Hybrid transcript, karaoke captions in sync with voice, working text input.
- Conversation feels alive: clear listening/thinking/speaking/acting states; barge-in
  intact; agency actions visible as chips.
- Three local agency capability sets working and permission-gated; comms/calendar
  scaffolded for phase 4.
- New backend logic unit-tested; app runs and a voice turn + text turn both work live.
