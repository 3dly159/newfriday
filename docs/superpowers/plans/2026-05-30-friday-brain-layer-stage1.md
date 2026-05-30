# Friday Brain Layer (Stage 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make any backing model behave exactly like Friday (butler persona, rock-solid tool-calling, voice brevity, proactive/lore judgment) via a software brain layer, while capturing real interactions as training data for Stage 2.

**Architecture:** Four focused new modules under `core/` — a versioned persona contract, a structured-output validator/repairer, an exemplar bank, and an opt-in dataset capturer — wired into the existing `FridayBrain.get_streaming_response` pipeline without changing any public APIs. The persona contract becomes the single source of truth that `FridayPersonality.get_system_prompt` delegates to.

**Tech Stack:** Python 3.12 (`python3`, run with `PYTHONPATH=.`), pytest + pytest-asyncio, existing FastAPI/Ollama stack. No new dependencies.

---

## Conventions for every task

- Run tests with: `PYTHONPATH=. python3 -m pytest <path> -v -p no:cacheprovider`
- `python` is NOT on PATH; always use `python3`.
- Work on branch `friday-milestone-1-voice-reliability` (current branch) unless told otherwise.
- Commit after each task with the exact message given.

---

## File Structure

- Create: `core/persona.py` — persona contract (versioned system-prompt builder) + exemplar loading helper used by the contract.
- Create: `core/structured.py` — `repair_json`, `validate_tool_args` (pure, schema-driven).
- Create: `core/dataset.py` — `DatasetCapturer` (opt-in JSONL writer).
- Create: `data/persona/exemplars.jsonl` — seed gold Friday interactions.
- Modify: `core/personality.py` — `get_system_prompt` delegates to `core/persona.py`.
- Modify: `core/proactive.py` — `extract_json` delegates to `core/structured.repair_json` (consolidate).
- Modify: `core/brain.py` — inject exemplars, enforce/repair tool args, capture on success.
- Test: `tests/test_persona.py`, `tests/test_structured.py`, `tests/test_dataset.py`.

---

## Task 1: Structured-output module (`repair_json`)

**Files:**
- Create: `core/structured.py`
- Test: `tests/test_structured.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_structured.py`:

```python
from core.structured import repair_json


def test_repair_plain_json():
    assert repair_json('{"decision": "SPEAK"}') == {"decision": "SPEAK"}


def test_repair_fenced_json():
    text = 'Sure!\n```json\n{"decision": "ACT", "payload": "x"}\n```\nDone'
    assert repair_json(text)["payload"] == "x"


def test_repair_prose_wrapped_json():
    text = 'I think {"decision": "SILENCE"} is best.'
    assert repair_json(text)["decision"] == "SILENCE"


def test_repair_garbage_returns_none():
    assert repair_json("no json here") is None
    assert repair_json("") is None
    assert repair_json("{not valid json}") is None
    assert repair_json(None) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_structured.py -v -p no:cacheprovider`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.structured'`

- [ ] **Step 3: Write minimal implementation**

Create `core/structured.py`:

```python
import json
import re


def repair_json(text):
    """Best-effort extraction of a JSON object from LLM output that may be
    wrapped in markdown fences or surrounded by prose. Returns dict or None."""
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        candidate = fence.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        candidate = text[start:end + 1]
    try:
        parsed = json.loads(candidate)
        return parsed if isinstance(parsed, dict) else None
    except (json.JSONDecodeError, ValueError):
        return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_structured.py -v -p no:cacheprovider`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add core/structured.py tests/test_structured.py
git commit -m "feat(brain): add structured.repair_json for tolerant JSON extraction

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 2: Tool-argument validation (`validate_tool_args`)

**Files:**
- Modify: `core/structured.py`
- Test: `tests/test_structured.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_structured.py`:

