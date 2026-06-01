# Conversation Upgrades Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Always-listening open mic (with guards), faster responses (pipeline-only), and a brain-generated greeting recorded in memory.

**Architecture:** Three phases. (A) Backend latency: pure `trim_history` helper + earlier/pipelined TTS in `voice_session.run_turn`. (B) UI open-mic in `app.js`: auto-start, VAD-gated sends, pause-while-speaking, mic-button-as-mute. (C) Brain greeting: pure `greeting_prompt` helper + reworked `/api/greeting` that generates via the LLM and records an episodic turn.

**Tech Stack:** Python 3.12 (`python3`, `PYTHONPATH=.`), FastAPI, pytest (async via `asyncio.run()`), vanilla JS. No new deps.

---

## Conventions

- Run tests: `PYTHONPATH=. python3 -m pytest <path> -v -p no:cacheprovider`
- `python3` only. Branch `friday-milestone-1-voice-reliability`. Commit per task; only `git add` named files.
- UI tasks end with explicit in-browser verification before commit.

## File Structure

- Modify: `core/voice_session.py` — earlier-first + pipelined TTS in `run_turn`.
- Create: `core/conversation_utils.py` — `trim_history(messages, max_turns)` (pure).
- Modify: `core/brain.py` — use `trim_history`, cap exemplars, in `get_streaming_response`.
- Modify: `core/greeting.py` — add `greeting_prompt(bio, hour, minutes_since_seen)` (pure).
- Modify: `core/main.py` — `/api/greeting` generates via brain + records episodic turn.
- Modify: `ui/js/app.js` — open-mic auto-start, VAD gating, pause-while-speaking, mute toggle.
- Test: `tests/test_conversation_utils.py`, `tests/test_greeting.py` (extend),
  `tests/test_voice_session.py` (extend).

---

# PHASE A — Faster responses (backend)

## Task 1: `trim_history` helper (pure)

**Files:** Create `core/conversation_utils.py`; Test `tests/test_conversation_utils.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_conversation_utils.py`:

```python
from core.conversation_utils import trim_history


def _msgs(n):
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(n)]


def test_trim_keeps_last_n_turns():
    out = trim_history(_msgs(20), max_turns=6)
    assert len(out) == 6
    assert out[-1]["content"] == "m19"
    assert out[0]["content"] == "m14"


def test_trim_noop_when_short():
    msgs = _msgs(4)
    assert trim_history(msgs, max_turns=6) == msgs


def test_trim_preserves_order_and_roles():
    out = trim_history(_msgs(10), max_turns=4)
    assert [m["role"] for m in out] == ["user", "assistant", "user", "assistant"]


def test_trim_handles_empty():
    assert trim_history([], max_turns=6) == []
```

- [ ] **Step 2: Run, expect FAIL** (`ModuleNotFoundError: No module named 'core.conversation_utils'`)

Run: `PYTHONPATH=. python3 -m pytest tests/test_conversation_utils.py -v -p no:cacheprovider`

- [ ] **Step 3: Create `core/conversation_utils.py`:**

```python
"""Pure conversation helpers (kept tiny + testable for latency work)."""


def trim_history(messages, max_turns=12):
    """Return at most the last `max_turns` messages, preserving order.
    Caps the episodic history sent to the LLM to reduce input tokens."""
    if max_turns <= 0:
        return []
    return messages[-max_turns:] if len(messages) > max_turns else messages
```

- [ ] **Step 4: Run, expect PASS (4 passed).**

- [ ] **Step 5: Commit**

```bash
git add core/conversation_utils.py tests/test_conversation_utils.py
git commit -m "feat(latency): trim_history helper to cap LLM context

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Use `trim_history` + cap exemplars in the brain

**Files:** Modify `core/brain.py`

- [ ] **Step 1: Add the import.** In `core/brain.py`, after `from core.agency import registry as agency_registry`, add:

```python
from core.conversation_utils import trim_history
```

- [ ] **Step 2: Cap the episodic history.** In `get_streaming_response`, replace:

```python
        messages = []
        for entry in self.memory.layers["episodic"]:
            # Claude expects role and content, and tool use must follow assistant role
            messages.append({"role": entry["role"], "content": entry["content"]})
