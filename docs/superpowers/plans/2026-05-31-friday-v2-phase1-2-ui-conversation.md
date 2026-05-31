# FRIDAY v2 — Phases 1–2 (UI Shell + Conversation Engine) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild FRIDAY's interface (adaptive arc-reactor orb, Hybrid layout, karaoke captions, text input) and the backend conversation engine that drives it via a clean WebSocket event contract.

**Architecture:** A backend conversation engine (`core/voice_session.py`) owns one turn end-to-end and emits a typed event stream (`core/events.py`) over the existing `/ws/voice`. Word-timed TTS (`core/tts.py`) powers karaoke captions. The frontend is split from two big files into focused ES modules (`orb`, `app`, `conversation`, `captions`, `hud`) that consume the event contract.

**Tech Stack:** Python 3.12 (`python3`, run with `PYTHONPATH=.`), FastAPI + WebSockets, Edge-TTS (WordBoundary events), Faster-Whisper, Three.js (ESM via importmap). pytest + pytest-asyncio.

---

## Conventions for every task

- Run Python tests: `PYTHONPATH=. python3 -m pytest <path> -v -p no:cacheprovider`
- `python` is NOT on PATH — always `python3`. Run the app: `python3 launcher.py` (serves http://localhost:8000).
- Branch: `friday-milestone-1-voice-reliability` (current) unless told otherwise.
- Commit after each task with the exact message given. Only `git add` the files named in the task.
- Backend logic tasks are strict TDD. UI tasks can't be unit-tested here, so they end with an explicit **manual verification** step in the browser — do it before committing.

---

## Event contract (server → UI) — the shared language

Every backend task emits, and every UI task consumes, exactly these JSON event shapes:

- `{"type":"state","state":"idle|listening|thinking|speaking|acting"}`
- `{"type":"transcript","role":"user|friday","text":<str>,"final":<bool>}`
- `{"type":"caption","segment_id":<str>,"mode":"word|sentence","words":[{"word":<str>,"offset_ms":<int>,"duration_ms":<int>}],"text":<str>}` — immediately followed by one binary audio frame (mp3 bytes)
- `{"type":"action","tool":<str>,"phase":"start|done|error","label":<str>}`
- `{"type":"mood","mood":<str>,"orb_color":<hex str>}`
- `{"type":"arg_unlocked","flags":[...]}` (unchanged)

UI → server: binary audio frames (mic), `{"type":"text","content":<str>}`, `{"type":"interrupt"}`.

---

## File Structure

- Modify: `core/tts.py` — add `words_from_chunks`, `boundary_to_word`, `generate_speech_timed`.
- Create: `core/events.py` — pure event-builder functions for the contract above.
- Create: `core/voice_session.py` — `is_sentence_end`, `VoiceSession` (owns a turn).
- Modify: `core/main.py` — `/ws/voice` delegates to `VoiceSession`; thin handler.
- Test: `tests/test_tts_timed.py`, `tests/test_events.py`, `tests/test_voice_session.py`.
- Rewrite: `ui/index.html` — restructured markup (orb canvas, transcript panel, command bar, chips).
- Rewrite: `ui/css/style.css` — adaptive theme + Hybrid layout.
- Rewrite: `ui/js/orb.js` — adaptive orb (state channel + mood color + voice reactivity).
- Rewrite: `ui/js/app.js` — WebSocket client, event router, audio playback, mic, text input, barge-in.
- Create: `ui/js/conversation.js` — transcript model + Hybrid panel choreography.
- Create: `ui/js/captions.js` — karaoke word-sync renderer + sentence fallback.
- Create: `ui/js/hud.js` — header, status, action chips, vitals, settings/permission modals.

---

## PHASE 2A — Backend conversation engine (TDD)

### Task 1: Word-boundary parsing in TTS

**Files:**
- Modify: `core/tts.py`
- Test: `tests/test_tts_timed.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_tts_timed.py`:

```python
from core.tts import boundary_to_word, words_from_chunks


def test_boundary_to_word_converts_ticks_to_ms():
    # Edge-TTS reports offset/duration in 100-nanosecond ticks (10000 ticks = 1 ms)
    chunk = {"type": "WordBoundary", "text": "Hello", "offset": 5000000, "duration": 2500000}
    assert boundary_to_word(chunk) == {"word": "Hello", "offset_ms": 500, "duration_ms": 250}


def test_words_from_chunks_keeps_only_word_boundaries():
    chunks = [
        {"type": "audio", "data": b"\x00\x01"},
        {"type": "WordBoundary", "text": "Good", "offset": 0, "duration": 1000000},
        {"type": "audio", "data": b"\x02"},
        {"type": "WordBoundary", "text": "evening", "offset": 1000000, "duration": 2000000},
    ]
    words = words_from_chunks(chunks)
    assert words == [
        {"word": "Good", "offset_ms": 0, "duration_ms": 100},
        {"word": "evening", "offset_ms": 100, "duration_ms": 200},
    ]


def test_words_from_chunks_empty_when_no_boundaries():
    assert words_from_chunks([{"type": "audio", "data": b"x"}]) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_tts_timed.py -v -p no:cacheprovider`
Expected: FAIL with `ImportError: cannot import name 'boundary_to_word'`

- [ ] **Step 3: Write minimal implementation**

In `core/tts.py`, add at module level (after the imports, before the class):

```python
TICKS_PER_MS = 10000  # Edge-TTS reports offset/duration in 100-nanosecond ticks


def boundary_to_word(chunk):
    """Convert one Edge-TTS WordBoundary chunk to our word-timing dict."""
    return {
        "word": chunk["text"],
        "offset_ms": chunk["offset"] // TICKS_PER_MS,
        "duration_ms": chunk["duration"] // TICKS_PER_MS,
    }


def words_from_chunks(chunks):
    """Filter an Edge-TTS chunk stream down to word-timing dicts."""
    return [boundary_to_word(c) for c in chunks if c.get("type") == "WordBoundary"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_tts_timed.py -v -p no:cacheprovider`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add core/tts.py tests/test_tts_timed.py
git commit -m "feat(tts): parse Edge-TTS word boundaries into timing dicts

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: `generate_speech_timed` (audio + word timings)

**Files:**
- Modify: `core/tts.py`
- Test: manual smoke (needs network/Edge-TTS; no unit test for the network call)

- [ ] **Step 1: Add the method**

In `core/tts.py`, add this method to the `FridayTTS` class (alongside `generate_speech`, do not remove `generate_speech`):

```python
    async def generate_speech_timed(self, text: str, output_path: str):
        """Synthesize speech and return (output_path, words) where words is a list
        of {word, offset_ms, duration_ms} from Edge-TTS WordBoundary events."""
        import edge_tts
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
        audio = bytearray()
        chunks = []
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])
            else:
                chunks.append(chunk)
        with open(output_path, "wb") as f:
            f.write(audio)
        return output_path, words_from_chunks(chunks)
```

- [ ] **Step 2: Smoke-test it live (Edge-TTS reaches Microsoft servers)**

Run:
```bash
PYTHONPATH=. python3 -c "
import asyncio
from core.tts import FridayTTS
async def main():
    t = FridayTTS()
    path, words = await t.generate_speech_timed('Good evening, Sir.', '/tmp/friday_timed.mp3')
    import os
    print('audio_bytes:', os.path.getsize(path))
    print('words:', words)
asyncio.run(main())
"
```
Expected: `audio_bytes:` > 0, and `words:` a non-empty list like `[{'word': 'Good', 'offset_ms': ...}, ...]`. (If Edge-TTS is unreachable, note it; the sentence-fallback path still works without timings.)

- [ ] **Step 3: Commit**

```bash
git add core/tts.py
git commit -m "feat(tts): add generate_speech_timed returning audio + word timings

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: Event-builder module

**Files:**
- Create: `core/events.py`
- Test: `tests/test_events.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_events.py`:

```python
from core import events


def test_state_event():
    assert events.state_event("thinking") == {"type": "state", "state": "thinking"}


def test_transcript_event():
    assert events.transcript_event("user", "hello", True) == {
        "type": "transcript", "role": "user", "text": "hello", "final": True
    }


def test_caption_event_word_mode():
    words = [{"word": "Hi", "offset_ms": 0, "duration_ms": 100}]
    ev = events.caption_event("seg1", words, "Hi", mode="word")
    assert ev == {
        "type": "caption", "segment_id": "seg1", "mode": "word",
        "words": words, "text": "Hi"
    }


def test_caption_event_defaults_to_sentence_when_no_words():
    ev = events.caption_event("seg2", [], "A full sentence.")
    assert ev["mode"] == "sentence"
    assert ev["words"] == []


def test_action_event():
    assert events.action_event("web_search", "start", "Searching the web") == {
        "type": "action", "tool": "web_search", "phase": "start",
        "label": "Searching the web"
    }


def test_mood_event():
    assert events.mood_event("banter", "#8B5CF6") == {
        "type": "mood", "mood": "banter", "orb_color": "#8B5CF6"
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_events.py -v -p no:cacheprovider`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.events'`

- [ ] **Step 3: Write minimal implementation**

Create `core/events.py`:

```python
"""Typed builders for the FRIDAY v2 WebSocket event contract (server -> UI)."""


def state_event(state):
    return {"type": "state", "state": state}


def transcript_event(role, text, final):
    return {"type": "transcript", "role": role, "text": text, "final": final}


def caption_event(segment_id, words, text, mode=None):
    # Default to word-sync when timings exist, otherwise sentence fade.
    if mode is None:
        mode = "word" if words else "sentence"
    return {
        "type": "caption",
        "segment_id": segment_id,
        "mode": mode,
        "words": words,
        "text": text,
    }


def action_event(tool, phase, label):
    return {"type": "action", "tool": tool, "phase": phase, "label": label}


def mood_event(mood, orb_color):
    return {"type": "mood", "mood": mood, "orb_color": orb_color}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_events.py -v -p no:cacheprovider`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add core/events.py tests/test_events.py
git commit -m "feat(events): add typed WebSocket event builders

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: `VoiceSession` — own one turn

**Files:**
- Create: `core/voice_session.py`
- Test: `tests/test_voice_session.py`

The session is decoupled from FastAPI: it takes `send_json`/`send_bytes` callables so it can be driven by fakes in tests.

- [ ] **Step 1: Write the failing test**

Create `tests/test_voice_session.py`:

```python
import pytest
from core.voice_session import is_sentence_end, VoiceSession


def test_is_sentence_end():
    assert is_sentence_end("Hello there.")
    assert is_sentence_end("Really?")
    assert is_sentence_end("Stop!")
    assert not is_sentence_end("hold on")


class _FakeBrain:
    """Minimal brain stub: streams two sentences, with a tool notification."""
    class _Pers:
        current_mood = "neutral"
        mood_states = {"neutral": {"orb_color": "#5cc8ff"}}
    def __init__(self):
        self.personality = self._Pers()
        self.config = {"ai_logic": {"llm_model": "test"}}
    async def get_streaming_response(self, text):
        for tok in ["Good ", "evening, Sir. ", "[System: Executing get_system_vitals...]",
                    "All ", "systems nominal."]:
            yield tok


class _FakeTTS:
    async def generate_speech_timed(self, text, output_path):
        with open(output_path, "wb") as f:
            f.write(b"FAKEAUDIO")
        return output_path, [{"word": text.strip().split(" ")[0], "offset_ms": 0, "duration_ms": 100}]


@pytest.mark.asyncio
async def test_run_turn_emits_contract_events(tmp_path):
    sent_json = []
    sent_bytes = []
    session = VoiceSession(
        brain=_FakeBrain(), stt=None, tts=_FakeTTS(),
        send_json=lambda m: sent_json.append(m),
        send_bytes=lambda b: sent_bytes.append(b),
        logs_dir=str(tmp_path),
    )
    await session.run_turn("status report")

    types = [m["type"] for m in sent_json]
    # A user transcript, a thinking state, at least one caption, an action chip,
    # and a trailing idle state must all appear.
    assert "transcript" in types
    assert any(m["type"] == "state" and m["state"] == "thinking" for m in sent_json)
    assert any(m["type"] == "state" and m["state"] == "speaking" for m in sent_json)
    assert any(m["type"] == "caption" for m in sent_json)
    assert any(m["type"] == "action" and m["tool"] == "get_system_vitals" for m in sent_json)
    assert sent_json[-1] == {"type": "state", "state": "idle"}
    # One audio frame per caption.
    n_caps = sum(1 for m in sent_json if m["type"] == "caption")
    assert len(sent_bytes) == n_caps
    assert n_caps >= 1


@pytest.mark.asyncio
async def test_run_turn_user_transcript_first(tmp_path):
    sent = []
    session = VoiceSession(
        brain=_FakeBrain(), stt=None, tts=_FakeTTS(),
        send_json=lambda m: sent.append(m), send_bytes=lambda b: None,
        logs_dir=str(tmp_path),
    )
    await session.run_turn("hello")
    assert sent[0] == {"type": "transcript", "role": "user", "text": "hello", "final": True}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_voice_session.py -v -p no:cacheprovider`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.voice_session'`

- [ ] **Step 3: Write minimal implementation**

Create `core/voice_session.py`:

```python
import os
import uuid
import inspect
from core import events


def is_sentence_end(text):
    return text.strip().endswith(('.', '?', '!'))


class VoiceSession:
    """Owns one conversational turn: input text -> brain stream -> word-timed TTS
    -> ordered contract events. Decoupled from FastAPI via send callables."""

    def __init__(self, brain, stt, tts, send_json, send_bytes, logs_dir="data/logs"):
        self.brain = brain
        self.stt = stt
        self.tts = tts
        self._send_json = send_json
        self._send_bytes = send_bytes
        self.logs_dir = logs_dir

    async def _send(self, fn, arg):
        # Support both sync and async send callables (FastAPI's are async).
        result = fn(arg)
        if inspect.isawaitable(result):
            await result

    async def _emit(self, event):
        await self._send(self._send_json, event)

    async def _emit_bytes(self, data):
        await self._send(self._send_bytes, data)

    async def _emit_mood(self):
        pers = self.brain.personality
        mood = pers.current_mood
        color = pers.mood_states.get(mood, {}).get("orb_color", "#5cc8ff")
        await self._emit(events.mood_event(mood, color))

    async def _synth_segment(self, text):
        os.makedirs(self.logs_dir, exist_ok=True)
        seg_id = uuid.uuid4().hex
        out = os.path.join(self.logs_dir, f"resp_{seg_id}.mp3")
        try:
            _, words = await self.tts.generate_speech_timed(text, out)
            with open(out, "rb") as f:
                audio = f.read()
            await self._emit(events.caption_event(seg_id, words, text))
            await self._emit_bytes(audio)
        except Exception as e:
            # Caption with no audio so the user can still read it.
            await self._emit(events.caption_event(seg_id, [], text, mode="sentence"))
            print(f"[VoiceSession] TTS error: {e}")
        finally:
            if os.path.exists(out):
                os.remove(out)

    async def run_turn(self, user_text):
        await self._emit(events.transcript_event("user", user_text, True))
        await self._emit_mood()
        await self._emit(events.state_event("thinking"))

        open_actions = []
        held = None
        buffer = ""
        full_reply = ""
        spoke = False

        async for token in self.brain.get_streaming_response(user_text):
            full_reply += token

            if token.startswith("[System: Executing "):
                tool = token[len("[System: Executing "):].rstrip(".]").rstrip(".")
                tool = tool.replace("...", "").strip()
                open_actions.append(tool)
                await self._emit(events.action_event(tool, "start", f"Running {tool}"))
                await self._emit(events.state_event("acting"))
                continue

            # First real text after an action closes the open chips.
            if open_actions:
                for t in open_actions:
                    await self._emit(events.action_event(t, "done", f"{t} complete"))
                open_actions = []

            buffer += token
            if is_sentence_end(buffer):
                if not spoke:
                    await self._emit(events.state_event("speaking"))
                    spoke = True
                if held:
                    await self._synth_segment(held)
                held = buffer
                buffer = ""

        # Close any actions that never got trailing text.
        for t in open_actions:
            await self._emit(events.action_event(t, "done", f"{t} complete"))

        final_text = (held or "") + buffer
        if final_text.strip():
            if not spoke:
                await self._emit(events.state_event("speaking"))
            await self._synth_segment(final_text)

        if full_reply.strip():
            await self._emit(events.transcript_event("friday", full_reply.strip(), True))

        await self._emit(events.state_event("idle"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_voice_session.py -v -p no:cacheprovider`
Expected: PASS (3 passed)

- [ ] **Step 5: Run the whole suite (no regressions)**

Run: `PYTHONPATH=. python3 -m pytest tests/ -p no:cacheprovider -q`
Expected: the 3 pre-existing failures only (`test_phase1::test_tts_generation`, `test_phase5_legion::test_legion_delegation`, `test_phase5_evolution::test_run_tests`); everything else passes.

- [ ] **Step 6: Commit**

```bash
git add core/voice_session.py tests/test_voice_session.py
git commit -m "feat(voice): add VoiceSession turn engine emitting contract events

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: Wire `/ws/voice` to `VoiceSession`

**Files:**
- Modify: `core/main.py`
- Test: import smoke + live turn

- [ ] **Step 1: Read `core/main.py`** to find the current `process_and_send_segment` function and the `@app.websocket("/ws/voice")` handler (the big `while True` loop with STT, wake-word, and the hold-one-ahead streaming).

- [ ] **Step 2: Add the import.** Near the other `from core...` imports at the top of `core/main.py`, add:

```python
from core.voice_session import VoiceSession
```

- [ ] **Step 3: Replace the websocket handler body.** Replace the ENTIRE `@app.websocket("/ws/voice")` function AND the now-unused `process_and_send_segment` helper and `is_sentence_end` helper (they move into `voice_session.py`) with:

```python
@app.websocket("/ws/voice")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    session = VoiceSession(
        brain=brain, stt=stt, tts=tts,
        send_json=websocket.send_json, send_bytes=websocket.send_bytes,
    )
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            # Text / control frames (JSON).
            if message.get("text") is not None:
                try:
                    ctrl = json.loads(message["text"])
                except (ValueError, TypeError):
                    continue
                if ctrl.get("type") == "interrupt":
                    print("[BARGE-IN] User interrupted Friday.")
                    continue
                if ctrl.get("type") == "text" and ctrl.get("content", "").strip():
                    user_text = ctrl["content"].strip()
                    print(f"[USER/text] {user_text}")
                    unlocked = brain.memory.add_episodic("user", user_text)
                    if unlocked:
                        await websocket.send_json({"type": "arg_unlocked", "flags": unlocked})
                    await session.run_turn(user_text)
                continue

            data = message.get("bytes")
            if not data:
                continue

            # Audio frame -> STT.
            temp_filename = f"data/logs/chunk_{uuid.uuid4().hex}.webm"
            os.makedirs("data/logs", exist_ok=True)
            with open(temp_filename, "wb") as f:
                f.write(data)
            try:
                transcription = stt.transcribe(temp_filename)
            except Exception as e:
                logger.error(f"Transcription error: {e}")
                transcription = ""
            if os.path.exists(temp_filename):
                os.remove(temp_filename)

            if not transcription:
                continue
            print(f"\n[TRANSCRIPTION] {transcription}")

            mode = brain.config.get("speech", {}).get("interaction_mode", "wake_word")
            is_addressed = any(kw in transcription.lower() for kw in ["friday", "hey friday", "computer"])
            is_greeting = any(transcription.lower().strip() == g for g in ["hello", "good morning", "good evening", "hi friday"])

            if mode == "wake_word" and not is_addressed and not is_greeting:
                print(f"[BACKGROUND] Recorded: {transcription}")
                brain.memory.add_episodic("background", transcription)
                continue

            print(f"[USER] {transcription}")
            unlocked = brain.memory.add_episodic("user", transcription)
            if unlocked:
                await websocket.send_json({"type": "arg_unlocked", "flags": unlocked})
            await session.run_turn(transcription)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error in voice loop: {e}")
    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
```

Note: `brain.get_streaming_response` already calls `memory.add_episodic("user", ...)` internally, so the explicit add above duplicates it as today's code did for ARG-flag capture; that pre-existing behavior is preserved intentionally.

- [ ] **Step 4: Import smoke**

Run: `PYTHONPATH=. python3 -c "import core.main; print('main imports OK')"`
Expected: `main imports OK` (no traceback).

- [ ] **Step 5: Live turn smoke (Ollama running)**

Run:
```bash
cp data/memory.json /tmp/fmem.bak 2>/dev/null
PYTHONPATH=. timeout 200 python3 -c "
import asyncio
from core.brain import FridayBrain
from core.tts import FridayTTS
from core.voice_session import VoiceSession
async def main():
    sent=[]
    s = VoiceSession(FridayBrain(), None, FridayTTS(),
                     send_json=lambda m: sent.append(m['type']), send_bytes=lambda b: None)
    await s.run_turn('Friday, introduce yourself in one short line.')
    print('EVENT_TYPES=', sent)
asyncio.run(main())
"
cp /tmp/fmem.bak data/memory.json 2>/dev/null
```
Expected: `EVENT_TYPES=` includes `transcript`, `mood`, `state` (thinking/speaking/idle), and `caption`.

- [ ] **Step 6: Commit**

```bash
git add core/main.py
git commit -m "feat(main): drive /ws/voice through VoiceSession; accept text input

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## PHASE 1 — UI shell rebuild (verify by running the app)

UI modules can't be unit-tested here. Each task ends with **manual verification** in the browser at http://localhost:8000 (`python3 launcher.py`, Ollama running). Do the verification before committing.

### Task 6: HTML structure + adaptive CSS theme + Hybrid layout

**Files:**
- Rewrite: `ui/index.html`
- Rewrite: `ui/css/style.css`

- [ ] **Step 1: Rewrite `ui/index.html`** with the new structure (orb canvas, idle caption, conversation panel, command bar, action-chip rail, modals). Keep the Three.js importmap and the nebula shader scripts from the current file.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>FRIDAY</title>
    <link rel="stylesheet" href="ui/css/style.css">
    <script type="importmap">
    { "imports": {
        "three": "https://unpkg.com/three@0.174.0/build/three.module.js",
        "three/addons/": "https://unpkg.com/three@0.174.0/examples/jsm/"
    }}
    </script>
</head>
<body data-state="idle">
    <canvas id="orb-canvas"></canvas>

    <div id="ui-layer">
        <header class="glass-panel main-header">
            <div class="wordmark">FRIDAY<span class="dot"></span></div>
            <div class="header-actions">
                <span class="state-label" id="state-label">STANDBY</span>
                <button class="icon-btn" id="settings-btn" title="Settings">⚙</button>
                <div class="status-dot" id="status-dot"></div>
            </div>
        </header>

        <!-- Idle/floating caption (cinematic, center-bottom) -->
        <div id="caption-stage"><div id="caption-line"></div></div>

        <!-- Action chips rail -->
        <div id="action-rail"></div>

        <!-- Hybrid conversation panel (grows on turn, recedes on idle) -->
        <aside class="glass-panel convo-panel" id="convo-panel">
            <header class="convo-head">CONVERSATION</header>
            <div class="convo-scroll" id="convo-scroll"></div>
        </aside>

        <!-- Command bar: mic + text input -->
        <div class="command-bar">
            <button class="mic-btn" id="mic-trigger" title="Talk">
                <svg class="mic-icon" viewBox="0 0 24 24"><path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/><path d="M17 11c0 2.76-2.34 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/></svg>
                <svg class="stop-icon" viewBox="0 0 24 24"><path d="M6 6h12v12H6z"/></svg>
            </button>
            <input id="text-input" type="text" placeholder='Talk, or type to Friday…' autocomplete="off" />
            <button class="send-btn" id="send-btn" title="Send">➤</button>
        </div>
    </div>

    <!-- Settings Modal -->
    <div id="settings-modal" class="modal hidden">
        <div class="glass-panel modal-content">
            <h2>System Configuration</h2>
            <div class="settings-grid" id="settings-form"></div>
            <h2 style="margin-top:28px">Security Permissions</h2>
            <div class="settings-grid" id="permissions-form"></div>
            <div class="modal-actions">
                <button id="save-settings" class="action-btn">APPLY</button>
                <button id="close-settings" class="action-btn secondary">CLOSE</button>
            </div>
        </div>
    </div>

    <!-- Permission toast -->
    <div id="permission-toast" class="toast hidden">
        <div class="glass-panel toast-content">
            <p id="toast-message">Permission Request</p>
            <div class="toast-actions">
                <button id="toast-allow" class="action-btn">ALLOW</button>
                <button id="toast-deny" class="action-btn secondary">DENY</button>
            </div>
        </div>
    </div>

    <script id="nebula-vs" type="x-shader/x-vertex">
        varying vec2 vUv;
        void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }
    </script>
    <script id="nebula-fs" type="x-shader/x-fragment">
        uniform float uTime; uniform vec3 uColor1; uniform vec3 uColor2; varying vec2 vUv;
        vec3 permute(vec3 x){ return mod(((x*34.0)+1.0)*x, 289.0); }
        float snoise(vec2 v){
            const vec4 C = vec4(0.211324865405187,0.366025403784439,-0.577350269189626,0.024390243902439);
            vec2 i=floor(v+dot(v,C.yy)); vec2 x0=v-i+dot(i,C.xx); vec2 i1;
            i1=(x0.x>x0.y)?vec2(1.0,0.0):vec2(0.0,1.0); vec4 x12=x0.xyxy+C.xxzz; x12.xy-=i1;
            i=mod(i,289.0); vec3 p=permute(permute(i.y+vec3(0.0,i1.y,1.0))+i.x+vec3(0.0,i1.x,1.0));
            vec3 m=max(0.5-vec3(dot(x0,x0),dot(x12.xy,x12.xy),dot(x12.zw,x12.zw)),0.0); m=m*m; m=m*m;
            vec3 x=2.0*fract(p*C.www)-1.0; vec3 h=abs(x)-0.5; vec3 ox=floor(x+0.5); vec3 a0=x-ox;
            m*=1.79284291400159-0.85373472095314*(a0*a0+h*h);
            vec3 g; g.x=a0.x*x0.x+h.x*x0.y; g.yz=a0.yz*x12.xz+h.yz*x12.yw; return 130.0*dot(m,g);
        }
        void main(){
            float n=snoise(vUv*3.0+uTime*0.1); n+=0.5*snoise(vUv*6.0-uTime*0.05);
            float mask=smoothstep(0.2,0.8,n); vec3 color=mix(uColor1,uColor2,mask);
            gl_FragColor=vec4(color, mask*0.3);
        }
    </script>
    <script type="module" src="ui/js/orb.js"></script>
    <script type="module" src="ui/js/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: Rewrite `ui/css/style.css`** with the adaptive theme + Hybrid layout. The accent is driven by the CSS variable `--accent` which `orb.js`/`app.js` update at runtime from mood/state.

```css
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
* { margin:0; padding:0; box-sizing:border-box; }
:root{
  --accent:#5cc8ff;            /* arc-reactor blue base; updated at runtime */
  --bg:#06070d;
  --panel:rgba(124,180,255,0.04);
  --border:rgba(124,180,255,0.14);
  --text-dim:rgba(255,255,255,0.45);
}
body,html{ width:100%; height:100%; overflow:hidden; background:var(--bg);
  font-family:'Inter',sans-serif; color:#fff; }
.glass-panel{ background:var(--panel); backdrop-filter:blur(16px); -webkit-backdrop-filter:blur(16px);
  border:1px solid var(--border); border-radius:14px; }
#orb-canvas{ position:absolute; inset:0; width:100%; height:100%; z-index:1; }
#ui-layer{ position:absolute; inset:0; z-index:10; pointer-events:none; display:flex; flex-direction:column; }

/* Header */
.main-header{ height:54px; margin:18px; display:flex; align-items:center; justify-content:space-between;
  padding:0 18px; pointer-events:auto; }
.wordmark{ font-weight:700; letter-spacing:.22em; font-size:16px; display:flex; align-items:center; }
.wordmark .dot{ width:6px; height:6px; background:var(--accent); border-radius:50%; margin-left:8px;
  box-shadow:0 0 10px var(--accent); transition:background .5s, box-shadow .5s; }
.header-actions{ display:flex; align-items:center; gap:14px; }
.state-label{ font-size:10px; letter-spacing:.18em; color:var(--text-dim); }
.icon-btn{ background:transparent; border:none; color:#fff; font-size:18px; cursor:pointer;
  padding:5px 8px; border-radius:8px; transition:background .3s; }
.icon-btn:hover{ background:rgba(255,255,255,.08); }
.status-dot{ width:9px; height:9px; border-radius:50%; background:#444; transition:all .3s; }
body[data-state="listening"] .status-dot{ background:var(--accent); box-shadow:0 0 10px var(--accent); animation:pulse 1.4s infinite; }
body[data-state="thinking"] .status-dot,
body[data-state="acting"] .status-dot{ background:#a855f7; box-shadow:0 0 10px #a855f7; }
body[data-state="speaking"] .status-dot{ background:var(--accent); box-shadow:0 0 12px var(--accent); }
@keyframes pulse{ 0%{transform:scale(1);opacity:1} 50%{transform:scale(1.25);opacity:.6} 100%{transform:scale(1);opacity:1} }

/* Floating caption (cinematic, center) */
#caption-stage{ position:absolute; left:0; right:0; bottom:140px; display:flex; justify-content:center;
  pointer-events:none; padding:0 12%; }
#caption-line{ font-size:22px; font-weight:300; letter-spacing:.01em; text-align:center; line-height:1.45;
  max-width:760px; opacity:0; transition:opacity .4s; text-shadow:0 0 18px rgba(0,0,0,.6); }
#caption-line.show{ opacity:1; }
#caption-line .w{ color:var(--text-dim); transition:color .12s, text-shadow .12s; }
#caption-line .w.lit{ color:#fff; text-shadow:0 0 14px var(--accent); }

/* Action chips */
#action-rail{ position:absolute; left:0; right:0; bottom:200px; display:flex; gap:8px; justify-content:center;
  pointer-events:none; flex-wrap:wrap; }
.chip{ font-size:11px; letter-spacing:.06em; padding:6px 12px; border-radius:20px;
  background:rgba(168,85,247,.12); border:1px solid rgba(168,85,247,.35); color:#e9d5ff;
  display:flex; align-items:center; gap:7px; opacity:0; transform:translateY(6px);
  transition:opacity .3s, transform .3s; }
.chip.show{ opacity:1; transform:translateY(0); }
.chip.done{ background:rgba(45,212,171,.12); border-color:rgba(45,212,171,.35); color:#bdfff0; }
.chip.error{ background:rgba(239,68,68,.12); border-color:rgba(239,68,68,.4); color:#fecaca; }
.chip .spin{ width:9px; height:9px; border:2px solid currentColor; border-top-color:transparent;
  border-radius:50%; animation:spin .7s linear infinite; }
.chip.done .spin,.chip.error .spin{ display:none; }
@keyframes spin{ to{ transform:rotate(360deg); } }

/* Hybrid conversation panel */
.convo-panel{ position:fixed; right:18px; top:90px; bottom:150px; width:340px; pointer-events:auto;
  display:flex; flex-direction:column; transform:translateX(380px); opacity:0;
  transition:transform .5s cubic-bezier(.16,1,.3,1), opacity .4s; }
.convo-panel.open{ transform:translateX(0); opacity:1; }
.convo-head{ font-size:10px; letter-spacing:.18em; color:var(--text-dim); padding:16px 18px 10px; }
.convo-scroll{ flex:1; overflow-y:auto; padding:0 14px 16px; display:flex; flex-direction:column; gap:10px; }
.convo-scroll::-webkit-scrollbar{ width:5px; } .convo-scroll::-webkit-scrollbar-thumb{ background:var(--border); border-radius:3px; }
.bubble{ max-width:90%; padding:9px 12px; border-radius:12px; font-size:13px; line-height:1.5; word-wrap:break-word; }
.bubble.user{ align-self:flex-end; background:rgba(124,180,255,.16); color:#dbeaff; border-bottom-right-radius:4px; }
.bubble.friday{ align-self:flex-start; background:rgba(255,255,255,.06); color:rgba(255,255,255,.9); border-bottom-left-radius:4px; }
.bubble .who{ font-size:9px; letter-spacing:.12em; color:var(--text-dim); margin-bottom:3px; }

/* Command bar */
.command-bar{ position:fixed; bottom:34px; left:50%; transform:translateX(-50%); display:flex; align-items:center;
  gap:12px; pointer-events:auto; }
.mic-btn{ width:60px; height:60px; border-radius:50%; background:#0d0f17; border:1px solid var(--border);
  cursor:pointer; display:flex; align-items:center; justify-content:center; position:relative; transition:all .3s; flex:none; }
.mic-btn.active{ border-color:var(--accent); box-shadow:0 0 26px color-mix(in srgb, var(--accent) 50%, transparent); }
.mic-btn svg{ width:24px; height:24px; fill:#fff; position:absolute; }
.mic-btn .stop-icon{ display:none; }
.mic-btn.active .mic-icon{ display:none; } .mic-btn.active .stop-icon{ display:block; }
.mic-btn::after{ content:''; position:absolute; inset:-1px; border-radius:50%; border:2px solid var(--accent); opacity:0; }
.mic-btn.active::after{ animation:ring 1.4s infinite cubic-bezier(.16,1,.3,1); }
@keyframes ring{ 0%{transform:scale(1);opacity:.9} 100%{transform:scale(1.5);opacity:0} }
#text-input{ width:380px; max-width:46vw; background:rgba(13,15,23,.85); border:1px solid var(--border);
  border-radius:24px; padding:13px 18px; color:#fff; font-size:14px; font-family:inherit; outline:none; transition:border .3s; }
#text-input:focus{ border-color:var(--accent); }
.send-btn{ width:44px; height:44px; border-radius:50%; background:var(--accent); color:#04121f; border:none;
  font-size:16px; cursor:pointer; flex:none; transition:transform .2s; }
.send-btn:hover{ transform:scale(1.08); }

/* Modals/toast (kept from v1, restyled) */
.modal{ position:fixed; inset:0; z-index:100; display:flex; align-items:center; justify-content:center; background:rgba(0,0,0,.55); }
.modal-content{ width:520px; padding:30px; pointer-events:auto; }
.modal-content h2{ font-weight:300; letter-spacing:.08em; margin-bottom:18px; }
.settings-grid{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.modal-actions{ display:flex; gap:12px; margin-top:24px; }
.action-btn{ padding:10px 20px; background:var(--accent); border:none; border-radius:6px; color:#04121f; font-weight:600; cursor:pointer; font-size:12px; }
.action-btn.secondary{ background:transparent; border:1px solid var(--border); color:#fff; }
.toast{ position:fixed; bottom:120px; left:50%; transform:translateX(-50%); z-index:200; width:420px; }
.toast-content{ padding:20px; text-align:center; pointer-events:auto; }
.toast-actions{ display:flex; justify-content:center; gap:12px; margin-top:14px; }
.hidden{ display:none !important; }

/* ARG glitch (kept) */
.glitch-mode{ animation:glitch .3s cubic-bezier(.25,.46,.45,.94) both infinite; }
@keyframes glitch{ 0%{transform:translate(0)} 20%{transform:translate(-2px,2px)} 40%{transform:translate(-2px,-2px)}
  60%{transform:translate(2px,2px)} 80%{transform:translate(2px,-2px)} 100%{transform:translate(0)} }
```

- [ ] **Step 3: Manual verification**

This task changes structure; `orb.js`/`app.js` still being the old versions may error. That's expected until Tasks 7–8. Just confirm the file is valid HTML/CSS by opening it — the page should at least render the header "FRIDAY", the command bar with mic + text box, with a dark background. (Full behavior verified after Task 8.)

- [ ] **Step 4: Commit**

```bash
git add ui/index.html ui/css/style.css
git commit -m "feat(ui): restructure HTML + adaptive Hybrid theme

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 7: Adaptive orb (state channel + mood color + voice reactivity)

**Files:**
- Rewrite: `ui/js/orb.js`

- [ ] **Step 1: Rewrite `ui/js/orb.js`.** Keep the existing starfield/nebula/rings/bloom foundation; add a state channel and mood color, expose `window.Orb`.

```javascript
import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

let scene, camera, renderer, composer, orb, starfield, nebula;
let rings = [];
const uniforms = {
    uTime: { value: 0 },
    uVoiceBright: { value: 0.0 },
    uColor1: { value: new THREE.Color('#5cc8ff') },
    uColor2: { value: new THREE.Color('#8B5CF6') },
};

// State channel drives motion/intensity independent of mood color.
const STATES = {
    idle:      { spin: 0.4, pulse: 1.0, bloom: 1.0 },
    listening: { spin: 0.8, pulse: 1.4, bloom: 1.3 },
    thinking:  { spin: 2.2, pulse: 1.1, bloom: 1.2 },
    speaking:  { spin: 1.0, pulse: 1.2, bloom: 1.6 },
    acting:    { spin: 2.6, pulse: 1.3, bloom: 1.4 },
};
let current = STATES.idle;
let bloomPass;

function init() {
    scene = new THREE.Scene();
    camera = new THREE.PerspectiveCamera(75, innerWidth / innerHeight, 0.1, 1000);
    camera.position.z = 5;
    renderer = new THREE.WebGLRenderer({ canvas: document.getElementById('orb-canvas'), antialias: true, alpha: true });
    renderer.setSize(innerWidth, innerHeight);
    renderer.setPixelRatio(devicePixelRatio);

    const starGeo = new THREE.BufferGeometry();
    const pos = new Float32Array(2000 * 3);
    for (let i = 0; i < pos.length; i++) pos[i] = (Math.random() - 0.5) * 20;
    starGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    starfield = new THREE.Points(starGeo, new THREE.PointsMaterial({ size: 0.02, color: 0xffffff }));
    scene.add(starfield);

    const nebulaMat = new THREE.ShaderMaterial({
        uniforms, vertexShader: document.getElementById('nebula-vs').textContent,
        fragmentShader: document.getElementById('nebula-fs').textContent,
        transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
    });
    nebula = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), nebulaMat);
    nebula.position.z = -2; scene.add(nebula);

    const coreMat = new THREE.ShaderMaterial({
        uniforms,
        vertexShader: `varying vec3 vNormal; varying vec3 vPosition;
            void main(){ vNormal=normalize(normalMatrix*normal); vPosition=position;
            gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }`,
        fragmentShader: `uniform float uTime; uniform float uVoiceBright; uniform vec3 uColor1;
            varying vec3 vNormal; varying vec3 vPosition;
            void main(){
                float fresnel=pow(1.0-dot(vNormal,vec3(0.0,0.0,1.0)),3.0);
                float scan=sin(vPosition.y*50.0-uTime*10.0)*0.1+0.9;
                float pulse=sin(uTime*2.0)*0.1+0.9;
                float alpha=(fresnel+0.2)*(uVoiceBright*2.0+0.5)*scan*pulse;
                gl_FragColor=vec4(uColor1, alpha);
            }`,
        transparent: true, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
    });
    orb = new THREE.Mesh(new THREE.SphereGeometry(1, 64, 64), coreMat);
    scene.add(orb);

    [{ r: 1.2, s: 0.5, a: 'z', t: 0.02 }, { r: 1.4, s: -0.3, a: 'y', t: 0.01 }, { r: 1.6, s: 0.8, a: 'x', t: 0.015 }]
      .forEach(d => {
        const ring = new THREE.Mesh(new THREE.TorusGeometry(d.r, d.t, 16, 100),
            new THREE.MeshBasicMaterial({ color: uniforms.uColor1.value, transparent: true, opacity: 0.4, blending: THREE.AdditiveBlending }));
        rings.push({ mesh: ring, speed: d.s, axis: d.a }); scene.add(ring);
      });

    bloomPass = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 1.5, 0.4, 0.1);
    composer = new EffectComposer(renderer);
    composer.addPass(new RenderPass(scene, camera));
    composer.addPass(bloomPass);

    addEventListener('resize', onResize);
    animate();
}
function onResize() {
    camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
    renderer.setSize(innerWidth, innerHeight); composer.setSize(innerWidth, innerHeight);
}
let focused = true;
addEventListener('focus', () => focused = true);
addEventListener('blur', () => focused = false);

