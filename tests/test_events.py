from core import events


def test_state_event():
    assert events.state_event("thinking") == {"type": "state", "state": "thinking"}


def test_result_event():
    ev = events.result_event("web_search", "Web · 3 results", ["a", "b", "c"])
    assert ev == {"type": "result", "tool": "web_search",
                  "title": "Web · 3 results", "lines": ["a", "b", "c"]}


def test_transcript_event():
    assert events.transcript_event("user", "hello", True) == {
        "type": "transcript", "role": "user", "text": "hello", "final": True
    }


def test_caption_event_word_mode():
    words = [{"word": "Hi", "offset_ms": 0, "duration_ms": 100}]
    ev = events.caption_event("seg1", words, "Hi", mode="word")
    assert ev == {
        "type": "caption", "segment_id": "seg1", "mode": "word",
        "words": words, "text": "Hi"
    }


def test_caption_event_defaults_to_sentence_when_no_words():
    ev = events.caption_event("seg2", [], "A full sentence.")
    assert ev["mode"] == "sentence"
    assert ev["words"] == []


def test_action_event():
    assert events.action_event("web_search", "start", "Searching the web") == {
        "type": "action", "tool": "web_search", "phase": "start",
        "label": "Searching the web"
    }


def test_mood_event():
    assert events.mood_event("banter", "#8B5CF6") == {
        "type": "mood", "mood": "banter", "orb_color": "#8B5CF6"
    }
