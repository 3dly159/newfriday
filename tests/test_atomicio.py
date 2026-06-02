import json
from core.atomicio import atomic_write_json


def test_writes_and_roundtrips(tmp_path):
    p = tmp_path / "d.json"
    atomic_write_json(str(p), {"a": 1})
    assert json.loads(p.read_text()) == {"a": 1}


def test_no_tmp_left_behind(tmp_path):
    p = tmp_path / "d.json"
    atomic_write_json(str(p), {"a": 1})
    assert not (tmp_path / "d.json.tmp").exists()


def test_rotates_backups(tmp_path):
    p = tmp_path / "d.json"
    atomic_write_json(str(p), {"v": 1})
    atomic_write_json(str(p), {"v": 2})
    atomic_write_json(str(p), {"v": 3})
    assert json.loads(p.read_text())["v"] == 3
    assert json.loads((tmp_path / "d.json.bak1").read_text())["v"] == 2
    assert json.loads((tmp_path / "d.json.bak2").read_text())["v"] == 1


def test_creates_parent_dir(tmp_path):
    p = tmp_path / "sub" / "d.json"
    atomic_write_json(str(p), {"ok": True})
    assert json.loads(p.read_text())["ok"] is True