```

with:

```python
        messages = []
        # Cap episodic history sent to the LLM to reduce input tokens / latency.
        for entry in trim_history(self.memory.layers["episodic"], max_turns=12):
            messages.append({"role": entry["role"], "content": entry["content"]})
```

- [ ] **Step 3: Verify import + a turn still works.**

Run:
```bash
PYTHONPATH=. python3 -c "from core.brain import FridayBrain; b=FridayBrain(); print('ok', len(b.tools))" 2>&1 | grep -E "ok|Error" | head -2
```
Expected: `ok <n>` (no traceback).

- [ ] **Step 4: Commit**

```bash
git add core/brain.py
git commit -m "feat(latency): cap episodic history via trim_history

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Earlier-first + pipelined TTS in `run_turn`

**Files:** Modify `core/voice_session.py`; Test `tests/test_voice_session.py`

The current loop holds one sentence and synthesizes the *previous* one, delaying first
audio. Change to: synth each sentence as soon as it completes, but overlap synthesis with
the previous segment's emit so there are no gaps.

- [ ] **Step 1: Write the failing test** — append to `tests/test_voice_session.py`:

```python
def test_first_caption_emitted_before_turn_ends(tmp_path):
    # The first spoken segment must be emitted as soon as the first sentence is
    # ready — not held until the stream finishes.
    order = []

    class _Brain:
        class _P:
            current_mood = "neutral"; mood_states = {"neutral": {"orb_color": "#5cc8ff"}}
        def __init__(self): self.personality = self._P(); self.config = {"ai_logic": {"llm_model": "t"}}
        async def get_streaming_response(self, text):
            for tok in ["One. ", "Two. ", "Three."]:
                order.append(("token", tok))
                yield tok

    class _TTS:
        async def generate_speech_timed(self, text, out):
            open(out, "wb").write(b"A")
            return out, [{"word": "x", "offset_ms": 0, "duration_ms": 10}]

    sent = []
    s = VoiceSession(_Brain(), None, _TTS(),
                     send_json=lambda m: (order.append(("emit", m.get("type"))) or sent.append(m)),
                     send_bytes=lambda b: None, logs_dir=str(tmp_path))
    asyncio.run(s.run_turn("go"))

    # A caption must appear in the event stream before the final transcript.
    caption_idx = next(i for i, m in enumerate(sent) if m["type"] == "caption")
    transcript_idxs = [i for i, m in enumerate(sent) if m["type"] == "transcript" and m["role"] == "friday"]
    assert transcript_idxs and caption_idx < transcript_idxs[-1]
    # All three sentences should have produced captions.
    assert sum(1 for m in sent if m["type"] == "caption") == 3
```

- [ ] **Step 2: Run, expect it to FAIL or PASS depending on current behavior** — run it to see the baseline:

Run: `PYTHONPATH=. python3 -m pytest tests/test_voice_session.py -k first_caption -v -p no:cacheprovider`
Expected: may FAIL on the count (the hold-one-ahead can drop/delay segments). Note the result.

- [ ] **Step 3: Rewrite the synth loop.** In `core/voice_session.py` `run_turn`, replace this block:

```python
            buffer += token
            if is_sentence_end(buffer):
                if not spoke:
                    await self._emit(events.state_event("speaking"))
                    spoke = True
                if held:
                    await self._synth_segment(held)
                held = buffer
                buffer = ""

        for t in open_actions:
            await self._emit(events.action_event(t, "done", f"{t} complete"))

        final_text = (held or "") + buffer
        if final_text.strip():
            if not spoke:
                await self._emit(events.state_event("speaking"))
            await self._synth_segment(final_text)
```

with (synthesize each sentence immediately; overlap next synth with current emit):

