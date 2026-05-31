import pytest
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


@pytest.mark.asyncio
async def test_run_turn_emits_contract_events(tmp_path):
    sent_json = []
    sent_bytes = []
    session = VoiceSession(
        brain=_FakeBrain(), stt=None, tts=_FakeTTS(),
        send_json=lambda m: sent_json.append(m),
        send_bytes=lambda b: sent_bytes.append(b),
        logs_dir=str(tmp_path),
    )
    await session.run_turn("status report")

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


@pytest.mark.asyncio
async def test_run_turn_user_transcript_first(tmp_path):
    sent = []
    session = VoiceSession(
        brain=_FakeBrain(), stt=None, tts=_FakeTTS(),
        send_json=lambda m: sent.append(m), send_bytes=lambda b: None,
        logs_dir=str(tmp_path),
    )
    await session.run_turn("hello")
    assert sent[0] == {"type": "transcript", "role": "user", "text": "hello", "final": True}