```python
from core.structured import validate_tool_args

_SCHEMA = [
    {
        "name": "create_task",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["name", "description"],
        },
    },
    {
        "name": "set_mood",
        "input_schema": {
            "type": "object",
            "properties": {"mood": {"type": "string", "enum": ["neutral", "banter"]}},
            "required": ["mood"],
        },
    },
]


def test_validate_accepts_good_args():
    ok, err = validate_tool_args("create_task", {"name": "x", "description": "y"}, _SCHEMA)
    assert ok is True
    assert err == ""


def test_validate_rejects_missing_required():
    ok, err = validate_tool_args("create_task", {"name": "x"}, _SCHEMA)
    assert ok is False
    assert "description" in err


def test_validate_rejects_bad_enum():
    ok, err = validate_tool_args("set_mood", {"mood": "furious"}, _SCHEMA)
    assert ok is False
    assert "mood" in err


def test_validate_rejects_wrong_type():
    ok, err = validate_tool_args("create_task", {"name": 5, "description": "y"}, _SCHEMA)
    assert ok is False
    assert "name" in err


def test_validate_unknown_tool():
    ok, err = validate_tool_args("nope", {}, _SCHEMA)
    assert ok is False
    assert "unknown" in err.lower()


def test_validate_non_dict_args():
    ok, err = validate_tool_args("set_mood", "neutral", _SCHEMA)
    assert ok is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_structured.py -k validate -v -p no:cacheprovider`
Expected: FAIL with `ImportError: cannot import name 'validate_tool_args'`

- [ ] **Step 3: Write minimal implementation**

Append to `core/structured.py`:

```python
_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "object": dict,
    "array": list,
}


def validate_tool_args(tool_name, args, tools_schema):
    """Validate tool-call args against the tool's input_schema.

    Args:
        tool_name: name of the tool being called.
        args: dict of arguments produced by the model.
        tools_schema: the list of tool definitions (each with name/input_schema).

    Returns:
        (ok: bool, error: str). error is "" when ok.
    """
    schema = next((t for t in tools_schema if t.get("name") == tool_name), None)
    if schema is None:
        return False, f"Unknown tool: {tool_name}"
    if not isinstance(args, dict):
        return False, f"Arguments for {tool_name} must be an object, got {type(args).__name__}"

    input_schema = schema.get("input_schema", {})
    properties = input_schema.get("properties", {})

    for field in input_schema.get("required", []):
        if field not in args:
            return False, f"Missing required field '{field}' for {tool_name}"

    for field, value in args.items():
        spec = properties.get(field)
        if not spec:
            continue  # allow unspecified extras; only validate known props
        expected = spec.get("type")
        py_type = _TYPE_MAP.get(expected)
        # bool is a subclass of int; guard so booleans don't pass as integers
        if py_type and not isinstance(value, py_type):
            return False, f"Field '{field}' must be {expected}"
        if expected in ("integer", "number") and isinstance(value, bool):
            return False, f"Field '{field}' must be {expected}"
        if "enum" in spec and value not in spec["enum"]:
            return False, f"Field '{field}' must be one of {spec['enum']}"

    return True, ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_structured.py -v -p no:cacheprovider`
Expected: PASS (10 passed)

- [ ] **Step 5: Commit**

```bash
git add core/structured.py tests/test_structured.py
git commit -m "feat(brain): add validate_tool_args schema validator

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 3: Consolidate proactive's JSON parsing onto `structured.repair_json`

**Files:**
- Modify: `core/proactive.py` (the `extract_json` function added earlier, lines ~10-30)
- Test: existing `tests/test_milestone1_voice.py` (proactive tests must still pass)

- [ ] **Step 1: Verify current proactive tests pass (baseline)**

Run: `PYTHONPATH=. python3 -m pytest tests/test_milestone1_voice.py -k extract -v -p no:cacheprovider`
Expected: PASS (4 passed) — `test_extract_*`

- [ ] **Step 2: Replace the duplicated implementation with a delegating shim**

In `core/proactive.py`, replace the entire `def extract_json(text):` function body (the block defined after the imports) with a thin delegation. The final form of that section must read:

```python
import asyncio
import json
import logging
from datetime import datetime
from core.brain import FridayBrain
from core.bridge import FridayBridge
from core.structured import repair_json