```python
            buffer += token
            if is_sentence_end(buffer):
                if not spoke:
                    await self._emit(events.state_event("speaking"))
                    spoke = True
                await self._synth_segment(buffer)
                buffer = ""

        for t in open_actions:
            await self._emit(events.action_event(t, "done", f"{t} complete"))

        final_text = buffer
        if final_text.strip():
            if not spoke:
                await self._emit(events.state_event("speaking"))
            await self._synth_segment(final_text)
```

Note: this removes the `held` one-ahead buffering so the first sentence is spoken
immediately. (The `held = None` initialization earlier in `run_turn` becomes unused but
harmless; leave it or remove it — if removed, also remove any later reference. Simplest:
leave the `held = None` line; it's now dead but inert.)

- [ ] **Step 4: Run, expect PASS.**

Run: `PYTHONPATH=. python3 -m pytest tests/test_voice_session.py -p no:cacheprovider -q`
Expected: all pass including the new first-caption test (3 captions, caption before final transcript).

- [ ] **Step 5: Commit**

```bash
git add core/voice_session.py tests/test_voice_session.py
git commit -m "feat(latency): speak first sentence immediately (drop hold-one-ahead)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

# PHASE B — Always-listening open mic (UI)

## Task 4: Open-mic auto-start + VAD gating + pause-while-speaking + mute

**Files:** Modify `ui/js/app.js`

- [ ] **Step 1: Add open-mic state + speech detection to the mic VAD loop.** In
  `ui/js/app.js`, replace the whole `startMicVAD` function with one that also tracks recent
  speech and gates sending:

```javascript
let micMuted = false;
let speechActive = false;
const SPEECH_RMS = 0.04; // above this = speech present

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
        speechActive = rms > SPEECH_RMS;
        requestAnimationFrame(tick);
    })();
}

// Send a chunk only when: not muted, Friday isn't speaking, and recent audio
// actually contains speech. This is the open-mic guard (no silence, no self-hearing).
function shouldSend() {
    return !micMuted
        && document.body.dataset.state !== 'speaking'
        && speechActive
        && socket?.readyState === WebSocket.OPEN;
}
```

- [ ] **Step 2: Gate the recorder's send on `shouldSend()`.** In `startRecording`, change:

```javascript
    mediaRecorder.ondataavailable = (ev) => {
        if (ev.data.size > 0 && socket?.readyState === WebSocket.OPEN) socket.send(ev.data);
    };
```

to:

```javascript
    mediaRecorder.ondataavailable = (ev) => {
        if (ev.data.size > 0 && shouldSend()) socket.send(ev.data);
    };
```

- [ ] **Step 3: Make the mic button a mute toggle and auto-start listening.** Replace the
  `toggleMic` function and the DOMContentLoaded mic wiring. Change `toggleMic` to:

```javascript
function toggleMute() {
    micMuted = !micMuted;
    const btn = document.getElementById('mic-trigger');
    btn.classList.toggle('active', !micMuted);   // active = listening
    btn.title = micMuted ? 'Muted — click to listen' : 'Listening — click to mute';
}
```

  And in the `DOMContentLoaded` handler, replace:

```javascript
    document.getElementById('mic-trigger').addEventListener('click', toggleMic);
```

with:

```javascript
    document.getElementById('mic-trigger').addEventListener('click', toggleMute);
    // Open mic: start listening automatically (best-effort; needs permission).
    startRecording().then(() => {
        document.getElementById('mic-trigger').classList.add('active');
    }).catch((e) => console.log('[mic] autostart failed (permission?):', e.message));
```

- [ ] **Step 4: Remove the now-unused `listening` toggle bookkeeping.** Delete the line
  `let listening = false;` if present (the old `toggleMic` referenced it). Ensure no other
  reference to `listening` or `toggleMic` remains:

Run: `grep -n "toggleMic\|let listening" ui/js/app.js`
Expected: no matches (all replaced).

- [ ] **Step 5: In-browser verification.** `python3 launcher.py`; open http://localhost:8000,
  allow mic. Verify: (a) mic is live without clicking (button shows active); (b) staying
  silent sends nothing (no spurious turns in the server log); (c) speak a sentence → Friday
  replies; (d) while she speaks, your voice does NOT trigger a new turn; (e) click the mic →
  it mutes (button inactive), speaking sends nothing; click again → resumes.

- [ ] **Step 6: Commit**

```bash
git add ui/js/app.js
git commit -m "feat(voice): always-listening open mic with VAD gate, pause-while-speaking, mute toggle

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

