"""Typed builders for the FRIDAY v2 WebSocket event contract (server -> UI)."""


def state_event(state):
    return {"type": "state", "state": state}


def transcript_event(role, text, final):
    return {"type": "transcript", "role": role, "text": text, "final": final}


def caption_event(segment_id, words, text, mode=None):
    # Default to word-sync when timings exist, otherwise sentence fade.
    if mode is None:
        mode = "word" if words else "sentence"
    return {
        "type": "caption",
        "segment_id": segment_id,
        "mode": mode,
        "words": words,
        "text": text,
    }


def action_event(tool, phase, label):
    return {"type": "action", "tool": tool, "phase": phase, "label": label}


def mood_event(mood, orb_color):
    return {"type": "mood", "mood": mood, "orb_color": orb_color}


def approval_event(category):
    """Friday is asking the user to grant a gated permission (e.g. hid_control)."""
    return {"type": "approval", "category": category}
