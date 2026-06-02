import os
import uuid
import inspect
from core import events


def is_sentence_end(text):
    return text.strip().endswith(('.', '?', '!'))


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


class VoiceSession:
    """Owns one conversational turn: input text -> brain stream -> word-timed TTS
    -> ordered contract events. Decoupled from FastAPI via send callables."""

    def __init__(self, brain, stt, tts, send_json, send_bytes, logs_dir="data/logs"):
        self.brain = brain
        self.stt = stt
        self.tts = tts
        self._send_json = send_json
        self._send_bytes = send_bytes
        self.logs_dir = logs_dir

    async def _send(self, fn, arg):
        # Support both sync and async send callables (FastAPI's are async).
        result = fn(arg)
        if inspect.isawaitable(result):
            await result

    async def _emit(self, event):
        await self._send(self._send_json, event)

    async def _emit_bytes(self, data):
        await self._send(self._send_bytes, data)

    async def _emit_mood(self):
        pers = self.brain.personality
        mood = pers.current_mood
        color = pers.mood_states.get(mood, {}).get("orb_color", "#5cc8ff")
        await self._emit(events.mood_event(mood, color))

    async def _synth_segment(self, text):
        # Skip segments with nothing speakable (whitespace/punctuation only).
        # Edge-TTS produces no audio for these and raises, dropping the segment.
        if not any(c.isalnum() for c in text):
            return
        os.makedirs(self.logs_dir, exist_ok=True)
        seg_id = uuid.uuid4().hex
        out = os.path.join(self.logs_dir, f"resp_{seg_id}.mp3")
        try:
            _, words = await self.tts.generate_speech_timed(text, out)
            with open(out, "rb") as f:
                audio = f.read()
            await self._emit(events.caption_event(seg_id, words, text))
            await self._emit_bytes(audio)
        except Exception as e:
            await self._emit(events.caption_event(seg_id, [], text, mode="sentence"))
            print(f"[VoiceSession] TTS error: {e}")
        finally:
            if os.path.exists(out):
                os.remove(out)

    async def run_turn(self, user_text):
        await self._emit(events.transcript_event("user", user_text, True))
        await self._emit_mood()
        await self._emit(events.state_event("thinking"))

        open_actions = []
        buffer = ""
        full_reply = ""
        spoke = False

        async for token in self.brain.get_streaming_response(user_text):
            if token.startswith("[System: Executing "):
                tool = token[len("[System: Executing "):].rstrip(".]").rstrip(".")
                tool = tool.replace("...", "").strip()
                open_actions.append(tool)
                await self._emit(events.action_event(tool, "start", f"Running {tool}"))
                await self._emit(events.state_event("acting"))
                continue

            if token.startswith("[Approval:"):
                category = token[len("[Approval:"):].rstrip("]").strip()
                # Mark the corresponding action chip as needing approval, and
                # ask the UI to prompt the user.
                if open_actions:
                    await self._emit(events.action_event(open_actions[-1], "error", "needs approval"))
                await self._emit(events.approval_event(category))
                continue

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

            # Real assistant text from here on.
            full_reply += token

            if open_actions:
                for t in open_actions:
                    await self._emit(events.action_event(t, "done", f"{t} complete"))
                open_actions = []

            buffer += token
            if is_sentence_end(buffer):
                if not spoke:
                    await self._emit(events.state_event("speaking"))
                    spoke = True
                # Speak each sentence as soon as it's ready (no hold-one-ahead),
                # so the first audio starts as early as possible.
                await self._synth_segment(buffer)
                buffer = ""

        for t in open_actions:
            await self._emit(events.action_event(t, "done", f"{t} complete"))

        final_text = buffer
        if final_text.strip():
            if not spoke:
                await self._emit(events.state_event("speaking"))
            await self._synth_segment(final_text)

        if full_reply.strip():
            await self._emit(events.transcript_event("friday", full_reply.strip(), True))

        await self._emit(events.state_event("idle"))
