# FRIDAY — Quick Start

A voice-first AI assistant with a holographic UI. This is the fastest path from a
fresh clone to talking to Friday.

## 1. Prerequisites

- **Python 3.11+** (this project is developed on 3.12). Note: use `python3` — `python`
  may not be on your PATH.
- **[Ollama](https://ollama.com)** running locally — Friday's default brain.
- A modern browser (Chrome/Edge/Firefox) for the UI and microphone access.

## 2. Install dependencies

```bash
pip install -r requirements.txt
```

## 3. Start the brain (Ollama)

Friday talks to an OpenAI-compatible endpoint at `http://localhost:11434/v1`.

```bash
ollama serve            # start the server (if not already running)
ollama pull <model>     # ensure the model in config/registry.json is available
```

The model is set in `config/registry.json` under `ai_logic.llm_model`
(default: `nemotron-3-super:cloud`). The first call to a `:cloud` model can take a
while to warm up; subsequent calls are fast.

> No Ollama? You can instead set `ai_logic.model_provider` to `anthropic` and export
> `ANTHROPIC_API_KEY`. Check `GET /api/health` to see whether the configured brain is reachable.

## 4. Launch Friday

```bash
python3 launcher.py
# then open http://localhost:8000
```

Or run the server directly:

```bash
PYTHONPATH=. python3 -m uvicorn core.main:app --host 0.0.0.0 --port 8000
```

## 5. Talk to her

- **Type** in the command bar and press Enter, **or**
- Click the **mic** and speak. In `continuous` mode she listens always but only
  answers when addressed ("Friday, …") or greeted.
- The orb wobbles and shifts color with her mood, then returns to arc-reactor blue.
- The **⚙ settings** sidebar edits config live; the **☉ neural map** opens on its own page.

## 6. Permissions

Risky actions (mouse/keyboard, scripts, file writes) are gated in
`config/permissions.json`: each category is `allow`, `ask`, or `deny`. With `ask`,
Friday surfaces an approval toast before acting. Edit them in the settings sidebar.

## 7. Tests

```bash
PYTHONPATH=. python3 -m pytest -q
```

Async tests use `asyncio.run()` directly (no `pytest-asyncio` plugin required in
this environment).

## Branch naming

Feature work goes on `friday-<area>-<short-description>` branches (e.g.
`friday-milestone-1-voice-reliability`), opened against the project's main branch.

## Troubleshooting

| Symptom | Likely cause / fix |
|---|---|
| "my local Ollama brain isn't responding" | Ollama isn't running, or the model isn't pulled. `ollama serve` + `ollama pull <model>`. |
| Friday is silent (no audio) | The configured `tts_voice` may not exist. Valid en-GB voices: Libby, Maisie, Ryan, Sonia, Thomas. |
| "internal snag (…)" reply | An internal error (not the server). Check the terminal — a full traceback is printed. |
| Mic does nothing | Browser mic permission denied, or not served over `localhost`/HTTPS. |
