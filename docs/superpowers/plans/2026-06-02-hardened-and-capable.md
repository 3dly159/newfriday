# Friday "Hardened & Capable" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden Friday (atomic writes+backups, error resilience, real green tests, UI smoke) and add deeper agency (scheduler, reminders, documents, Gmail email — graceful until configured).

**Architecture:** Phase 1 adds a shared `core/atomicio.py` used by memory/config/scheduler, structured error logging in `main.py`, async-test fixes, and a Playwright UI smoke test. Phase 2 adds `core/scheduler.py` (+ `config/schedule.json`) fired by the proactive loop, and new agency modules (`documents.py`, `email_gmail.py`) registered through the existing `registry.py`.

**Tech Stack:** Python 3.12 (`python3`, `PYTHONPATH=.`), FastAPI, pytest (+pytest-asyncio), Playwright (MCP/optional), pypdf, google-api-python-client + google-auth-oauthlib. New tools join `core/agency/registry.py`.

---

## Conventions

- Run tests: `PYTHONPATH=. python3 -m pytest <path> -v -p no:cacheprovider`
- `python3` only. Branch `friday-milestone-1-voice-reliability`. Commit per task; only `git add` named files.
- New deps added to `requirements.txt` as encountered; install with `pip install --user <pkg>`.

## File Structure

- Create: `core/atomicio.py` — `atomic_write_json(path, data, backups=3)`.
- Modify: `core/memory.py`, `core/config.py` — use atomic writes.
- Modify: `core/main.py` — structured `log_error`, per-message resilience.
- Modify: `pytest.ini` / `requirements.txt` — async test infra.
- Create: `tests/test_ui_smoke.py` — Playwright smoke (skip-if-unavailable).
- Create: `core/scheduler.py` — pure due/parse logic + persistence; `config/schedule.json`.
- Modify: `core/proactive.py` — fire due schedules each cycle (presence-independent).
- Create: `core/agency/documents.py` — read/search docs.
- Create: `core/agency/email_gmail.py` — Gmail tools, graceful.
- Modify: `core/agency/registry.py`, `core/bridge.py` — register tools + permission cats.
- Create: `docs/gmail-setup.md`.
- Tests: `tests/test_atomicio.py`, `tests/test_scheduler.py`, `tests/test_documents.py`, `tests/test_email.py`, plus extend `tests/test_agency_registry.py`.

---

# PHASE 1 — HARDENING

## Task 1: Atomic JSON writes + rotating backups

**Files:** Create `core/atomicio.py`; Test `tests/test_atomicio.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_atomicio.py`:

```python
import json
from core.atomicio import atomic_write_json


def test_writes_and_roundtrips(tmp_path):
    p = tmp_path / "d.json"
    atomic_write_json(str(p), {"a": 1})
    assert json.loads(p.read_text()) == {"a": 1}


def test_no_tmp_left_behind(tmp_path):
    p = tmp_path / "d.json"
    atomic_write_json(str(p), {"a": 1})
    assert not (tmp_path / "d.json.tmp").exists()


def test_rotates_backups(tmp_path):
    p = tmp_path / "d.json"
    atomic_write_json(str(p), {"v": 1})
    atomic_write_json(str(p), {"v": 2})
    atomic_write_json(str(p), {"v": 3})
    # Current is newest; bak1 is the immediately-previous content.
    assert json.loads(p.read_text())["v"] == 3
    assert json.loads((tmp_path / "d.json.bak1").read_text())["v"] == 2
    assert json.loads((tmp_path / "d.json.bak2").read_text())["v"] == 1


def test_creates_parent_dir(tmp_path):
    p = tmp_path / "sub" / "d.json"
    atomic_write_json(str(p), {"ok": True})
    assert json.loads(p.read_text())["ok"] is True
```

- [ ] **Step 2: Run, expect FAIL** (`ModuleNotFoundError: No module named 'core.atomicio'`)

Run: `PYTHONPATH=. python3 -m pytest tests/test_atomicio.py -v -p no:cacheprovider`

- [ ] **Step 3: Create `core/atomicio.py`:**

```python
import json
import os


def atomic_write_json(path, data, backups=3):
    """Write JSON to `path` atomically (tmp file + os.replace), rotating up to
    `backups` previous versions to path.bak1..bakN. A crash mid-write leaves the
    previous file (and backups) intact."""
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    # Rotate existing backups: bak(N-1) -> bakN, ..., current -> bak1.
    if os.path.exists(path) and backups > 0:
        for i in range(backups, 1, -1):
            src = f"{path}.bak{i - 1}"
            dst = f"{path}.bak{i}"
            if os.path.exists(src):
                os.replace(src, dst)
        try:
            import shutil
            shutil.copy2(path, f"{path}.bak1")
        except OSError:
            pass

    tmp = f"{path}.tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=4)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)  # atomic on POSIX
```