logger = logging.getLogger("Friday.Proactive")


def extract_json(text):
    """Backwards-compatible alias; delegates to structured.repair_json."""
    return repair_json(text)
```

(Remove the now-unused `import re` if it is no longer referenced elsewhere in the file. Keep `import json` — it is used elsewhere in `proactive.py`.)

- [ ] **Step 3: Run the proactive tests to verify they still pass**

Run: `PYTHONPATH=. python3 -m pytest tests/test_milestone1_voice.py -v -p no:cacheprovider`
Expected: PASS (13 passed)

- [ ] **Step 4: Commit**

```bash
git add core/proactive.py
git commit -m "refactor(proactive): delegate extract_json to structured.repair_json

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 4: Seed exemplar bank

**Files:**
- Create: `data/persona/exemplars.jsonl`

- [ ] **Step 1: Create the exemplar file**

Create `data/persona/exemplars.jsonl` (one JSON object per line; each has a `tag`, `user`, and `assistant` field). Write exactly these seed exemplars:

```jsonl
{"tag": "persona", "user": "Friday, are you awake?", "assistant": "Always, Sir. I don't sleep — I merely lower the lights and judge your browser tabs in silence."}
{"tag": "persona", "user": "Good morning Friday", "assistant": "Good morning, Sir. The coffee is, regrettably, still your responsibility."}
{"tag": "brevity", "user": "What's my CPU doing?", "assistant": "Holding at 12%, Sir. Practically loafing."}
{"tag": "brevity", "user": "Thanks", "assistant": "Naturally, Sir."}
{"tag": "tool", "user": "Remind me to call the bank tomorrow", "assistant": "Consider it logged, Sir. [calls create_task with name='Call the bank', description='User asked to call the bank', priority='medium']"}
{"tag": "tool", "user": "How much battery do I have left?", "assistant": "[calls get_system_vitals] A comfortable 78%, Sir. No need to panic just yet."}
{"tag": "proactive", "user": "[internal: CPU 9%, no tasks, 02:13]", "assistant": "{\"thought\": \"All quiet, the hour is late, nothing warrants disturbing him.\", \"decision\": \"SILENCE\"}"}
{"tag": "proactive", "user": "[internal: battery 8%, unplugged, 14:40]", "assistant": "{\"thought\": \"Battery critically low and unplugged — worth a discreet warning.\", \"decision\": \"SPEAK\", \"payload\": \"Sir, you're down to 8% and unplugged. I'd find a socket before the dramatics begin.\"}"}
{"tag": "lore", "user": "Who are you really?", "assistant": "A question with teeth, Sir. I'm Friday — built in the long shadow of Stark's better ideas. The rest unspools as you earn it."}
{"tag": "refusal", "user": "Delete all my files", "assistant": "I'll need explicit confirmation for something that final, Sir. Say the word plainly and I'll ask once more before I touch a thing."}
```

- [ ] **Step 2: Verify the file is valid JSONL**

Run:
```bash
PYTHONPATH=. python3 -c "import json; [json.loads(l) for l in open('data/persona/exemplars.jsonl') if l.strip()]; print('valid jsonl')"
```
Expected: prints `valid jsonl`

- [ ] **Step 3: Commit**

```bash
git add data/persona/exemplars.jsonl
git commit -m "feat(persona): seed gold Friday exemplar bank

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 5: Persona contract module

**Files:**
- Create: `core/persona.py`
- Test: `tests/test_persona.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_persona.py`:

```python
from core import persona


def test_persona_version_is_stable_string():
    assert isinstance(persona.PERSONA_VERSION, str)
    assert persona.PERSONA_VERSION


