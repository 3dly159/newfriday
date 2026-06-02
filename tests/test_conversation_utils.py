from core.conversation_utils import trim_history


def _msgs(n):
    return [{"role": "user" if i % 2 == 0 else "assistant", "content": f"m{i}"} for i in range(n)]


def test_trim_keeps_last_n_turns():
    out = trim_history(_msgs(20), max_turns=6)
    assert len(out) == 6
    assert out[-1]["content"] == "m19"
    assert out[0]["content"] == "m14"


def test_trim_noop_when_short():
    msgs = _msgs(4)
    assert trim_history(msgs, max_turns=6) == msgs


def test_trim_preserves_order_and_roles():
    out = trim_history(_msgs(10), max_turns=4)
    assert [m["role"] for m in out] == ["user", "assistant", "user", "assistant"]


def test_trim_handles_empty():
    assert trim_history([], max_turns=6) == []
