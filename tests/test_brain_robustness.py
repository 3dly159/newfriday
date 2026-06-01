"""Regression tests for the Ollama tool-call 'id' crash, honest error
classification, and the approval marker — all pure, no network."""
import httpx
import pytest
from core.brain import FridayBrain


@pytest.fixture
def brain():
    return FridayBrain()


def test_approval_marker_detects_pending(brain):
    assert brain._approval_marker("PENDING_APPROVAL: hid_control") == "[Approval: hid_control]"
    assert brain._approval_marker("PENDING_APPROVAL: script_execution") == "[Approval: script_execution]"


def test_approval_marker_ignores_normal_results(brain):
    assert brain._approval_marker("Clicked") is None
    assert brain._approval_marker({"stdout": "ok"}) is None
    assert brain._approval_marker(None) is None


def test_connection_errors_classified(brain):
    assert brain._is_connection_error(httpx.ConnectError("refused")) is True
    assert brain._is_connection_error(ConnectionError()) is True
    assert brain._is_connection_error(TimeoutError()) is True


def test_internal_errors_not_blamed_on_server(brain):
    # KeyError('id') is the bug that used to be mislabeled as "Ollama down".
    assert brain._is_connection_error(KeyError("id")) is False
    assert brain._is_connection_error(TypeError("x")) is False


def test_error_messages_differ_by_cause(brain):
    conn = brain._error_message(httpx.ConnectError("x"))
    bug = brain._error_message(KeyError("id"))
    assert "responding" in conn or "uplink" in conn or "unreachable" in conn
    assert "internal snag" in bug
    assert conn != bug
