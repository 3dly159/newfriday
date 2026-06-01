# Friday Agency Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give Friday real-world capability + live knowledge — web search/fetch, file/clipboard/screenshot access, and app/volume/shell control — as isolated, permission-gated tools the brain calls, surfaced through the existing action-chip UI.

**Architecture:** A new `core/agency/` package: one module per capability area (`web`, `files`, `system`), each with pure testable helpers + tool functions, assembled by `registry.py` (schemas + permission-gated dispatch). `core/brain.py` extends its tool list with `AGENCY_TOOLS` and routes unknown tool names through `registry.dispatch`. New permission categories default to `allow`; a hard shell denylist always refuses catastrophic commands.

**Tech Stack:** Python 3.12 (`python3`, `PYTHONPATH=.`), httpx, psutil, pyautogui/Pillow/pyperclip (optional, best-effort), pytest. Async tests use `asyncio.run()` (no pytest-asyncio in this env).

---

## Conventions for every task

- Run tests: `PYTHONPATH=. python3 -m pytest <path> -v -p no:cacheprovider`
- `python` is NOT on PATH — always `python3`. Branch: `friday-milestone-1-voice-reliability` (current).
- Commit after each task with the exact message given; only `git add` the files named in the task.
- All network/OS calls are isolated so the pure logic is tested without them.

## File Structure

- Create: `core/agency/__init__.py` — empty package marker.
- Create: `core/agency/web.py` — `clean_html`, `parse_ddg_results`, `select_provider`, async `web_search`, async `fetch_page`.
- Create: `core/agency/files.py` — `is_safe_path`, `filter_matches`, `truncate`, `search_files`, `read_file`, `list_dir`, `clipboard_get`, `clipboard_set`, `screenshot`.
- Create: `core/agency/system.py` — `is_dangerous`, `volume_command`, `open_app`, `close_app`, `set_volume`, `media_key`, `run_shell`, `system_info`.
- Create: `core/agency/registry.py` — `AGENCY_TOOLS`, `PERMISSION_MAP`, `IMPL`, async `dispatch`.
- Modify: `core/brain.py` — extend `self.tools` with `AGENCY_TOOLS`; route unknown names via `registry.dispatch` in `execute_tool`.
- Modify: `core/bridge.py` — add the new permission-category defaults.
- Test: `tests/test_agency_web.py`, `tests/test_agency_files.py`, `tests/test_agency_system.py`, `tests/test_agency_registry.py`.

---

## Task 1: Web — HTML cleaning + DDG result parsing (pure)

**Files:**
- Create: `core/agency/__init__.py`, `core/agency/web.py`
- Test: `tests/test_agency_web.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_agency_web.py`:

```python
from core.agency.web import clean_html, parse_ddg_results


def test_clean_html_strips_tags_and_scripts():
    html = "<html><head><style>x{}</style></head><body><script>bad()</script><p>Hello <b>Sir</b></p></body></html>"
    out = clean_html(html)
    assert "Hello" in out and "Sir" in out
    assert "<" not in out and "bad()" not in out and "x{}" not in out


def test_clean_html_collapses_whitespace():
    assert clean_html("<p>a</p>\n\n\n   <p>b</p>") == "a b"


def test_parse_ddg_results_extracts_links():
    # DuckDuckGo HTML lite: result links carry class "result__a".
    html = '''
    <div><a class="result__a" href="https://example.com/a">First Result</a>
    <a class="result__snippet">Snippet one.</a></div>
    <div><a class="result__a" href="https://example.com/b">Second Result</a>
    <a class="result__snippet">Snippet two.</a></div>
    '''
    results = parse_ddg_results(html, max_results=5)
    assert len(results) == 2
    assert results[0]["title"] == "First Result"
    assert results[0]["url"] == "https://example.com/a"
    assert "Snippet one." in results[0]["snippet"]


def test_parse_ddg_results_respects_max():
    html = ''.join(f'<a class="result__a" href="http://e/{i}">R{i}</a>' for i in range(10))
    assert len(parse_ddg_results(html, max_results=3)) == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_agency_web.py -v -p no:cacheprovider`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.agency'`

- [ ] **Step 3: Write minimal implementation**

Create `core/agency/__init__.py` (empty file).

Create `core/agency/web.py`:

