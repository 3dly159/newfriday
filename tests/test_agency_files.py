from core.agency.files import is_safe_path, filter_matches, truncate


def test_is_safe_path_blocks_traversal():
    assert is_safe_path("notes/todo.txt") is True
    assert is_safe_path("/etc/passwd") is False
    assert is_safe_path("../../etc/shadow") is False
    assert is_safe_path("~/.ssh/id_rsa") is False


def test_is_safe_path_blocks_sensitive_names():
    assert is_safe_path("project/id_rsa") is False
    assert is_safe_path("project/.env") is False
    assert is_safe_path("project/readme.md") is True


def test_filter_matches_by_glob():
    names = ["a.py", "b.txt", "c.py", "d.md"]
    assert filter_matches(names, "*.py") == ["a.py", "c.py"]


def test_truncate_caps_length_with_notice():
    out = truncate("x" * 100, 10)
    assert out.startswith("xxxxxxxxxx")
    assert "truncated" in out.lower()


def test_truncate_short_text_unchanged():
    assert truncate("short", 100) == "short"


import os
from core.agency.files import read_file, list_dir, search_files


def test_read_file_reads_safe_relative(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "note.txt").write_text("hello sir")
    assert "hello sir" in read_file("note.txt")


def test_read_file_refuses_unsafe(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = read_file("/etc/passwd")
    assert "refus" in out.lower() or "not allowed" in out.lower()


def test_list_dir_lists_entries(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.txt").write_text("x")
    (tmp_path / "sub").mkdir()
    entries = list_dir(".")
    assert "a.txt" in entries and "sub" in entries


def test_search_files_finds_by_pattern(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "x.py").write_text("x")
    (tmp_path / "y.txt").write_text("y")
    sub = tmp_path / "sub"; sub.mkdir()
    (sub / "z.py").write_text("z")
    found = search_files(".", "*.py")
    assert any(f.endswith("x.py") for f in found)
    assert any(f.endswith("z.py") for f in found)
    assert not any(f.endswith("y.txt") for f in found)