function animate() {
    requestAnimationFrame(animate);
    if (!focused && Math.random() > 0.15) return;
    uniforms.uTime.value += 0.01;
    starfield.rotation.y += 0.0005;
    bloomPass.strength = 1.5 * current.bloom;
    rings.forEach(r => {
        r.mesh.rotation[r.axis] += r.speed * 0.02 * current.spin;
        const scale = 1 + uniforms.uVoiceBright.value * 0.2;
        r.mesh.scale.set(scale, scale, scale);
        r.mesh.material.color.copy(uniforms.uColor1.value);
    });
    composer.render();
}
init();

// Public API consumed by app.js
window.Orb = {
    setVoiceBright: (v) => { uniforms.uVoiceBright.value = v; },
    setState: (name) => { current = STATES[name] || STATES.idle; },
    setColor: (hex) => {
        const c = new THREE.Color(hex);
        uniforms.uColor1.value.copy(c);
        const hsl = {}; c.getHSL(hsl);
        uniforms.uColor2.value.setHSL((hsl.h + 0.5) % 1, 0.8, 0.5);
        document.documentElement.style.setProperty('--accent', hex);
    },
};
// Back-compat shims (in case anything still calls the old names)
window.setVoiceBright = (v) => window.Orb.setVoiceBright(v);
window.setOrbColor = (hex) => window.Orb.setColor(hex);
```

- [ ] **Step 2: Manual verification (after Task 8 too, but check now):**

Run `python3 launcher.py`, open http://localhost:8000. The orb renders with arc-reactor-blue core, rings, bloom, drifting nebula. In the browser console run `Orb.setState('thinking')` → rings spin faster; `Orb.setColor('#8B5CF6')` → orb + `--accent` turn violet. No console errors from orb.js.

- [ ] **Step 3: Commit**

```bash
git add ui/js/orb.js
git commit -m "feat(ui): adaptive orb with state channel and mood color API

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 8: App core — WebSocket client, event router, audio, mic, text input, barge-in