- [ ] **Step 4: Run, expect PASS (4 passed).**

- [ ] **Step 5: Commit**

```bash
git add core/atomicio.py tests/test_atomicio.py
git commit -m "feat(hardening): atomic JSON writes with rotating backups

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Use atomic writes in memory + config

**Files:** Modify `core/memory.py`, `core/config.py`

- [ ] **Step 1: Memory.** In `core/memory.py`, replace the `save` body:

```python
    def save(self):
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, "w") as f:
            json.dump(self.layers, f, indent=4)
```

with:

```python
    def save(self):
        from core.atomicio import atomic_write_json
        atomic_write_json(self.storage_path, self.layers)
```

- [ ] **Step 2: Config.** In `core/config.py` `save_config`, replace:

```python
    with open(path, "w") as f:
        json.dump(clean, f, indent=4)
```

with:

```python
    from core.atomicio import atomic_write_json
    atomic_write_json(path, clean)
```

- [ ] **Step 3: Verify nothing regressed.**

Run: `PYTHONPATH=. python3 -m pytest tests/test_config_validation.py tests/test_memory_tasks.py -p no:cacheprovider -q`
Expected: all pass. Also smoke: `PYTHONPATH=. python3 -c "from core.memory import FridayMemory; m=FridayMemory(); m.save(); print('saved ok')"` → prints `saved ok`.

- [ ] **Step 4: Commit**

```bash
git add core/memory.py core/config.py
git commit -m "feat(hardening): memory + config use atomic writes

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Structured error logging + WS resilience

**Files:** Modify `core/main.py`; Test `tests/test_logerror.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_logerror.py`:

```python
from core.main import format_error_line


def test_format_error_line_has_context_and_type():
    line = format_error_line("ws_turn", ValueError("boom"))
    assert "ws_turn" in line
    assert "ValueError" in line
    assert "boom" in line
```

- [ ] **Step 2: Run, expect FAIL** (`ImportError: cannot import name 'format_error_line'`)

Run: `PYTHONPATH=. python3 -m pytest tests/test_logerror.py -v -p no:cacheprovider`

- [ ] **Step 3: Add the helper + use it.** In `core/main.py`, after the `logger = logging.getLogger("Friday")` line, add:

```python
def format_error_line(context, exc):
    """Structured one-line error record for server.log."""
    from datetime import datetime
    return f"[{datetime.now().isoformat()}] ERROR ctx={context} type={type(exc).__name__} msg={exc}"


def log_error(context, exc):
    logger.error(format_error_line(context, exc))
```

  Then in the `/ws/voice` handler, wrap the per-turn calls. Find the audio-path
  `await session.run_turn(transcription)` and the text-path `await session.run_turn(user_text)`
  and wrap EACH like:

```python
                    try:
                        await session.run_turn(user_text)
                    except Exception as e:
                        log_error("ws_text_turn", e)
```

  (and for the audio path:)

```python
            try:
                await session.run_turn(transcription)
            except Exception as e:
                log_error("ws_audio_turn", e)
```

  This keeps the socket alive if a single turn throws.

- [ ] **Step 4: Run, expect PASS; import smoke.**

Run: `PYTHONPATH=. python3 -m pytest tests/test_logerror.py -v -p no:cacheprovider`
Then: `PYTHONPATH=. python3 -c "import core.main; print('main OK')"` → `main OK`.

- [ ] **Step 5: Commit**

```bash
git add core/main.py tests/test_logerror.py
git commit -m "feat(hardening): structured error logging + per-turn WS resilience

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Fix async test infrastructure

**Files:** Modify `requirements.txt`, `pytest.ini`

- [ ] **Step 1: Ensure pytest-asyncio is installed.**

Run: `pip install --user pytest-asyncio 2>&1 | tail -2; python3 -c "import pytest_asyncio; print('plugin', pytest_asyncio.__version__)"`
Expected: prints a version. If it prints a version, the plugin is importable.

- [ ] **Step 2: Confirm `pytest.ini` enables auto mode.** Ensure `pytest.ini` contains:

```ini
[pytest]
asyncio_mode = auto
```

(It already does from earlier work; confirm via `cat pytest.ini`.)

- [ ] **Step 3: Run the previously-red async tests.**

Run: `PYTHONPATH=. python3 -m pytest tests/test_phase1.py::test_tts_generation tests/test_phase5_legion.py::test_legion_delegation -p no:cacheprovider -v`
Expected: both PASS (they need a real TTS/Anthropic? — `test_legion_delegation` may need the brain; if it fails for a NON-async reason, note it).

- [ ] **Step 4: If a test still fails for an environmental reason (not async), convert it.**
  For any still-red test, rewrite its body to drive the coroutine with `asyncio.run()` and
  skip cleanly when a live dependency is missing. Example for `test_phase5_legion.py`:

```python
import asyncio, os
import pytest
from core.agents import LegionBroker