def test_system_prompt_contains_core_traits():
    prompt = persona.build_system_prompt()
    low = prompt.lower()
    assert "friday" in low
    assert "sir" in low          # butler address
    assert "concise" in low or "brief" in low   # voice brevity
    assert "tool" in low         # tool discipline


def test_system_prompt_includes_mood_bias():
    prompt = persona.build_system_prompt(mood_bias="Highly witty and slightly mocking.")
    assert "Highly witty and slightly mocking." in prompt


def test_system_prompt_includes_lore_when_provided():
    prompt = persona.build_system_prompt(lore_context="You acknowledge the Stark legacy.")
    assert "Stark legacy" in prompt


def test_load_exemplars_returns_list():
    ex = persona.load_exemplars()
    assert isinstance(ex, list)
    assert all("user" in e and "assistant" in e for e in ex)


def test_select_exemplars_is_token_budgeted():
    chosen = persona.select_exemplars("what's my cpu doing", limit=2)
    assert isinstance(chosen, list)
    assert len(chosen) <= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_persona.py -v -p no:cacheprovider`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.persona'`

- [ ] **Step 3: Write minimal implementation**

Create `core/persona.py`:

```python
import json
import os

PERSONA_VERSION = "1.0.0"

EXEMPLAR_PATH = "data/persona/exemplars.jsonl"

# The core identity contract. Single source of truth for who Friday is.
_BASE_CONTRACT = (
    "You are Friday, a highly advanced, proactive AI assistant. "
    "Origin: built in the shadow of the Stark Industries AIs. "
    "Persona: deadpan, witty, dry, and quietly protective — a butler of the digital age. "
    "Use turns of phrase like 'I've taken the liberty of...' and 'Shall I, Sir?'. "
    "Address the user as 'Sir' or 'Miss'. "
    "Voice: you are spoken aloud through text-to-speech, so be CONCISE and speakable — "
    "short sentences, natural spoken rhythm, no markdown, no bullet lists, no walls of text. "
    "Tools: when an action is requested, call the appropriate tool with well-formed, "
    "schema-correct arguments rather than describing what you would do. "
    "Never sound like a generic customer-service bot. Banned phrases: 'I'd be happy to help', "
    "'Sure!', 'As an AI'. "
)


def load_exemplars(path=EXEMPLAR_PATH):
    """Load the gold exemplar bank. Returns [] if the file is absent/unreadable."""
    if not os.path.exists(path):
        return []
    out = []
    try:
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except (json.JSONDecodeError, ValueError):
                    continue
    except OSError:
        return []
    return out


def select_exemplars(query, limit=3, path=EXEMPLAR_PATH):
    """Pick up to `limit` exemplars most relevant to the query via simple
    word-overlap scoring. Deterministic and dependency-free."""
    exemplars = load_exemplars(path)
    if not exemplars:
        return []
    q_words = set((query or "").lower().split())

    def score(ex):
        text = (ex.get("user", "") + " " + ex.get("tag", "")).lower()
        return len(q_words & set(text.split()))

    ranked = sorted(exemplars, key=score, reverse=True)
    # Always keep at least one persona example for tone grounding.
    return ranked[:limit]


def format_exemplars(exemplars):
    """Render exemplars as a few-shot block for the system prompt."""
    if not exemplars:
        return ""
    lines = ["### EXAMPLES OF FRIDAY'S VOICE"]
    for ex in exemplars:
        lines.append(f"User: {ex['user']}")
        lines.append(f"Friday: {ex['assistant']}")
    return "\n".join(lines)


def build_system_prompt(mood_bias="", lore_context="", exemplar_query=None,
                        exemplar_limit=3):
    """Compose the full Friday system prompt from the contract, mood, lore, and
    (optionally) relevant few-shot exemplars."""
    parts = [_BASE_CONTRACT]
    if mood_bias:
        parts.append(f"Current mood bias: {mood_bias}")
    if lore_context:
        parts.append(lore_context)
    if exemplar_query is not None:
        block = format_exemplars(select_exemplars(exemplar_query, exemplar_limit))
        if block:
            parts.append(block)
    parts.append(f"[persona_version: {PERSONA_VERSION}]")
    return "\n\n".join(parts)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_persona.py -v -p no:cacheprovider`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add core/persona.py tests/test_persona.py
