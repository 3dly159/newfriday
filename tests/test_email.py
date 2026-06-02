from core.agency import email_gmail as eg


def test_status_unconfigured(tmp_path, monkeypatch):
    monkeypatch.setattr(eg, "CREDENTIALS_PATH", str(tmp_path / "nope.json"))
    monkeypatch.setattr(eg, "TOKEN_PATH", str(tmp_path / "tok.json"))
    assert eg.is_configured() is False
    assert "not configured" in eg.email_status().lower()


def test_tools_graceful_when_unconfigured(tmp_path, monkeypatch):
    monkeypatch.setattr(eg, "CREDENTIALS_PATH", str(tmp_path / "nope.json"))
    monkeypatch.setattr(eg, "TOKEN_PATH", str(tmp_path / "tok.json"))
    for out in (eg.email_check(), eg.email_search("x"),
                eg.email_draft("a@b.c", "s", "b"), eg.email_send("a@b.c", "s", "b")):
        assert "not configured" in out.lower()


def test_format_message_is_base64():
    raw = eg.format_message("a@b.c", "Subject", "Body")
    assert isinstance(raw, dict) and "raw" in raw and raw["raw"]