**Files:**
- Rewrite: `ui/js/app.js`

This module owns the socket and delegates rendering to `window.Conversation`, `window.Captions`, `window.Hud` (created in Tasks 9–11). Until those exist it guards calls with `?.`, so the app runs after this task with captions/transcript wired in subsequent tasks.

- [ ] **Step 1: Rewrite `ui/js/app.js`:**

```javascript
let socket, mediaRecorder, micStream;
let audioCtx, micAnalyser, bargeFrames = 0;
const BARGE_RMS = 0.08;

let audioQueue = [];          // {buffer, segment_id, words, mode, text}
let isPlaying = false;
let pendingCaption = null;    // caption event awaiting its audio frame

function setState(state) {
    document.body.dataset.state = state;
    window.Orb?.setState(state);
    window.Hud?.setStateLabel(state);
}

function connect() {
    socket = new WebSocket(`ws://${location.host}/ws/voice`);
    socket.binaryType = 'arraybuffer';
    socket.onmessage = async (e) => {
        if (typeof e.data === 'string') return handleEvent(JSON.parse(e.data));
        // binary: audio frame belongs to the most recent caption event
        if (pendingCaption) {
            audioQueue.push({ buffer: e.data, ...pendingCaption });
            pendingCaption = null;
            if (!isPlaying) pump();
        }
    };
    socket.onclose = () => setTimeout(connect, 1000);
}

