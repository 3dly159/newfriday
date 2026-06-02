# Friday "Hardened & Capable" — Design

**Date:** 2026-06-02
**Goal:** Make Friday trustworthy to run continuously (hardening) and meaningfully more
capable over time (deeper agency: scheduling, reminders, documents, email).

Two phases in one run. **Phase 1 (Hardening) first** because it protects everything,
including the new agency work. Then **Phase 2 (Deeper Agency).**

## Decisions locked (from brainstorming)

- **Hardening scope (all):** atomic memory writes + rotating backups; global error
  resilience (turn loop + endpoints never die; structured logging); fix the async test
  infra so "green" is real; UI smoke tests (Playwright).
- **Agency scope (all):** scheduled/recurring tasks; reminders & timers; document
  understanding; email.
- **Email:** Gmail API (OAuth). Built fully but **degrades gracefully** when
  `config/credentials.json` / token is absent — reports "not configured" instead of
  erroring. Google-side setup (Cloud project, consent screen, credentials.json, one-time
  browser auth) is the user's to do; a setup doc is included.
- **Schedule store:** new `config/schedule.json` (atomic writes), surfaced in the task
  layer / HUD — separate from rolling session memory.

## Context (verified 2026-06-02)

- `core/memory.py::save` writes `memory.json` directly (non-atomic; a quest bug already
  caused a KeyError class issue). `core/config.py::save_config` writes registry directly too.
- Agency layer exists: `core/agency/{web,files,system,registry}.py`; `registry.dispatch`
  permission-gates via `bridge.PermissionManager` and returns `PENDING_APPROVAL`/denied
  sentinels. Tools join `brain.tools` + route through `brain.execute_tool`.
- Proactivity: `core/proactive.py` runs a timer cycle, evaluates `core/triggers.py`, and
  broadcasts via the v2 contract; gated by `core/presence.py`.
- Tests: `pytest-asyncio` does NOT load in this env; 3 tests are perma-red
  (`test_phase1::test_tts_generation`, `test_phase5_legion::test_legion_delegation`,
  `test_phase5_evolution::test_run_tests`). Other async tests use `asyncio.run()`.
- `python3` + `PYTHONPATH=.`. Playwright MCP available; `requirements.txt` pins deps.

---

## PHASE 1 — Hardening

### 1A. Atomic writes + backups (`core/atomicio.py` new; used by memory + config + scheduler)
- `atomic_write_json(path, data, backups=3)`: write to `path.tmp` then `os.replace` (atomic
  on POSIX); before replacing, rotate existing file to `path.bak1`, shifting `bak1→bak2→bak3`.
- `core/memory.py::save` and `core/config.py::save_config` call it. Pure-ish (filesystem)
  but unit-testable with `tmp_path`: verifies no partial file on simulated failure, backups
  rotate, content round-trips.

### 1B. Global error resilience (`core/main.py`)
- The `/ws/voice` loop already has a broad `except`; add structured logging (timestamp,
  context) to `server.log` and ensure a per-message try/except so one bad frame/turn never
  breaks the socket. Wrap `run_turn` invocation so an exception emits an in-character error
  + `state: idle` rather than dropping the connection.
- Helper `log_error(context, exc)` writes a structured line; unit-testable (formats a line).

### 1C. Fix async test infra
- Add `pytest-asyncio` config so `@pytest.mark.asyncio` tests run. Approach: add
  `asyncio_mode = auto` in `pytest.ini` AND ensure the plugin is importable; if it cannot be
  made to load in this environment, convert the 3 red tests to `asyncio.run()` (the pattern
  already used elsewhere). Success = full suite green (0 failures) or those tests rewritten.

### 1D. UI smoke tests (`tests/test_ui_smoke.py`, Playwright)
- Launch the app (uvicorn on a test port), load `/` and `/ui/neural.html`, assert: no
  console errors, key elements present (`#orb-canvas`, `#telemetry-rail`, `#convo-panel`;
  neural `#neural-canvas`, `#neural-detail`). Skipped cleanly if Playwright/browser
  unavailable so it never blocks the suite.

---

## PHASE 2 — Deeper Agency

### 2A. Scheduler (`core/scheduler.py` + `config/schedule.json`)
- Durable schedule entries: `{id, kind: "once"|"recurring", when, text, created_at, last_run}`.
  - `once`: an ISO datetime; fires once then is removed.
  - `recurring`: a simple spec — `daily@HH:MM` (extendable). 
- Pure core: `due_entries(entries, now) -> list` (what should fire at `now`), and
  `next_run(entry, now)` — fully unit-tested (daily rollover, one-off past/future, dedupe via
  `last_run`).
