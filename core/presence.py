"""User-presence state for camera-gated proactivity.

The webcam lives in the browser, so the browser reports presence here via
POST /api/presence. Proactivity reads is_present() and stays silent when the
user isn't recognized in front of the camera. Strict by default: if no fresh
"present" report exists, the user is considered absent.
"""
import time

# Reports older than this many seconds are stale → treated as absent.
PRESENCE_WINDOW = 15.0

_state = {"present": False, "ts": 0.0}


def set_presence(present, now=None):
    """Record a presence report from the browser."""
    _state["present"] = bool(present)
    _state["ts"] = float(now) if now is not None else time.time()


def is_present(now=None, window=PRESENCE_WINDOW):
    """True only if the latest report says present AND is fresh (within window)."""
    now = float(now) if now is not None else time.time()
    return bool(_state["present"]) and (now - _state["ts"]) <= window


def _reset():
    """Test helper: clear presence state."""
    _state["present"] = False
    _state["ts"] = 0.0