function handleEvent(msg) {
    switch (msg.type) {
        case 'state': setState(msg.state); if (msg.state !== 'idle') window.Conversation?.open(); break;
        case 'mood': window.Orb?.setColor(msg.orb_color); break;
        case 'transcript':
            window.Conversation?.addMessage(msg.role, msg.text);
            break;
        case 'caption':
            pendingCaption = { segment_id: msg.segment_id, words: msg.words, mode: msg.mode, text: msg.text };
            break;
        case 'action': window.Hud?.action(msg); break;
        case 'arg_unlocked': window.Hud?.glitch(); break;
        case 'status': /* legacy no-op */ break;
    }
}

async function pump() {
    if (!audioQueue.length) { isPlaying = false; if (document.body.dataset.state === 'speaking') setState('idle'); return; }
    isPlaying = true;
    const seg = audioQueue.shift();
    try { await playSegment(seg); } catch (err) { console.error('playback', err); }
    pump();
}

async function playSegment(seg) {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const buf = await audioCtx.decodeAudioData(seg.buffer.slice(0));
    const src = audioCtx.createBufferSource();
    const analyser = audioCtx.createAnalyser();
    src.buffer = buf; src.connect(analyser); analyser.connect(audioCtx.destination);
    analyser.fftSize = 256;
    const data = new Uint8Array(analyser.frequencyBinCount);
    window.Captions?.play(seg, buf.duration * 1000);

    return new Promise((resolve) => {
        src.onended = () => { window.Orb?.setVoiceBright(0); resolve(); };
        src.start(0);
        (function tick() {
            if (!isPlaying) return;
            analyser.getByteFrequencyData(data);
            const avg = data.reduce((a, b) => a + b, 0) / data.length;
            window.Orb?.setVoiceBright(avg / 128);
            requestAnimationFrame(tick);
        })();
    });
}

