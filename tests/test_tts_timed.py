from core.tts import boundary_to_word, words_from_chunks


def test_boundary_to_word_converts_ticks_to_ms():
    # Edge-TTS reports offset/duration in 100-nanosecond ticks (10000 ticks = 1 ms)
    chunk = {"type": "WordBoundary", "text": "Hello", "offset": 5000000, "duration": 2500000}
    assert boundary_to_word(chunk) == {"word": "Hello", "offset_ms": 500, "duration_ms": 250}


def test_words_from_chunks_keeps_only_word_boundaries():
    chunks = [
        {"type": "audio", "data": b"\x00\x01"},
        {"type": "WordBoundary", "text": "Good", "offset": 0, "duration": 1000000},
        {"type": "audio", "data": b"\x02"},
        {"type": "WordBoundary", "text": "evening", "offset": 1000000, "duration": 2000000},
    ]
    words = words_from_chunks(chunks)
    assert words == [
        {"word": "Good", "offset_ms": 0, "duration_ms": 100},
        {"word": "evening", "offset_ms": 100, "duration_ms": 200},
    ]


def test_words_from_chunks_empty_when_no_boundaries():
    assert words_from_chunks([{"type": "audio", "data": b"x"}]) == []
