# Friday "Alive & Aware" — Design (Cinematic HUD + Boot/Recognition + Smarter Proactivity)

**Date:** 2026-06-01
**Goal:** Make Friday feel alive and aware like the films — a data-rich cinematic HUD,
a boot sequence that recognizes and greets the user, and proactivity that watches real
signals and speaks when it matters.

This is **subsystems 2, 3, 4 of 4** in the "match the movies" effort (subsystem 1, the
agency layer, is done — commit 20e6857). Built as one combined effort in three phases.

## Decisions locked (from brainstorming)

- **HUD layout:** Left telemetry rail — persistent left margin for vitals + tasks; agency
  result cards rise bottom-center near the orb; conversation panel stays right.
- **Recognition:** Browser face recognition (webcam + face-api.js), one-time enroll, local
  storage. ALWAYS falls back to an identity-profile greeting (name/"Sir" from `bio` memory,
  time-of-day aware) when there's no camera, permission, or match — boot never breaks.
- **Proactive triggers:** all four — system vitals, time/routine, tasks/memory, web/world
  (via agency). **Balanced** cadence (noticeable but not annoying).

## Context (verified 2026-06-01)

- `ui/js/hud.js` already polls `GET /api/vitals` every 2.5s into `window.__vitals` but
  renders nothing. `/api/vitals` returns `{cpu_usage, memory_usage, battery, temp}`.
- `/api/config` returns config + injected `system_memory` (incl. `task` layer) for the UI.
- The v2 UI event contract (server→UI) is `state | transcript | caption | action | mood |
  approval | arg_unlocked`; `app.js` routes them; agency action chips already work.
- **Bug to fix:** `core/main.py::broadcast_proactive_message` still emits the legacy
  `speak_segment` event the v2 UI ignores — proactive messages play audio but show no
  caption/transcript. Subsystem 4 routes proactive output through the v2 contract.
- `core/proactive.py` currently: sleep N min → ask LLM for SPEAK/ACT/SILENCE JSON →
  broadcast. `core/memory.py` has `bio` (layer 1) and `social` (trust/banter) layers and
  `update_bio`. `python3` + `PYTHONPATH=.`; async tests use `asyncio.run()`.

---

## Subsystem 2 — Cinematic HUD (left telemetry rail)

### Components
- **`ui/index.html`** — add a left `#telemetry-rail` (vitals + tasks sections) and a
  `#result-cards` container bottom-center.
- **`ui/css/style.css`** — rail styling (glass, arc-reactor accents), animated vital bars,
  result-card rise/fade.
- **`ui/js/hud.js`** — render vitals from the existing poll into the rail bars (bar color
  shifts toward amber/red past 70%/90%); render the task list from `/api/config`'s
  `system_memory.task`; add `result(msg)` to render a bottom-center result card from a new
  `result` event, auto-fading after a few seconds.
- **`core/events.py`** — add `result_event(tool, title, lines)`.
- **`core/voice_session.py`** — when an agency tool returns structured data (web results,
  file lists), emit a `result` event so the HUD shows a card (in addition to the action
  chip). A small pure helper `summarize_result(tool, result) -> {title, lines} | None`
  decides what (if anything) is card-worthy.

### Data flow
Vitals/tasks: existing 2.5s poll → rail render (no backend change). Result cards: agency
tool result → `summarize_result` → `result` event → `hud.result()` renders card.

---

## Subsystem 3 — Boot sequence + recognize-and-greet

