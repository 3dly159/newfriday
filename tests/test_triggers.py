from core.triggers import evaluate_triggers, THRESHOLD


def _ctx(**kw):
    base = {"vitals": {"cpu_usage": 10, "memory_usage": 30, "battery": 80, "plugged": True},
            "tasks": [], "hour": 15, "idle_seconds": 60, "minutes_since_interaction": 5,
            "last_topic": None}
    base.update(kw)
    return base


def test_low_battery_unplugged_fires_high():
    cands = evaluate_triggers(_ctx(vitals={"cpu_usage": 5, "memory_usage": 20, "battery": 8, "plugged": False}))
    batt = [c for c in cands if c["kind"] == "vitals"]
    assert batt and batt[0]["score"] >= THRESHOLD


def test_all_quiet_produces_nothing_actionable():
    cands = evaluate_triggers(_ctx())
    assert all(c["score"] < THRESHOLD for c in cands)


def test_pending_tasks_trigger():
    cands = evaluate_triggers(_ctx(tasks=[{"name": "Ghost", "status": "active"}]))
    assert any(c["kind"] == "tasks" for c in cands)


def test_late_night_trigger():
    cands = evaluate_triggers(_ctx(hour=3))
    assert any(c["kind"] == "time" for c in cands)


def test_long_idle_trigger():
    cands = evaluate_triggers(_ctx(minutes_since_interaction=180))
    assert any(c["kind"] == "time" and "idle" in c["message_hint"].lower() for c in cands)


def test_web_topic_trigger_flagged():
    cands = evaluate_triggers(_ctx(last_topic="quantum computing"))
    assert any(c["kind"] == "web" for c in cands)


def test_results_sorted_by_score_desc():
    cands = evaluate_triggers(_ctx(vitals={"cpu_usage": 99, "memory_usage": 95, "battery": 5, "plugged": False},
                                    tasks=[{"name": "x", "status": "active"}], hour=3))
    scores = [c["score"] for c in cands]
    assert scores == sorted(scores, reverse=True)