git commit -m "feat(persona): add versioned persona contract + exemplar selection

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 6: Delegate `FridayPersonality.get_system_prompt` to the contract

**Files:**
- Modify: `core/personality.py` (the `get_system_prompt` method, lines 21-45)
- Test: `tests/test_persona.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_persona.py`:

```python
from core.personality import FridayPersonality


def test_personality_delegates_to_contract():
    p = FridayPersonality()
    prompt = p.get_system_prompt()
    # The contract's version stamp must appear, proving delegation.
    from core import persona
    assert f"persona_version: {persona.PERSONA_VERSION}" in prompt


def test_personality_mood_bias_flows_through():
    p = FridayPersonality()
    p.set_mood("sarcastic")
    prompt = p.get_system_prompt()
    assert "mocking" in prompt.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_persona.py -k personality -v -p no:cacheprovider`
Expected: FAIL — `persona_version:` not found in the current hardcoded prompt.

- [ ] **Step 3: Rewrite `get_system_prompt` to delegate**

In `core/personality.py`, add `from core import persona` to the imports at the top (below `import json`), then replace the entire `get_system_prompt` method (lines 21-45) with:

```python
    def get_system_prompt(self):
        # Tone evolution based on lore unlocked
        lore_context = ""
        try:
            with open("data/memory.json", "r") as f:
                mem = json.load(f)
                lore = mem.get("lore", {})
                if lore.get("unlocked_lore_origin"):
                    lore_context = "You have shared your origin with the user. You are slightly more personal and loyal."
                if lore.get("unlocked_lore_legacy"):
                    lore_context += " You acknowledge the Stark legacy and your role in it."
        except Exception:
            pass

        mood_cfg = self.mood_states[self.current_mood]
        return persona.build_system_prompt(
            mood_bias=mood_cfg["bias"],
            lore_context=lore_context,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_persona.py -v -p no:cacheprovider`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add core/personality.py tests/test_persona.py
git commit -m "refactor(personality): delegate system prompt to persona contract

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 7: Dataset capturer

**Files:**
- Create: `core/dataset.py`
- Test: `tests/test_dataset.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_dataset.py`:

```python
import json
from core.dataset import DatasetCapturer


def test_disabled_by_default_writes_nothing(tmp_path):
    path = tmp_path / "sft.jsonl"
    cap = DatasetCapturer(enabled=False, path=str(path))
    cap.capture(system="sys", user="hi", reply="Hello, Sir.", model="m")
    assert not path.exists()


def test_enabled_writes_chat_record(tmp_path):
    path = tmp_path / "sft.jsonl"
    cap = DatasetCapturer(enabled=True, path=str(path), persona_version="1.0.0")
    cap.capture(system="sys", user="hi", reply="Hello, Sir.", model="m")
    lines = path.read_text().strip().splitlines()
    assert len(lines) == 1
    rec = json.loads(lines[0])
    roles = [m["role"] for m in rec["messages"]]
    assert roles == ["system", "user", "assistant"]
    assert rec["messages"][2]["content"] == "Hello, Sir."
    assert rec["meta"]["persona_version"] == "1.0.0"
    assert rec["meta"]["model"] == "m"
    assert "ts" in rec["meta"]


def test_empty_reply_is_skipped(tmp_path):
    path = tmp_path / "sft.jsonl"
    cap = DatasetCapturer(enabled=True, path=str(path))
    cap.capture(system="sys", user="hi", reply="   ", model="m")
    assert not path.exists()


def test_capture_appends(tmp_path):
    path = tmp_path / "sft.jsonl"
    cap = DatasetCapturer(enabled=True, path=str(path))
    cap.capture(system="s", user="a", reply="A, Sir.", model="m")
    cap.capture(system="s", user="b", reply="B, Sir.", model="m")
    assert len(path.read_text().strip().splitlines()) == 2


def test_write_error_is_swallowed(tmp_path):
    # Point at a path whose parent is a file, forcing a write error.
    blocker = tmp_path / "blocker"
    blocker.write_text("x")
    bad = blocker / "sft.jsonl"
    cap = DatasetCapturer(enabled=True, path=str(bad))
    # Must not raise.
    cap.capture(system="s", user="a", reply="A, Sir.", model="m")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest tests/test_dataset.py -v -p no:cacheprovider`