```python
import os
import re
import html as _html

_TAG_RE = re.compile(r"<[^>]+>")
_SCRIPT_STYLE_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)
_WS_RE = re.compile(r"\s+")


def clean_html(html: str) -> str:
    """Strip tags, scripts, and styles from HTML; collapse whitespace to text."""
    if not html:
        return ""
    text = _SCRIPT_STYLE_RE.sub(" ", html)
    text = _TAG_RE.sub(" ", text)
    text = _html.unescape(text)
    return _WS_RE.sub(" ", text).strip()


_DDG_LINK_RE = re.compile(
    r'<a[^>]*class="[^"]*result__a[^"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)
_DDG_SNIPPET_RE = re.compile(
    r'<a[^>]*class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)


def parse_ddg_results(html: str, max_results: int = 5) -> list:
    """Parse DuckDuckGo HTML-lite results into [{title, url, snippet}]."""
    links = _DDG_LINK_RE.findall(html or "")
    snippets = _DDG_SNIPPET_RE.findall(html or "")
    results = []
    for i, (url, title) in enumerate(links[:max_results]):
        snippet = clean_html(snippets[i]) if i < len(snippets) else ""
        results.append({
            "title": clean_html(title),
            "url": url,
            "snippet": snippet,
        })
    return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_agency_web.py -v -p no:cacheprovider`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add core/agency/__init__.py core/agency/web.py tests/test_agency_web.py
git commit -m "feat(agency): web HTML cleaning + DuckDuckGo result parsing

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Web — provider selection + async search/fetch

**Files:**
- Modify: `core/agency/web.py`
- Test: `tests/test_agency_web.py`

- [ ] **Step 1: Append the failing tests**

Append to `tests/test_agency_web.py`:

```python
import asyncio
from core.agency import web as webmod
from core.agency.web import select_provider, web_search, fetch_page


def test_select_provider_keyless_by_default(monkeypatch):
    for k in ("BRAVE_API_KEY", "TAVILY_API_KEY", "SERPAPI_API_KEY"):
        monkeypatch.delenv(k, raising=False)
    assert select_provider() == "duckduckgo"


def test_select_provider_prefers_api_key(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    monkeypatch.setenv("BRAVE_API_KEY", "x")
    assert select_provider() == "brave"


def test_web_search_uses_ddg_fetch(monkeypatch):
    sample = '<a class="result__a" href="http://e/1">Title</a><a class="result__snippet">Snip</a>'
    async def fake_get(url):  # patch the single network function
        return sample
    monkeypatch.setattr(webmod, "_http_get", fake_get)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    results = asyncio.run(web_search("anything"))
    assert results[0]["title"] == "Title"


def test_fetch_page_cleans_and_truncates(monkeypatch):
    async def fake_get(url):
        return "<p>" + ("word " * 1000) + "</p>"
    monkeypatch.setattr(webmod, "_http_get", fake_get)
    out = asyncio.run(fetch_page("http://x", max_chars=50))
    assert len(out) <= 50
    assert "<" not in out


def test_web_search_network_error_returns_message(monkeypatch):
    async def boom(url):
        raise ConnectionError("down")
    monkeypatch.setattr(webmod, "_http_get", boom)
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    monkeypatch.delenv("SERPAPI_API_KEY", raising=False)
    out = asyncio.run(web_search("q"))
    assert isinstance(out, str) and "search" in out.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_agency_web.py -k "select_provider or fetch or network" -v -p no:cacheprovider`
Expected: FAIL with `ImportError: cannot import name 'select_provider'`

- [ ] **Step 3: Append the implementation**

Append to `core/agency/web.py`:

