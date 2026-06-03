"""Tests for SeelSupport API integration — CRUD + proactive state tracking."""
import json
import pytest
from unittest.mock import MagicMock
import core.agency.seelsupport as seelsupport
from core.agency.seelsupport import (
    BASE_URL, seel_fetch, seel_create, seel_update, seel_delete,
    check_new_notifications,
)


@pytest.fixture(autouse=True)
def mock_creds(monkeypatch):
    """Automatically mock _load_creds so tests run as if configured."""
    monkeypatch.setattr("core.agency.seelsupport._load_creds",
                        lambda: {"phone": "01044179416", "password": "Mike@2204"})
    # Also clear session cache to avoid test pollution
    monkeypatch.setitem(seelsupport._session_cache, "cookie", None)
    monkeypatch.setitem(seelsupport._session_cache, "token", "fake-token")


def _mock_response(json_data, status_code=200):
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = json.dumps(json_data)
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# Unconfigured state tests
# ---------------------------------------------------------------------------

def test_unconfigured_error(monkeypatch):
    # Temporarily remove creds mock
    monkeypatch.setattr("core.agency.seelsupport._load_creds", lambda: None)
    res = seel_fetch("tasks")
    assert "not configured" in res.lower()

    res = seel_create("tasks", {"title": "X"})
    assert "not configured" in res.lower()

    res = seel_update("tasks", 1, {"title": "X"})
    assert "not configured" in res.lower()

    res = seel_delete("tasks", 1)
    assert "not configured" in res.lower()

    # check_new_notifications should return empty list when unconfigured
    assert check_new_notifications() == []


# ---------------------------------------------------------------------------
# CRUD — seel_fetch
# ---------------------------------------------------------------------------

def test_fetch_all_tasks(monkeypatch):
    fake = [{"id": 1, "title": "TT", "status": "pending"}]
    monkeypatch.setattr("core.agency.seelsupport.httpx.request",
                        lambda method, url, **kw: _mock_response(fake))
    result = seel_fetch("tasks")
    assert isinstance(result, list) and result[0]["title"] == "TT"


def test_fetch_single_task(monkeypatch):
    fake = {"id": 1, "title": "TT"}
    monkeypatch.setattr("core.agency.seelsupport.httpx.request",
                        lambda method, url, **kw: _mock_response(fake))
    result = seel_fetch("tasks", item_id=1)
    assert result["id"] == 1


def test_fetch_graceful_on_error(monkeypatch):
    def _boom(method, url, **kw):
        raise Exception("network down")
    monkeypatch.setattr("core.agency.seelsupport.httpx.request", _boom)
    result = seel_fetch("tasks")
    assert "failed" in result.lower() or "error" in result.lower()


# ---------------------------------------------------------------------------
# CRUD — seel_create
# ---------------------------------------------------------------------------

def test_create_task(monkeypatch):
    fake = {"id": 5, "title": "New Task", "status": "pending"}
    monkeypatch.setattr("core.agency.seelsupport.httpx.request",
                        lambda method, url, **kw: _mock_response(fake, 201))
    result = seel_create("tasks", {"title": "New Task", "project_id": 1})
    assert result["id"] == 5


def test_create_graceful_on_error(monkeypatch):
    def _boom(method, url, **kw):
        raise Exception("server 500")
    monkeypatch.setattr("core.agency.seelsupport.httpx.request", _boom)
    result = seel_create("tasks", {"title": "X"})
    assert isinstance(result, str) and ("failed" in result.lower() or "error" in result.lower())


# ---------------------------------------------------------------------------
# CRUD — seel_update
# ---------------------------------------------------------------------------

def test_update_task(monkeypatch):
    fake = {"id": 1, "title": "Updated", "status": "in_progress"}
    monkeypatch.setattr("core.agency.seelsupport.httpx.request",
                        lambda method, url, **kw: _mock_response(fake))
    result = seel_update("tasks", 1, {"status": "in_progress"})
    assert result["status"] == "in_progress"


# ---------------------------------------------------------------------------
# CRUD — seel_delete
# ---------------------------------------------------------------------------