function stopSpeaking() {
    audioQueue = []; pendingCaption = null; isPlaying = false;
    window.Captions?.clear();
    setState('idle');
    if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: 'interrupt' }));
}

// ---- Mic ----
async function startRecording() {
    micStream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
    startMicVAD(micStream);
    const opts = { mimeType: 'audio/webm;codecs=opus' };
    if (!MediaRecorder.isTypeSupported(opts.mimeType)) delete opts.mimeType;
    mediaRecorder = new MediaRecorder(micStream, opts);
    mediaRecorder.ondataavailable = (ev) => {
        if (ev.data.size > 0 && socket?.readyState === WebSocket.OPEN) socket.send(ev.data);
    };
    const iv = setInterval(() => {
        if (mediaRecorder.state === 'recording') { mediaRecorder.stop(); mediaRecorder.start(); }
        else clearInterval(iv);
    }, 3000);
    mediaRecorder.start();
    setState('listening');
}
function stopRecording() {
    micAnalyser = null;
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop(); mediaRecorder.stream.getTracks().forEach(t => t.stop());
    }
    setState('idle');
}
function startMicVAD(stream) {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const src = ctx.createMediaStreamSource(stream);
    micAnalyser = ctx.createAnalyser(); micAnalyser.fftSize = 512; src.connect(micAnalyser);
    const buf = new Uint8Array(micAnalyser.fftSize);
    (function tick() {
        if (!micAnalyser) return;
        micAnalyser.getByteTimeDomainData(buf);
        let s = 0; for (let i = 0; i < buf.length; i++) { const v = (buf[i] - 128) / 128; s += v * v; }
        const rms = Math.sqrt(s / buf.length);
        if (isPlaying && rms > BARGE_RMS) { if (++bargeFrames >= 3) { stopSpeaking(); bargeFrames = 0; } }
        else bargeFrames = 0;
        requestAnimationFrame(tick);
    })();
}