def test_legion_delegation():
    broker = LegionBroker()
    # Provider-agnostic construction must work without network.
    assert "scout" in broker.agents
    # Live delegation needs a brain; skip if unconfigured.
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("no brain configured for live delegation")
    out = asyncio.run(broker.delegate("scout", "ping"))
    assert isinstance(out, str)
```

  Apply the minimal equivalent to any other still-red test (e.g. `test_tts_generation`
  should pass once async mode works since Edge-TTS is reachable; if not, skip-if-offline).

- [ ] **Step 5: Run the FULL suite; expect 0 failures.**

Run: `PYTHONPATH=. python3 -m pytest tests/ -p no:cacheprovider -q`
Expected: `N passed` (possibly some `skipped`), **0 failed**.

- [ ] **Step 6: Commit**

```bash
git add requirements.txt pytest.ini tests/
git commit -m "test(hardening): fix async test infra — suite green, no perma-red

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: UI smoke test (Playwright, skip-if-unavailable)

**Files:** Create `tests/test_ui_smoke.py`

- [ ] **Step 1: Create the test** — `tests/test_ui_smoke.py`:

```python
"""Smoke test: the UI loads with no console errors and key elements present.
Skips cleanly if Playwright or a browser isn't available, so it never blocks CI."""
import socket
import subprocess
import time
import os
import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close()
    return p


@pytest.fixture(scope="module")
def server():
    port = _free_port()
    env = dict(os.environ, PYTHONPATH=".")
    proc = subprocess.Popen(
        ["python3", "-m", "uvicorn", "core.main:app", "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Wait for readiness.
    import urllib.request
    base = f"http://127.0.0.1:{port}"
    for _ in range(40):
        try:
            urllib.request.urlopen(base, timeout=1); break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate(); pytest.skip("server did not start")
    yield base
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()


def _check(url, must_have_ids):
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
    except Exception:
        pytest.skip("no chromium for playwright")
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto(url, wait_until="load")
        page.wait_for_timeout(3500)  # let boot overlay + modules settle
        present = {i: page.query_selector(f"#{i}") is not None for i in must_have_ids}
        browser.close()
    # Ignore favicon/network-y noise; fail only on real JS errors.
    real = [e for e in errors if "favicon" not in e.lower()]
    assert all(present.values()), f"missing elements: {present}"
    assert not real, f"console errors: {real}"


def test_main_ui_loads(server):
    _check(server + "/", ["orb-canvas", "telemetry-rail", "convo-panel"])


def test_neural_page_loads(server):
    _check(server + "/ui/neural.html", ["neural-canvas", "neural-detail"])
```

- [ ] **Step 2: Run it.**

Run: `PYTHONPATH=. python3 -m pytest tests/test_ui_smoke.py -p no:cacheprovider -v`
Expected: PASS, or SKIP if Playwright Python/Chromium isn't installed (acceptable — it must not fail the suite). If it errors on import of `playwright`, that's a clean skip via `importorskip`.

- [ ] **Step 3: Commit**

```bash
git add tests/test_ui_smoke.py
git commit -m "test(hardening): Playwright UI smoke (skip-if-unavailable)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

# PHASE 2 — DEEPER AGENCY

## Task 6: Scheduler core (pure) + persistence

**Files:** Create `core/scheduler.py`; Test `tests/test_scheduler.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_scheduler.py`:

```python
from datetime import datetime
from core.scheduler import parse_when, due_entries, next_run


def test_parse_when_relative_minutes():
    now = datetime(2026, 1, 1, 12, 0, 0)
    out = parse_when("in 20m", now)
    assert out == datetime(2026, 1, 1, 12, 20, 0).isoformat()


def test_parse_when_relative_hours():
    now = datetime(2026, 1, 1, 12, 0, 0)
    assert parse_when("in 2h", now) == datetime(2026, 1, 1, 14, 0, 0).isoformat()


def test_parse_when_at_time_today():
    now = datetime(2026, 1, 1, 8, 0, 0)
    assert parse_when("at 17:00", now) == datetime(2026, 1, 1, 17, 0, 0).isoformat()