def test_delete_task(monkeypatch):
    monkeypatch.setattr("core.agency.seelsupport.httpx.request",
                        lambda method, url, **kw: _mock_response({"message": "deleted"}))
    result = seel_delete("tasks", 1)
    assert "deleted" in result.lower() or "success" in result.lower()


# ---------------------------------------------------------------------------
# Proactive — notification state tracking
# ---------------------------------------------------------------------------

def test_check_new_notifications_first_run(tmp_path, monkeypatch):
    state_file = tmp_path / "seel_state.json"
    monkeypatch.setattr("core.agency.seelsupport.STATE_PATH", str(state_file))
    notifications = [
        {"id": 3, "title": "New Ticket: X", "message": "Created by Y"},
        {"id": 2, "title": "New Task: Z", "message": "Admin created"},
        {"id": 1, "title": "New Project: A", "message": "Created"},
    ]
    monkeypatch.setattr("core.agency.seelsupport.httpx.request",
                        lambda method, url, **kw: _mock_response(notifications))
    new = check_new_notifications()
    # First run: all 3 are new.
    assert len(new) == 3
    # State should now be saved.
    assert state_file.exists()
    saved = json.loads(state_file.read_text())
    assert saved["last_notified_id"] == 3


def test_check_new_notifications_incremental(tmp_path, monkeypatch):
    state_file = tmp_path / "seel_state.json"
    state_file.write_text(json.dumps({"last_notified_id": 2}))
    monkeypatch.setattr("core.agency.seelsupport.STATE_PATH", str(state_file))
    notifications = [
        {"id": 4, "title": "Urgent", "message": "New urgent ticket"},
        {"id": 3, "title": "New Ticket: X", "message": "Created by Y"},
        {"id": 2, "title": "Old", "message": "Already seen"},
    ]
    monkeypatch.setattr("core.agency.seelsupport.httpx.request",
                        lambda method, url, **kw: _mock_response(notifications))
    new = check_new_notifications()
    # Only id 3 and 4 are new (> last_notified_id 2).
    assert len(new) == 2
    assert all(n["id"] > 2 for n in new)
    saved = json.loads(state_file.read_text())
    assert saved["last_notified_id"] == 4


def test_check_new_notifications_graceful_on_error(tmp_path, monkeypatch):
    monkeypatch.setattr("core.agency.seelsupport.STATE_PATH", str(tmp_path / "s.json"))
    def _boom(method, url, **kw):
        raise Exception("timeout")
    monkeypatch.setattr("core.agency.seelsupport.httpx.request", _boom)
    new = check_new_notifications()
    assert new == []


def test_import_tasks_from_file_unsafe_path():
    res = seelsupport.seel_import_tasks_from_file("/etc/passwd")
    assert "refused" in res.lower() or "not a safe" in res.lower()


def test_import_tasks_from_file_missing_file():
    res = seelsupport.seel_import_tasks_from_file("nonexistent_tasks_file.json")
    assert "does not exist" in res.lower()


def test_import_tasks_from_file_success(tmp_path, monkeypatch):
    test_file = tmp_path / "tasks.json"
    tasks_data = [
        {"title": "Task 1", "project_id": 2, "status": "completed"},
        {"title": "Task 2", "project_id": 2, "status": "pending"}
    ]
    test_file.write_text(json.dumps(tasks_data))
    
    # We must patch is_safe_path to allow our tmp_path or use a relative path
    # Since tmp_path is absolute, is_safe_path would normally reject it because of absolute path checks.
    # Let's mock is_safe_path to always return True for this test.
    monkeypatch.setattr("core.agency.seelsupport.is_safe_path", lambda path: True)

    created_ids = [101, 102]
    call_count = 0

    def _mock_post(method, url, **kw):
        nonlocal call_count
        item = tasks_data[call_count]
        res_data = {
            "id": created_ids[call_count],
            "title": item["title"],
            "project_id": item["project_id"],
            "status": item["status"]
        }
        call_count += 1
        return _mock_response(res_data, 201)

    monkeypatch.setattr("core.agency.seelsupport.httpx.request", _mock_post)

    res = seelsupport.seel_import_tasks_from_file(str(test_file))
    assert "successfully imported 2 tasks" in res.lower()
    assert call_count == 2