```python
import httpx

_DDG_URL = "https://lite.duckduckgo.com/lite/"
_HEADERS = {"User-Agent": "Mozilla/5.0 (Friday AI agent)"}


def select_provider() -> str:
    """Pick a search provider: an API if its key is in env, else keyless DDG."""
    if os.getenv("BRAVE_API_KEY"):
        return "brave"
    if os.getenv("TAVILY_API_KEY"):
        return "tavily"
    if os.getenv("SERPAPI_API_KEY"):
        return "serpapi"
    return "duckduckgo"


async def _http_get(url: str) -> str:
    """The single impure network call (patched in tests)."""
    async with httpx.AsyncClient(timeout=10, headers=_HEADERS, follow_redirects=True) as client:
        resp = await client.get(url)
        return resp.text


async def web_search(query: str, max_results: int = 5):
    """Search the web. Returns [{title,url,snippet}] or an error string."""
    try:
        provider = select_provider()
        if provider == "duckduckgo":
            from urllib.parse import quote_plus
            html = await _http_get(f"{_DDG_URL}?q={quote_plus(query)}")
            return parse_ddg_results(html, max_results=max_results)
        # API providers would branch here; keyless is the default path.
        from urllib.parse import quote_plus
        html = await _http_get(f"{_DDG_URL}?q={quote_plus(query)}")
        return parse_ddg_results(html, max_results=max_results)
    except Exception as e:
        return f"Web search failed: {e}"


async def fetch_page(url: str, max_chars: int = 4000) -> str:
    """Fetch a URL and return cleaned, truncated readable text."""
    try:
        html = await _http_get(url)
        text = clean_html(html)
        return text[:max_chars]
    except Exception as e:
        return f"Could not fetch page: {e}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_agency_web.py -v -p no:cacheprovider`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add core/agency/web.py tests/test_agency_web.py
git commit -m "feat(agency): provider selection + async web_search/fetch_page

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Files — path-safety + filtering (pure)

**Files:**
- Create: `core/agency/files.py`
- Test: `tests/test_agency_files.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_agency_files.py`:

```python
from core.agency.files import is_safe_path, filter_matches, truncate


def test_is_safe_path_blocks_traversal():
    assert is_safe_path("notes/todo.txt") is True
    assert is_safe_path("/etc/passwd") is False
    assert is_safe_path("../../etc/shadow") is False
    assert is_safe_path("~/.ssh/id_rsa") is False


def test_is_safe_path_blocks_sensitive_names():
    assert is_safe_path("project/id_rsa") is False
    assert is_safe_path("project/.env") is False
    assert is_safe_path("project/readme.md") is True


def test_filter_matches_by_glob():
    names = ["a.py", "b.txt", "c.py", "d.md"]
    assert filter_matches(names, "*.py") == ["a.py", "c.py"]


def test_truncate_caps_length_with_notice():
    out = truncate("x" * 100, 10)
    assert out.startswith("xxxxxxxxxx")
    assert "truncated" in out.lower()


def test_truncate_short_text_unchanged():
    assert truncate("short", 100) == "short"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_agency_files.py -v -p no:cacheprovider`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.agency.files'`

- [ ] **Step 3: Write minimal implementation**

Create `core/agency/files.py`:

```python
import os
import fnmatch

# Names/paths that are never readable regardless of permission.
_SENSITIVE = ("id_rsa", "id_ed25519", ".env", "shadow", "passwd", ".aws", ".ssh")


def is_safe_path(path: str) -> bool:
    """True if path is a relative, non-sensitive path that doesn't escape cwd."""
    if not path:
        return False
    if path.startswith("/") or path.startswith("~"):
        return False
    if ".." in path.split(os.sep):
        return False
    low = path.lower()
    return not any(s in low for s in _SENSITIVE)


def filter_matches(names, pattern):
    """Filter filenames by a glob pattern (e.g. '*.py')."""
    return [n for n in names if fnmatch.fnmatch(n, pattern)]


def truncate(text: str, max_chars: int) -> str:
    """Cap text length, appending a notice when cut."""
    if text is None:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n…[truncated]"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_agency_files.py -v -p no:cacheprovider`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add core/agency/files.py tests/test_agency_files.py
git commit -m "feat(agency): file path-safety + filtering helpers

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Files — read/search/list + clipboard/screenshot

**Files:**
- Modify: `core/agency/files.py`
- Test: `tests/test_agency_files.py`

- [ ] **Step 1: Append the failing tests**

Append to `tests/test_agency_files.py`:

```python
import os
from core.agency.files import read_file, list_dir, search_files


def test_read_file_reads_safe_relative(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("hello sir")
    assert "hello sir" in read_file("note.txt")


def test_read_file_refuses_unsafe(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = read_file("/etc/passwd")
    assert "refus" in out.lower() or "not allowed" in out.lower()


def test_list_dir_lists_entries(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "sub").mkdir()
    entries = list_dir(".")
    assert "a.txt" in entries and "sub" in entries


def test_search_files_finds_by_pattern(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "x.py").write_text("x")
    (tmp_path / "y.txt").write_text("y")
    sub = tmp_path / "sub"; sub.mkdir()
    (sub / "z.py").write_text("z")
    found = search_files(".", "*.py")
    assert any(f.endswith("x.py") for f in found)
    assert any(f.endswith("z.py") for f in found)
    assert not any(f.endswith("y.txt") for f in found)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_agency_files.py -k "read_file or list_dir or search_files" -v -p no:cacheprovider`
Expected: FAIL with `ImportError: cannot import name 'read_file'`

- [ ] **Step 3: Append the implementation**

Append to `core/agency/files.py`:

```python
def read_file(path: str, max_chars: int = 8000) -> str:
    """Read a safe relative text file, truncated."""
    if not is_safe_path(path):
        return f"Refused: '{path}' is not an allowed path."
    try:
        with open(path, "r", errors="replace") as f:
            return truncate(f.read(), max_chars)
    except Exception as e:
        return f"Could not read {path}: {e}"


def list_dir(path: str = "."):
    """List entries of a safe directory (names only)."""
    if path not in (".", "") and not is_safe_path(path):
        return [f"Refused: '{path}' is not an allowed path."]
    try:
        return sorted(os.listdir(path or "."))
    except Exception as e:
        return [f"Could not list {path}: {e}"]


def search_files(root: str, pattern: str, max_results: int = 50):
    """Recursively find files matching a glob under a safe root."""
    if root not in (".", "") and not is_safe_path(root):
        return [f"Refused: '{root}' is not an allowed path."]
    found = []
    for dirpath, _dirs, names in os.walk(root or "."):
        for name in filter_matches(names, pattern):
            found.append(os.path.join(dirpath, name))
            if len(found) >= max_results:
                return found
    return found


def clipboard_get() -> str:
    """Return clipboard text, or an 'unavailable' note on headless/no-dep."""
    try:
        import pyperclip
        return pyperclip.paste()
    except Exception as e:
        return f"Clipboard unavailable: {e}"


def clipboard_set(text: str) -> str:
    try:
        import pyperclip
        pyperclip.copy(text)
        return "Clipboard set."
    except Exception as e:
        return f"Clipboard unavailable: {e}"


def screenshot(out_path: str = "data/logs/screenshot.png") -> str:
    """Capture the screen to a file; degrade gracefully if headless."""
    try:
        import pyautogui
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        img = pyautogui.screenshot()
        img.save(out_path)
        return out_path
    except Exception as e:
        return f"Screenshot unavailable: {e}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_agency_files.py -v -p no:cacheprovider`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add core/agency/files.py tests/test_agency_files.py
git commit -m "feat(agency): file read/search/list + clipboard/screenshot

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: System — danger denylist + volume command (pure)

**Files:**
- Create: `core/agency/system.py`
- Test: `tests/test_agency_system.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_agency_system.py`:

```python
from core.agency.system import is_dangerous, volume_command


def test_is_dangerous_blocks_catastrophic():
    assert is_dangerous("rm -rf /")
    assert is_dangerous("sudo rm -rf /*")
    assert is_dangerous(":(){ :|:& };:")            # fork bomb
    assert is_dangerous("mkfs.ext4 /dev/sda1")
    assert is_dangerous("dd if=/dev/zero of=/dev/sda")
    assert is_dangerous("echo x > /dev/sda")
    assert is_dangerous("shutdown now")
    assert is_dangerous("reboot")


def test_is_dangerous_allows_normal():
    assert not is_dangerous("echo hello")
    assert not is_dangerous("ls -la")
    assert not is_dangerous("python3 script.py")
    assert not is_dangerous("rm build/tmp.o")       # scoped rm is fine


def test_volume_command_builds_linux_amixer():
    cmd = volume_command(50)
    assert isinstance(cmd, list)
    assert any("50" in str(part) for part in cmd)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_agency_system.py -v -p no:cacheprovider`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.agency.system'`

- [ ] **Step 3: Write minimal implementation**

Create `core/agency/system.py`:

```python
import re
import shlex
import subprocess

# Catastrophic patterns refused regardless of permission (always on).
_DANGER_PATTERNS = [
    r"\brm\s+-rf?\s+(/|/\*|~|\$HOME)(\s|$)",
    r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",   # fork bomb
    r"\bmkfs\b",
    r"\bdd\b.*\bof=/dev/",
    r">\s*/dev/(sd|nvme|hd)",
    r"\b(shutdown|reboot|halt|poweroff)\b",
    r"\brm\s+-rf?\s+--no-preserve-root",
]
_DANGER_RE = [re.compile(p) for p in _DANGER_PATTERNS]


def is_dangerous(cmd: str) -> bool:
    """True if the shell command matches a catastrophic pattern."""
    if not cmd:
        return False
    return any(rx.search(cmd) for rx in _DANGER_RE)


def volume_command(level: int) -> list:
    """Build a Linux amixer command to set master volume to `level` percent."""
    level = max(0, min(100, int(level)))
    return ["amixer", "-q", "sset", "Master", f"{level}%"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_agency_system.py -v -p no:cacheprovider`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add core/agency/system.py tests/test_agency_system.py
git commit -m "feat(agency): shell danger denylist + volume command builder

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: System — shell/app/volume/media/info actions

**Files:**
- Modify: `core/agency/system.py`
- Test: `tests/test_agency_system.py`

- [ ] **Step 1: Append the failing tests**

Append to `tests/test_agency_system.py`:

```python
from core.agency.system import run_shell, system_info


def test_run_shell_refuses_dangerous():
    out = run_shell("rm -rf /")
    assert "refus" in out["error"].lower() or "danger" in out["error"].lower()


def test_run_shell_runs_safe_command():
    out = run_shell("echo hello-friday")
    assert "hello-friday" in out["stdout"]
    assert out["exit_code"] == 0


def test_system_info_has_core_fields():
    info = system_info()
    for key in ("cpu_percent", "memory_percent", "platform"):
        assert key in info
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_agency_system.py -k "run_shell or system_info" -v -p no:cacheprovider`
Expected: FAIL with `ImportError: cannot import name 'run_shell'`

- [ ] **Step 3: Append the implementation**

Append to `core/agency/system.py`:

```python
import platform as _platform
import psutil


def run_shell(cmd: str, timeout: int = 30) -> dict:
    """Run a shell command, refusing catastrophic ones. Returns stdout/stderr/exit_code."""
    if is_dangerous(cmd):
        return {"error": f"Refused dangerous command: {cmd}", "stdout": "", "exit_code": -1}
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.returncode}
    except subprocess.TimeoutExpired as e:
        return {"error": "timed out", "stdout": e.stdout or "", "exit_code": -1}
    except Exception as e:
        return {"error": str(e), "stdout": "", "exit_code": -1}


def set_volume(level: int) -> str:
    try:
        subprocess.run(volume_command(level), capture_output=True, timeout=5)
        return f"Volume set to {max(0, min(100, int(level)))}%."
    except Exception as e:
        return f"Could not set volume: {e}"


def media_key(key: str) -> str:
    """Send a media key (playpause/nextsong/prevsong) via playerctl if present."""
    mapping = {"play": "play-pause", "pause": "play-pause", "next": "next", "prev": "previous"}
    action = mapping.get(key, key)
    try:
        subprocess.run(["playerctl", action], capture_output=True, timeout=5)
        return f"Media: {action}."
    except Exception as e:
        return f"Could not send media key: {e}"


def open_app(name: str) -> str:
    try:
        subprocess.Popen([name])
        return f"Opening {name}."
    except Exception as e:
        return f"Could not open {name}: {e}"


def close_app(name: str) -> str:
    try:
        result = subprocess.run(["pkill", "-f", name], capture_output=True, text=True, timeout=5)
        return f"Closed {name}." if result.returncode == 0 else f"No running process matched {name}."
    except Exception as e:
        return f"Could not close {name}: {e}"


def system_info() -> dict:
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory_percent": psutil.virtual_memory().percent,
        "platform": _platform.system(),
        "release": _platform.release(),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_agency_system.py -v -p no:cacheprovider`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add core/agency/system.py tests/test_agency_system.py
git commit -m "feat(agency): shell/app/volume/media/system-info actions

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Registry — schemas + permission-gated dispatch