# PHASE C — Brain-generated greeting recorded in memory

## Task 5: `greeting_prompt` helper (pure)

**Files:** Modify `core/greeting.py`; Test `tests/test_greeting.py`

- [ ] **Step 1: Append the failing tests** to `tests/test_greeting.py`:

```python
from core.greeting import greeting_prompt


def test_greeting_prompt_includes_time_and_name():
    p = greeting_prompt({"name": "Tony", "title": "Sir"}, hour=8, minutes_since_seen=0)
    assert "morning" in p.lower()
    assert "Tony" in p or "Sir" in p
    # It's an instruction to the model to produce ONE short greeting line.
    assert "one" in p.lower() and "greet" in p.lower()


def test_greeting_prompt_mentions_absence():
    p = greeting_prompt({"title": "Sir"}, hour=14, minutes_since_seen=600)
    assert "while" in p.lower() or "back" in p.lower() or "hours" in p.lower()
```

- [ ] **Step 2: Run, expect FAIL** (`ImportError: cannot import name 'greeting_prompt'`)

Run: `PYTHONPATH=. python3 -m pytest tests/test_greeting.py -k prompt -v -p no:cacheprovider`

- [ ] **Step 3: Add to `core/greeting.py`:**

```python
def greeting_prompt(bio, hour, minutes_since_seen=0):
    """Build an LLM instruction to generate ONE short in-persona greeting line."""
    address = bio.get("title") or bio.get("name") or "Sir"
    tod = _time_of_day(hour)
    absence = ""
    if minutes_since_seen >= 240:
        hrs = minutes_since_seen // 60
        absence = f" The user has been away about {hrs} hours, so welcome them back."
    return (
        f"As Friday, greet the user with ONE short, in-character spoken line. "
        f"It is {tod}; address them as {address}.{absence} "
        f"No preamble or quotation marks — just the greeting line."
    )
```

- [ ] **Step 4: Run, expect PASS.**

Run: `PYTHONPATH=. python3 -m pytest tests/test_greeting.py -p no:cacheprovider -q`
Expected: all pass (existing 6 + 2 new).

- [ ] **Step 5: Commit**

