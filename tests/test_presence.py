"""Tests for camera-presence gating state (core/presence.py)."""
import pytest
from core import presence


@pytest.fixture(autouse=True)
def _clean():
    presence._reset()
    yield
    presence._reset()


def test_absent_by_default():
    assert presence.is_present(now=1000) is False


def test_present_when_fresh():
    presence.set_presence(True, now=1000)
    assert presence.is_present(now=1005) is True


def test_stale_report_is_absent():
    presence.set_presence(True, now=1000)
    # Beyond the window → treated as absent (strict).
    assert presence.is_present(now=1000 + presence.PRESENCE_WINDOW + 1) is False


def test_explicit_absent_report():
    presence.set_presence(True, now=1000)
    presence.set_presence(False, now=1001)
    assert presence.is_present(now=1002) is False


def test_window_boundary_inclusive():
    presence.set_presence(True, now=1000)
    assert presence.is_present(now=1000 + presence.PRESENCE_WINDOW) is True