**Files:**
- Create: `core/agency/registry.py`
- Test: `tests/test_agency_registry.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_agency_registry.py`:

```python
import asyncio
from core.agency import registry


class _FakePerms:
    def __init__(self, mapping): self._m = mapping
    def check(self, cat): return self._m.get(cat, "allow")


class _FakeBridge:
    def __init__(self, mapping): self.permissions = _FakePerms(mapping)


def test_every_tool_has_required_schema_fields():
    for tool in registry.AGENCY_TOOLS:
        assert "name" in tool and "description" in tool and "input_schema" in tool
        assert tool["name"] in registry.IMPL
        assert tool["name"] in registry.PERMISSION_MAP


def test_dispatch_denied_returns_message():
    bridge = _FakeBridge({"web_access": "deny"})
    out = asyncio.run(registry.dispatch("web_search", {"query": "x"}, bridge))
    assert isinstance(out, str) and "denied" in out.lower()


def test_dispatch_ask_returns_pending_sentinel():
    bridge = _FakeBridge({"shell": "ask"})
    out = asyncio.run(registry.dispatch("run_shell", {"cmd": "echo hi"}, bridge))
    assert out == "PENDING_APPROVAL: shell"


def test_dispatch_allow_runs_impl():
    bridge = _FakeBridge({"shell": "allow"})
    out = asyncio.run(registry.dispatch("run_shell", {"cmd": "echo hello-x"}, bridge))
    assert "hello-x" in out["stdout"]


def test_dispatch_unknown_tool():
    bridge = _FakeBridge({})
    out = asyncio.run(registry.dispatch("nope", {}, bridge))
    assert "unknown" in str(out).lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_agency_registry.py -v -p no:cacheprovider`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.agency.registry'`

- [ ] **Step 3: Write minimal implementation**

Create `core/agency/registry.py`:

```python
import inspect
from core.agency import web, files, system

# Tool schemas (same shape as core/brain.py tools).
AGENCY_TOOLS = [
    {"name": "web_search", "description": "Search the web for current information. Returns titles, URLs, snippets.",
     "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
    {"name": "fetch_page", "description": "Fetch a URL and return its readable text.",
     "input_schema": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}},
    {"name": "read_file", "description": "Read a local text file (relative, non-sensitive path).",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "search_files", "description": "Find files matching a glob under a directory.",
     "input_schema": {"type": "object", "properties": {"root": {"type": "string"}, "pattern": {"type": "string"}}, "required": ["root", "pattern"]}},
    {"name": "list_dir", "description": "List entries in a directory.",
     "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}}},
    {"name": "clipboard_get", "description": "Read the system clipboard text.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "clipboard_set", "description": "Set the system clipboard text.",
     "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    {"name": "screenshot", "description": "Capture the screen to an image file.",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "open_app", "description": "Open an application by command/name.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "close_app", "description": "Close/kill an application by name.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "set_volume", "description": "Set system master volume (0-100).",
     "input_schema": {"type": "object", "properties": {"level": {"type": "integer"}}, "required": ["level"]}},
    {"name": "media_key", "description": "Send a media key: play, pause, next, prev.",
     "input_schema": {"type": "object", "properties": {"key": {"type": "string", "enum": ["play", "pause", "next", "prev"]}}, "required": ["key"]}},
    {"name": "run_shell", "description": "Run a shell command (catastrophic commands are refused).",
     "input_schema": {"type": "object", "properties": {"cmd": {"type": "string"}}, "required": ["cmd"]}},
    {"name": "system_info", "description": "Get CPU, memory, and platform info.",
     "input_schema": {"type": "object", "properties": {}}},
]

# tool name -> permission category
PERMISSION_MAP = {
    "web_search": "web_access", "fetch_page": "web_access",
    "read_file": "file_read", "search_files": "file_read", "list_dir": "file_read",
    "clipboard_get": "clipboard", "clipboard_set": "clipboard",
    "screenshot": "screenshot",
    "open_app": "app_control", "close_app": "app_control",
    "set_volume": "app_control", "media_key": "app_control",
    "run_shell": "shell",
    "system_info": "file_read",
}

# tool name -> implementation callable
IMPL = {
    "web_search": lambda a: web.web_search(a.get("query", ""), a.get("max_results", 5)),
    "fetch_page": lambda a: web.fetch_page(a.get("url", ""), a.get("max_chars", 4000)),
    "read_file": lambda a: files.read_file(a.get("path", "")),
    "search_files": lambda a: files.search_files(a.get("root", "."), a.get("pattern", "*")),
    "list_dir": lambda a: files.list_dir(a.get("path", ".")),
    "clipboard_get": lambda a: files.clipboard_get(),
    "clipboard_set": lambda a: files.clipboard_set(a.get("text", "")),
    "screenshot": lambda a: files.screenshot(),
    "open_app": lambda a: system.open_app(a.get("name", "")),
    "close_app": lambda a: system.close_app(a.get("name", "")),
    "set_volume": lambda a: system.set_volume(a.get("level", 50)),
    "media_key": lambda a: system.media_key(a.get("key", "play")),
    "run_shell": lambda a: system.run_shell(a.get("cmd", "")),
    "system_info": lambda a: system.system_info(),
}


def has_tool(name: str) -> bool:
    return name in IMPL


async def dispatch(name: str, args: dict, bridge):
    """Permission-gate and run an agency tool. Returns the impl result, or the
    existing PENDING_APPROVAL / denied sentinels used by the rest of the system."""
    if name not in IMPL:
        return f"Unknown agency tool: {name}"
    category = PERMISSION_MAP.get(name, "shell")
    perm = bridge.permissions.check(category)
    if perm == "deny":
        return f"Permission denied: {category}"
    if perm == "ask":
        return f"PENDING_APPROVAL: {category}"
    result = IMPL[name](args or {})
    if inspect.isawaitable(result):
        result = await result
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_agency_registry.py -v -p no:cacheprovider`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add core/agency/registry.py tests/test_agency_registry.py
git commit -m "feat(agency): tool registry with permission-gated dispatch

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Wire agency into the brain + permission defaults