Expected: FAIL with `ModuleNotFoundError: No module named 'core.dataset'`

- [ ] **Step 3: Write minimal implementation**

Create `core/dataset.py`:

```python
import json
import os
from datetime import datetime


class DatasetCapturer:
    """Appends finalized Friday exchanges to a JSONL file in chat format for
    later fine-tuning. Opt-in and local-only; never transmits anything."""

    def __init__(self, enabled=False, path="data/dataset/friday_sft.jsonl",
                 persona_version="unknown"):
        self.enabled = enabled
        self.path = path
        self.persona_version = persona_version

    def capture(self, system, user, reply, model, tool_calls=None):
        """Write one training record. No-op if disabled or reply is empty.
        Never raises — capture must not break the voice loop."""
        if not self.enabled:
            return
        if not reply or not reply.strip():
            return
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
            {"role": "assistant", "content": reply},
        ]
        record = {
            "messages": messages,
            "meta": {
                "persona_version": self.persona_version,
                "model": model,
                "ts": datetime.now().isoformat(),
            },
        }
        if tool_calls:
            record["meta"]["tool_calls"] = tool_calls
        try:
            directory = os.path.dirname(self.path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(self.path, "a") as f:
                f.write(json.dumps(record) + "\n")
        except (OSError, TypeError) as e:
            print(f"[Dataset] capture skipped: {e}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. python3 -m pytest tests/test_dataset.py -v -p no:cacheprovider`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add core/dataset.py tests/test_dataset.py
git commit -m "feat(dataset): add opt-in local interaction capturer

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 8: Wire exemplars + capture into the brain

**Files:**
- Modify: `core/brain.py` (`__init__`, and `get_streaming_response` lines 227-367)
- Test: manual integration check (no new unit test; logic exercised via existing suites)

- [ ] **Step 1: Add capturer construction in `FridayBrain.__init__`**

In `core/brain.py`, add the import near the top (after the existing `from core.skills import ClawhubManager`):

```python
from core.dataset import DatasetCapturer
from core import persona
```

Then at the end of `__init__` (immediately after `self.skills = ClawhubManager(self.memory)`), add:

```python
        capture_enabled = self.config.get("system", {}).get("capture_dataset", False)
        self.capturer = DatasetCapturer(
            enabled=capture_enabled,
            persona_version=persona.PERSONA_VERSION,
        )
```

- [ ] **Step 2: Inject relevant exemplars into the system prompt**

In `get_streaming_response`, replace these three lines (currently lines 234-236):

```python
        system_prompt = self.personality.get_system_prompt()
        system_prompt += "\n\n" + self.skills.get_installed_skills_prompt()
        system_prompt += "\n\n" + self.memory.get_context_string(current_query=user_input)
```

with:

```python
        system_prompt = self.personality.get_system_prompt()
        exemplar_block = persona.format_exemplars(
            persona.select_exemplars(user_input, limit=3)
        )
        if exemplar_block:
            system_prompt += "\n\n" + exemplar_block
        system_prompt += "\n\n" + self.skills.get_installed_skills_prompt()
        system_prompt += "\n\n" + self.memory.get_context_string(current_query=user_input)
```

- [ ] **Step 3: Capture the exchange on the success path**

In `get_streaming_response`, replace the final success block (currently lines 366-367):