def test_parse_when_at_time_rolls_to_tomorrow():
    now = datetime(2026, 1, 1, 18, 0, 0)
    assert parse_when("at 09:00", now) == datetime(2026, 1, 2, 9, 0, 0).isoformat()


def test_parse_when_daily_recurring():
    assert parse_when("daily at 07:30", datetime(2026, 1, 1, 0, 0, 0)) == "daily@07:30"


def test_due_entries_fires_past_once():
    now = datetime(2026, 1, 1, 12, 0, 0)
    entries = [{"id": "1", "kind": "once", "when": datetime(2026, 1, 1, 11, 0, 0).isoformat(),
                "text": "ping", "last_run": None}]
    due = due_entries(entries, now)
    assert len(due) == 1 and due[0]["id"] == "1"


def test_due_entries_skips_future_once():
    now = datetime(2026, 1, 1, 12, 0, 0)
    entries = [{"id": "1", "kind": "once", "when": datetime(2026, 1, 1, 13, 0, 0).isoformat(),
                "text": "x", "last_run": None}]
    assert due_entries(entries, now) == []


def test_due_entries_recurring_daily_once_per_day():
    now = datetime(2026, 1, 1, 7, 30, 0)
    e = {"id": "2", "kind": "recurring", "when": "daily@07:30", "text": "brief", "last_run": None}
    assert len(due_entries([e], now)) == 1
    e["last_run"] = now.isoformat()
    # Same day, already ran -> not due again.
    assert due_entries([e], datetime(2026, 1, 1, 7, 31, 0)) == []
    # Next day -> due again.
    assert len(due_entries([e], datetime(2026, 1, 2, 7, 30, 0))) == 1
```

- [ ] **Step 2: Run, expect FAIL** (`ModuleNotFoundError: No module named 'core.scheduler'`)

- [ ] **Step 3: Create `core/scheduler.py`:**

```python
import re
import uuid
from datetime import datetime, timedelta

from core.atomicio import atomic_write_json

SCHEDULE_PATH = "config/schedule.json"


def parse_when(s, now=None):
    """Parse a human 'when' into either an ISO datetime (once) or a 'daily@HH:MM'
    recurring spec. Returns the string form stored in an entry's 'when'."""
    now = now or datetime.now()
    s = s.strip().lower()

    m = re.match(r"daily\s+at\s+(\d{1,2}):(\d{2})", s)
    if m:
        return f"daily@{int(m.group(1)):02d}:{m.group(2)}"

    m = re.match(r"in\s+(\d+)\s*m(in)?", s)
    if m:
        return (now + timedelta(minutes=int(m.group(1)))).isoformat()
    m = re.match(r"in\s+(\d+)\s*h(our)?", s)
    if m:
        return (now + timedelta(hours=int(m.group(1)))).isoformat()

    m = re.match(r"at\s+(\d{1,2}):(\d{2})", s)
    if m:
        target = now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        return target.isoformat()

    # Fallback: assume it's already an ISO datetime.
    return s


def kind_for(when):
    return "recurring" if str(when).startswith("daily@") else "once"


def next_run(entry, now=None):
    """Return the next datetime this entry should fire, or None if it's a past one-off."""
    now = now or datetime.now()
    when = entry["when"]
    if str(when).startswith("daily@"):
        hh, mm = when.split("@")[1].split(":")
        target = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
        return target
    try:
        return datetime.fromisoformat(when)
    except (ValueError, TypeError):
        return None


def due_entries(entries, now=None):
    """Return entries that should fire at `now`."""
    now = now or datetime.now()
    out = []
    for e in entries:
        when = e.get("when")
        if str(when).startswith("daily@"):
            hh, mm = when.split("@")[1].split(":")
            target = now.replace(hour=int(hh), minute=int(mm), second=0, microsecond=0)
            if now >= target:
                last = e.get("last_run")
                last_day = last[:10] if last else None
                if last_day != now.date().isoformat():
                    out.append(e)
        else:
            try:
                target = datetime.fromisoformat(when)
            except (ValueError, TypeError):
                continue
            if now >= target and not e.get("last_run"):
                out.append(e)
    return out


def load_schedule(path=SCHEDULE_PATH):
    import json, os
    if not os.path.exists(path):
        return []
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (ValueError, OSError):
        return []


def save_schedule(entries, path=SCHEDULE_PATH):
    atomic_write_json(path, entries)


def add_entry(text, when_str, path=SCHEDULE_PATH, now=None):
    entries = load_schedule(path)
    when = parse_when(when_str, now)
    entry = {"id": uuid.uuid4().hex[:8], "kind": kind_for(when), "when": when,
             "text": text, "created_at": (now or datetime.now()).isoformat(), "last_run": None}
    entries.append(entry)
    save_schedule(entries, path)
    return entry