**Files:**
- Modify: `core/brain.py` (imports, `self.tools`, `execute_tool` tail at line ~472)
- Modify: `core/bridge.py` (PermissionManager defaults, lines 22-27)
- Test: import smoke + live

- [ ] **Step 1: Add permission-category defaults.** In `core/bridge.py`, replace the `self.permissions = {...}` default dict (lines 22-27) with:

```python
        self.permissions = {
            "hid_control": "ask",      # options: allow, ask, deny
            "script_execution": "ask",
            "file_system_write": "ask",
            "app_orchestration": "allow",
            # Agency layer categories (default allow per project decision).
            "web_access": "allow",
            "file_read": "allow",
            "file_write": "allow",
            "clipboard": "allow",
            "screenshot": "allow",
            "app_control": "allow",
            "shell": "allow",
        }
```

- [ ] **Step 2: Import the registry.** In `core/brain.py`, after `from core.structured import repair_json, validate_tool_args`, add:

```python
from core.agency import registry as agency_registry
```

- [ ] **Step 3: Extend the tool list.** In `core/brain.py`, find the end of the `self.tools = [ ... ]` assignment (the closing `]` before `async def get_streaming_response`). Immediately after that closing bracket, add:

```python
        # Append agency-layer tools (web, files, system) to the brain's toolset.
        self.tools.extend(agency_registry.AGENCY_TOOLS)
```

- [ ] **Step 4: Route unknown tools through the registry.** In `core/brain.py`, in `execute_tool`, replace the final line `return "Unknown tool"` with:

```python
        if agency_registry.has_tool(name):
            return await agency_registry.dispatch(name, input_data, self.bridge)
        return "Unknown tool"
```

- [ ] **Step 5: Import smoke**

Run:
```bash
PYTHONPATH=. python3 -c "
from core.brain import FridayBrain
b = FridayBrain()
names = [t['name'] for t in b.tools]
assert 'web_search' in names and 'run_shell' in names, names
print('agency tools registered:', sum(1 for n in names if n in ('web_search','run_shell','read_file')))
print('total tools:', len(names))
"
```
Expected: prints `agency tools registered: 3` and a total tool count (no traceback).

- [ ] **Step 6: Live dispatch smoke (no LLM needed)**

