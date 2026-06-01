"""Regression tests: task ops must not crash on tasks lacking an 'id'
(quest.py rebuilds the task layer without ids). See KeyError: 'id' in update_task."""
import os
import tempfile
import pytest

from core.memory import FridayMemory


@pytest.fixture
def mem(tmp_path):
    storage = tmp_path / "memory.json"
    vdb = tmp_path / "vdb"
    m = FridayMemory(storage_path=str(storage), vector_db_path=str(vdb))
    return m


def test_update_task_ignores_idless_tasks(mem):
    # A quest-style task with no 'id' key, plus a normal one.
    mem.layers["task"] = [
        {"name": "Ghost in the Machine", "desc": "quest", "status": "active"},
        {"id": "0", "name": "Buy milk", "desc": "x", "status": "pending"},
    ]
    # Must not raise, and must update the matching task.
    result = mem.update_task("0", status="completed")
    assert "updated" in result.lower()
    assert mem.layers["task"][1]["status"] == "completed"


def test_update_task_missing_returns_not_found(mem):
    mem.layers["task"] = [{"name": "idless", "desc": "x", "status": "active"}]
    result = mem.update_task("nope", status="done")
    assert "not found" in result.lower()


def test_delete_task_ignores_idless_tasks(mem):
    mem.layers["task"] = [
        {"name": "idless quest", "desc": "x", "status": "active"},
        {"id": "5", "name": "real", "desc": "y", "status": "pending"},
    ]
    result = mem.delete_task("5")
    assert "deleted" in result.lower()
    # The id-less task survives; the real one is gone.
    assert len(mem.layers["task"]) == 1
    assert mem.layers["task"][0]["name"] == "idless quest"
