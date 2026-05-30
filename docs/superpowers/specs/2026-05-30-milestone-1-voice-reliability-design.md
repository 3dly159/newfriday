# Milestone 1 — "She Reliably Talks Back"

**Date:** 2026-05-30
**Branch:** `friday-milestone-1-voice-reliability`
**Goal:** A rock-solid real-time voice loop. This is the foundation every other JARVIS
pillar (proactivity, agency, HUD, ARG) depends on. Right now Friday cannot hold a
reliable conversation, so this comes first.

## Context: what's broken today

Verified at runtime on 2026-05-30:
- **No brain connected.** Config targets Ollama at `localhost:11434` (nothing listening)
  and `ANTHROPIC_API_KEY` is unset → zero LLM behind Friday.
- **Legion agents hardcoded to Anthropic** (`core/agents.py`) → `delegate_to_legion`
  crashes under the Ollama config.
- **Proactive loop does `json.loads()` on raw model output** → fragile; local models
  rarely emit clean JSON, so cycles silently fail.
- **Continuous mode + no VAD gating** → Whisper `base.en` hallucinates phrases like
  "Thank you." on silence; Friday answers her own imagination.
- **No barge-in** → user cannot interrupt Friday mid-sentence.
- **`registry.json` polluted** with `[object Object]` from a UI config round-trip.

## Scope (this milestone only)

1. **STT reliability** — gate out silence/hallucinations using faster-whisper
   confidence signals (`no_speech_prob`, avg logprob) plus a known-hallucination
   phrase filter. Extract a pure, unit-testable `filter_transcription()` helper.
2. **Brain robustness** — provider auto-detection and a `/api/health` endpoint that
   reports whether the configured brain is reachable. When the brain is unreachable,
   Friday speaks a graceful in-character message instead of failing silently.
3. **Legion provider-agnostic** — sub-agents reuse the brain's provider/client config
   rather than hardcoding Anthropic.
4. **Proactive tolerant parsing** — extract JSON from fenced/prose output; on parse
   failure, default to SILENCE rather than erroring.
5. **Config sanitization** — stop persisting the injected `system_memory` blob back to
   `registry.json`; clean the existing junk.
6. **Barge-in** — backend honors an `interrupt` control message to stop streaming
   queued audio; frontend stops playback and sends `interrupt` when the user speaks.

## Out of scope (future milestones)

Cinematic HUD polish, expanded agency/tools, deep proactive intelligence, ARG
narrative expansion. Tracked separately; revisited after this foundation is solid.

## Design decisions

- **Default provider stays Ollama** (the user's established path per git history) but
  every brain path becomes provider-agnostic and degrades gracefully. The one manual
  step the user must do — start their brain (`ollama serve` + a pulled model, or set an
  API key) — is surfaced clearly via `/api/health` and a spoken status, never a silent
  hang.
- **Testability first.** Reliability logic (transcription filtering, JSON extraction,
  config sanitization) is extracted into pure functions covered by pytest, so it is
  verifiable without a live mic or brain.

## Verification

- Unit tests for: `filter_transcription`, proactive JSON extraction, config
  sanitization, provider-agnostic Legion construction.
- `pytest` green for all non-LLM tests.
- Manual: documented one-command brain bring-up; `/api/health` reflects reachability.
