# Friday "Alive & Aware" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Friday feel alive and aware — a cinematic left-rail HUD with live telemetry + agency result cards, a boot sequence that recognizes & greets the user (browser face, graceful profile fallback), and proactivity that scans real signals and speaks at a balanced cadence.

**Architecture:** Pure, unit-tested logic modules (`core/triggers.py`, `core/greeting.py`, plus `summarize_result` in `voice_session` and `pick_greeting_mode` in `greeting`) drive thin integration layers (`proactive.py` rework, `/api/greeting`, v2-event broadcast fix) and UI modules (`hud.js` rail/cards, `boot.js`, `recognition.js`). Three phases: HUD → proactivity → boot/recognition.

**Tech Stack:** Python 3.12 (`python3`, `PYTHONPATH=.`), FastAPI, pytest (async via `asyncio.run()`), Three.js, face-api.js (CDN). No new pip deps.

---

## Conventions for every task

- Run tests: `PYTHONPATH=. python3 -m pytest <path> -v -p no:cacheprovider`
- `python` is NOT on PATH — always `python3`. Branch: `friday-milestone-1-voice-reliability`.
- Commit after each task with the exact message given; only `git add` the files named.
- UI tasks can't be unit-tested here → each ends with an explicit in-browser verification
  step (`python3 launcher.py` or uvicorn, open http://localhost:8000) before committing.

## File Structure

- Modify: `core/events.py` — add `result_event(tool, title, lines)`.
- Modify: `core/voice_session.py` — `summarize_result(tool, result)` + emit `result` events.
- Create: `core/triggers.py` — `evaluate_triggers(ctx)` + scoring/threshold (pure).
- Modify: `core/proactive.py` — trigger-scan rework; broadcast via v2 contract.
- Modify: `core/main.py` — rewrite `broadcast_proactive_message` to v2 contract; add `GET /api/greeting`.
- Create: `core/greeting.py` — `build_greeting(...)`, `pick_greeting_mode(...)` (pure).
- Modify: `ui/index.html` — `#telemetry-rail`, `#result-cards`, boot overlay markup, module tags.
- Modify: `ui/css/style.css` — rail, result cards, boot overlay styles.
- Modify: `ui/js/hud.js` — render vitals/tasks rail; `result(msg)` cards.
- Modify: `ui/js/app.js` — route `result` event to `Hud.result`; trigger boot+greeting on load.
- Create: `ui/js/boot.js` — cinematic boot overlay.
- Create: `ui/js/recognition.js` — webcam face enroll/recognize + greeting trigger.
- Test: `tests/test_events.py` (extend), `tests/test_voice_session.py` (extend),
  `tests/test_triggers.py`, `tests/test_greeting.py`.

---

# PHASE 1 — Cinematic HUD

## Task 1: `result_event` builder

**Files:** Modify `core/events.py`; Test `tests/test_events.py`

- [ ] **Step 1: Append the failing test** to `tests/test_events.py`:

```python
def test_result_event():
    from core import events
    ev = events.result_event("web_search", "Web · 3 results", ["a", "b", "c"])
    assert ev == {"type": "result", "tool": "web_search",
                  "title": "Web · 3 results", "lines": ["a", "b", "c"]}
```

- [ ] **Step 2: Run it, expect FAIL** (`AttributeError: module 'core.events' has no attribute 'result_event'`)

Run: `PYTHONPATH=. python3 -m pytest tests/test_events.py::test_result_event -v -p no:cacheprovider`

- [ ] **Step 3: Append to `core/events.py`:**

```python
def result_event(tool, title, lines):
    """A card-worthy agency result for the HUD (rendered bottom-center)."""
    return {"type": "result", "tool": tool, "title": title, "lines": lines}
```

- [ ] **Step 4: Run it, expect PASS.**

- [ ] **Step 5: Commit**

```bash
git add core/events.py tests/test_events.py
git commit -m "feat(hud): add result_event for agency result cards

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: `summarize_result` + emit result events

**Files:** Modify `core/voice_session.py`; Test `tests/test_voice_session.py`

- [ ] **Step 1: Append the failing tests** to `tests/test_voice_session.py`:

```python
from core.voice_session import summarize_result


def test_summarize_web_results():
    res = [{"title": "Foo", "url": "http://x", "snippet": "bar"},
           {"title": "Baz", "url": "http://y", "snippet": "qux"}]
    card = summarize_result("web_search", res)
    assert card["title"].lower().startswith("web")
    assert any("Foo" in ln for ln in card["lines"])


def test_summarize_file_list():
    card = summarize_result("search_files", ["a.py", "b.py", "c.py"])
    assert "file" in card["title"].lower()
    assert len(card["lines"]) <= 6


def test_summarize_non_card_returns_none():
    # Short string results aren't card-worthy.
    assert summarize_result("set_volume", "Volume set to 50%.") is None
    assert summarize_result("run_shell", {"stdout": "ok", "exit_code": 0}) is None


def test_summarize_unknown_tool_returns_none():
    assert summarize_result("create_task", "Task created") is None
```

- [ ] **Step 2: Run it, expect FAIL** (`ImportError: cannot import name 'summarize_result'`)

Run: `PYTHONPATH=. python3 -m pytest tests/test_voice_session.py -k summarize -v -p no:cacheprovider`

- [ ] **Step 3: Add to `core/voice_session.py`** (module-level function, after `is_sentence_end`):

```python
def summarize_result(tool, result):
    """Decide whether an agency tool result is HUD-card-worthy; return
    {title, lines} or None. Only data-bearing results (web/files) make cards."""
    if tool in ("web_search",) and isinstance(result, list) and result:
        lines = []
        for r in result[:5]:
            if isinstance(r, dict) and r.get("title"):
                lines.append(r["title"])
        if lines:
            return {"title": f"Web · {len(result)} results", "lines": lines}
        return None
    if tool in ("search_files", "list_dir") and isinstance(result, list) and result:
        shown = [str(x) for x in result[:6]]
        return {"title": f"Files · {len(result)} found", "lines": shown}
    return None
```

- [ ] **Step 4: Run it, expect PASS (4 passed).**

- [ ] **Step 5: Emit `result` events on tool completion.** In `core/voice_session.py`,
  the agency result isn't currently visible to the session (the brain runs tools and only
  yields `[System: Executing X]` markers). Add result surfacing via a new brain marker.

  In `core/brain.py`, in BOTH tool paths, right after `marker = self._approval_marker(result)`
  blocks, add a result marker yield. Specifically, after the existing
  `yield f"[System: Executing {tool_call.name}...]"` (anthropic path) and
  `yield f"[System: Executing {tool_call.function.name}...]"` (openai path), the result is
  computed below; after `result = await self.execute_tool(...)` / dispatch in each path, add:

  ```python
                        from core.voice_session import summarize_result
                        _card = summarize_result(tool_call.name if self.provider == "anthropic" else tool_call.function.name, result)
                        if _card:
                            import json as _json
                            yield "[Result: " + _json.dumps({"tool": (tool_call.name if self.provider == "anthropic" else tool_call.function.name), **_card}) + "]"
  ```

  (Place this once per path, immediately after the line that computes `result` and before the
  `messages.append(... tool_result ...)`.)

- [ ] **Step 6: Handle the `[Result: …]` marker in `core/voice_session.py`.** In `run_turn`,
  in the token loop, add a branch BEFORE the `full_reply += token` line, alongside the
  existing `[Approval:` branch:

```python
            if token.startswith("[Result:"):
                import json as _json
                try:
                    payload = _json.loads(token[len("[Result:"):].rstrip("]").strip())
                    await self._emit(events.result_event(payload.get("tool", ""),
                                                          payload.get("title", ""),
                                                          payload.get("lines", [])))
                except (ValueError, KeyError):
                    pass
                continue
```

- [ ] **Step 7: Run the voice_session suite, expect PASS.**

Run: `PYTHONPATH=. python3 -m pytest tests/test_voice_session.py -p no:cacheprovider -q`
Expected: all pass (existing + 4 new summarize tests).

- [ ] **Step 8: Commit**

```bash
git add core/voice_session.py core/brain.py tests/test_voice_session.py
git commit -m "feat(hud): summarize agency results into result events

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: HUD telemetry rail + result cards (UI)

**Files:** Modify `ui/index.html`, `ui/css/style.css`, `ui/js/hud.js`, `ui/js/app.js`

- [ ] **Step 1: Add markup.** In `ui/index.html`, immediately after `<div id="ui-layer">`
  line, add the rail; and after `<div id="action-rail"></div>` add the result-cards host:

```html
        <aside class="telemetry-rail glass-panel" id="telemetry-rail">
            <section class="tr-section">
                <header>VITALS</header>
                <div class="tr-vital"><span>CPU</span><div class="tr-bar"><i id="tr-cpu"></i></div></div>
                <div class="tr-vital"><span>RAM</span><div class="tr-bar"><i id="tr-ram"></i></div></div>
                <div class="tr-vital"><span>BATT</span><div class="tr-bar"><i id="tr-batt"></i></div></div>
            </section>
            <section class="tr-section">
                <header>TASKS</header>
                <div id="tr-tasks" class="tr-tasks"></div>
            </section>
        </aside>
        <div id="result-cards"></div>
```

- [ ] **Step 2: Add styles.** Append to `ui/css/style.css`:

```css
/* Cinematic HUD — left telemetry rail */
.telemetry-rail{ position:fixed; left:18px; top:90px; bottom:150px; width:190px; pointer-events:auto;
  padding:16px 14px; display:flex; flex-direction:column; gap:20px; overflow-y:auto; }
.telemetry-rail::-webkit-scrollbar{ width:5px; } .telemetry-rail::-webkit-scrollbar-thumb{ background:var(--border); border-radius:3px; }
.tr-section > header{ font-size:9px; letter-spacing:.2em; color:var(--accent); margin-bottom:10px; }
.tr-vital{ font-size:9px; color:var(--text-dim); letter-spacing:.06em; margin-bottom:9px; }
.tr-vital span{ display:block; margin-bottom:3px; }
.tr-bar{ height:5px; background:rgba(124,180,255,.12); border-radius:3px; overflow:hidden; }
.tr-bar i{ display:block; height:100%; width:0%; background:var(--accent); border-radius:3px;
  box-shadow:0 0 8px var(--accent); transition:width .5s, background .5s; }
.tr-bar i.warn{ background:#FBBF24; box-shadow:0 0 8px #FBBF24; }
.tr-bar i.crit{ background:#EF4444; box-shadow:0 0 8px #EF4444; }
.tr-tasks{ font-size:10px; color:rgba(255,255,255,.6); line-height:1.7; }
.tr-tasks .t{ display:flex; gap:6px; } .tr-tasks .t::before{ content:'▸'; color:var(--accent); }
#result-cards{ position:fixed; left:50%; bottom:110px; transform:translateX(-50%); width:380px; max-width:60vw;
  display:flex; flex-direction:column; gap:8px; pointer-events:none; z-index:11; }
.result-card{ background:rgba(124,245,213,.06); border:1px solid rgba(124,245,213,.28); border-radius:10px;
  padding:10px 12px; opacity:0; transform:translateY(10px); transition:opacity .35s, transform .35s; }
.result-card.show{ opacity:1; transform:translateY(0); }
.result-card .rc-title{ font-size:9px; letter-spacing:.12em; color:#7cf5d5; margin-bottom:5px; }
.result-card .rc-line{ font-size:11px; color:rgba(255,255,255,.78); line-height:1.5; white-space:nowrap;
  overflow:hidden; text-overflow:ellipsis; }
```

- [ ] **Step 3: Render rail + cards in `ui/js/hud.js`.** Replace the existing `updateVitals`
  function body so it renders into the rail, and add `renderTasks` + `result`:

```javascript
async function updateVitals() {
    try {
        const v = await (await fetch('/api/vitals')).json();
        window.__vitals = v;
        setBar('tr-cpu', v.cpu_usage);
        setBar('tr-ram', v.memory_usage);
        setBar('tr-batt', v.battery, true);
        const cfg = await (await fetch('/api/config')).json();
        renderTasks((cfg.system_memory && cfg.system_memory.task) || []);
    } catch (e) { /* ignore */ }
}

function setBar(id, pct, isBattery) {
    const el = document.getElementById(id);
    if (!el) return;
    const p = Math.max(0, Math.min(100, Number(pct) || 0));
    el.style.width = p + '%';
    el.classList.remove('warn', 'crit');
    // Battery is inverted: low is bad. Others: high is bad.
    const bad = isBattery ? (p < 20 ? 'crit' : p < 40 ? 'warn' : '') : (p > 90 ? 'crit' : p > 70 ? 'warn' : '');
    if (bad) el.classList.add(bad);
}

function renderTasks(tasks) {
    const host = document.getElementById('tr-tasks');
    if (!host) return;
    if (!tasks.length) { host.innerHTML = '<span style="opacity:.4">none</span>'; return; }
    host.innerHTML = tasks.slice(0, 6).map(t =>
        `<div class="t">${(t.name || t.title || 'task').replace(/[<>&]/g, '')}</div>`).join('');
}

function result(msg) {
    const host = document.getElementById('result-cards');
    if (!host) return;
    const card = document.createElement('div');
    card.className = 'result-card';
    card.innerHTML = `<div class="rc-title">${(msg.title || '').replace(/[<>&]/g, '')}</div>` +
        (msg.lines || []).slice(0, 5).map(l => `<div class="rc-line">${String(l).replace(/[<>&]/g, '')}</div>`).join('');
    host.appendChild(card);
    requestAnimationFrame(() => card.classList.add('show'));
    setTimeout(() => { card.classList.remove('show'); setTimeout(() => card.remove(), 400); }, 7000);
}
```

  And add `result` to the exported object — change the last line of `hud.js` to:

```javascript
window.Hud = { init, action, glitch, setStateLabel, requestApproval, result };
```

- [ ] **Step 4: Route the `result` event in `ui/js/app.js`.** In `handleEvent`, add a case:

```javascript
        case 'result': window.Hud?.result(msg); break;
```

- [ ] **Step 5: In-browser verification.** `python3 launcher.py`; open http://localhost:8000.
  Confirm: the left rail shows CPU/RAM/BATT bars that update every ~2.5s and a TASKS list;
  ask Friday (text) "search the web for the RTX 3050" — a green result card rises
  bottom-center and fades after ~7s. No console errors.

- [ ] **Step 6: Commit**

```bash
git add ui/index.html ui/css/style.css ui/js/hud.js ui/js/app.js
git commit -m "feat(hud): left telemetry rail (vitals+tasks) + agency result cards

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

# PHASE 2 — Smarter Proactivity

## Task 4: `evaluate_triggers` (pure)

**Files:** Create `core/triggers.py`; Test `tests/test_triggers.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_triggers.py`:

```python
from core.triggers import evaluate_triggers, THRESHOLD


def _ctx(**kw):
    base = {"vitals": {"cpu_usage": 10, "memory_usage": 30, "battery": 80, "plugged": True},
            "tasks": [], "hour": 15, "idle_seconds": 60, "minutes_since_interaction": 5,
            "last_topic": None}
    base.update(kw)
    return base


def test_low_battery_unplugged_fires_high():
    cands = evaluate_triggers(_ctx(vitals={"cpu_usage": 5, "memory_usage": 20, "battery": 8, "plugged": False}))
    batt = [c for c in cands if c["kind"] == "vitals"]
    assert batt and batt[0]["score"] >= THRESHOLD


def test_all_quiet_produces_nothing_actionable():
    cands = evaluate_triggers(_ctx())
    assert all(c["score"] < THRESHOLD for c in cands)


def test_pending_tasks_trigger():
    cands = evaluate_triggers(_ctx(tasks=[{"name": "Ghost", "status": "active"}]))
    assert any(c["kind"] == "tasks" for c in cands)


def test_late_night_trigger():
    cands = evaluate_triggers(_ctx(hour=3))
    assert any(c["kind"] == "time" for c in cands)


def test_long_idle_trigger():
    cands = evaluate_triggers(_ctx(minutes_since_interaction=180))
    assert any(c["kind"] == "time" and "idle" in c["message_hint"].lower() for c in cands)


def test_web_topic_trigger_flagged():
    cands = evaluate_triggers(_ctx(last_topic="quantum computing"))
    assert any(c["kind"] == "web" for c in cands)


def test_results_sorted_by_score_desc():
    cands = evaluate_triggers(_ctx(vitals={"cpu_usage": 99, "memory_usage": 95, "battery": 5, "plugged": False},
                                    tasks=[{"name": "x", "status": "active"}], hour=3))
    scores = [c["score"] for c in cands]
    assert scores == sorted(scores, reverse=True)
```

- [ ] **Step 2: Run it, expect FAIL** (`ModuleNotFoundError: No module named 'core.triggers'`)

- [ ] **Step 3: Create `core/triggers.py`:**

```python
"""Pure proactive trigger evaluation. No LLM, no I/O — just scoring signals.
A candidate scoring >= THRESHOLD is worth surfacing (balanced cadence)."""

THRESHOLD = 0.6


def evaluate_triggers(ctx):
    """Score proactive candidates from a context dict. Returns a list of
    {kind, score, message_hint}, sorted by score descending."""
    cands = []
    vitals = ctx.get("vitals", {})
    battery = vitals.get("battery", 100)
    plugged = vitals.get("plugged", True)
    cpu = vitals.get("cpu_usage", 0)
    mem = vitals.get("memory_usage", 0)

    # --- vitals ---
    if battery <= 15 and not plugged:
        cands.append({"kind": "vitals", "score": 0.95,
                      "message_hint": f"Battery at {battery}% and unplugged."})
    elif battery <= 30 and not plugged:
        cands.append({"kind": "vitals", "score": 0.7,
                      "message_hint": f"Battery getting low ({battery}%)."})
    if cpu >= 90:
        cands.append({"kind": "vitals", "score": 0.72,
                      "message_hint": f"CPU sustained at {cpu}%."})
    if mem >= 90:
        cands.append({"kind": "vitals", "score": 0.7,
                      "message_hint": f"Memory pressure at {mem}%."})

    # --- time / routine ---
    hour = ctx.get("hour", 12)
    mins = ctx.get("minutes_since_interaction", 0)
    if hour >= 1 and hour <= 4:
        cands.append({"kind": "time", "score": 0.62,
                      "message_hint": "It's quite late; suggest wrapping up."})
    if mins >= 120:
        cands.append({"kind": "time", "score": 0.66,
                      "message_hint": f"Idle for {mins} minutes; a gentle check-in."})

    # --- tasks / memory ---
    active = [t for t in ctx.get("tasks", []) if t.get("status") in ("active", "pending")]
    if active:
        cands.append({"kind": "tasks", "score": 0.64,
                      "message_hint": f"{len(active)} task(s) still open."})

    # --- web / world (the fetch itself happens in proactive.py) ---
    topic = ctx.get("last_topic")
    if topic:
        cands.append({"kind": "web", "score": 0.61,
                      "message_hint": f"Could look up more on '{topic}'."})

    cands.sort(key=lambda c: c["score"], reverse=True)
    return cands
```

- [ ] **Step 4: Run it, expect PASS (7 passed).**

- [ ] **Step 5: Commit**

```bash
git add core/triggers.py tests/test_triggers.py
git commit -m "feat(proactive): pure trigger evaluation + scoring

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Proactive rework + v2-contract broadcast

**Files:** Modify `core/proactive.py`, `core/main.py`

- [ ] **Step 1: Rewrite `broadcast_proactive_message` in `core/main.py`** to use the v2
  event contract instead of the dead `speak_segment`. Replace the whole function body with:

```python
async def broadcast_proactive_message(message: str):
    """Broadcasts a proactive message to all connected UIs using the v2 event
    contract (state + transcript + caption + audio), so it shows captions and
    pulses the orb like a normal turn."""
    if not active_connections:
        return
    mood_cfg = brain.personality.mood_states[brain.personality.current_mood]
    output_path = f"data/logs/proactive_{uuid.uuid4().hex}.mp3"
    try:
        _, words = await tts.generate_speech_timed(message, output_path)
        with open(output_path, "rb") as f:
            audio_bytes = f.read()
    except Exception as e:
        logger.error(f"Proactive TTS error: {e}")
        words, audio_bytes = [], b""
    seg_id = uuid.uuid4().hex
    for connection in active_connections:
        try:
            await connection.send_json({"type": "mood", "mood": brain.personality.current_mood,
                                        "orb_color": mood_cfg["orb_color"]})
            await connection.send_json({"type": "state", "state": "speaking"})
            await connection.send_json({"type": "transcript", "role": "friday",
                                        "text": message, "final": True})
            await connection.send_json({"type": "caption", "segment_id": seg_id,
                                        "mode": "word" if words else "sentence",
                                        "words": words, "text": message})
            if audio_bytes:
                await connection.send_bytes(audio_bytes)
            await connection.send_json({"type": "state", "state": "idle"})
        except Exception:
            pass
    if os.path.exists(output_path):
        os.remove(output_path)
```

- [ ] **Step 2: Rework `run_cycle` in `core/proactive.py`** to use the trigger scan. Replace
  the body of `run_cycle` (the context gather + thought_prompt + LLM JSON decision) with:

```python
    async def run_cycle(self):
        """A single trigger-scan cycle: gather signals, score, and speak only if
        a candidate clears the balanced threshold."""
        from core.triggers import evaluate_triggers, THRESHOLD
        from datetime import datetime
        logger.info("Friday proactive scan...")

        vitals = self.bridge.get_system_vitals()
        # bridge vitals don't include 'plugged'; treat full battery as plugged.
        vitals.setdefault("plugged", vitals.get("battery", 100) >= 99)
        tasks = self.brain.memory.layers.get("task", [])
        episodic = self.brain.memory.layers.get("episodic", [])
        last = episodic[-1] if episodic else None
        last_topic = None
        for entry in reversed(episodic):
            if entry.get("role") == "user":
                last_topic = entry.get("content", "")[:60]
                break

        ctx = {
            "vitals": vitals,
            "tasks": tasks,
            "hour": datetime.now().hour,
            "idle_seconds": 0,
            "minutes_since_interaction": 0,
            "last_topic": last_topic,
        }
        candidates = evaluate_triggers(ctx)
        top = candidates[0] if candidates else None
        if not top or top["score"] < THRESHOLD:
            logger.info("Proactive scan: nothing worth surfacing.")
            return

        # Phrase the chosen trigger in-persona via the brain (short, single line).
        hint = top["message_hint"]
        try:
            prompt = (f"As Friday, say ONE short, in-character spoken line to the user about: "
                      f"{hint}. No preamble, just the line.")
            line = ""
            async for tok in self.brain.get_streaming_response(prompt):
                if not tok.startswith("[System") and not tok.startswith("[Approval") and not tok.startswith("[Result"):
                    line += tok
            line = line.strip() or hint
        except Exception as e:
            logger.error(f"Proactive phrasing error: {e}")
            line = hint

        await self.broadcast_callback(line)
        self.brain.memory.layers.setdefault("internal_monologue", []).append({
            "timestamp": datetime.now().isoformat(), "thought": f"[{top['kind']}] {hint}"})
        self.brain.memory.save()
```

- [ ] **Step 3: Import smoke**

Run: `PYTHONPATH=. python3 -c "import core.main, core.proactive; print('ok')"`
Expected: `ok` (no traceback).

- [ ] **Step 4: Live proactive smoke (forces one cycle, Ollama running).**

```bash
cp data/memory.json /tmp/m.bak 2>/dev/null
PYTHONPATH=. timeout 200 python3 -c "
import asyncio
from core.brain import FridayBrain
from core.proactive import ProactiveEngine
async def main():
    b = FridayBrain()
    # Force a battery trigger.
    eng = ProactiveEngine(b)
    eng.bridge.get_system_vitals = lambda: {'cpu_usage':5,'memory_usage':20,'battery':8,'plugged':False,'temp':0}
    captured = []
    eng.broadcast_callback = lambda msg: captured.append(msg) or asyncio.sleep(0)
    await eng.run_cycle()
    print('SPOKE:', captured[0][:160] if captured else '(silent)')
asyncio.run(main())
"
cp /tmp/m.bak data/memory.json 2>/dev/null
```
Expected: `SPOKE:` a short in-persona line about the low battery.

- [ ] **Step 5: Full suite (no regressions).**

Run: `PYTHONPATH=. python3 -m pytest tests/ -p no:cacheprovider -q`
Expected: triggers (7) pass; no regressions beyond the 3 known pre-existing failures.

- [ ] **Step 6: Commit**

```bash
git add core/proactive.py core/main.py
git commit -m "feat(proactive): trigger-scan rework + v2-contract broadcast

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

# PHASE 3 — Boot Sequence + Recognize-and-Greet

## Task 6: `build_greeting` + `pick_greeting_mode` (pure)

**Files:** Create `core/greeting.py`; Test `tests/test_greeting.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_greeting.py`:

```python
from core.greeting import build_greeting, pick_greeting_mode


def test_greeting_morning_named():
    g = build_greeting({"name": "Tony", "title": "Sir"}, hour=8, minutes_since_seen=0)
    assert "morning" in g.lower()
    assert "Sir" in g or "Tony" in g


def test_greeting_evening():
    g = build_greeting({"title": "Sir"}, hour=20, minutes_since_seen=0)
    assert "evening" in g.lower()


def test_greeting_welcome_back_after_absence():
    g = build_greeting({"title": "Sir"}, hour=14, minutes_since_seen=600)
    assert "welcome back" in g.lower()


def test_greeting_defaults_when_bio_empty():
    g = build_greeting({}, hour=12, minutes_since_seen=0)
    assert "Sir" in g  # default address
    assert len(g) > 0


def test_pick_mode_face_when_matched():
    assert pick_greeting_mode(has_camera=True, enrolled=True, matched=True) == "face"


def test_pick_mode_profile_on_any_failure():
    assert pick_greeting_mode(has_camera=False, enrolled=True, matched=False) == "profile"
    assert pick_greeting_mode(has_camera=True, enrolled=False, matched=False) == "profile"
    assert pick_greeting_mode(has_camera=True, enrolled=True, matched=False) == "profile"
```

- [ ] **Step 2: Run it, expect FAIL** (`ModuleNotFoundError: No module named 'core.greeting'`)

- [ ] **Step 3: Create `core/greeting.py`:**

```python
"""Pure greeting composition + recognition-mode decision (mirrors recognition.js)."""


def _time_of_day(hour):
    if 5 <= hour < 12:
        return "morning"
    if 12 <= hour < 18:
        return "afternoon"
    return "evening"


def build_greeting(bio, hour, minutes_since_seen=0):
    """Compose an in-persona greeting from bio + time + absence length."""
    address = bio.get("title") or bio.get("name") or "Sir"
    tod = _time_of_day(hour)
    if minutes_since_seen >= 240:
        return f"Welcome back, {address}. It's been a while — good {tod}."
    return f"Good {tod}, {address}. Friday is online and at your service."


def pick_greeting_mode(has_camera, enrolled, matched):
    """Return 'face' only when camera + enrollment + match all hold; else 'profile'."""
    if has_camera and enrolled and matched:
        return "face"
    return "profile"
```

- [ ] **Step 4: Run it, expect PASS (6 passed).**

- [ ] **Step 5: Commit**

```bash
git add core/greeting.py tests/test_greeting.py
git commit -m "feat(boot): greeting composition + recognition-mode decision (pure)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: `/api/greeting` endpoint

**Files:** Modify `core/main.py`

- [ ] **Step 1: Add the endpoint** after the `/api/health` route in `core/main.py`:

```python
@app.get("/api/greeting")
async def get_greeting():
    """Build a time/identity-aware greeting from the bio memory layer."""
    from core.greeting import build_greeting
    from datetime import datetime
    bio = brain.memory.layers.get("bio", {})
    last_seen = bio.get("last_seen")
    minutes = 0
    if last_seen:
        try:
            delta = datetime.now() - datetime.fromisoformat(last_seen)
            minutes = int(delta.total_seconds() // 60)
        except (ValueError, TypeError):
            minutes = 0
    text = build_greeting(bio, datetime.now().hour, minutes)
    # Record this visit.
    bio["last_seen"] = datetime.now().isoformat()
    brain.memory.layers["bio"] = bio
    brain.memory.save()
    return {"text": text}
```

- [ ] **Step 2: Verify (server running).**

```bash
curl -s http://localhost:8000/api/greeting
```
Expected: JSON like `{"text": "Good evening, Sir. Friday is online and at your service."}`.

- [ ] **Step 3: Commit**

```bash
git add core/main.py
git commit -m "feat(boot): /api/greeting endpoint (time + identity aware)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Boot overlay (UI)

**Files:** Modify `ui/index.html`, `ui/css/style.css`; Create `ui/js/boot.js`

- [ ] **Step 1: Add overlay markup.** In `ui/index.html`, right after `<body data-state="idle">`,
  add:

```html
    <div id="boot-overlay">
        <div class="boot-lines" id="boot-lines"></div>
        <div class="boot-hint">click to skip</div>
    </div>
```

- [ ] **Step 2: Add styles.** Append to `ui/css/style.css`:

```css
/* Boot sequence overlay */
#boot-overlay{ position:fixed; inset:0; z-index:300; background:#04060c;
  display:flex; flex-direction:column; align-items:center; justify-content:center; gap:14px;
  transition:opacity .8s; }
#boot-overlay.gone{ opacity:0; pointer-events:none; }
.boot-lines{ font-family:'Inter',monospace; font-size:13px; letter-spacing:.18em; color:var(--accent);
  text-align:left; min-width:320px; min-height:140px; }
.boot-lines .bl{ opacity:0; animation:bootline .4s forwards; }
@keyframes bootline{ to{ opacity:1; } }
.boot-hint{ font-size:9px; letter-spacing:.2em; color:var(--text-dim); }
```

- [ ] **Step 3: Create `ui/js/boot.js`:**

```javascript
// Cinematic boot overlay: prints init lines, then dissolves into the HUD.
const LINES = [
    "INITIALIZING COGNITIVE CORE…",
    "MOUNTING MEMORY LAYERS [7/7]",
    "CALIBRATING VOICE SYNTHESIS…",
    "AGENCY SUBSYSTEMS ONLINE",
    "FRIDAY READY.",
];

function runBoot(onDone) {
    const overlay = document.getElementById('boot-overlay');
    const host = document.getElementById('boot-lines');
    if (!overlay || !host) { onDone && onDone(); return; }
    let i = 0;
    const skip = () => finish();
    let finished = false;
    function finish() {
        if (finished) return;
        finished = true;
        overlay.removeEventListener('click', skip);
        overlay.classList.add('gone');
        setTimeout(() => { overlay.style.display = 'none'; onDone && onDone(); }, 800);
    }
    overlay.addEventListener('click', skip);
    const tick = () => {
        if (finished) return;
        if (i < LINES.length) {
            const div = document.createElement('div');
            div.className = 'bl';
            div.textContent = '› ' + LINES[i];
            host.appendChild(div);
            i++;
            setTimeout(tick, 420);
        } else {
            setTimeout(finish, 500);
        }
    };
    tick();
}

window.Boot = { runBoot };
```

- [ ] **Step 4: Add the script tag** in `ui/index.html` before `app.js`:

```html
    <script type="module" src="ui/js/boot.js"></script>
    <script type="module" src="ui/js/app.js"></script>
```

- [ ] **Step 5: In-browser verification.** Reload http://localhost:8000 — the boot overlay
  prints the init lines over ~2.5s then dissolves to reveal the HUD; clicking skips it.

- [ ] **Step 6: Commit**

```bash
git add ui/index.html ui/css/style.css ui/js/boot.js
git commit -m "feat(boot): cinematic boot overlay

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: Face recognition + greeting trigger (UI)

**Files:** Create `ui/js/recognition.js`; Modify `ui/index.html`, `ui/js/app.js`

- [ ] **Step 1: Create `ui/js/recognition.js`** (face-api.js via CDN; all failures → profile):

```javascript
// Browser face recognition with graceful profile fallback.
// Loads face-api.js from CDN; any failure (no lib, no camera, no permission,
// not enrolled, no match) resolves to mode 'profile'.
const FACEAPI = 'https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js';
const MODELS = 'https://cdn.jsdelivr.net/npm/@vladmandic/face-api@1.7.13/model/';
const KEY = 'friday_face_descriptor';

function pickGreetingMode(hasCamera, enrolled, matched) {
    return (hasCamera && enrolled && matched) ? 'face' : 'profile';
}

async function _loadLib() {
    if (window.faceapi) return true;
    await new Promise((res, rej) => {
        const s = document.createElement('script');
        s.src = FACEAPI; s.onload = res; s.onerror = rej;
        document.head.appendChild(s);
    });
    return !!window.faceapi;
}

async function _camera() {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    const video = document.createElement('video');
    video.srcObject = stream; video.muted = true; await video.play();
    return { video, stream };
}

async function recognize() {
    // Returns 'face' or 'profile'. Never throws.
    try {
        if (!await _loadLib()) return 'profile';
        await faceapi.nets.tinyFaceDetector.loadFromUri(MODELS);
        await faceapi.nets.faceRecognitionNet.loadFromUri(MODELS);
        await faceapi.nets.faceLandmark68Net.loadFromUri(MODELS);
        const enrolled = localStorage.getItem(KEY);
        const { video, stream } = await _camera();
        const det = await faceapi.detectSingleFace(video, new faceapi.TinyFaceDetectorOptions())
            .withFaceLandmarks().withFaceDescriptor();
        let matched = false;
        if (det && enrolled) {
            const saved = new Float32Array(JSON.parse(enrolled));
            const dist = faceapi.euclideanDistance(saved, det.descriptor);
            matched = dist < 0.55;
        } else if (det && !enrolled) {
            // First run: enroll this face for next time.
            localStorage.setItem(KEY, JSON.stringify(Array.from(det.descriptor)));
        }
        stream.getTracks().forEach(t => t.stop());
        return pickGreetingMode(true, !!enrolled, matched);
    } catch (e) {
        console.log('[recognition] falling back to profile:', e.message);
        return 'profile';
    }
}

window.Recognition = { recognize, pickGreetingMode };
```

- [ ] **Step 2: Add the script tag** in `ui/index.html` before `app.js` (after boot.js):

```html
    <script type="module" src="ui/js/boot.js"></script>
    <script type="module" src="ui/js/recognition.js"></script>
    <script type="module" src="ui/js/app.js"></script>
```

- [ ] **Step 3: Trigger boot + greeting on load in `ui/js/app.js`.** In the
  `window.addEventListener('DOMContentLoaded', ...)` handler, after `connect();`, add:

```javascript
    // Cinematic boot, then greet (face if recognized, else profile).
    window.Boot?.runBoot(async () => {
        try { await window.Recognition?.recognize(); } catch (e) {}
        try {
            const g = await (await fetch('/api/greeting')).json();
            if (g.text && socket?.readyState === WebSocket.OPEN) {
                // Speak the greeting by sending it as a system-origin text turn.
                socket.send(JSON.stringify({ type: 'text', content: '(boot greeting) ' + g.text }));
            }
        } catch (e) {}
    });
```

  Note: simplest path is to let the greeting be spoken by Friday. To avoid the model
  re-interpreting it, instead emit it directly — replace the greeting fetch block above with
  a direct approach: fetch `/api/greeting` and call a new lightweight server broadcast. To
  keep this task UI-only and avoid backend coupling, we display+speak via the existing
  proactive endpoint is overkill; the `text` turn above is acceptable for v1 and the model
  will simply read it back in-character. (If it reinterprets oddly, Phase-4 polish can add a
  dedicated `/ws` "speak" control; out of scope here.)

- [ ] **Step 4: In-browser verification.** Reload http://localhost:8000. Boot plays; the
  browser asks for camera permission. **Allow** → on first run it enrolls your face silently,
  and Friday greets you; reload again → she recognizes you ("Welcome back"). **Deny** camera
  → she still greets you via the profile path. No console errors that break the page.

- [ ] **Step 5: Commit**

```bash
git add ui/js/recognition.js ui/index.html ui/js/app.js
git commit -m "feat(boot): browser face recognition with profile fallback + greeting

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] **Backend suite green (besides the 3 known pre-existing failures):**

Run: `PYTHONPATH=. python3 -m pytest tests/ -p no:cacheprovider -q`
Expected: events, voice_session (incl. summarize), triggers (7), greeting (6) all pass.

- [ ] **Full in-browser demo (Ollama running):** boot sequence → greeting → left rail shows
  live vitals + tasks → ask a web search → result card appears → wait/force a proactive
  cycle → captioned proactive line + orb pulse. No console errors.

- [ ] **Update CLAUDE.md** — add bullets for `core/triggers.py`, `core/greeting.py`, and the
  HUD/boot UI modules; commit:

```bash
git add CLAUDE.md
git commit -m "docs: document HUD, triggers, greeting, boot/recognition modules

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (completed by plan author)

- **Spec coverage:** HUD rail + cards → Tasks 1-3; result event/summarize → Tasks 1-2;
  proactivity triggers → Task 4; proactive rework + v2-broadcast fix → Task 5; greeting +
  mode decision → Task 6; `/api/greeting` → Task 7; boot overlay → Task 8; face recognition +
  fallback + greeting trigger → Task 9. All spec sections covered.
- **Placeholder scan:** none — every code step has full code. (Task 9 Step 3 contains a
  design note about a future optional refinement, not a placeholder; the v1 path is fully
  specified.)
- **Type consistency:** `result_event(tool,title,lines)` ↔ `Hud.result(msg)` ↔
  `summarize_result(tool,result)->{title,lines}|None` ↔ `[Result: {...}]` marker. `evaluate_triggers(ctx)->[{kind,score,message_hint}]` + `THRESHOLD` consistent in tests/impl/proactive. `build_greeting(bio,hour,minutes_since_seen)` and `pick_greeting_mode(has_camera,enrolled,matched)` match across greeting.py + recognition.js (`pickGreetingMode`). v2 event names (`state/transcript/caption/result/mood`) match `app.js handleEvent`.
- **Scope:** subsystems 2-4 only; comms/calendar and GPU face models excluded.