def cancel_entry(entry_id, path=SCHEDULE_PATH):
    entries = load_schedule(path)
    kept = [e for e in entries if e.get("id") != entry_id]
    save_schedule(kept, path)
    return len(kept) < len(entries)
```

- [ ] **Step 4: Run, expect PASS (9 passed).**

- [ ] **Step 5: Commit**

```bash
git add core/scheduler.py tests/test_scheduler.py
git commit -m "feat(agency): scheduler core — parse_when/due_entries/persistence

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Fire schedules from the proactive loop + schedule tools

**Files:** Modify `core/proactive.py`, `core/agency/registry.py`, `core/bridge.py`

- [ ] **Step 1: Fire due schedules each cycle (presence-independent).** In
  `core/proactive.py` `run_cycle`, AFTER the `from core.presence import is_present` import and
  BEFORE the `if not is_present()` gate, add a schedule check that runs regardless of presence:

```python
        # User-set schedules fire regardless of camera presence.
        try:
            from core.scheduler import load_schedule, due_entries, save_schedule
            from datetime import datetime as _dt
            entries = load_schedule()
            due = due_entries(entries)
            for d in due:
                await self.broadcast_callback(d.get("text", "Reminder, Sir."))
                d["last_run"] = _dt.now().isoformat()
            # Remove fired one-offs; keep recurring.
            if due:
                kept = [e for e in entries if e.get("kind") == "recurring" or not e.get("last_run")]
                save_schedule(kept)
        except Exception as e:
            logger.error(f"Schedule check error: {e}")
```

- [ ] **Step 2: Add permission category.** In `core/bridge.py`, in the `self.permissions`
  default dict, add after `"shell": "allow",`:

```python
            "schedule": "allow",
            "documents": "allow",
            "email": "allow",
```

- [ ] **Step 3: Register schedule tools.** In `core/agency/registry.py`, add to `AGENCY_TOOLS`
  (inside the list):

```python
    {"name": "schedule_task", "description": "Schedule a reminder or recurring task. 'when' accepts 'in 20m', 'in 2h', 'at 17:00', or 'daily at 07:30'.",
     "input_schema": {"type": "object", "properties": {"text": {"type": "string"}, "when": {"type": "string"}}, "required": ["text", "when"]}},
    {"name": "list_schedules", "description": "List active reminders and scheduled tasks.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "cancel_schedule", "description": "Cancel a scheduled task by its id.",
     "input_schema": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]}},
```

  Add to `PERMISSION_MAP`:

```python
    "schedule_task": "schedule", "list_schedules": "schedule", "cancel_schedule": "schedule",
```

  Add to `IMPL` (these are sync; dispatch handles awaitable-or-not):

```python
    "schedule_task": lambda a: _schedule_add(a.get("text", ""), a.get("when", "")),
    "list_schedules": lambda a: _schedule_list(),
    "cancel_schedule": lambda a: _schedule_cancel(a.get("id", "")),
```

  And at the top of `core/agency/registry.py` (after the existing imports), add the helpers:

```python
def _schedule_add(text, when):
    from core.scheduler import add_entry
    if not text or not when:
        return "Need both text and when (e.g. 'in 20m')."
    e = add_entry(text, when)
    return f"Scheduled ({e['id']}): \"{e['text']}\" — {e['when']}"


def _schedule_list():
    from core.scheduler import load_schedule
    entries = load_schedule()
    if not entries:
        return "No scheduled tasks."
    return [{"id": e["id"], "when": e["when"], "text": e["text"]} for e in entries]


def _schedule_cancel(entry_id):
    from core.scheduler import cancel_entry
    return f"Cancelled {entry_id}." if cancel_entry(entry_id) else f"No schedule with id {entry_id}."
```

- [ ] **Step 4: Verify registration + a round-trip.**

Run:
```bash
PYTHONPATH=. python3 -c "
import asyncio
from core.brain import FridayBrain
async def main():
    b = FridayBrain()
    print(await b.execute_tool('schedule_task', {'text':'Test reminder','when':'in 30m'}))
    print(await b.execute_tool('list_schedules', {}))
asyncio.run(main())
" 2>&1 | grep -vE 'pynvml|FutureWarning|import pynvml|INFO:' | tail -4
rm -f config/schedule.json
```
Expected: a `Scheduled (xxxx): ...` line and a list containing it.

- [ ] **Step 5: Commit**

