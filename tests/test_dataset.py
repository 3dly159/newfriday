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