// ---- Text input ----
function sendText() {
    const input = document.getElementById('text-input');
    const content = input.value.trim();
    if (!content || socket?.readyState !== WebSocket.OPEN) return;
    window.Conversation?.open();
    socket.send(JSON.stringify({ type: 'text', content }));
    input.value = '';
}

// ---- Wiring ----
let listening = false;
function toggleMic() {
    listening = !listening;
    document.getElementById('mic-trigger').classList.toggle('active', listening);
    listening ? startRecording() : stopRecording();
}
window.addEventListener('DOMContentLoaded', () => {
    document.getElementById('mic-trigger').addEventListener('click', toggleMic);
    document.getElementById('send-btn').addEventListener('click', sendText);
    document.getElementById('text-input').addEventListener('keydown', (e) => { if (e.key === 'Enter') sendText(); });
    window.Hud?.init();
    connect();
});
```

- [ ] **Step 2: Manual verification (Ollama running):**

`python3 launcher.py` → http://localhost:8000. Type "Friday, introduce yourself" in the text box, press Enter. Expected: orb goes thinking→speaking, audio plays, orb brightens with her voice, returns to idle. No console errors. (Transcript bubbles + karaoke come online in Tasks 9–10; for now confirm audio + states + text send work.)

- [ ] **Step 3: Commit**

```bash
git add ui/js/app.js
git commit -m "feat(ui): WebSocket event router, audio, mic, text input, barge-in

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 9: Conversation transcript + Hybrid panel choreography