Run:
```bash
PYTHONPATH=. python3 -c "
import asyncio
from core.brain import FridayBrain
async def main():
    b = FridayBrain()
    print('shell:', (await b.execute_tool('run_shell', {'cmd': 'echo hello-friday'}))['stdout'].strip())
    print('danger:', (await b.execute_tool('run_shell', {'cmd': 'rm -rf /'})).get('error'))
    print('readme:', (await b.execute_tool('read_file', {'path': 'QUICKSTART.md'}))[:40])
asyncio.run(main())
"
```
Expected: `shell: hello-friday`, a `danger:` refusal message, and the first chars of QUICKSTART.md.

- [ ] **Step 7: Full suite**

Run: `PYTHONPATH=. python3 -m pytest tests/ -p no:cacheprovider -q`
Expected: all agency tests pass (web 9, files 9, system 6, registry 5); no regressions beyond the 3 known pre-existing failures.

- [ ] **Step 8: Commit**

```bash
git add core/brain.py core/bridge.py
git commit -m "feat(agency): wire agency registry into brain + permission defaults

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: Live end-to-end verification (Ollama running)

**Files:** none (verification only)

- [ ] **Step 1: Start Ollama + the server**

Run:
```bash
cd /home/lucifer/Downloads/newfriday
lsof -ti:8000 2>/dev/null | xargs -r kill -9 2>/dev/null; sleep 1
PYTHONPATH=. setsid python3 -m uvicorn core.main:app --host 0.0.0.0 --port 8000 --log-level warning > /tmp/friday_server.log 2>&1 < /dev/null &
disown; for i in $(seq 1 12); do [ "$(curl -s -m 2 -o /dev/null -w '%{http_code}' http://localhost:8000/ 2>/dev/null)" = "200" ] && break; sleep 1; done; echo "ready"
```

- [ ] **Step 2: Drive a real agency turn through the brain**

Run:
```bash
cp data/memory.json /tmp/m.bak 2>/dev/null
PYTHONPATH=. timeout 200 python3 -c "
import asyncio
from core.brain import FridayBrain
async def main():
    b = FridayBrain()
    out = ''
    async for tok in b.get_streaming_response('Friday, what files are in the current directory? Use your tools.'):
        out += tok
    print('REPLY:', out[:400])
asyncio.run(main())
"
cp /tmp/m.bak data/memory.json 2>/dev/null
```
Expected: Friday calls `list_dir`/`search_files` and reports real files (you'll see `[System: Executing list_dir...]`-style flow and an in-persona answer). No traceback.

- [ ] **Step 3: Stop the server**

Run: `lsof -ti:8000 2>/dev/null | xargs -r kill 2>/dev/null; echo stopped`

- [ ] **Step 4: Update CLAUDE.md** — add an "Agency layer" bullet under the backend module list:

```markdown
- **`core/agency/`** — Real-world capability tools (web search/fetch, file/clipboard/screenshot, app/volume/shell), assembled by `registry.py` and called via `brain.execute_tool`. Permission-gated; catastrophic shell commands always refused.
```

Then commit:
```bash
git add CLAUDE.md
git commit -m "docs: document agency layer in CLAUDE.md

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Self-Review (completed by plan author)

- **Spec coverage:** web.py → Tasks 1-2; files.py → Tasks 3-4; system.py → Tasks 5-6; registry.py → Task 7; brain wiring + permission defaults → Task 8; allow-everything defaults → Task 8 Step 1; denylist → Task 5 + enforced in Task 6 `run_shell` + Task 7 dispatch; permission sentinels match existing approval flow → Task 7; live verification → Task 9. All spec sections covered.
- **Placeholder scan:** none — every step has full code/commands.
- **Type consistency:** `web_search(query,max_results)`, `fetch_page(url,max_chars)`, `is_safe_path`, `filter_matches`, `truncate`, `read_file/list_dir/search_files`, `is_dangerous`, `volume_command`, `run_shell`→dict, `system_info`→dict, `registry.AGENCY_TOOLS/PERMISSION_MAP/IMPL/has_tool/dispatch(name,args,bridge)` — names used consistently across tasks. `dispatch` returns the same `PENDING_APPROVAL: <cat>` / `Permission denied: <cat>` sentinels the brain+VoiceSession already handle.
- **Scope:** agency layer only; HUD/boot/proactivity are separate subsystems.