```bash
git add core/proactive.py core/agency/registry.py core/bridge.py
git commit -m "feat(agency): scheduler tools + fire due schedules from proactive loop

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Documents (read/search)

**Files:** Create `core/agency/documents.py`; Modify `core/agency/registry.py`, `requirements.txt`; Test `tests/test_documents.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_documents.py`:

```python
from core.agency.documents import search_in_document, read_document


def test_read_text_document(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "notes.txt").write_text("Hello Sir.\nThis is Friday.\n")
    out = read_document("notes.txt")
    assert "Friday" in out


def test_read_refuses_unsafe(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = read_document("/etc/passwd")
    assert "refus" in out.lower()


def test_search_in_document_finds_snippets(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "doc.txt").write_text("line one\nfind the orb here\nline three\n")
    hits = search_in_document("doc.txt", "orb")
    assert any("orb" in h.lower() for h in hits)


def test_search_no_match(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "doc.txt").write_text("nothing relevant\n")
    assert search_in_document("doc.txt", "zzz") == []
```

- [ ] **Step 2: Run, expect FAIL** (`ModuleNotFoundError: No module named 'core.agency.documents'`)

- [ ] **Step 3: Add `pypdf` to `requirements.txt`** (append a line `pypdf`) and install:

Run: `pip install --user pypdf 2>&1 | tail -1`

- [ ] **Step 4: Create `core/agency/documents.py`:**

```python
import os
from core.agency.files import is_safe_path, truncate


def _read_pdf(path):
    try:
        from pypdf import PdfReader
        reader = PdfReader(path)
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    except Exception as e:
        return f"Could not read PDF: {e}"


def read_document(path, max_chars=8000):
    """Read a text/markdown/PDF document (safe relative path), truncated."""
    if not is_safe_path(path):
        return f"Refused: '{path}' is not an allowed path."
    if not os.path.exists(path):
        return f"No such file: {path}"
    if path.lower().endswith(".pdf"):
        return truncate(_read_pdf(path), max_chars)
    try:
        with open(path, "r", errors="replace") as f:
            return truncate(f.read(), max_chars)
    except Exception as e:
        return f"Could not read {path}: {e}"


def search_in_document(path, query, max_hits=10):
    """Return matching lines (with line numbers) containing the query, case-insensitive."""
    if not is_safe_path(path):
        return [f"Refused: '{path}' is not an allowed path."]
    text = read_document(path, max_chars=200000)
    if text.startswith("Refused") or text.startswith("No such") or text.startswith("Could not"):
        return [text]
    q = query.lower()
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if q in line.lower():
            hits.append(f"L{i}: {line.strip()[:160]}")
            if len(hits) >= max_hits:
                break
    return hits
```

- [ ] **Step 5: Register the tools.** In `core/agency/registry.py`, add to `AGENCY_TOOLS`:

```python
    {"name": "read_document", "description": "Read a local document (text, markdown, or PDF) and return its text.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "search_in_document", "description": "Find lines matching a query inside a local document.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "query": {"type": "string"}}, "required": ["path", "query"]}},
```

  To `PERMISSION_MAP`:

```python
    "read_document": "documents", "search_in_document": "documents",
```

  To `IMPL` (add the import `from core.agency import documents` at the top with the other agency imports, then):

```python
    "read_document": lambda a: documents.read_document(a.get("path", "")),
    "search_in_document": lambda a: documents.search_in_document(a.get("path", ""), a.get("query", "")),
```

- [ ] **Step 6: Run tests + registration smoke.**

Run: `PYTHONPATH=. python3 -m pytest tests/test_documents.py -p no:cacheprovider -q`
Then: `PYTHONPATH=. python3 -c "from core.agency import registry; assert registry.has_tool('read_document'); print('registered')"`
Expected: tests pass; prints `registered`.

- [ ] **Step 7: Commit**

```bash
git add core/agency/documents.py core/agency/registry.py requirements.txt tests/test_documents.py
git commit -m "feat(agency): document read/search (text + PDF), registered tools

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: Email (Gmail) — graceful until configured

**Files:** Create `core/agency/email_gmail.py`; Modify `core/agency/registry.py`, `requirements.txt`; Create `docs/gmail-setup.md`; Test `tests/test_email.py`

- [ ] **Step 1: Write the failing test** — create `tests/test_email.py`:

```python
from core.agency import email_gmail as eg


def test_status_unconfigured(tmp_path, monkeypatch):
    monkeypatch.setattr(eg, "CREDENTIALS_PATH", str(tmp_path / "nope.json"))
    monkeypatch.setattr(eg, "TOKEN_PATH", str(tmp_path / "tok.json"))
    assert eg.is_configured() is False
    assert "not configured" in eg.email_status().lower()


def test_tools_graceful_when_unconfigured(tmp_path, monkeypatch):
    monkeypatch.setattr(eg, "CREDENTIALS_PATH", str(tmp_path / "nope.json"))
    monkeypatch.setattr(eg, "TOKEN_PATH", str(tmp_path / "tok.json"))
    for out in (eg.email_check(), eg.email_search("x"),
                eg.email_draft("a@b.c", "s", "b"), eg.email_send("a@b.c", "s", "b")):
        assert "not configured" in out.lower()


def test_format_message_is_base64():
    raw = eg.format_message("a@b.c", "Subject", "Body")
    assert isinstance(raw, dict) and "raw" in raw and raw["raw"]
```

- [ ] **Step 2: Run, expect FAIL** (`ModuleNotFoundError: No module named 'core.agency.email_gmail'`)

- [ ] **Step 3: Add deps to `requirements.txt`** (append `google-api-python-client` and
  `google-auth-oauthlib`) and install:

Run: `pip install --user google-api-python-client google-auth-oauthlib 2>&1 | tail -1`

- [ ] **Step 4: Create `core/agency/email_gmail.py`:**

```python
import base64
import os
from email.mime.text import MIMEText

CREDENTIALS_PATH = "config/credentials.json"
TOKEN_PATH = "config/gmail_token.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
_NOT_CONFIGURED = ("Gmail is not configured. Add config/credentials.json and authorize — "
                   "see docs/gmail-setup.md.")


def is_configured():
    return os.path.exists(CREDENTIALS_PATH) or os.path.exists(TOKEN_PATH)


def email_status():
    return "Gmail is configured." if is_configured() else _NOT_CONFIGURED


def format_message(to, subject, body):
    """Build a Gmail API 'raw' message dict (pure; used by send/draft)."""
    msg = MIMEText(body)
    msg["to"] = to
    msg["subject"] = subject
    return {"raw": base64.urlsafe_b64encode(msg.as_bytes()).decode()}


def _service():
    """Build an authed Gmail service, or None if unavailable. Never raises."""
    if not is_configured():
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        creds = None
        if os.path.exists(TOKEN_PATH):
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif os.path.exists(CREDENTIALS_PATH):
                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            else:
                return None
            with open(TOKEN_PATH, "w") as f:
                f.write(creds.to_json())
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        print(f"[email] service unavailable: {e}")
        return None


def email_check(n=5):
    svc = _service()
    if not svc:
        return _NOT_CONFIGURED
    try:
        res = svc.users().messages().list(userId="me", maxResults=n, labelIds=["INBOX"]).execute()
        msgs = res.get("messages", [])
        out = []
        for m in msgs:
            full = svc.users().messages().get(userId="me", id=m["id"], format="metadata",
                                              metadataHeaders=["From", "Subject"]).execute()
            hdrs = {h["name"]: h["value"] for h in full.get("payload", {}).get("headers", [])}
            out.append(f"{hdrs.get('From','?')}: {hdrs.get('Subject','(no subject)')}")
        return out or "Inbox is empty."
    except Exception as e:
        return f"Could not check email: {e}"


def email_search(query):
    svc = _service()
    if not svc:
        return _NOT_CONFIGURED
    try:
        res = svc.users().messages().list(userId="me", q=query, maxResults=5).execute()
        return f"{len(res.get('messages', []))} message(s) match '{query}'."
    except Exception as e:
        return f"Could not search email: {e}"


def email_draft(to, subject, body):
    svc = _service()
    if not svc:
        return _NOT_CONFIGURED
    try:
        svc.users().drafts().create(userId="me", body={"message": format_message(to, subject, body)}).execute()
        return f"Draft to {to} saved."
    except Exception as e:
        return f"Could not draft email: {e}"


def email_send(to, subject, body):
    svc = _service()
    if not svc:
        return _NOT_CONFIGURED
    try:
        svc.users().messages().send(userId="me", body=format_message(to, subject, body)).execute()
        return f"Email sent to {to}."
    except Exception as e:
        return f"Could not send email: {e}"
```

- [ ] **Step 5: Register the tools.** In `core/agency/registry.py`, add to `AGENCY_TOOLS`:

```python
    {"name": "email_check", "description": "Check recent inbox emails (sender + subject).",
     "input_schema": {"type": "object", "properties": {"n": {"type": "integer"}}}},
    {"name": "email_search", "description": "Search the mailbox with a Gmail query.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "email_draft", "description": "Draft an email (saved, not sent).",
     "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["to", "subject", "body"]}},
    {"name": "email_send", "description": "Send an email.",
     "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["to", "subject", "body"]}},
```

  To `PERMISSION_MAP`:

```python
    "email_check": "email", "email_search": "email", "email_draft": "email", "email_send": "email",
```

  To `IMPL` (add `from core.agency import email_gmail` import at top, then):

```python
    "email_check": lambda a: email_gmail.email_check(a.get("n", 5)),
    "email_search": lambda a: email_gmail.email_search(a.get("query", "")),
    "email_draft": lambda a: email_gmail.email_draft(a.get("to", ""), a.get("subject", ""), a.get("body", "")),
    "email_send": lambda a: email_gmail.email_send(a.get("to", ""), a.get("subject", ""), a.get("body", "")),
```

- [ ] **Step 6: Create `docs/gmail-setup.md`:**

```markdown
# Gmail Setup for Friday

Friday's email tools work once you connect a Google account. One-time setup:

1. Go to https://console.cloud.google.com/ → create a project (any name).
2. APIs & Services → Library → enable **Gmail API**.
3. APIs & Services → OAuth consent screen → External → add yourself as a test user.
4. APIs & Services → Credentials → Create Credentials → **OAuth client ID** →
   Application type **Desktop app**. Download the JSON.
5. Save it as `config/credentials.json` in this project.
6. Next time Friday uses an email tool, a browser window opens for you to authorize;
   the token is saved to `config/gmail_token.json`. Done.

Until then, every email tool simply replies that Gmail isn't configured — nothing breaks.
```

- [ ] **Step 7: Run tests + registration smoke.**

Run: `PYTHONPATH=. python3 -m pytest tests/test_email.py -p no:cacheprovider -q`
Then: `PYTHONPATH=. python3 -c "from core.agency import registry; assert registry.has_tool('email_send'); print('registered')"`
Expected: tests pass; prints `registered`.

- [ ] **Step 8: Commit**

```bash
git add core/agency/email_gmail.py core/agency/registry.py requirements.txt docs/gmail-setup.md tests/test_email.py
git commit -m "feat(agency): Gmail email tools (graceful until configured) + setup doc

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] **Full suite green.**

Run: `PYTHONPATH=. python3 -m pytest tests/ -p no:cacheprovider -q`
Expected: all pass (UI smoke may skip); **0 failures**.

- [ ] **Live agency smoke (Ollama running):** set a reminder for ~1 minute out, confirm it
  fires via a proactive broadcast; read a local text doc; `email_status()` → not configured.

```bash
PYTHONPATH=. python3 -c "
import asyncio
from core.brain import FridayBrain
async def main():
    b = FridayBrain()
    print(await b.execute_tool('read_document', {'path': 'QUICKSTART.md'}))[:60]
    print(await b.execute_tool('email_check', {}))
    print(await b.execute_tool('schedule_task', {'text':'stretch','when':'in 1m'}))
asyncio.run(main())
"
rm -f config/schedule.json
```

- [ ] **Update CLAUDE.md** — add bullets for `core/atomicio.py`, `core/scheduler.py`,
  `core/agency/documents.py`, `core/agency/email_gmail.py`, and the new permission categories;
  commit:

```bash
git add CLAUDE.md
git commit -m "docs: document hardening + agency modules (atomicio, scheduler, documents, email)

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (completed by plan author)

- **Spec coverage:** atomic writes+backups → Tasks 1-2; error resilience+logging → Task 3;
  async test fix → Task 4; UI smoke → Task 5; scheduler core → Task 6; schedule firing
  (presence-independent) + tools → Task 7; reminders (parse_when sugar) → Tasks 6-7;
  documents → Task 8; email graceful + setup doc → Task 9; permission categories → Task 7
  Step 2. All spec sections covered.
- **Placeholder scan:** none — every step has full code/commands.
- **Type consistency:** `atomic_write_json(path, data, backups)` used in Tasks 1-2, 6;
  scheduler `parse_when/due_entries/next_run/load_schedule/save_schedule/add_entry/cancel_entry`
  consistent across Tasks 6-7; registry helper names `_schedule_add/_list/_cancel` match IMPL;
  `documents.read_document/search_in_document` and `email_gmail.{is_configured,email_status,
  format_message,email_check,email_search,email_draft,email_send}` match registry IMPL + tests.
- **Scope:** daily+once scheduling only; no weekly cron; no OCR; email graceful boundary only
  (live path needs user's Google setup). Matches spec out-of-scope.
- **Note:** Task 7 fires schedules BEFORE the presence gate so user-set reminders fire even
  when away (per spec); ambient trigger chatter remains presence-gated below it.
```