**Files:**
- Create: `ui/js/conversation.js`
- Modify: `ui/index.html` (add the module script tag)

- [ ] **Step 1: Create `ui/js/conversation.js`:**

```javascript
// Transcript model + Hybrid panel show/recede choreography.
const panel = () => document.getElementById('convo-panel');
const scroll = () => document.getElementById('convo-scroll');
let recedeTimer = null;

function addMessage(role, text) {
    const who = role === 'user' ? 'YOU' : 'FRIDAY';
    const div = document.createElement('div');
    div.className = `bubble ${role === 'user' ? 'user' : 'friday'}`;
    div.innerHTML = `<div class="who">${who}</div>${escapeHtml(text)}`;
    scroll().appendChild(div);
    scroll().scrollTop = scroll().scrollHeight;
    open();
}
function open() {
    panel().classList.add('open');
    if (recedeTimer) clearTimeout(recedeTimer);
}
function scheduleRecede() {
    if (recedeTimer) clearTimeout(recedeTimer);
    recedeTimer = setTimeout(() => panel().classList.remove('open'), 12000);
}
function escapeHtml(s) {
    return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

window.Conversation = { addMessage, open, scheduleRecede };
```

- [ ] **Step 2: Wire idle-recede.** In `ui/js/app.js`, in `handleEvent`, in the `case 'state':` branch, after the existing body add a recede trigger on idle:

Change the `case 'state':` line to:

```javascript
        case 'state':
            setState(msg.state);
            if (msg.state !== 'idle') window.Conversation?.open();
            else window.Conversation?.scheduleRecede();
            break;
```

- [ ] **Step 3: Add the script tag.** In `ui/index.html`, change the trailing module scripts so `conversation.js` loads before `app.js`:

```html
    <script type="module" src="ui/js/orb.js"></script>
    <script type="module" src="ui/js/conversation.js"></script>
    <script type="module" src="ui/js/app.js"></script>
```

- [ ] **Step 4: Manual verification:** Send a text message. The conversation panel slides in from the right; a YOU bubble then a FRIDAY bubble appear; panel recedes ~12s after Friday returns to idle. Sending again re-opens it.

- [ ] **Step 5: Commit**

```bash
git add ui/js/conversation.js ui/index.html
git commit -m "feat(ui): transcript model + Hybrid panel choreography

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 10: Karaoke captions + sentence fallback

**Files:**
- Create: `ui/js/captions.js`
- Modify: `ui/index.html` (add the module script tag before app.js)

- [ ] **Step 1: Create `ui/js/captions.js`:**

```javascript
// Word-sync ("karaoke") caption renderer with sentence-fade fallback.
const stage = () => document.getElementById('caption-line');
let timers = [];

function clear() {
    timers.forEach(clearTimeout); timers = [];
    const el = stage(); el.classList.remove('show'); el.innerHTML = '';
}

function play(seg, audioMs) {
    clear();
    const el = stage();
    if (seg.mode === 'word' && seg.words && seg.words.length) {
        el.innerHTML = seg.words.map((w, i) => `<span class="w" data-i="${i}">${escapeHtml(w.word)}</span>`).join(' ');
        el.classList.add('show');
        seg.words.forEach((w, i) => {
            timers.push(setTimeout(() => {
                const span = el.querySelector(`.w[data-i="${i}"]`);
                if (span) span.classList.add('lit');
            }, w.offset_ms));
        });
    } else {
        // Sentence fade fallback
        el.innerHTML = `<span class="w lit">${escapeHtml(seg.text)}</span>`;
        el.classList.add('show');
    }
    // Fade caption out shortly after audio ends.
    timers.push(setTimeout(() => el.classList.remove('show'), (audioMs || 2000) + 600));
}