- Persistence via `atomic_write_json` to `config/schedule.json`.
- Integration: `core/proactive.py` checks `due_entries` each cycle (independent of the
  presence gate? — schedules the user explicitly set SHOULD fire regardless of camera
  presence; trigger-based chatter stays presence-gated). Due items broadcast via the v2
  contract; recurring entries update `last_run`, one-offs are removed.
- Tools (via registry, category `schedule`): `schedule_task(text, when)`,
  `list_schedules()`, `cancel_schedule(id)`.

### 2B. Reminders & timers
- Thin sugar over the scheduler: `remind_me(text, when)` where `when` accepts `in 20m`,
  `in 2h`, `at 17:00`, or an ISO time → normalized to a `once` entry. Pure `parse_when(s, now)`
  is unit-tested.

### 2C. Documents (`core/agency/documents.py`)
- `read_document(path)`: text/markdown directly; PDF via `pypdf` (add to requirements) →
  extracted text; path-safety reuses `files.is_safe_path`. Returns truncated text.
- `summarize_document(path)`: read → ask brain to summarize (runs in the tool by returning
  text the model then summarizes, OR a direct brain call — chosen: return cleaned text +
  let the calling model summarize, keeping the tool pure of LLM coupling).
- `search_in_document(path, query)`: pure substring/keyword scan returning matching
  snippets with line numbers. Unit-tested (chunking, snippet windows, path-safety).
- Tools (category `documents`): `read_document`, `search_in_document`.

### 2D. Email (`core/agency/email_gmail.py`, Gmail API)
- `email_status()`: reports configured/unconfigured. `email_check(n)`, `email_search(query)`,
  `email_draft(to, subject, body)`, `email_send(to, subject, body)`.
- Uses `google-api-python-client` + `google-auth-oauthlib` (add to requirements). Reads
  `config/credentials.json`, stores token at `config/gmail_token.json`.
- **Graceful degradation:** if creds/token missing or libs absent, every email tool returns
  a clear "Gmail not configured — see docs/gmail-setup.md" string (never raises). Only the
  pure helpers (e.g. message formatting, `is_configured()` path check) are unit-tested; live
  send/read needs the user's Google setup.
- Tools (category `email`): the four above. `docs/gmail-setup.md` written with exact steps.

### Registry + permissions
- New categories default to **allow** (consistent with prior decision): `schedule`,
  `documents`, `email`. Added to `bridge.PermissionManager` defaults; appear in Settings.
- All new tools registered in `core/agency/registry.py` (schemas + IMPL + PERMISSION_MAP);
  `brain` picks them up automatically via `AGENCY_TOOLS`.

## Data flow

- Schedule: user asks → `schedule_task` tool → `scheduler` persists → each proactive cycle
  `due_entries` fires due items via v2 broadcast → recurring updates `last_run`, one-offs removed.
- Documents: model calls `read_document`/`search_in_document` → text returned → model answers.
- Email: model calls an email tool → Gmail API (or "not configured") → result to model.

## Error handling

- All filesystem writes atomic; a failed write leaves the prior file + backups intact.
- WS loop: per-message try/except + structured log; never drops the socket on one error.
- Scheduler parse errors → tool returns a helpful message; a malformed `schedule.json` loads
  as empty (logged) rather than crashing.
- Documents: missing file / bad PDF / unsafe path → clear message, no raise.
- Email: any missing-config/lib/auth failure → "not configured" message, no raise.

## Testing

- Pure units (pytest): `atomic_write_json` (rotation, round-trip, no partial), `log_error`
  formatting, scheduler `due_entries`/`next_run`/`parse_when`, documents
  `search_in_document`/chunking/path-safety, email `is_configured`/message formatting.
- Async infra fixed so the full suite reports green.
- UI smoke (Playwright, skip-if-unavailable).
- Live smoke: set a one-off reminder ~1 min out and confirm it fires; read a local text doc;
  `email_status()` returns "not configured" cleanly.

## Out of scope

- Non-daily recurring cron complexity (weekly/monthly) — `daily@HH:MM` + one-off now;
  extendable later. Multi-account email. OCR for scanned PDFs. Calendar (separate).

## Success criteria

- A crash mid-save cannot corrupt `memory.json`/`schedule.json`; backups exist.
- One bad turn/frame never kills the WebSocket session; errors are logged with context.
- Full test suite green (no perma-red); UI smoke passes (or skips cleanly).
- Friday can set/list/cancel schedules and reminders that fire spoken; read & search local
  documents; and email tools work the moment Gmail creds are added (graceful until then).