### Components
- **`ui/js/boot.js`** + CSS — a brief cinematic init overlay on first load ("INITIALIZING
  COGNITIVE CORE… CALIBRATING…") over the spinning-up orb, then dissolves into the HUD.
  Short and skippable (click/keypress).
- **`ui/js/recognition.js`** — webcam + face-api.js (CDN). `enroll()` captures and stores a
  face descriptor in `localStorage`; `recognize()` returns match|none. Pure helper
  `pickGreetingMode(hasCamera, enrolled, matched) -> "face" | "profile"` is unit-testable.
  All failures (no camera, denied permission, no enrollment, no match, lib load fail) →
  `"profile"`.
- **`core/greeting.py`** (new) — `build_greeting(bio, now, last_seen) -> str`: composes an
  in-persona line from the user's name/title, time of day, and time since last seen. Pure,
  unit-tested.
- **`core/main.py`** — `GET /api/greeting` returns `{text}` from `build_greeting` using the
  `bio` layer + server time + a stored `last_seen` (persisted in `bio`). The UI speaks it
  through the normal voice path after boot.

### Data flow
Boot overlay → `recognition.pickGreetingMode` → fetch `/api/greeting` → speak via existing
voice/caption pipeline. Face path personalizes the spoken line ("Welcome back, Sir"); profile
path is the same endpoint without a face match.

---

## Subsystem 4 — Smarter proactivity (trigger-scan, balanced)

### Components
- **`core/triggers.py`** (new) — pure, testable trigger evaluation. `evaluate_triggers(ctx)`
  takes a context dict (vitals, tasks, time, last-interaction, idle seconds) and returns a
  scored list of candidate triggers `[{kind, score, message_hint}]`. Covers:
  - **vitals**: battery low+unplugged, CPU/RAM sustained high, disk low.
  - **time/routine**: greeting windows, "long focus session", late-night, idle-too-long.
  - **tasks/memory**: pending tasks/quests, follow-ups.
  - **web/world**: flagged when a recent topic warrants a fetch (the agency call itself runs
    in `proactive.py`, not in the pure scorer).
  Each candidate has a score; a **balanced threshold** decides whether to surface.
- **`core/proactive.py`** — rework `run_cycle` to: gather context → `evaluate_triggers` →
  if top candidate ≥ threshold, ask the LLM to phrase it in-persona (or use the hint
  directly) → broadcast via the v2 event contract. Optionally run an agency web fetch for
  `web/world` triggers.
- **`core/main.py::broadcast_proactive_message`** — rewritten to emit the v2 contract
  (`state: speaking` → `transcript(friday)` + `caption` + audio → `state: idle`) instead of
  the dead `speak_segment`, so proactive speech shows captions/transcript and pulses the orb.

### Data flow
Timer cycle → context gather → pure `evaluate_triggers` → threshold gate → (LLM phrasing) →
v2-contract broadcast to all connected UIs.

## Error handling (all subsystems)

- HUD: missing vitals/tasks fields render as "—", never throw; result cards are best-effort.
- Boot/recognition: any camera/lib/permission failure silently → profile greeting; the
  boot overlay always dissolves on a timeout even if greeting fetch fails.
- Greeting: missing `bio` fields → sensible defaults ("Welcome, Sir").
- Proactivity: trigger scan and broadcast wrapped so a failure logs and the loop continues
  (existing pattern); web fetch failures are swallowed.

## Testing (pure logic via pytest; UI verified in-browser)

- `summarize_result` (card-worthy vs not, shapes), `build_greeting` (time-of-day, last-seen,
  missing bio), `pickGreetingMode` (all fallback paths — tested in JS-agnostic form by
  porting the truth table into a Python helper OR documented + manually verified), and
  `evaluate_triggers` (each trigger kind fires/doesn't, threshold gating, scoring order).
- Live/in-browser: HUD rail shows real vitals + tasks; an agency turn shows a result card;
  boot overlay → greeting plays; a forced proactive cycle shows a captioned message.

> Note on `pickGreetingMode`: implemented in `recognition.js` (JS) but its decision table is
> mirrored in `core/greeting.py::pick_greeting_mode` and unit-tested there, so the logic is
> covered without a JS test runner.

## Build order (one effort, three phases)

1. **HUD** — rail + result cards + `result_event`/`summarize_result`. Visible foundation.
2. **Proactivity** — `triggers.py` + proactive rework + v2-event broadcast fix.
3. **Boot/Recognition** — `greeting.py` + `/api/greeting` + `boot.js` + `recognition.js`.

Each phase leaves the app working and demoable.

## Out of scope

Comms/calendar (needs account setup). Real GPU-accelerated face models (face-api.js tiny
model is sufficient). Multi-user profiles (single user/"Sir"). Spatial/holographic
window-throwing. These can follow later.

## Success criteria

- HUD shows live vitals (color-reactive) + tasks in the left rail; agency results surface as
  bottom-center cards.
- Boot plays a cinematic sequence and greets the user — by face when enrolled+matched, else
  by profile — and never hangs.
- Proactivity reacts to real signals across all four trigger kinds at a balanced cadence,
  and proactive speech shows captions/transcript + orb pulse via the v2 contract.
- New pure logic (`summarize_result`, `build_greeting`, `pick_greeting_mode`,
  `evaluate_triggers`) is unit-tested; app runs and all three phases verify in-browser.