function escapeHtml(s) {
    return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

window.Captions = { play, clear };
```

- [ ] **Step 2: Add the script tag** in `ui/index.html` (before `app.js`):

```html
    <script type="module" src="ui/js/orb.js"></script>
    <script type="module" src="ui/js/conversation.js"></script>
    <script type="module" src="ui/js/captions.js"></script>
    <script type="module" src="ui/js/app.js"></script>
```

- [ ] **Step 3: Manual verification:** Send a message. As Friday speaks, the floating caption shows her words and they illuminate one-by-one roughly in sync with the voice. If word timings are absent, the full sentence shows lit (fallback). Caption fades after the segment.

- [ ] **Step 4: Commit**

```bash
git add ui/js/captions.js ui/index.html
git commit -m "feat(ui): karaoke word-sync captions with sentence fallback

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 11: HUD — action chips, status label, vitals, settings/permissions

**Files:**
- Create: `ui/js/hud.js`
- Modify: `ui/index.html` (add the module script tag before app.js)

- [ ] **Step 1: Create `ui/js/hud.js`** (action chips + state label + glitch + settings/permission modals + vitals; ports the modal/vitals logic from the old app.js):

```javascript
const rail = () => document.getElementById('action-rail');
const chips = {};

function setStateLabel(state) {
    const map = { idle: 'STANDBY', listening: 'LISTENING', thinking: 'THINKING', speaking: 'SPEAKING', acting: 'WORKING' };
    document.getElementById('state-label').textContent = map[state] || state.toUpperCase();
}

function action(msg) {
    let chip = chips[msg.tool];
    if (msg.phase === 'start') {
        if (!chip) {
            chip = document.createElement('div');
            chip.className = 'chip';
            chip.innerHTML = `<span class="spin"></span><span class="lbl"></span>`;
            rail().appendChild(chip);
            chips[msg.tool] = chip;
        }
        chip.querySelector('.lbl').textContent = msg.label;
        requestAnimationFrame(() => chip.classList.add('show'));
    } else if (chip) {
        chip.classList.add(msg.phase === 'error' ? 'error' : 'done');
        chip.querySelector('.lbl').textContent = msg.label;
        setTimeout(() => { chip.classList.remove('show'); setTimeout(() => chip.remove(), 400); delete chips[msg.tool]; }, 2500);
    }
}

function glitch() {
    document.body.classList.add('glitch-mode');
    setTimeout(() => document.body.classList.remove('glitch-mode'), 3000);
}

// ---- Settings + permissions (ported from v1) ----
function init() {
    document.getElementById('settings-btn').addEventListener('click', openSettings);
    document.getElementById('close-settings').addEventListener('click', () => modal().classList.add('hidden'));
    document.getElementById('save-settings').addEventListener('click', saveSettings);
    setInterval(updateVitals, 2500);
}
const modal = () => document.getElementById('settings-modal');
async function openSettings() {
    const cfg = await (await fetch('/api/config')).json();
    renderSettings(cfg);
    const perms = await (await fetch('/api/permissions')).json();
    renderPermissions(perms);
    modal().classList.remove('hidden');
}
function renderSettings(cfg) {
    const form = document.getElementById('settings-form'); form.innerHTML = '';
    for (const section in cfg) {
        if (typeof cfg[section] !== 'object' || cfg[section] === null) continue;
        for (const key in cfg[section]) {
            const label = document.createElement('label'); label.textContent = `${section}.${key}`; label.style.fontSize = '11px';
            const input = document.createElement('input'); input.type = 'text'; input.value = cfg[section][key];
            input.dataset.section = section; input.dataset.key = key;
            input.style.cssText = 'background:rgba(255,255,255,.08);border:1px solid var(--border);color:#fff;padding:6px;border-radius:6px';
            form.appendChild(label); form.appendChild(input);
        }
    }
}
function renderPermissions(perms) {
    const form = document.getElementById('permissions-form'); form.innerHTML = '';
    if (typeof perms !== 'object') return;
    for (const key in perms) {
        const label = document.createElement('label'); label.textContent = key.replace(/_/g, ' '); label.style.fontSize = '11px';
        const sel = document.createElement('select'); sel.dataset.key = key;
        ['allow', 'ask', 'deny'].forEach(o => { const op = document.createElement('option'); op.value = o; op.textContent = o.toUpperCase(); if (o === perms[key]) op.selected = true; sel.appendChild(op); });
        sel.style.cssText = 'background:rgba(255,255,255,.08);border:1px solid var(--border);color:#fff;padding:6px;border-radius:6px';
        form.appendChild(label); form.appendChild(sel);
    }
}
async function saveSettings() {
    const cfg = {};
    document.querySelectorAll('#settings-form input').forEach(i => {
        const { section, key } = i.dataset; cfg[section] = cfg[section] || {};
        let v = i.value; if (v !== '' && !isNaN(v)) v = parseFloat(v); cfg[section][key] = v;
    });
    await fetch('/api/config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(cfg) });
    const perms = {}; document.querySelectorAll('#permissions-form select').forEach(s => perms[s.dataset.key] = s.value);
    await fetch('/api/permissions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(perms) });
    modal().classList.add('hidden');
}
async function updateVitals() {
    try {
        const v = await (await fetch('/api/vitals')).json();
        // Vitals are surfaced via the orb subtly; expose for future panels.
        window.__vitals = v;
    } catch (e) { /* ignore */ }
}

// Permission approval toast (driven if a tool returns PENDING_APPROVAL via caption text)
function requestApproval(perm) {
    const toast = document.getElementById('permission-toast');
    document.getElementById('toast-message').textContent = `Friday requests permission: ${perm.toUpperCase()}`;
    toast.classList.remove('hidden');
    document.getElementById('toast-allow').onclick = async () => { await setPerm(perm, 'allow'); toast.classList.add('hidden'); };
    document.getElementById('toast-deny').onclick = async () => { await setPerm(perm, 'deny'); toast.classList.add('hidden'); };
}
async function setPerm(perm, val) {
    await fetch('/api/permissions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ [perm]: val }) });
}

window.Hud = { init, action, glitch, setStateLabel, requestApproval };
```

- [ ] **Step 2: Add the script tag** in `ui/index.html` (before `app.js`):

```html
    <script type="module" src="ui/js/orb.js"></script>
    <script type="module" src="ui/js/conversation.js"></script>
    <script type="module" src="ui/js/captions.js"></script>
    <script type="module" src="ui/js/hud.js"></script>
    <script type="module" src="ui/js/app.js"></script>
```

- [ ] **Step 3: Full integration verification (Ollama running):**

`python3 launcher.py` → http://localhost:8000. Verify the complete loop:
1. State label cycles STANDBY → THINKING → SPEAKING → STANDBY on a turn.
2. Settings gear opens the modal; values load; APPLY persists (no console error).
3. Ask something that triggers a tool ("Friday, what's my system status?") → a purple action chip appears and resolves to green.
4. Text and voice both produce captions + transcript bubbles + audio.
5. Barge-in: talk over Friday → she stops.

- [ ] **Step 4: Commit**

```bash
git add ui/js/hud.js ui/index.html
git commit -m "feat(ui): HUD action chips, status, settings/permissions, vitals

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] **Backend suite green (besides the 3 known pre-existing failures):**

Run: `PYTHONPATH=. python3 -m pytest tests/ -p no:cacheprovider -q`
Expected: new tests pass (tts_timed 3, events 6, voice_session 3); only the 3 pre-existing failures remain.

- [ ] **Full app demo:** one voice turn and one text turn, each showing: orb state changes + mood color, karaoke caption, transcript bubble, audio, and (for a tool request) an action chip. Barge-in works.

- [ ] **Remove dead files if unreferenced:** `ui/js/neural.js` is no longer imported. Leave it in place (out of scope) unless asked.

---

## Self-Review (completed by plan author)

- **Spec coverage:** Hybrid layout → Tasks 6, 9. Adaptive orb (mood+state) → Task 7 (+ mood event Tasks 4–5). Voice+text input → Tasks 6, 8. Karaoke captions + fallback → Tasks 1–2, 10 (+ caption_event Task 3). Conversation engine + event contract → Tasks 3–5. Action chips/agency-visibility scaffold → Tasks 4, 11 (agency tools themselves are Phases 3–4, separate plan). Error handling (caption fallback, TTS failure, barge-in) → Tasks 4, 8, 10. Testing approach → backend TDD Tasks 1,3,4; UI manual verify.
- **Placeholder scan:** none — all steps contain full code/commands.
- **Type consistency:** event shapes identical across `core/events.py` (Task 3), `VoiceSession` emissions (Task 4), and UI `handleEvent` (Task 8). Orb API `window.Orb.{setState,setColor,setVoiceBright}` consistent across Tasks 7–8. `window.Conversation.{addMessage,open,scheduleRecede}`, `window.Captions.{play,clear}`, `window.Hud.{init,action,glitch,setStateLabel,requestApproval}` consistent across their defining and calling tasks.
- **Scope:** Phases 1–2 only; agency capability modules (Phases 3–4) deferred to their own plan. Action-chip rendering is included now so agency drops in cleanly later.
```
