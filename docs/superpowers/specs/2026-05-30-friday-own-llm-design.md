# Friday's Own LLM — Staged Design

**Date:** 2026-05-30
**Goal:** Give Friday a brain that matches our vision *exactly* and fits the system
perfectly — first via a software "brain layer" that runs today on any backing model,
then via genuinely custom weights fine-tuned locally on the RTX 3050 and served
through Ollama with zero changes to the rest of the system.

## Vision: what "our own Friday" must nail

All four of Friday's DNA traits are in scope (user-selected):
1. **Butler persona & wit** — deadpan, witty, "I've taken the liberty of…", addresses
   the user as Sir/Miss, never a generic chatbot.
2. **Rock-solid tool-calling** — always well-formed calls for the system's 17 tools.
3. **Brevity & voice cadence** — short, speakable replies tuned for TTS.
4. **Proactive judgment & lore** — sound SPEAK/ACT/SILENCE decisions; depth on the
   Friday/ARG narrative.

## Hardware reality (verified 2026-05-30)

RTX 3050 Laptop **6GB**, CUDA working; 16 cores; 24GB RAM; 110GB free. Training stack
already installed: torch 2.10+cu128, transformers 5.5, peft 0.19, trl 0.24, datasets
4.3, accelerate 1.13, bitsandbytes 0.49. **Consequence:** local 4-bit QLoRA on a small
model is feasible and free — no cloud GPU required.

Brain runs via Ollama (provider `ollama`, `http://localhost:11434/v1`); no
`ANTHROPIC_API_KEY`. `python3` only (no `python` on PATH); run with `PYTHONPATH=.`.

## Decomposition

Two independent sub-projects. **This spec covers Stage 1 in full** and commits to
Stage 2 as roadmap (its own spec/plan when data is flowing).

---

## Stage 1 — The Friday Brain Layer (no training; ships now; free)

Makes any backing model behave like Friday, and captures the data that trains Stage 2.

### Components

**1. Persona Contract — `core/persona.py` (new)**
- Single source of truth for Friday's identity, composed from the four traits.
- Versioned (`PERSONA_VERSION`) so captured data records which persona produced it.
- Returns a composable system prompt; replaces the hardcoded string in
  `core/personality.py::get_system_prompt`. Mood/lore layering is preserved by
  delegating to the contract. `FridayPersonality` keeps its public API
  (`get_system_prompt`, `set_mood`, `mood_states`) so `brain.py`/`main.py` are untouched.

**2. Structured-output enforcement — `core/structured.py` (new)**
- `validate_tool_args(tool_name, args, tools_schema) -> (ok, error)`: checks required
  fields/enums/types against the existing tool schemas in `brain.py`.
- `repair_json(text) -> dict | None`: reuses/*generalizes* the tolerant extractor from
  `core/proactive.py` (consolidate both call sites onto one helper).
- Brain integration: on a malformed tool call, retry **once** with a corrective system
  nudge; if still bad, surface an in-character "I fumbled that" rather than crashing.

**3. Exemplar bank — `data/persona/exemplars.jsonl` + loader in `core/persona.py`**
- Curated "gold" Friday interactions (persona, tool-call, brevity, proactive samples).
- A small, relevant subset injected as few-shot context (token-budgeted).
- Hand-authored seed set (~15–25 exemplars) created as part of this stage.

**4. Interaction capture — `core/dataset.py` (new)**
- Appends finalized exchanges to `data/dataset/friday_sft.jsonl` in chat format
  (`{"messages": [...], "meta": {persona_version, model, ts}}`).
- **Opt-in** via `config.system.capture_dataset` (default `false`); **local-only**,
  never transmitted. Captures system prompt, user msg, tool calls/results, final reply.
- Hooked at the end of `brain.get_streaming_response` (success path only).

### Data flow
`user → brain → persona contract builds system prompt (+exemplars) → model →
structured enforcement (validate/repair/retry) → reply → capture (if enabled)`

### Error handling
- Malformed tool args → one repair retry → in-character apology tool-result.
- Repair/validation failures degrade gracefully; never raise into the voice loop.
- Capture failures are swallowed with a log line (never block a response).

### Testing (pure, no live LLM)
- Persona contract: contains required trait markers; version stable; mood/lore layering.
- `validate_tool_args`: accepts good calls; rejects missing-required/bad-enum/wrong-type.
- `repair_json`: fenced/prose/garbage cases (port existing proactive tests).
- Capture: writes valid JSONL, respects opt-in flag, tolerates write errors.

---

## Stage 2 — Local QLoRA fine-tune (RTX 3050; free; roadmap)

- **Base model:** **Qwen2.5-1.5B-Instruct** (Apache-2.0) — chosen for fastest local
  train/inference and maximum 6GB headroom.
- **Data:** captured real interactions + synthetic exemplars distilled from the strong
  cloud models (nemotron-3-super / deepseek) under the persona contract; deduped,
  quality-filtered, train/val split.
- **Train:** 4-bit QLoRA (TRL `SFTTrainer` + PEFT + bitsandbytes), 6GB-tuned
  (batch 1, grad-accum, gradient checkpointing, short seq len, paged optimizer).
- **Serve:** merge adapter → convert to GGUF → quantize → `ollama create friday` →
  point `registry.json` `llm_model` at `friday:latest`. No other system change.
- **Eval:** held-out persona/tool/brevity prompts; A/B vs base; tool-call validity rate.

## Out of scope
Pretraining from scratch; multi-GPU/cloud training; RLHF/DPO; changing the
voice/HUD/agency systems. Stage 2 implementation details are finalized in its own spec.

## Success criteria
- **Stage 1:** Friday's four traits are enforced by code, not luck; tool-call validity
  measurably improved via repair/retry; real interactions accumulate in
  `friday_sft.jsonl`; all new unit tests green; voice loop behavior unchanged for users.
- **Stage 2 (later):** a local `friday` Ollama model that holds the persona and tool
  discipline at least as well as the prompted cloud model, running fully offline.
