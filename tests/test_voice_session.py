import asyncio
from core.voice_session import is_sentence_end, VoiceSession


def test_is_sentence_end():
    assert is_sentence_end("Hello there.")
    assert is_sentence_end("Really?")
    assert is_sentence_end("Stop!")
    assert not is_sentence_end("hold on")


class _FakeBrain:
    """Minimal brain stub: streams two sentences, with a tool notification."""
    class _Pers:
        current_mood = "neutral"
        mood_states = {"neutral": {"orb_color": "#5cc8ff"}}

    def __init__(self):
        self.personality = self._Pers()
        self.config = {"ai_logic": {"llm_model": "test"}}

    async def get_streaming_response(self, text):
        for tok in ["Good ", "evening, Sir. ", "[System: Executing get_system_vitals...]",
                    "All ", "systems nominal."]:
            yield tok


class _FakeTTS:
    async def generate_speech_timed(self, text, output_path):
        with open(output_path, "wb") as f:
            f.write(b"FAKEAUDIO")
        return output_path, [{"word": text.strip().split(" ")[0], "offset_ms": 0, "duration_ms": 100}]


# These tests drive the coroutine with asyncio.run() directly so they need no
# pytest async plugin (pytest-asyncio is unreliable in this environment).

def test_run_turn_emits_contract_events(tmp_path):
    sent_json = []
    sent_bytes = []
    session = VoiceSession(
        brain=_FakeBrain(), stt=None, tts=_FakeTTS(),
        send_json=lambda m: sent_json.append(m),
        send_bytes=lambda b: sent_bytes.append(b),
        logs_dir=str(tmp_path),
    )
    asyncio.run(session.run_turn("status report"))

    types = [m["type"] for m in sent_json]
    assert "transcript" in types
    assert any(m["type"] == "state" and m["state"] == "thinking" for m in sent_json)
    assert any(m["type"] == "state" and m["state"] == "speaking" for m in sent_json)
    assert any(m["type"] == "caption" for m in sent_json)
    assert any(m["type"] == "action" and m["tool"] == "get_system_vitals" for m in sent_json)
    assert sent_json[-1] == {"type": "state", "state": "idle"}
    n_caps = sum(1 for m in sent_json if m["type"] == "caption")
    assert len(sent_bytes) == n_caps
    assert n_caps >= 1


def test_run_turn_user_transcript_first(tmp_path):
    sent = []
    session = VoiceSession(
        brain=_FakeBrain(), stt=None, tts=_FakeTTS(),
        send_json=lambda m: sent.append(m), send_bytes=lambda b: None,
        logs_dir=str(tmp_path),
    )
    asyncio.run(session.run_turn("hello"))
    assert sent[0] == {"type": "transcript", "role": "user", "text": "hello", "final": True}


class _ExplodingTTS:
    """Fails if asked to synthesize — proves non-speakable segments are skipped."""
    async def generate_speech_timed(self, text, output_path):
        raise AssertionError(f"should not synthesize non-speakable text: {text!r}")


def test_synth_skips_non_speakable_segment(tmp_path):
    sent = []
    session = VoiceSession(
        brain=_FakeBrain(), stt=None, tts=_ExplodingTTS(),
        send_json=lambda m: sent.append(m), send_bytes=lambda b: None,
        logs_dir=str(tmp_path),
    )
    # Whitespace/punctuation-only segments must be skipped: TTS is never called
    # (else _ExplodingTTS raises) and no caption is emitted.
    asyncio.run(session._synth_segment("   ...  \n"))
    assert sent == []


from core.voice_session import summarize_result


def test_summarize_web_results():
    res = [{"title": "Foo", "url": "http://x", "snippet": "bar"},
           {"title": "Baz", "url": "http://y", "snippet": "qux"}]
    card = summarize_result("web_search", res)
    assert card["title"].lower().startswith("web")
    assert any("Foo" in ln for ln in card["lines"])


def test_summarize_file_list():
    card = summarize_result("search_files", ["a.py", "b.py", "c.py"])
    assert "file" in card["title"].lower()
    assert len(card["lines"]) <= 6


def test_summarize_non_card_returns_none():
    assert summarize_result("set_volume", "Volume set to 50%.") is None
    assert summarize_result("run_shell", {"stdout": "ok", "exit_code": 0}) is None


def test_summarize_unknown_tool_returns_none():
    assert summarize_result("create_task", "Task created") is None


def test_first_caption_emitted_before_turn_ends(tmp_path):
    # The first spoken segment must be emitted as soon as the first sentence is
    # ready — not held until the stream finishes.
    class _Brain:
        class _P:
            current_mood = "neutral"; mood_states = {"neutral": {"orb_color": "#5cc8ff"}}
        def __init__(self): self.personality = self._P(); self.config = {"ai_logic": {"llm_model": "t"}}
        async def get_streaming_response(self, text):
            for tok in ["One. ", "Two. ", "Three."]:
                yield tok

    class _TTS:
        async def generate_speech_timed(self, text, out):
            open(out, "wb").write(b"A")
            return out, [{"word": "x", "offset_ms": 0, "duration_ms": 10}]

    sent = []
    s = VoiceSession(_Brain(), None, _TTS(),
                     send_json=lambda m: sent.append(m),
                     send_bytes=lambda b: None, logs_dir=str(tmp_path))
    asyncio.run(s.run_turn("go"))

    caption_idx = next(i for i, m in enumerate(sent) if m["type"] == "caption")
    transcript_idxs = [i for i, m in enumerate(sent) if m["type"] == "transcript" and m["role"] == "friday"]
    assert transcript_idxs and caption_idx < transcript_idxs[-1]
    assert sum(1 for m in sent if m["type"] == "caption") == 3