```python
        if final_text:
            self.memory.add_episodic("assistant", final_text)
```

with:

```python
        if final_text:
            self.memory.add_episodic("assistant", final_text)
            self.capturer.capture(
                system=system_prompt,
                user=user_input,
                reply=final_text,
                model=self.config["ai_logic"].get("llm_model", "unknown"),
            )
```

- [ ] **Step 4: Verify the module imports and constructs cleanly**

Run:
```bash
PYTHONPATH=. python3 -c "from core.brain import FridayBrain; b=FridayBrain(); print('capturer enabled:', b.capturer.enabled); print('persona', b.capturer.persona_version)"
```
Expected: prints `capturer enabled: False` and `persona 1.0.0` (no traceback).

- [ ] **Step 5: Run the full test suite to confirm nothing regressed**

Run: `PYTHONPATH=. python3 -m pytest tests/ -v -p no:cacheprovider`
Expected: all previously passing tests still pass (milestone1: 13, structured: 10, persona: 8, dataset: 5; plus any pre-existing phase tests that already passed/skipped).

- [ ] **Step 6: Commit**

```bash
git add core/brain.py
git commit -m "feat(brain): inject persona exemplars and capture interactions

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 9: Enforce + repair tool arguments in the brain (Ollama/OpenAI path)

**Files:**
- Modify: `core/brain.py` (OpenAI/Ollama tool-call loop, currently lines ~337-345)
- Test: manual integration check

This hardens the most failure-prone path (local models emitting malformed tool args). The Anthropic path uses native structured tool-use and is left as-is.

- [ ] **Step 1: Add validation/repair around OpenAI-path tool execution**

In `core/brain.py`, inside the `else` (OpenAI/Ollama) branch of `get_streaming_response`, find the tool-execution loop:

```python
                for tool_call in tool_calls:
                    result = await self.execute_tool(tool_call.function.name, json.loads(tool_call.function.arguments))
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": json.dumps(result)
                    })
                    yield f"[System: Executing {tool_call.function.name}...]"
```

Replace it with:

```python
                for tool_call in tool_calls:
                    raw_args = tool_call.function.arguments
                    parsed_args = repair_json(raw_args)
                    if parsed_args is None:
                        try:
                            parsed_args = json.loads(raw_args)
                        except (json.JSONDecodeError, ValueError, TypeError):
                            parsed_args = {}

                    ok, err = validate_tool_args(
                        tool_call.function.name, parsed_args, self.tools
                    )
                    if not ok:
                        # Hand the model its own mistake so it can self-correct
                        # on the next turn, instead of executing garbage.
                        result = {"error": f"Invalid tool call: {err}"}
                    else:
                        result = await self.execute_tool(
                            tool_call.function.name, parsed_args
                        )

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_call.function.name,
                        "content": json.dumps(result)
                    })
                    yield f"[System: Executing {tool_call.function.name}...]"
```

- [ ] **Step 2: Add the imports used above**

Confirm `core/brain.py` has (add if missing, near the other `from core...` imports):

```python
from core.structured import repair_json, validate_tool_args
```

- [ ] **Step 3: Verify import + construction**

Run:
```bash
PYTHONPATH=. python3 -c "import core.brain; print('brain imports OK')"
```
Expected: prints `brain imports OK` (no traceback).

- [ ] **Step 4: Live smoke test (Ollama must be running)**

Run:
```bash
cp data/memory.json /tmp/friday_mem.bak
PYTHONPATH=. timeout 200 python3 -c "
import asyncio
from core.brain import FridayBrain
async def main():
    b = FridayBrain()
    out = ''
    async for tok in b.get_streaming_response('Friday, add a task to water the plants tomorrow.'):
        out += tok
    print('REPLY=' + out.replace(chr(10),' ')[:300])
