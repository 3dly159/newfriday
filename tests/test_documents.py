from core.agency.documents import search_in_document, read_document


def test_read_text_document(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "notes.txt").write_text("Hello Sir.\nThis is Friday.\n")
    out = read_document("notes.txt")
    assert "Friday" in out


def test_read_refuses_unsafe(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = read_document("/etc/passwd")
    assert "refus" in out.lower()


def test_search_in_document_finds_snippets(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "doc.txt").write_text("line one\nfind the orb here\nline three\n")
    hits = search_in_document("doc.txt", "orb")
    assert any("orb" in h.lower() for h in hits)


def test_search_no_match(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "doc.txt").write_text("nothing relevant\n")
    assert search_in_document("doc.txt", "zzz") == []
