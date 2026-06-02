"""Pure conversation helpers (kept tiny + testable for latency work)."""


def trim_history(messages, max_turns=12):
    """Return at most the last `max_turns` messages, preserving order.
    Caps the episodic history sent to the LLM to reduce input tokens."""
    if max_turns <= 0:
        return []
    return messages[-max_turns:] if len(messages) > max_turns else messages
