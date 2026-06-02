from datetime import datetime
from core.scheduler import parse_when, due_entries, next_run


def test_parse_when_relative_minutes():
    now = datetime(2026, 1, 1, 12, 0, 0)
    out = parse_when("in 20m", now)
    assert out == datetime(2026, 1, 1, 12, 20, 0).isoformat()


def test_parse_when_relative_hours():
    now = datetime(2026, 1, 1, 12, 0, 0)
    assert parse_when("in 2h", now) == datetime(2026, 1, 1, 14, 0, 0).isoformat()


def test_parse_when_at_time_today():
    now = datetime(2026, 1, 1, 8, 0, 0)
    assert parse_when("at 17:00", now) == datetime(2026, 1, 1, 17, 0, 0).isoformat()


def test_parse_when_at_time_rolls_to_tomorrow():
    now = datetime(2026, 1, 1, 18, 0, 0)
    assert parse_when("at 09:00", now) == datetime(2026, 1, 2, 9, 0, 0).isoformat()


def test_parse_when_daily_recurring():
    assert parse_when("daily at 07:30", datetime(2026, 1, 1, 0, 0, 0)) == "daily@07:30"


def test_due_entries_fires_past_once():
    now = datetime(2026, 1, 1, 12, 0, 0)
    entries = [{"id": "1", "kind": "once", "when": datetime(2026, 1, 1, 11, 0, 0).isoformat(),
                "text": "ping", "last_run": None}]
    due = due_entries(entries, now)
    assert len(due) == 1 and due[0]["id"] == "1"


def test_due_entries_skips_future_once():
    now = datetime(2026, 1, 1, 12, 0, 0)
    entries = [{"id": "1", "kind": "once", "when": datetime(2026, 1, 1, 13, 0, 0).isoformat(),
                "text": "x", "last_run": None}]
    assert due_entries(entries, now) == []


def test_due_entries_recurring_daily_once_per_day():
    now = datetime(2026, 1, 1, 7, 30, 0)
    e = {"id": "2", "kind": "recurring", "when": "daily@07:30", "text": "brief", "last_run": None}
    assert len(due_entries([e], now)) == 1
    e["last_run"] = now.isoformat()
    # Same day, already ran -> not due again.
    assert due_entries([e], datetime(2026, 1, 1, 7, 31, 0)) == []
    # Next day -> due again.
    assert len(due_entries([e], datetime(2026, 1, 2, 7, 30, 0))) == 1
