# Friday Agency Layer — Design

**Date:** 2026-06-01
**Goal:** Give Friday real-world capability and live knowledge — web search/fetch,
file & clipboard & screenshot access, and app/system/shell control — as isolated,
permission-gated tools the brain can call, surfaced through the existing action-chip UI.

This is **subsystem 1 of 4** in the "make Friday match the movies" effort. The others
(cinematic HUD, boot/recognize-greet, smarter proactivity) get their own spec→plan→build
cycles after this. This spec covers the agency layer in full.

## Decisions locked (from brainstorming)

- **Web search:** keyless by default (DuckDuckGo HTML/lite + page fetch), auto-upgrade
  to an API (Brave/Tavily/SerpAPI) when a corresponding `*_API_KEY` is in the env.
- **System reach:** full — open/close apps, volume/media keys, shell, file read/search,
  file write, clipboard, screenshots, system info.
- **Permission posture:** allow-everything by default (user's call). BUT every category
  is editable to `ask`/`deny` in Settings, and a hard, always-on denylist refuses a few
  catastrophic shell patterns regardless of permission.

## Context (verified 2026-06-01)

- No `core/agency/` exists yet. Current tools (in `core/brain.py`) are task mgmt, HID
  (move/click/type), `open_app`, `run_script`, source read/write, run_tests, mood,
  skills, Legion. `core/bridge.py` already does HID, `run_script`, `get_system_vitals`,
  source read/write, all gated by `PermissionManager` (`config/permissions.json`).
- Tool-calling works on the Ollama path with validate/repair + synthesized ids; the
  approval flow (`PENDING_APPROVAL` → `[Approval: cat]` marker → `approval` event →
  toast) was just fixed and works.
- `pydantic`, `httpx`, `psutil`, `pyautogui`, `Pillow` available. `python3` + `PYTHONPATH=.`.
  pytest-asyncio does NOT load here — async tests use `asyncio.run()`.

## Architecture — `core/agency/` package

Each module owns one capability area, exposing (a) pure, testable helpers and (b)
tool functions. A registry assembles schemas + dispatch so the brain imports one thing.

### `core/agency/web.py`
- `web_search(query, max_results=5) -> list[{title, url, snippet}]`
- `fetch_page(url, max_chars=4000) -> str` (HTML stripped to readable text, truncated)
- Provider selection: `_select_provider()` returns an API provider if its key is in env
  (checks `BRAVE_API_KEY`, `TAVILY_API_KEY`, `SERPAPI_API_KEY`), else the keyless
  DuckDuckGo provider. Each provider implements the same `search()` interface.
- Pure/testable: HTML→text cleaning, DuckDuckGo result parsing, provider selection.
  Network calls (httpx) are the only impure part and are mocked in tests.

### `core/agency/files.py`
- `search_files(root, pattern, max_results=50)`, `read_file(path, max_chars=8000)`,
  `list_dir(path)`, `clipboard_get()`, `clipboard_set(text)`, `screenshot() -> path`.
- Pure/testable: path-safety (block escaping a configurable root / sensitive paths),
  glob/filter logic, text truncation. Clipboard/screenshot wrap optional deps
  (`pyperclip`/`pyautogui`/`Pillow`); degrade gracefully if unavailable (headless).

### `core/agency/system.py`
- `open_app(name)`, `close_app(name)`, `set_volume(level)`, `media_key(key)`,
  `run_shell(cmd, timeout=30)`, `system_info()`.
- **Catastrophic-command denylist** (always refuses, even when `shell=allow`): patterns
  like `rm -rf /`, `rm -rf ~`, `:(){ :|:& };:` (fork bomb), `mkfs`, `dd of=/dev/`,
  `> /dev/sda`, shutdown/reboot of the host. `is_dangerous(cmd) -> bool` is pure/tested.
- Builds on `bridge.py` where it already does the job (reuse, don't duplicate).

### `core/agency/registry.py`
- `AGENCY_TOOLS`: list of tool schemas (same shape as `brain.py` tools:
  `{name, description, input_schema}`).
- `PERMISSION_MAP`: tool name → permission category.
- `async dispatch(name, args, bridge) -> result`: permission-gates via the bridge's
  `PermissionManager` (returning the existing `PENDING_APPROVAL: <cat>` sentinel when a
  category is `ask`, `"Permission denied: <cat>"` when `deny`), else calls the impl.
- One integration point: `brain.py` extends `self.tools` with `AGENCY_TOOLS` and routes
  unknown names in `execute_tool` through `registry.dispatch`.

## Permissions

Extend `config/permissions.json` defaults with: `web_access`, `file_read`, `file_write`,
`clipboard`, `screenshot`, `app_control`, `shell` — all `"allow"` by default (user's
choice). `PermissionManager` already merges unknown keys, so adding defaults is additive.
The Settings sidebar already renders every permission as an allow/ask/deny dropdown, so
new categories appear automatically. The shell denylist is independent of permissions and
cannot be disabled from the UI.

## Data flow (one agency call)

`model emits tool call → brain.execute_tool(name, args) → if name in agency registry →
registry.dispatch(name, args, bridge) → permission check → (PENDING_APPROVAL → approval
toast | denied | run impl) → result back to model`. The existing `[System: Executing X]`
notification drives the action chip (⚡ start → ✓ done / ✗ error) — no new transport.

## Error handling

- Network failure (web) → return a short error string the model can relay; never raises
  into the turn loop. Retry transient errors with the existing `retry_async` pattern.
- Missing optional dep (clipboard/screenshot on headless) → return a clear "unavailable"
  message, not a crash.
- Shell: denylist match → immediate refusal string; timeout → killed, returns partial +
  timeout note.
- Path-safety violation (files) → refusal string, no I/O.

## Testing (pure logic via pytest; no live network)

- `web`: HTML→text cleaning, DDG result parsing (fixture HTML), provider selection by env.
- `files`: path-safety (escape attempts blocked), glob/search filtering, truncation.
- `system`: `is_dangerous` denylist (positive + negative cases), volume/media arg building.
- `registry`: schema integrity (every tool has name/description/input_schema), dispatch
  routes to the right impl, permission gating returns the right sentinels.
- Live smoke (manual): one real `web_search`, one `read_file`, one safe `run_shell` ("echo hi").

## Out of scope (later subsystems / future)

Cinematic HUD result cards (subsystem 2 — agency just returns data; HUD renders it),
boot/recognition (3), proactivity upgrades (4). No comms/calendar in this layer
(separate, needs account setup). No GUI window-management beyond open/close.

## Success criteria

- Friday can answer a current-events question via `web_search`+`fetch_page`, read/search
  local files, manage clipboard, screenshot, control apps/volume, and run shell commands —
  all through tool calls, permission-gated, visible as action chips.
- Catastrophic shell commands are always refused.
- New pure logic is unit-tested; the app runs and a live web search + file read + shell
  command all work end-to-end.