```bash
git add core/greeting.py tests/test_greeting.py
git commit -m "feat(boot): greeting_prompt builder for brain-generated greeting

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: `/api/greeting` generates via brain + records episodic turn

**Files:** Modify `core/main.py`

- [ ] **Step 1: Rewrite the `/api/greeting` endpoint.** Replace the current `get_greeting`
  function body with one that asks the brain, records the turn, and falls back gracefully:

```python
@app.get("/api/greeting")
async def get_greeting():
    """Generate an in-persona greeting via the brain, record it as Friday's first
    assistant turn (so she's aware she greeted the user), and return it. Falls back
    to the templated greeting if the brain is unreachable."""
    from core.greeting import build_greeting, greeting_prompt
    bio = brain.memory.layers.get("bio", {})
    last_seen = bio.get("last_seen")
    minutes = 0
    if last_seen:
        try:
            minutes = int((datetime.now() - datetime.fromisoformat(last_seen)).total_seconds() // 60)
        except (ValueError, TypeError):
            minutes = 0

    hour = datetime.now().hour
    text = ""
    try:
        prompt = greeting_prompt(bio, hour, minutes)
        async for tok in brain.get_streaming_response(prompt):
            if not tok.startswith("[System") and not tok.startswith("[Approval") and not tok.startswith("[Result"):
                text += tok
        text = text.strip()
    except Exception as e:
        logger.error(f"Greeting generation failed: {e}")
        text = ""
    if not text:
        text = build_greeting(bio, hour, minutes)

    # get_streaming_response already appends the user prompt + assistant reply to
    # episodic memory; if we fell back, record the greeting as an assistant turn.
    if text and (not brain.memory.layers["episodic"] or
                 brain.memory.layers["episodic"][-1].get("content") != text):
        brain.memory.add_episodic("assistant", text)

    bio["last_seen"] = datetime.now().isoformat()
    brain.memory.layers["bio"] = bio
    brain.memory.save()
    return {"text": text}
```

- [ ] **Step 2: Verify (server running, Ollama up).**

```bash
cd /home/lucifer/Downloads/newfriday
cp data/memory.json /tmp/m.bak 2>/dev/null
lsof -ti:8000 2>/dev/null | xargs -r kill -9 2>/dev/null; sleep 1
PYTHONPATH=. setsid python3 -m uvicorn core.main:app --host 0.0.0.0 --port 8000 --log-level warning > /tmp/friday_server.log 2>&1 < /dev/null & disown
for i in $(seq 1 12); do [ "$(curl -s -m 2 -o /dev/null -w '%{http_code}' http://localhost:8000/ 2>/dev/null)" = "200" ] && break; sleep 1; done
curl -s http://localhost:8000/api/greeting
echo ""
PYTHONPATH=. python3 -c "import json; e=json.load(open('data/memory.json'))['episodic']; print('last role:', e[-1]['role'] if e else None)"
lsof -ti:8000 2>/dev/null | xargs -r kill 2>/dev/null
cp /tmp/m.bak data/memory.json 2>/dev/null
```
Expected: a JSON `{"text": "..."}` in-persona greeting, and `last role: assistant`
(the greeting is recorded in episodic memory).

- [ ] **Step 3: Commit**

```bash
git add core/main.py
git commit -m "feat(boot): brain-generated greeting recorded as conversation turn

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] **Backend suite green (besides the 3 known pre-existing failures):**

Run: `PYTHONPATH=. python3 -m pytest tests/ -p no:cacheprovider -q`
Expected: conversation_utils (4), greeting (8), voice_session (incl. first-caption) all pass.

- [ ] **Full in-browser demo (Ollama running):** load → brain greeting plays and appears as a
  Friday transcript bubble → speak naturally (no tap) → reply starts speaking sooner, no
  gaps between sentences → talking while she speaks doesn't trigger a new turn → mic button
  mutes/unmutes. No console errors.

- [ ] **Update CLAUDE.md** — note open-mic, the latency pipeline, and brain greeting; commit:

```bash
git add CLAUDE.md
git commit -m "docs: open-mic, latency pipeline, brain greeting

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (completed by plan author)

- **Spec coverage:** open-mic auto-start/VAD/pause-while-speaking/mute → Task 4; earlier+
  pipelined TTS → Task 3; leaner context (`trim_history`) → Tasks 1-2; brain greeting +
  episodic record + fallback → Tasks 5-6. All spec sections covered.
- **Placeholder scan:** none — every step has full code/commands. The "leave `held = None`
  dead but inert" note is an explicit instruction, not a placeholder.
- **Type consistency:** `trim_history(messages, max_turns)` used identically in Tasks 1-2;
  `greeting_prompt(bio, hour, minutes_since_seen)` matches `build_greeting`'s signature and
  Task 6 usage; UI helpers `shouldSend()`, `micMuted`, `speechActive`, `toggleMute` defined
  and referenced consistently in Task 4.
- **Scope:** no model swap; sentence-granularity TTS retained; backend wake-word logic left
  intact (UI just runs open-mic). Matches spec's out-of-scope.
- **Note on "pipelined TTS":** Task 3 makes the first sentence speak immediately (the main
  win). True overlapping synth-while-playing is bounded by `_synth_segment` awaiting each
  TTS; emitting each segment as soon as ready already removes the one-ahead delay. Full
  async overlap is deferred (YAGNI) since segments are emitted serially to preserve audio
  order on the client.
```
