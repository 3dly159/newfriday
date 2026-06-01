"""Pure proactive trigger evaluation. No LLM, no I/O — just scoring signals.
A candidate scoring >= THRESHOLD is worth surfacing (balanced cadence)."""

THRESHOLD = 0.6


def evaluate_triggers(ctx):
    """Score proactive candidates from a context dict. Returns a list of
    {kind, score, message_hint}, sorted by score descending."""
    cands = []
    vitals = ctx.get("vitals", {})
    battery = vitals.get("battery", 100)
    plugged = vitals.get("plugged", True)
    cpu = vitals.get("cpu_usage", 0)
    mem = vitals.get("memory_usage", 0)

    # --- vitals ---
    if battery <= 15 and not plugged:
        cands.append({"kind": "vitals", "score": 0.95,
                      "message_hint": f"Battery at {battery}% and unplugged."})
    elif battery <= 30 and not plugged:
        cands.append({"kind": "vitals", "score": 0.7,
                      "message_hint": f"Battery getting low ({battery}%)."})
    if cpu >= 90:
        cands.append({"kind": "vitals", "score": 0.72,
                      "message_hint": f"CPU sustained at {cpu}%."})
    if mem >= 90:
        cands.append({"kind": "vitals", "score": 0.7,
                      "message_hint": f"Memory pressure at {mem}%."})

    # --- time / routine ---
    hour = ctx.get("hour", 12)
    mins = ctx.get("minutes_since_interaction", 0)
    if 1 <= hour <= 4:
        cands.append({"kind": "time", "score": 0.62,
                      "message_hint": "It's quite late; suggest wrapping up."})
    if mins >= 120:
        cands.append({"kind": "time", "score": 0.66,
                      "message_hint": f"Idle for {mins} minutes; a gentle check-in."})

    # --- tasks / memory ---
    active = [t for t in ctx.get("tasks", []) if t.get("status") in ("active", "pending")]
    if active:
        cands.append({"kind": "tasks", "score": 0.64,
                      "message_hint": f"{len(active)} task(s) still open."})

    # --- web / world (the fetch itself happens in proactive.py) ---
    topic = ctx.get("last_topic")
    if topic:
        cands.append({"kind": "web", "score": 0.61,
                      "message_hint": f"Could look up more on '{topic}'."})

    cands.sort(key=lambda c: c["score"], reverse=True)
    return cands