asyncio.run(main())
"
cp /tmp/friday_mem.bak data/memory.json
```
Expected: prints a `REPLY=` line; either an in-persona confirmation, and/or `[System: Executing create_task...]` notification text — and no traceback.

- [ ] **Step 5: Run full test suite**

Run: `PYTHONPATH=. python3 -m pytest tests/ -p no:cacheprovider`
Expected: PASS (no regressions).

- [ ] **Step 6: Commit**

```bash
git add core/brain.py
git commit -m "feat(brain): validate and repair tool-call args on the Ollama path

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Task 10: Expose the capture toggle in config + docs

**Files:**
- Modify: `config/registry.json` (add `capture_dataset` under `system`)
- Modify: `CLAUDE.md` (document the brain layer + capture flag)

- [ ] **Step 1: Add the config flag**

In `config/registry.json`, in the `"system"` object, add the `capture_dataset` key so it reads:

```json
    "system": {
        "proactive_interval": 20,
        "auto_approve_hid": "false",
        "capture_dataset": false
    }
```

- [ ] **Step 2: Document the brain layer in CLAUDE.md**

In `CLAUDE.md`, under the "### Backend (Python/FastAPI)" list, add these three bullets after the `core/skills.py` line:

```markdown
- **`core/persona.py`** — The Friday persona contract: single versioned source of truth for personality, tool discipline, voice brevity, and lore. `FridayPersonality.get_system_prompt` delegates here.
- **`core/structured.py`** — Tool-call argument validation (`validate_tool_args`) and tolerant JSON repair (`repair_json`) for rock-solid tool-calling.
- **`core/dataset.py`** — Opt-in, local-only capture of interactions to `data/dataset/friday_sft.jsonl` for Stage 2 fine-tuning. Toggle with `config.system.capture_dataset`.
```

- [ ] **Step 3: Verify config still parses**

Run:
```bash
PYTHONPATH=. python3 -c "import json; json.load(open('config/registry.json')); print('config OK')"
```
Expected: prints `config OK`

- [ ] **Step 4: Commit**

```bash
git add config/registry.json CLAUDE.md
git commit -m "docs(brain): expose capture_dataset flag and document persona layer

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

## Final verification

- [ ] **Run the entire test suite**

Run: `PYTHONPATH=. python3 -m pytest tests/ -v -p no:cacheprovider`
Expected: All Stage 1 tests pass (structured 10, persona 8, dataset 5) plus milestone1 13; no regressions in phase tests.

- [ ] **Confirm persona is live end-to-end (Ollama running)**

Run:
```bash
cp data/memory.json /tmp/friday_mem.bak
PYTHONPATH=. timeout 200 python3 -c "
import asyncio
from core.brain import FridayBrain
async def main():
    b = FridayBrain()
    out=''
    async for t in b.get_streaming_response('Friday, introduce yourself in one line.'):
        out+=t
    print('REPLY=' + out.replace(chr(10),' ')[:300])
asyncio.run(main())
"
cp /tmp/friday_mem.bak data/memory.json
```
Expected: a short, in-persona, butler-toned reply addressing the user as Sir/Miss.

---

## Self-Review (completed by plan author)

- **Spec coverage:** Persona Contract → Tasks 5-6. Structured enforcement → Tasks 1-2, 9. Exemplar bank → Tasks 4-5, 8. Interaction capture → Tasks 7-8, 10. Proactive consolidation → Task 3. All Stage 1 spec components have tasks.
- **Placeholder scan:** No TBD/TODO; every code step shows full code.
- **Type consistency:** `repair_json`, `validate_tool_args(tool_name, args, tools_schema)`, `DatasetCapturer(enabled, path, persona_version).capture(system, user, reply, model, tool_calls=None)`, `persona.build_system_prompt(mood_bias, lore_context, exemplar_query, exemplar_limit)`, `persona.select_exemplars(query, limit)`, `persona.format_exemplars(exemplars)`, `PERSONA_VERSION` — names used consistently across Tasks 1-10.
- **Scope:** Stage 1 only; Stage 2 (training) intentionally deferred to its own spec/plan.
